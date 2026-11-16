"""
FFmpeg Video Editing & Rendering Engine
Renders:
1. Long-form 16:9 documentary video with dynamic Ken Burns zoom & subtitles (main_video.mp4).
2. Vertical 9:16 teaser Short with blurred background & hook banners (teaser_short.mp4).
3. Seamless concatenation and 12% background audio mixing.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from src.config import Config

logger = logging.getLogger("youtube_agent.video")


def _escape_drawtext(text: str) -> str:
    """Escape special characters for FFmpeg's drawtext filter syntax."""
    escaped = text.replace("\\", "\\\\")
    escaped = escaped.replace("'", "'\\''")
    escaped = escaped.replace(":", "\\:")
    escaped = escaped.replace("%", "\\%")
    escaped = escaped.replace("[", "\\[").replace("]", "\\]")
    return escaped


def render_scene_clip(
    image_path: Path,
    audio_path: Path,
    duration: float,
    output_path: Path,
    scene_index: int,
    on_screen_text: Optional[str] = None,
    font_path: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    ffmpeg_bin: Optional[str] = None,
) -> Path:
    """Render a single 16:9 scene video clip combining image, Ken Burns zoom, and audio."""
    binary = ffmpeg_bin or Config.FFMPEG_PATH or "ffmpeg"
    font = font_path or Config.FONT_PATH

    total_frames = max(fps, int(round(duration * fps)))

    # Alternating Ken Burns zoom: odd scenes zoom in, even scenes zoom out
    if scene_index % 2 == 1:
        zoom_expr = f"1.0+0.15*(on/{total_frames})"
    else:
        zoom_expr = f"1.15-0.15*(on/{total_frames})"

    filter_chain = [
        f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase",
        f"crop={width*2}:{height*2}",
        f"zoompan=z='{zoom_expr}':d={total_frames}:x='(iw-iw/zoom)/2':y='ih-ih/zoom':s={width}x{height}:fps={fps}",
    ]

    # Lower-third text overlay
    if on_screen_text and on_screen_text.strip():
        safe_text = _escape_drawtext(on_screen_text.strip())
        fade_dur = min(0.6, duration * 0.2)
        alpha_expr = f"if(lt(t,{fade_dur}),t/{fade_dur},if(gt(t,{duration}-{fade_dur}),({duration}-t)/{fade_dur},1))"

        font_option = f":fontfile='{font}'" if font and Path(font).is_file() else ""
        drawtext_filter = (
            f"drawtext=text='{safe_text}'{font_option}:fontsize=44:fontcolor=white"
            f":box=1:boxcolor=black@0.65:boxborderw=14"
            f":x=(w-text_w)/2:y=h-th-90:alpha='{alpha_expr}'"
        )
        filter_chain.append(drawtext_filter)

    video_filters = ",".join(filter_chain)

    cmd = [
        binary,
        "-y",
        "-loop", "1",
        "-t", f"{duration:.3f}",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", video_filters,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg error rendering 16:9 scene {scene_index}:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg failed for scene {scene_index}: {result.stderr[-400:]}")

    logger.info(f"Rendered 16:9 scene {scene_index:03d}: {output_path.name} ({duration:.2f}s)")
    return output_path


def render_teaser_scene_clip(
    image_path: Path,
    audio_path: Path,
    duration: float,
    output_path: Path,
    scene_index: int,
    on_screen_text: Optional[str] = None,
    font_path: Optional[str] = None,
    fps: int = 30,
    ffmpeg_bin: Optional[str] = None,
) -> Path:
    """Render a single 9:16 vertical teaser scene (blurred background + centered sharp visual)."""
    binary = ffmpeg_bin or Config.FFMPEG_PATH or "ffmpeg"
    font = font_path or Config.FONT_PATH
    font_opt = f":fontfile='{font}'" if font and Path(font).is_file() else ""

    banner_cta = "WATCH FULL DOCUMENTARY ON CHANNEL 👇"
    safe_banner = _escape_drawtext(banner_cta)

    # Complex filter:
    # 1. Scale & blur 9:16 background
    # 2. Scale 16:9 foreground to 1080 width
    # 3. Overlay in center
    # 4. Top hook text (if any) and bottom CTA banner
    filter_parts = [
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg]",
        "[0:v]scale=1080:-1[fg]",
        "[bg][fg]overlay=0:(H-h)/2[base]",
    ]

    cta_filter = (
        f"drawtext=text='{safe_banner}'{font_opt}:fontsize=34:fontcolor=yellow"
        f":box=1:boxcolor=black@0.75:boxborderw=16"
        f":x=(w-text_w)/2:y=h-220"
    )

    if on_screen_text and on_screen_text.strip():
        safe_text = _escape_drawtext(on_screen_text.strip())
        top_filter = (
            f"drawtext=text='{safe_text}'{font_opt}:fontsize=40:fontcolor=white"
            f":box=1:boxcolor=black@0.7:boxborderw=12"
            f":x=(w-text_w)/2:y=240"
        )
        final_filter = f"[base]{cta_filter},{top_filter}[vout]"
    else:
        final_filter = f"[base]{cta_filter}[vout]"

    filter_complex = ";".join(filter_parts) + ";" + final_filter

    cmd = [
        binary,
        "-y",
        "-loop", "1",
        "-t", f"{duration:.3f}",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg error rendering 9:16 teaser scene {scene_index}:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg failed for teaser scene {scene_index}: {result.stderr[-400:]}")

    logger.info(f"Rendered 9:16 teaser scene {scene_index:03d}: {output_path.name} ({duration:.2f}s)")
    return output_path


def concatenate_scenes(
    scene_clips: List[Path],
    output_path: Path,
    ffmpeg_bin: Optional[str] = None,
) -> Path:
    """Concatenate individual scene MP4 files seamlessly into one video stream."""
    binary = ffmpeg_bin or Config.FFMPEG_PATH or "ffmpeg"
    concat_list_file = output_path.parent / f"concat_{output_path.stem}.txt"

    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip in scene_clips:
            f.write(f"file '{clip.resolve()}'\n")

    cmd = [
        binary,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(output_path),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg concat failed:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg concatenation failed: {result.stderr[-400:]}")

    return output_path


def mix_background_music(
    raw_video_path: Path,
    bg_music_path: Path,
    output_path: Path,
    bg_volume: float = 0.12,
    ffmpeg_bin: Optional[str] = None,
) -> Path:
    """Mix looped background music at specified volume under the voiceover track."""
    binary = ffmpeg_bin or Config.FFMPEG_PATH or "ffmpeg"

    if not bg_music_path.is_file():
        logger.warning(f"Background music '{bg_music_path}' not found. Exporting without bg music.")
        if raw_video_path != output_path:
            import shutil
            shutil.copyfile(raw_video_path, output_path)
        return output_path

    filter_complex = (
        f"[0:a]volume=1.0[voice];"
        f"[1:a]volume={bg_volume:.2f}[bg];"
        f"[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )

    cmd = [
        binary,
        "-y",
        "-i", str(raw_video_path),
        "-stream_loop", "-1",
        "-i", str(bg_music_path),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg audio mixing failed:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg audio mixing failed: {result.stderr[-400:]}")

    return output_path


def render_full_documentary_video(
    scene_items: List[Tuple[int, Path, Path, float, Optional[str]]],
    output_dir: Path,
    bg_music_path: Optional[Path] = None,
    bg_volume: float = 0.12,
    font_path: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> Path:
    """Render the master 16:9 documentary video (main_video.mp4)."""
    import shutil
    final_output = output_dir / "main_video.mp4"
    compat_output = output_dir / "output.mp4"

    # Graceful fallback if FFmpeg is not installed on the current host
    has_ffmpeg = bool(Config.FFMPEG_PATH or shutil.which("ffmpeg"))
    if not has_ffmpeg:
        logger.warning("⚠️  FFmpeg binary not detected on this machine. Simulating video export for dry-run...")
        dummy_bytes = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free"
        with open(final_output, "wb") as f:
            f.write(dummy_bytes)
        with open(compat_output, "wb") as f:
            f.write(dummy_bytes)
        return final_output

    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    rendered_clips: List[Path] = []
    total_scenes = len(scene_items)

    for idx, img_path, aud_path, dur, screen_text in scene_items:
        clip_path = clips_dir / f"scene_{idx:03d}.mp4"
        render_scene_clip(
            image_path=img_path,
            audio_path=aud_path,
            duration=dur,
            output_path=clip_path,
            scene_index=idx,
            on_screen_text=screen_text,
            font_path=font_path,
            width=width,
            height=height,
            fps=fps,
        )
        rendered_clips.append(clip_path)

    raw_combined = output_dir / "raw_main_combined.mp4"
    concatenate_scenes(rendered_clips, raw_combined)

    final_output = output_dir / "main_video.mp4"
    music_file = bg_music_path or Path(Config.BG_MUSIC_PATH)
    mix_background_music(
        raw_video_path=raw_combined,
        bg_music_path=music_file,
        output_path=final_output,
        bg_volume=bg_volume,
    )

    # Maintain output.mp4 link/copy for backwards compatibility
    compat_output = output_dir / "output.mp4"
    import shutil
    shutil.copyfile(final_output, compat_output)

    logger.info(f"Master 16:9 video rendered successfully: {final_output}")
    return final_output


def render_teaser_short(
    hook_scene_items: List[Tuple[int, Path, Path, float, Optional[str]]],
    output_dir: Path,
    bg_music_path: Optional[Path] = None,
    bg_volume: float = 0.12,
    font_path: Optional[str] = None,
    fps: int = 30,
) -> Path:
    """Render the vertical 9:16 marketing teaser Short (teaser_short.mp4)."""
    import shutil
    final_teaser = output_dir / "teaser_short.mp4"

    has_ffmpeg = bool(Config.FFMPEG_PATH or shutil.which("ffmpeg"))
    if not has_ffmpeg:
        logger.warning("⚠️  FFmpeg binary not detected on this machine. Simulating teaser short for dry-run...")
        dummy_bytes = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free"
        with open(final_teaser, "wb") as f:
            f.write(dummy_bytes)
        return final_teaser

    short_clips_dir = output_dir / "short_clips"
    short_clips_dir.mkdir(parents=True, exist_ok=True)

    rendered_short_clips: List[Path] = []

    for idx, img_path, aud_path, dur, screen_text in hook_scene_items:
        clip_path = short_clips_dir / f"short_scene_{idx:03d}.mp4"
        render_teaser_scene_clip(
            image_path=img_path,
            audio_path=aud_path,
            duration=dur,
            output_path=clip_path,
            scene_index=idx,
            on_screen_text=screen_text,
            font_path=font_path,
            fps=fps,
        )
        rendered_short_clips.append(clip_path)

    raw_teaser = output_dir / "raw_teaser_combined.mp4"
    concatenate_scenes(rendered_short_clips, raw_teaser)

    final_teaser = output_dir / "teaser_short.mp4"
    music_file = bg_music_path or Path(Config.BG_MUSIC_PATH)
    mix_background_music(
        raw_video_path=raw_teaser,
        bg_music_path=music_file,
        output_path=final_teaser,
        bg_volume=bg_volume,
    )

    logger.info(f"Vertical 9:16 Teaser Short rendered successfully: {final_teaser}")
    return final_teaser
