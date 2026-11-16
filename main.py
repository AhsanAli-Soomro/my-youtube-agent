#!/usr/bin/env python3
"""
Automated Documentary YouTube Video Creator, Uploader & Multi-Platform Marketing Agent
End-to-End Orchestrator Pipeline
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("youtube_agent")

from src.config import Config, OUTPUT_DIR, BASE_DIR
from src.topic_manager import get_next_topic, mark_topic_completed
from src.script_generator import generate_documentary_script, DocumentaryScript
from src.voice_generator import run_voice_generation
from src.image_generator import (
    run_image_generation,
    generate_thumbnail_background,
)
from src.thumbnail_generator import create_documentary_thumbnail
from src.video_editor import render_full_documentary_video, render_teaser_short
from src.uploader import upload_video_to_youtube, upload_teaser_short_to_youtube
from src.marketing import run_marketing_campaign


def print_banner():
    banner = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║  🎬 AUTOMATED YOUTUBE DOCUMENTARY & MULTI-PLATFORM AGENT        ║
    ║  100% Free AI Pipeline • High-Retention Videos • Auto-Marketing  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_pipeline(
    topic_override: str = None,
    duration_minutes: int = 2,
    language: str = "urdu",
    dry_run: bool = True,
    custom_output_dir: Path = None,
    skip_upload: bool = False,
    skip_marketing: bool = False,
):
    start_time = time.time()
    print_banner()

    # Pre-flight validation
    logger.info("🔍 Running pre-flight configuration checks...")
    issues = Config.validate_for_execution(dry_run=dry_run)
    if issues:
        print("\n⚠️  CONFIGURATION ISSUES DETECTED:")
        for issue in issues:
            print(f"  • {issue}")
        print("\nPlease resolve these issues in your .env file or environment.\n")
        if not dry_run and not Config.GEMINI_API_KEY:
            sys.exit(1)

    # Resolve topic from queue or CLI override
    topic = get_next_topic(override_topic=topic_override)

    # Prepare project run directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_topic = "".join(c if c.isalnum() else "_" for c in topic)[:30].strip("_")
    run_folder_name = f"{timestamp}_{sanitized_topic}"
    project_dir = custom_output_dir or (OUTPUT_DIR / run_folder_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    audio_dir = project_dir / "audio"
    images_dir = project_dir / "images"
    audio_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)

    logger.info(f"📁 Output Directory: {project_dir}")
    logger.info(f"🎯 Selected Topic:   '{topic}'")
    logger.info(f"⏱️  Target Duration:  {duration_minutes} minute(s)")
    logger.info(f"🌐 Language:         {language.upper()}")
    logger.info(f"⚙️  Dry Run Mode:     {dry_run}")

    # =========================================================================
    # STEP 1: Script, SEO & Marketing Copy (Google Gemini Free API)
    # =========================================================================
    print("\n" + "=" * 65)
    print("📜 STEP 1: Generating Script, SEO & Social Marketing Copy (Gemini)...")
    print("=" * 65)

    script: DocumentaryScript = generate_documentary_script(
        topic=topic,
        duration_minutes=duration_minutes,
        language=language,
    )

    metadata_file = project_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)

    hook_scenes_count = sum(1 for s in script.scenes if s.is_hook_clip)
    print(f"✅ Title:             {script.title}")
    print(f"✅ Total Scenes:      {len(script.scenes)} (Hook clips marked: {hook_scenes_count})")
    print(f"✅ Thumbnail Hook:    '{script.thumbnail_text}'")
    print(f"✅ Marketing Copy:    Generated for YouTube, Facebook, X & Telegram")
    print(f"💾 Saved metadata to: {metadata_file.name}")

    # =========================================================================
    # STEP 2: Voiceover Generation (Edge-TTS)
    # =========================================================================
    print("\n" + "=" * 65)
    print(f"🎙️  STEP 2: Synthesizing Voiceovers with Edge-TTS ({Config.VOICE_NAME})...")
    print("=" * 65)

    audio_results = run_voice_generation(
        scenes=script.scenes,
        output_dir=audio_dir,
        voice=Config.VOICE_NAME,
        rate=Config.VOICE_RATE,
        pitch=Config.VOICE_PITCH,
    )

    total_speech_sec = sum(item[2] for item in audio_results)
    print(f"✅ Synthesized {len(audio_results)} scene audio clips.")
    print(f"⏱️  Total Spoken Duration: {total_speech_sec:.1f}s ({total_speech_sec/60:.2f} mins)")

    # =========================================================================
    # STEP 3: Visual Asset Generation (Pollinations.ai)
    # =========================================================================
    print("\n" + "=" * 65)
    print("🎨 STEP 3: Fetching 1080p Visual Assets from Pollinations.ai...")
    print("=" * 65)

    image_results = run_image_generation(
        scenes=script.scenes,
        output_dir=images_dir,
        width=Config.VIDEO_WIDTH,
        height=Config.VIDEO_HEIGHT,
    )

    raw_thumb_path = project_dir / "thumbnail_raw.jpg"
    logger.info("Fetching raw thumbnail background illustration...")
    import asyncio
    asyncio.run(
        generate_thumbnail_background(
            thumbnail_prompt=script.thumbnail_prompt,
            output_path=raw_thumb_path,
            width=Config.VIDEO_WIDTH,
            height=Config.VIDEO_HEIGHT,
        )
    )
    print(f"✅ Downloaded {len(image_results)} scene visuals + 1 thumbnail background.")

    # =========================================================================
    # STEP 4: Automated Thumbnail Generation (Pillow)
    # =========================================================================
    print("\n" + "=" * 65)
    print("🖼️  STEP 4: Rendering High-CTR Thumbnail...")
    print("=" * 65)

    final_thumb_path = project_dir / "thumbnail.jpg"
    create_documentary_thumbnail(
        raw_image_path=raw_thumb_path,
        output_path=final_thumb_path,
        hook_text=script.thumbnail_text,
        font_path=Config.FONT_PATH,
        width=1280,
        height=720,
    )
    print(f"✅ Thumbnail created: {final_thumb_path.name}")

    # =========================================================================
    # STEP 5: Dual Video Rendering (Long-Form 16:9 + Vertical 9:16 Short)
    # =========================================================================
    print("\n" + "=" * 65)
    print("🎞️  STEP 5: Dual Video Rendering (FFmpeg)...")
    print("=" * 65)

    # 5A: Main 16:9 Video
    print("🎥 Rendering Main 16:9 Long-Form Documentary Video...")
    all_scene_items = []
    hook_scene_items = []

    for i, scene in enumerate(script.scenes):
        idx = i + 1
        img_p = images_dir / f"scene_{idx:03d}.jpg"
        aud_p = audio_dir / f"scene_{idx:03d}.mp3"
        dur = audio_results[i][2]
        item = (idx, img_p, aud_p, dur, scene.on_screen_text)
        all_scene_items.append(item)

        if scene.is_hook_clip:
            hook_scene_items.append(item)

    # Fallback: if no scene was marked as hook clip, take first 4 scenes (~25-35s)
    if not hook_scene_items:
        hook_scene_items = all_scene_items[: min(4, len(all_scene_items))]

    main_video_path = render_full_documentary_video(
        scene_items=all_scene_items,
        output_dir=project_dir,
        bg_music_path=Path(Config.BG_MUSIC_PATH),
        bg_volume=Config.BG_MUSIC_VOLUME,
        font_path=Config.FONT_PATH,
        width=Config.VIDEO_WIDTH,
        height=Config.VIDEO_HEIGHT,
        fps=Config.VIDEO_FPS,
    )
    main_size_mb = main_video_path.stat().st_size / (1024 * 1024)
    print(f"✅ Main 16:9 Video Rendered: {main_video_path.name} ({main_size_mb:.2f} MB)")

    # 5B: Teaser 9:16 Short
    print("\n📱 Rendering Vertical 9:16 Teaser Short (Blurred BG + Top/Bottom CTA)...")
    teaser_short_path = render_teaser_short(
        hook_scene_items=hook_scene_items,
        output_dir=project_dir,
        bg_music_path=Path(Config.BG_MUSIC_PATH),
        bg_volume=Config.BG_MUSIC_VOLUME,
        font_path=Config.FONT_PATH,
        fps=Config.VIDEO_FPS,
    )
    teaser_size_mb = teaser_short_path.stat().st_size / (1024 * 1024)
    print(f"✅ Teaser 9:16 Short Rendered: {teaser_short_path.name} ({teaser_size_mb:.2f} MB)")

    # =========================================================================
    # STEP 6: YouTube Auto-Upload / Dry-Run
    # =========================================================================
    upload_result = {}
    short_upload_result = {}
    youtube_service = None

    if not skip_upload:
        print("\n" + "=" * 65)
        print("🚀 STEP 6: YouTube Upload / Dry-Run Verification...")
        print("=" * 65)

        # 6A: Upload Main Video
        upload_result = upload_video_to_youtube(
            video_path=main_video_path,
            title=script.title,
            description=script.description,
            tags=script.tags,
            thumbnail_path=final_thumb_path,
            privacy_status=Config.YOUTUBE_PRIVACY_STATUS,
            category_id=Config.YOUTUBE_CATEGORY_ID,
            dry_run=dry_run,
        )
        youtube_service = upload_result.get("service")

        # 6B: Upload Teaser Short
        if Config.UPLOAD_TEASER_SHORT:
            print("\n📱 Uploading Teaser Short to YouTube Shorts...")
            short_upload_result = upload_teaser_short_to_youtube(
                teaser_video_path=teaser_short_path,
                title=script.title,
                main_video_url=upload_result.get("url", "https://youtu.be/main_video"),
                privacy_status=Config.YOUTUBE_PRIVACY_STATUS,
                category_id=Config.YOUTUBE_CATEGORY_ID,
                dry_run=dry_run,
            )

    published_video_id = upload_result.get("video_id", "DRY_RUN_ID")
    published_video_url = upload_result.get("url", "https://youtu.be/DRY_RUN_ID")

    # =========================================================================
    # STEP 7: Auto-Marketing & Multi-Platform Social Distribution
    # =========================================================================
    marketing_results = {}
    if not skip_marketing:
        print("\n" + "=" * 65)
        print("📢 STEP 7: Multi-Platform Auto-Marketing & Distribution...")
        print("=" * 65)

        marketing_results = run_marketing_campaign(
            video_id=published_video_id,
            video_url=published_video_url,
            youtube_pinned_comment=script.youtube_pinned_comment,
            facebook_post=script.facebook_post,
            twitter_thread=script.twitter_thread,
            telegram_post=script.telegram_post,
            thumbnail_path=final_thumb_path,
            output_dir=project_dir,
            youtube_service=youtube_service,
            dry_run=dry_run,
        )

    # Mark topic completed in queue
    mark_topic_completed(topic=topic, video_id=published_video_id)

    elapsed_time = time.time() - start_time

    # =========================================================================
    # FINAL SUMMARY REPORT
    # =========================================================================
    print("\n" + "═" * 65)
    print("🎉 FULL PRODUCTION & MARKETING CAMPAIGN COMPLETED!")
    print("═" * 65)
    print(f"🎬 Video Title:     {script.title}")
    print(f"📁 Project Folder:   {project_dir}")
    print(f"📹 Main Video 16:9:  {main_video_path.name} ({main_size_mb:.2f} MB)")
    print(f"📱 Teaser Short 9:16:{teaser_short_path.name} ({teaser_size_mb:.2f} MB)")
    print(f"🖼️  Thumbnail:        {final_thumb_path.name}")
    print(f"⏱️  Narration Time:   {total_speech_sec:.1f}s")
    print(f"⚡ Pipeline Runtime: {elapsed_time:.1f}s ({elapsed_time/60:.2f} mins)")
    if upload_result:
        print(f"🌐 Main Video URL:   {published_video_url}")
    if short_upload_result:
        print(f"📱 Teaser Short URL: {short_upload_result.get('url')}")
    if marketing_results.get("preview_file"):
        print(f"📢 Marketing File:   {Path(marketing_results['preview_file']).name}")
    print("═" * 65 + "\n")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Automated YouTube Documentary Creator, Uploader & Multi-Platform Marketing Agent",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Custom documentary topic. If omitted, reads next unused topic from topics.txt",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=Config.TARGET_DURATION_MINUTES,
        help="Target long-form video duration in minutes",
    )
    parser.add_argument(
        "--lang",
        "--language",
        dest="language",
        type=str,
        choices=["urdu", "hindi", "english"],
        default=Config.LANGUAGE,
        help="Narration language",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=Config.DRY_RUN,
        help="Run full pipeline locally without uploading or posting externally",
    )
    parser.add_argument(
        "--live",
        dest="dry_run",
        action="store_false",
        help="Disable dry run and perform live upload & multi-platform distribution",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for generated files",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip YouTube uploading entirely",
    )
    parser.add_argument(
        "--skip-marketing",
        action="store_true",
        help="Skip social media distribution",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    custom_out = Path(args.output_dir) if args.output_dir else None

    run_pipeline(
        topic_override=args.topic,
        duration_minutes=args.duration,
        language=args.language,
        dry_run=args.dry_run,
        custom_output_dir=custom_out,
        skip_upload=args.skip_upload,
        skip_marketing=args.skip_marketing,
    )
