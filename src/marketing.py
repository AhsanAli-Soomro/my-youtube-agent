"""
Multi-Platform Auto-Marketing & Social Distribution Engine
Automates distribution of promotional copy and visual assets across:
1. YouTube Pinned Comment (via YouTube Data API v3)
2. Facebook Page (via Facebook Graph API v19.0)
3. X / Twitter Mystery Thread (via X API v2)
4. Telegram Channel Broadcast (via Telegram Bot API)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from src.config import Config

logger = logging.getLogger("youtube_agent.marketing")


def post_youtube_pinned_comment(youtube_service, video_id: str, comment_text: str) -> Optional[str]:
    """Post an engaging discussion starter comment on the newly uploaded YouTube video."""
    if not comment_text or not comment_text.strip():
        logger.debug("No YouTube comment text provided. Skipping.")
        return None

    try:
        logger.info(f"Posting engagement comment on YouTube video {video_id}...")
        body = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": comment_text.strip()
                    }
                }
            }
        }
        response = youtube_service.commentThreads().insert(
            part="snippet",
            body=body,
        ).execute()
        comment_id = response.get("id")
        logger.info(f"✅ YouTube comment posted successfully (ID: {comment_id})")
        return comment_id
    except Exception as err:
        logger.warning(f"Failed to post YouTube comment: {err}")
        return None


def post_to_facebook_page(
    page_id: str,
    access_token: str,
    message: str,
    video_url: str,
    thumbnail_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Post thumbnail and storytelling hook to Facebook Page via Facebook Graph API."""
    if not page_id or not access_token:
        logger.info("Facebook Page credentials not configured. Skipping Facebook post.")
        return None

    caption = f"{message.strip()}\n\n🎬 Watch the full documentary here: {video_url}"
    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"

    try:
        logger.info(f"Posting promotional update to Facebook Page {page_id}...")
        with httpx.Client(timeout=30.0) as client:
            if thumbnail_path and thumbnail_path.is_file():
                with open(thumbnail_path, "rb") as img_file:
                    files = {"source": (thumbnail_path.name, img_file, "image/jpeg")}
                    data = {"caption": caption, "access_token": access_token}
                    resp = client.post(url, data=data, files=files)
            else:
                feed_url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
                resp = client.post(feed_url, data={"message": caption, "access_token": access_token})

            if resp.status_code in [200, 201]:
                result = resp.json()
                logger.info(f"✅ Facebook post published successfully (ID: {result.get('id')})")
                return result
            else:
                logger.warning(f"Facebook Graph API returned error {resp.status_code}: {resp.text}")
                return None
    except Exception as err:
        logger.warning(f"Error publishing to Facebook: {err}")
        return None


def post_twitter_thread(
    tweets: List[str],
    video_url: str,
    api_key: str,
    api_secret: str,
    access_token: str,
    access_secret: str,
) -> Optional[List[str]]:
    """Post an episodic suspense thread on X (Twitter) using X API v2."""
    if not api_key or not api_secret or not access_token or not access_secret:
        logger.info("X (Twitter) API credentials not configured. Skipping X thread.")
        return None

    if not tweets:
        logger.debug("No tweets found in thread copy. Skipping X thread.")
        return None

    try:
        import tweepy

        logger.info(f"Posting {len(tweets)}-tweet thread on X (Twitter)...")
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )

        tweet_ids = []
        previous_id = None

        for idx, text in enumerate(tweets):
            tweet_content = text.strip()
            # Append video URL to the final tweet
            if idx == len(tweets) - 1:
                tweet_content += f"\n\nWatch the full documentary: {video_url}"

            # Ensure tweet length stays under 280 characters
            if len(tweet_content) > 275:
                tweet_content = tweet_content[:270] + "..."

            response = client.create_tweet(
                text=tweet_content,
                in_reply_to_tweet_id=previous_id,
            )
            tweet_id = response.data.get("id")
            tweet_ids.append(tweet_id)
            previous_id = tweet_id

        logger.info(f"✅ X thread published successfully ({len(tweet_ids)} tweets linked)")
        return tweet_ids
    except Exception as err:
        logger.warning(f"Error posting to X (Twitter): {err}")
        return None


def post_telegram_broadcast(
    bot_token: str,
    chat_id: str,
    caption_text: str,
    video_url: str,
    thumbnail_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Broadcast formatted announcement to a Telegram Channel via Telegram Bot API."""
    if not bot_token or not chat_id:
        logger.info("Telegram Bot credentials not configured. Skipping Telegram broadcast.")
        return None

    message = f"{caption_text.strip()}\n\n🎬 *Watch Full Documentary:*\n{video_url}"

    try:
        logger.info(f"Broadcasting update to Telegram Channel ({chat_id})...")
        with httpx.Client(timeout=30.0) as client:
            if thumbnail_path and thumbnail_path.is_file():
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                with open(thumbnail_path, "rb") as img_file:
                    files = {"photo": (thumbnail_path.name, img_file, "image/jpeg")}
                    data = {
                        "chat_id": chat_id,
                        "caption": message[:1024],  # Telegram photo caption max 1024 chars
                        "parse_mode": "Markdown",
                    }
                    resp = client.post(url, data=data, files=files)
            else:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                resp = client.post(url, json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                })

            if resp.status_code == 200:
                result = resp.json()
                logger.info("✅ Telegram broadcast published successfully!")
                return result
            else:
                logger.warning(f"Telegram Bot API error {resp.status_code}: {resp.text}")
                return None
    except Exception as err:
        logger.warning(f"Error broadcasting to Telegram: {err}")
        return None


def run_marketing_campaign(
    video_id: str,
    video_url: str,
    youtube_pinned_comment: str,
    facebook_post: str,
    twitter_thread: List[str],
    telegram_post: str,
    thumbnail_path: Optional[Path],
    output_dir: Path,
    youtube_service=None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Execute full multi-platform marketing campaign:
    - Generates output/marketing_preview.json
    - Simulates distribution in DRY_RUN mode
    - Posts live updates across enabled platforms in live mode
    """
    campaign_preview = {
        "video_id": video_id,
        "video_url": video_url,
        "youtube_pinned_comment": youtube_pinned_comment,
        "facebook_post": facebook_post,
        "twitter_thread": twitter_thread,
        "telegram_post": telegram_post,
        "dry_run": dry_run,
    }

    # Save marketing preview JSON
    preview_file = output_dir / "marketing_preview.json"
    with open(preview_file, "w", encoding="utf-8") as f:
        json.dump(campaign_preview, f, ensure_ascii=False, indent=2)

    logger.info(f"💾 Saved marketing campaign preview to: {preview_file.name}")

    results = {
        "preview_file": str(preview_file),
        "platforms": {},
    }

    # DRY RUN Simulation
    if dry_run:
        logger.info("=" * 65)
        logger.info("📢 DRY_RUN MODE: Multi-Platform Marketing Simulation")
        logger.info("=" * 65)
        logger.info(f"💬 YouTube Comment:  {youtube_pinned_comment[:100]}...")
        logger.info(f"📘 Facebook Post:    {facebook_post[:100]}...")
        logger.info(f"🐦 X Thread ({len(twitter_thread)}):    {twitter_thread[0][:80] if twitter_thread else 'N/A'}...")
        logger.info(f"✈️  Telegram Post:    {telegram_post[:100]}...")
        logger.info("✅ Marketing simulation complete. No external APIs called.")

        results["platforms"] = {
            "youtube_comment": "simulated",
            "facebook": "simulated",
            "twitter": "simulated",
            "telegram": "simulated",
        }
        return results

    # Live Distribution
    # 1. YouTube Pinned Comment
    if Config.ENABLE_YOUTUBE_COMMENT and youtube_service and video_id:
        c_id = post_youtube_pinned_comment(youtube_service, video_id, youtube_pinned_comment)
        results["platforms"]["youtube_comment"] = c_id or "failed"

    # 2. Facebook Page Post
    if Config.ENABLE_FACEBOOK_POST:
        fb_res = post_to_facebook_page(
            page_id=Config.FACEBOOK_PAGE_ID,
            access_token=Config.FACEBOOK_PAGE_ACCESS_TOKEN,
            message=facebook_post,
            video_url=video_url,
            thumbnail_path=thumbnail_path,
        )
        results["platforms"]["facebook"] = "success" if fb_res else "skipped_or_failed"

    # 3. X (Twitter) Thread
    if Config.ENABLE_TWITTER_THREAD:
        tw_res = post_twitter_thread(
            tweets=twitter_thread,
            video_url=video_url,
            api_key=Config.TWITTER_API_KEY,
            api_secret=Config.TWITTER_API_SECRET,
            access_token=Config.TWITTER_ACCESS_TOKEN,
            access_secret=Config.TWITTER_ACCESS_SECRET,
        )
        results["platforms"]["twitter"] = "success" if tw_res else "skipped_or_failed"

    # 4. Telegram Broadcast
    if Config.ENABLE_TELEGRAM_BROADCAST:
        tg_res = post_telegram_broadcast(
            bot_token=Config.TELEGRAM_BOT_TOKEN,
            chat_id=Config.TELEGRAM_CHAT_ID,
            caption_text=telegram_post,
            video_url=video_url,
            thumbnail_path=thumbnail_path,
        )
        results["platforms"]["telegram"] = "success" if tg_res else "skipped_or_failed"

    return results
