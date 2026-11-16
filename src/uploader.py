"""
YouTube Data API v3 Auto-Uploader Module
Handles OAuth2 Refresh Token authentication, resumable video uploading,
metadata synchronization, and custom thumbnail attachment with Dry Run simulation.
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.config import Config

logger = logging.getLogger("youtube_agent.upload")


def get_authenticated_service(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    refresh_token: Optional[str] = None,
):
    """Build and return an authorized YouTube Data API service instance."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    cid = client_id or Config.YOUTUBE_CLIENT_ID
    csec = client_secret or Config.YOUTUBE_CLIENT_SECRET
    rtoken = refresh_token or Config.YOUTUBE_REFRESH_TOKEN

    if not cid or not csec or not rtoken:
        raise ValueError(
            "Missing YouTube OAuth credentials. Ensure YOUTUBE_CLIENT_ID, "
            "YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN are set in .env "
            "or run `python get_youtube_token.py`."
        )

    credentials = Credentials(
        token=None,
        refresh_token=rtoken,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cid,
        client_secret=csec,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    return build("youtube", "v3", credentials=credentials)


def upload_thumbnail(youtube_service, video_id: str, thumbnail_path: Path):
    """Upload and attach a custom thumbnail to an uploaded YouTube video."""
    from googleapiclient.http import MediaFileUpload

    if not thumbnail_path.is_file():
        logger.warning(f"Thumbnail file '{thumbnail_path}' not found. Skipping thumbnail upload.")
        return

    logger.info(f"Setting custom thumbnail for video {video_id}: {thumbnail_path.name}...")
    try:
        media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg", resumable=False)
        request = youtube_service.thumbnails().set(videoId=video_id, media_body=media)
        request.execute()
        logger.info(f"Thumbnail successfully attached to video {video_id}!")
    except Exception as e:
        logger.error(f"Failed to attach thumbnail: {e}")


def upload_video_to_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    thumbnail_path: Optional[Path] = None,
    privacy_status: Optional[str] = None,
    category_id: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> Dict[str, Any]:
    """Upload video to YouTube with metadata and thumbnail, or simulate if dry_run=True."""
    is_dry = Config.DRY_RUN if dry_run is None else dry_run
    privacy = (privacy_status or Config.YOUTUBE_PRIVACY_STATUS or "private").lower()
    category = category_id or Config.YOUTUBE_CATEGORY_ID or "27"

    # Truncate title to YouTube limit (100 chars, ideally < 70)
    safe_title = title.strip()[:100]

    # DRY RUN Simulation Mode
    if is_dry:
        logger.info("=" * 60)
        logger.info("🚀 DRY_RUN MODE ACTIVE: Skipping actual YouTube upload.")
        logger.info("=" * 60)
        logger.info(f"📁 Video File:        {video_path} (exists: {video_path.is_file()})")
        if video_path.is_file():
            size_mb = video_path.stat().st_size / (1024 * 1024)
            logger.info(f"   Size:              {size_mb:.2f} MB")
        logger.info(f"🖼️  Thumbnail File:    {thumbnail_path} (exists: {thumbnail_path.is_file() if thumbnail_path else False})")
        logger.info(f"📌 Title:             {safe_title}")
        logger.info(f"🔒 Privacy Status:    {privacy}")
        logger.info(f"🏷️  Category ID:       {category}")
        logger.info(f"🏷️  Tags ({len(tags)}):       {', '.join(tags[:6])}...")
        logger.info(f"📝 Description:\n{'-'*40}\n{description[:300]}...\n{'-'*40}")
        logger.info("✅ Dry Run completed successfully without API requests.")

        return {
            "status": "dry_run",
            "video_id": "DRY_RUN_VIDEO_ID_12345",
            "url": "https://youtu.be/DRY_RUN_VIDEO_ID_12345",
            "title": safe_title,
            "privacy": privacy,
            "service": None,
        }

    # Live YouTube Upload
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file to upload does not exist: {video_path}")

    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": safe_title,
            "description": description,
            "tags": tags,
            "categoryId": category,
            "defaultLanguage": "ur" if Config.LANGUAGE == "urdu" else ("hi" if Config.LANGUAGE == "hindi" else "en"),
            "defaultAudioLanguage": "ur" if Config.LANGUAGE == "urdu" else ("hi" if Config.LANGUAGE == "hindi" else "en"),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    # 10MB chunk size for resumable upload
    chunk_size = 10 * 1024 * 1024
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=chunk_size,
        resumable=True,
    )

    logger.info(f"Initiating YouTube resumable upload for '{safe_title}'...")
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    retry_count = 0
    max_retries = 5

    while response is None:
        try:
            status, response = insert_request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Upload progress: {progress}%")
        except HttpError as err:
            if err.resp.status in [500, 502, 503, 504] and retry_count < max_retries:
                retry_count += 1
                wait_sec = 2 ** retry_count
                logger.warning(f"Transient HTTP error {err.resp.status}. Retrying in {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                raise

    video_id = response.get("id")
    video_url = f"https://youtu.be/{video_id}"
    logger.info(f"🎉 Video successfully uploaded! ID: {video_id} -> {video_url}")

    # Attach thumbnail if provided
    if thumbnail_path and thumbnail_path.is_file():
        upload_thumbnail(youtube, video_id, thumbnail_path)

    return {
        "status": "published",
        "video_id": video_id,
        "url": video_url,
        "title": safe_title,
        "privacy": privacy,
        "service": youtube,
    }


def upload_teaser_short_to_youtube(
    teaser_video_path: Path,
    title: str,
    main_video_url: str,
    privacy_status: Optional[str] = None,
    category_id: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> Dict[str, Any]:
    """Upload vertical 9:16 teaser Short to YouTube with #Shorts tag."""
    short_title = f"{title[:80]} #Shorts"
    short_desc = (
        f"Watch the full investigative documentary here: {main_video_url}\n\n"
        f"Subscribe for more untold mysteries!\n\n#Shorts #Documentary #Mystery"
    )

    logger.info(f"Preparing YouTube Short upload: '{short_title}'...")
    return upload_video_to_youtube(
        video_path=teaser_video_path,
        title=short_title,
        description=short_desc,
        tags=["Shorts", "YouTubeShorts", "Mystery", "Documentary"],
        thumbnail_path=None,  # YouTube Shorts auto-generate from frames
        privacy_status=privacy_status,
        category_id=category_id,
        dry_run=dry_run,
    )
