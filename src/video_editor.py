"""
FFmpeg Video Editing & Rendering Engine
Renders individual scene clips with dynamic Ken Burns zoom effects and lower-third text overlays,
concatenates scenes, and mixes looped background audio with voiceovers.
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
    # Escape backslash, single quote, colon, percent, and square brackets
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
    """Render a single scene video clip combining image, Ken Burns zoom, and audio."""
    binary = ffmpeg_bin or Config.FFMPEG_PATH or "ffmpeg"
    font = font_path or Config.FONT_PATH

    total_frames = max(fps, int(round(duration * fps)))

    # Alternating Ken Burns: odd scenes zoom in, even scenes zoom out
    # Monotonic formula: 1.0 -> 1.15 for zoom in, 1.15 -> 1.0 for zoom out
    if scene_index % 2 == 1:
        zoom_expr = f"1.0+0.15*(on/{total_frames})"
    else:
        zoom_expr = f"1.15-0.15*(on/{total_frames})"

    # Ken Burns filter: center the crop smoothly
    # Note: scale input image first to ensure zoompan operates on high-resolution canvas
    filter_chain = [
        f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase",
        f"crop={width*2}:{height*2}",
        f"zoompan=z='{zoom_expr}':d={total_frames}:x='(iw-iw/zoom)/2':y='ih-ih/zoom':s={width}x{height}:fps={fps}",
    ]

    # Add lower-third on-screen text overlay if provided
    if on_screen_text and on_screen_text.strip():
        safe_text = _escape_drawtext(on_screen_text.strip())
        fade_dur = min(0.6, duration * 0.2)
        # Smooth fade-in at start, fade-out before end
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

    logger.debug(f"Rendering scene {scene_index:03d}: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        logger.error(f"FFmpeg error rendering scene {scene_index}:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg failed for scene {scene_index}: {result.stderr[-500:]}")

    logger.info(f"Rendered scene clip: {output_path.name} ({duration:.2f}s)")
    return output_path


def concatenate_scenes(
    scene_clips: List[Path],
    output_path: Path,
    ffmpeg_bin: Optional[str] = None,
) -> Path:
    """Concatenate individual scene MP4 files seamlessly into one video stream."""
    binary = ffmpeg_bin or Config.FFMPEG_PATH or "ffmpeg"
    concat_list_file = output_path.parent / "concat_list.txt"

    # Write FFmpeg concat demuxer manifest
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

    logger.info(f"Concatenating {len(scene_clips)} scene clips into '{output_path.name}'...")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        logger.error(f"FFmpeg concat failed:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg concatenation failed: {result.stderr[-500:]}")

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
        logger.warning(
            f"Background music '{bg_music_path}' not found. Exporting raw video without bg music."
        )
        if raw_video_path != output_path:
            import shutil
            shutil.copyfile(raw_video_path, output_path)
        return output_path

    # Filter complex: loop background audio, lower its volume to bg_volume, mix with voiceover
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

    logger.info(f"Mixing background music ({bg_volume*100:.0f}% volume) into '{output_path.name}'...")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        logger.error(f"FFmpeg audio mixing failed:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg audio mixing failed: {result.stderr[-500:]}")

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
    """Orchestrate end-to-end video rendering from scene clips to final output.mp4."""
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    rendered_clips: List[Path] = []
    total_scenes = len(scene_items)

    for idx, img_path, aud_path, dur, screen_text in scene_items:
        clip_path = clips_dir / f"scene_{idx:03d}.mp4"
        logger.info(f"Rendering scene {idx}/{total_scenes} (duration: {dur:.2f}s)...")
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

    # Concatenate all rendered scenes
    raw_combined = output_dir / "raw_combined.mp4"
    concatenate_scenes(rendered_clips, raw_combined)

    # Final audio mix with ambient background track
    final_output = output_dir / "output.mp4"
    music_file = bg_music_path or Path(Config.BG_MUSIC_PATH)
    mix_background_music(
        raw_video_path=raw_combined,
        bg_music_path=music_file,
        output_path=final_output,
        bg_volume=bg_volume,
    )

    logger.info(f"Final documentary video rendered successfully: {final_output}")
    return final_output
