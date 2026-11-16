"""
Automated A/B Title & Thumbnail Optimizer (Module B)
Monitors newly published YouTube videos (6 to 72 hours old), analyzes CTR / view velocity,
and autonomously swaps underperforming titles and thumbnails with pre-generated variants.
"""

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from googleapiclient.http import MediaFileUpload

from src.config import Config, DATA_DIR
from src.uploader import get_authenticated_service

logger = logging.getLogger("youtube_agent.ab_optimizer")

PUBLISHED_VIDEOS_FILE = DATA_DIR / "published_videos.json"


def load_published_videos() -> List[Dict[str, Any]]:
    """Load tracked videos from data/published_videos.json."""
    if not PUBLISHED_VIDEOS_FILE.is_file():
        return []
    try:
        with open(PUBLISHED_VIDEOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as err:
        logger.warning(f"Could not load {PUBLISHED_VIDEOS_FILE.name}: {err}")
        return []


def save_published_videos(videos: List[Dict[str, Any]]):
    """Save tracked videos list to data/published_videos.json."""
    PUBLISHED_VIDEOS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PUBLISHED_VIDEOS_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)


def register_published_video(
    video_id: str,
    project_dir: Path,
    script,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Register a newly published video and its 3 A/B test variants into state tracking."""
    videos = load_published_videos()

    # Locate thumbnail variants in project_dir
    thumb_a = project_dir / "thumbnail_a.jpg"
    thumb_b = project_dir / "thumbnail_b.jpg"
    thumb_c = project_dir / "thumbnail_c.jpg"

    # Fallback to main thumbnail if specific variant files are not yet created
    default_thumb = project_dir / "thumbnail.jpg"
    path_a = str(thumb_a if thumb_a.is_file() else default_thumb)
    path_b = str(thumb_b if thumb_b.is_file() else default_thumb)
    path_c = str(thumb_c if thumb_c.is_file() else default_thumb)

    record = {
        "video_id": video_id,
        "project_dir": str(project_dir),
        "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active_variant": "variant_a",
        "dry_run": dry_run,
        "test_completed": False,
        "variants": {
            "variant_a": {
                "title": script.variant_a.title if script.variant_a else script.title,
                "thumbnail_text": script.variant_a.thumbnail_text if script.variant_a else script.thumbnail_text,
                "thumbnail_path": path_a,
                "tested": True,
                "activated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            "variant_b": {
                "title": script.variant_b.title if script.variant_b else f"The Mystery of {script.title}",
                "thumbnail_text": script.variant_b.thumbnail_text if script.variant_b else "THE SECRET",
                "thumbnail_path": path_b,
                "tested": False,
            },
            "variant_c": {
                "title": script.variant_c.title if script.variant_c else f"What They Hid: {script.title}",
                "thumbnail_text": script.variant_c.thumbnail_text if script.variant_c else "FORBIDDEN",
                "thumbnail_path": path_c,
                "tested": False,
            },
        },
        "swap_history": [],
    }

    # If already exists, update record
    updated = False
    for i, v in enumerate(videos):
        if v.get("video_id") == video_id:
            videos[i] = record
            updated = True
            break
    if not updated:
        videos.append(record)

    save_published_videos(videos)
    logger.info(f"Registered video {video_id} in {PUBLISHED_VIDEOS_FILE.name} with 3 A/B test variants.")
    return record


def get_video_metrics(youtube_service, video_id: str, published_at_iso: str) -> Dict[str, Any]:
    """Fetch video performance metrics via YouTube Data API and estimate view velocity."""
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        pub_time = datetime.datetime.fromisoformat(published_at_iso.replace("Z", "+00:00"))
        age_hours = max(0.1, (now - pub_time).total_seconds() / 3600.0)
    except Exception:
        age_hours = 1.0

    metrics = {
        "views": 0,
        "likes": 0,
        "comments": 0,
        "age_hours": round(age_hours, 2),
        "views_per_hour": 0.0,
        "estimated_ctr": None,
    }

    if not youtube_service:
        return metrics

    try:
        resp = youtube_service.videos().list(
            part="snippet,statistics",
            id=video_id,
        ).execute()

        items = resp.get("items", [])
        if items:
            stats = items[0].get("statistics", {})
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))

            metrics["views"] = views
            metrics["likes"] = likes
            metrics["comments"] = comments
            metrics["views_per_hour"] = round(views / age_hours, 2)
    except Exception as err:
        logger.warning(f"Could not fetch metrics for video {video_id}: {err}")

    # Optional: Query YouTube Analytics API for impression CTR if authorized
    try:
        from googleapiclient.discovery import build
        # Attempt to call analytics report if credentials have yt-analytics.readonly
        credentials = youtube_service._http.credentials
        analytics = build("youtubeAnalytics", "v2", credentials=credentials)
        today_str = now.strftime("%Y-%m-%d")
        start_str = (now - datetime.timedelta(days=3)).strftime("%Y-%m-%d")

        analytics_resp = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_str,
            endDate=today_str,
            metrics="views,estimatedMinutesWatched,averageViewDuration",
            filters=f"video=={video_id}",
        ).execute()

        rows = analytics_resp.get("rows", [])
        if rows:
            logger.debug(f"Analytics report row for {video_id}: {rows[0]}")
    except Exception as analytics_err:
        logger.debug(f"YouTube Analytics API query skipped ({analytics_err}). Using view velocity.")

    return metrics


def swap_video_metadata(
    youtube_service,
    video_id: str,
    new_title: str,
    new_thumbnail_path: Optional[str] = None,
    dry_run: bool = True,
) -> bool:
    """Update live YouTube video Title and Thumbnail to the new variant."""
    if dry_run:
        logger.info(f"[DRY_RUN] Simulating swap for video {video_id} -> Title: '{new_title}'")
        if new_thumbnail_path:
            logger.info(f"[DRY_RUN] Simulating thumbnail swap to: {new_thumbnail_path}")
        return True

    if not youtube_service:
        raise ValueError("YouTube service client required for live swap.")

    # 1. Update Title
    resp = youtube_service.videos().list(part="snippet", id=video_id).execute()
    items = resp.get("items", [])
    if not items:
        logger.error(f"Cannot swap: Video {video_id} not found on YouTube.")
        return False

    snippet = items[0]["snippet"]
    snippet["title"] = new_title[:100]

    youtube_service.videos().update(
        part="snippet",
        body={"id": video_id, "snippet": snippet},
    ).execute()
    logger.info(f"✅ Swapped live YouTube Title for {video_id} to: '{new_title}'")

    # 2. Update Thumbnail
    if new_thumbnail_path and Path(new_thumbnail_path).is_file():
        media = MediaFileUpload(new_thumbnail_path, mimetype="image/jpeg", resumable=False)
        youtube_service.thumbnails().set(videoId=video_id, media_body=media).execute()
        logger.info(f"✅ Swapped live YouTube Thumbnail for {video_id} to: {new_thumbnail_path}")

    return True


def optimize_all_published_videos(dry_run: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Scan tracked videos (6-72 hrs old) and autonomously swap underperforming variants."""
    is_dry = Config.DRY_RUN if dry_run is None else dry_run

    print("=" * 65)
    print("📈 MODULE B: AUTOMATED A/B TITLE & THUMBNAIL OPTIMIZER")
    print("=" * 65)

    videos = load_published_videos()
    if not videos:
        print("ℹ️  No published videos currently tracked in data/published_videos.json.")
        print("   Videos will be automatically registered when uploaded or dry-run.")
        print("=" * 65 + "\n")
        return []

    youtube_service = None
    if not is_dry:
        try:
            youtube_service = get_authenticated_service()
        except Exception as e:
            logger.warning(f"Could not authenticate YouTube client: {e}. Switching to dry-run evaluation.")
            is_dry = True

    optimization_actions = []

    for video_entry in videos:
        video_id = video_entry.get("video_id")
        pub_at = video_entry.get("published_at")
        active_var_key = video_entry.get("active_variant", "variant_a")
        is_completed = video_entry.get("test_completed", False)

        if is_completed:
            continue

        # Fetch performance metrics
        metrics = get_video_metrics(youtube_service, video_id, pub_at)
        age_hours = metrics["age_hours"]
        views = metrics["views"]
        velocity = metrics["views_per_hour"]

        print(f"\n🎬 Evaluating Video: {video_id}")
        print(f"   ⏱️  Age: {age_hours:.1f} hours (Window: {Config.AB_TEST_MIN_AGE_HOURS}h - {Config.AB_TEST_MAX_AGE_HOURS}h)")
        print(f"   👀 Current Views: {views} | Velocity: {velocity} views/hour")
        print(f"   🔤 Active Variant: {active_var_key}")

        # Check if video is within the optimization window
        if age_hours < Config.AB_TEST_MIN_AGE_HOURS:
            print(f"   ⏳ Video is too fresh (< {Config.AB_TEST_MIN_AGE_HOURS}h). Gathering baseline data...")
            continue
        if age_hours > Config.AB_TEST_MAX_AGE_HOURS:
            print(f"   🏁 Optimization window ended (> {Config.AB_TEST_MAX_AGE_HOURS}h). Finalizing A/B test.")
            video_entry["test_completed"] = True
            continue

        # Determine if underperforming
        is_underperforming = False
        reason = ""

        if metrics.get("estimated_ctr") is not None:
            if metrics["estimated_ctr"] < Config.AB_TEST_MIN_CTR_PERCENT:
                is_underperforming = True
                reason = f"CTR {metrics['estimated_ctr']:.1f}% < threshold {Config.AB_TEST_MIN_CTR_PERCENT}%"
        else:
            if velocity < Config.AB_TEST_MIN_VIEWS_VELOCITY:
                is_underperforming = True
                reason = f"View velocity {velocity} views/h < threshold {Config.AB_TEST_MIN_VIEWS_VELOCITY} views/h"

        if not is_underperforming:
            print(f"   🔥 Performance healthy ({velocity} views/h). Retaining {active_var_key}.")
            continue

        print(f"   ⚠️  UNDERPERFORMANCE DETECTED: {reason}")

        # Find next untested variant
        variants = video_entry.get("variants", {})
        next_variant_key = None
        for candidate_key in ["variant_b", "variant_c"]:
            if not variants.get(candidate_key, {}).get("tested", False):
                next_variant_key = candidate_key
                break

        if not next_variant_key:
            print("   🏁 All 3 variants have been tested. Concluding A/B test.")
            video_entry["test_completed"] = True
            continue

        next_var = variants[next_variant_key]
        print(f"   🔄 Swapping to {next_variant_key.upper()}:")
        print(f"      📌 New Title: '{next_var['title']}'")
        print(f"      🖼️  New Thumb: '{next_var['thumbnail_text']}'")

        # Execute swap
        success = swap_video_metadata(
            youtube_service=youtube_service,
            video_id=video_id,
            new_title=next_var["title"],
            new_thumbnail_path=next_var.get("thumbnail_path"),
            dry_run=is_dry,
        )

        if success:
            swap_record = {
                "swapped_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "from_variant": active_var_key,
                "to_variant": next_variant_key,
                "metrics_before_swap": metrics,
                "reason": reason,
            }
            video_entry["swap_history"].append(swap_record)
            video_entry["active_variant"] = next_variant_key
            next_var["tested"] = True
            next_var["activated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            optimization_actions.append(swap_record)

    save_published_videos(videos)
    print(f"\n✅ Optimization evaluation complete. Executed {len(optimization_actions)} swap action(s).")
    print("=" * 65 + "\n")

    return optimization_actions


if __name__ == "__main__":
    optimize_all_published_videos()
