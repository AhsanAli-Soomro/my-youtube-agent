"""
Voiceover Generation Module using Edge-TTS (100% Free)
Generates high quality, natural voiceovers for each scene clip and measures exact durations.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import edge_tts

from src.config import Config
from src.script_generator import Scene

logger = logging.getLogger("youtube_agent.voice")


def _find_edge_tts_bin() -> str:
    """Find the edge-tts executable in PATH or the current virtualenv."""
    which_path = shutil.which("edge-tts")
    if which_path:
        return which_path
    venv_candidate = Path(sys.executable).parent / "edge-tts"
    if venv_candidate.is_file():
        return str(venv_candidate)
    return "edge-tts"


def get_audio_duration_ffprobe(audio_path: str, ffprobe_bin: Optional[str] = None) -> float:
    """Measure exact duration of an audio file using ffprobe."""
    binary = ffprobe_bin or Config.FFPROBE_PATH or "ffprobe"

    cmd = [
        binary,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=15,
        )
        duration_str = result.stdout.strip()
        return max(0.5, float(duration_str))
    except Exception as err:
        logger.warning(
            f"ffprobe duration check failed for '{audio_path}' ({err}). Using fallback estimation."
        )
        # Fallback approximation: estimate based on file size for 48kbps or 64kbps MP3
        # ~6000 bytes per second for standard Edge TTS MP3 output
        file_size = os.path.getsize(audio_path)
        est_duration = max(2.0, file_size / 6000.0)
        return round(est_duration, 2)


async def synthesize_scene_audio(
    scene_index: int,
    narration: str,
    output_dir: Path,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
    ffprobe_bin: Optional[str] = None,
) -> Tuple[int, Path, float]:
    """Synthesize voiceover for a single scene with robust CLI fallback."""
    v_voice = voice or Config.VOICE_NAME
    v_rate = rate or Config.VOICE_RATE
    v_pitch = pitch or Config.VOICE_PITCH

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"scene_{scene_index:03d}.mp3"
    clean_text = narration.strip() if narration and narration.strip() else "خاموشی"

    # Build candidate voices list for resilience (e.g. AsadNeural sometimes rejects specific Urdu vocabulary)
    voices_to_try = [v_voice]
    if "ur-PK" in v_voice or "urdu" in v_voice.lower():
        for alt in ["ur-IN-SalmanNeural", "ur-PK-UzmaNeural"]:
            if alt not in voices_to_try:
                voices_to_try.append(alt)
    elif "hi-IN" in v_voice or "hindi" in v_voice.lower():
        if "hi-IN-SwaraNeural" not in voices_to_try:
            voices_to_try.append("hi-IN-SwaraNeural")
    elif "en-US" in v_voice or "english" in v_voice.lower():
        if "en-US-GuyNeural" not in voices_to_try:
            voices_to_try.append("en-US-GuyNeural")

    tts_bin = _find_edge_tts_bin()

    for voice_candidate in voices_to_try:
        # Attempt 1: Native edge-tts Python API
        try:
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=voice_candidate,
                rate=v_rate,
                pitch=v_pitch,
            )
            await communicate.save(str(filename))
            if filename.is_file() and filename.stat().st_size > 500:
                duration = get_audio_duration_ffprobe(str(filename), ffprobe_bin)
                logger.info(f"Scene {scene_index:03d} synthesized (API - {voice_candidate}): {duration:.2f}s -> {filename.name}")
                return scene_index, filename, duration
        except Exception as api_err:
            logger.debug(f"Native TTS API call failed for scene {scene_index} with {voice_candidate}: {api_err}. Trying CLI...")

        # Attempt 2: Direct edge-tts CLI execution
        try:
            cmd = [
                tts_bin,
                "--voice", voice_candidate,
                f"--rate={v_rate}",
                f"--pitch={v_pitch}",
                "--text", clean_text,
                "--write-media", str(filename),
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
            if res.returncode == 0 and filename.is_file() and filename.stat().st_size > 500:
                duration = get_audio_duration_ffprobe(str(filename), ffprobe_bin)
                logger.info(f"Scene {scene_index:03d} synthesized (CLI - {voice_candidate}): {duration:.2f}s -> {filename.name}")
                return scene_index, filename, duration
        except Exception as cli_err:
            logger.warning(f"TTS CLI execution error for scene {scene_index} ({voice_candidate}): {cli_err}")

        # Attempt 3: CLI with default rate and pitch
        try:
            cmd_fallback = [
                tts_bin,
                "--voice", voice_candidate,
                "--text", clean_text,
                "--write-media", str(filename),
            ]
            res = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
            if res.returncode == 0 and filename.is_file() and filename.stat().st_size > 500:
                duration = get_audio_duration_ffprobe(str(filename), ffprobe_bin)
                logger.info(f"Scene {scene_index:03d} synthesized (CLI Fallback - {voice_candidate}): {duration:.2f}s -> {filename.name}")
                return scene_index, filename, duration
        except Exception as e:
            logger.debug(f"TTS fallback failed for scene {scene_index} with {voice_candidate}: {e}")

    # Emergency fallback: generate 100% valid silent MP3 via FFmpeg so video rendering never crashes
    logger.warning(f"⚠️  All voice synthesizers failed for scene {scene_index}. Generating clean silent MP3 via FFmpeg.")
    ffmpeg_bin = Config.FFMPEG_PATH or "ffmpeg"
    cmd_silent = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-t", "4.0",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        str(filename),
    ]
    subprocess.run(cmd_silent, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return scene_index, filename, 4.0


async def generate_all_scene_audios(
    scenes: List[Scene],
    output_dir: Path,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
) -> List[Tuple[int, Path, float]]:
    """Synthesize voiceover for all scenes with safe concurrency pacing."""
    output_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(2)  # Microsoft Edge TTS prefers <= 2 concurrent streams

    async def _worker(idx: int, scene: Scene):
        async with semaphore:
            res = await synthesize_scene_audio(
                scene_index=idx,
                narration=scene.narration,
                output_dir=output_dir,
                voice=voice,
                rate=rate,
                pitch=pitch,
            )
            await asyncio.sleep(0.3)
            return res

    tasks = [_worker(i + 1, scene) for i, scene in enumerate(scenes)]
    results = await asyncio.gather(*tasks)

    results.sort(key=lambda x: x[0])
    total_audio_length = sum(r[2] for r in results)
    logger.info(
        f"Total audio synthesized for {len(results)} scenes: {total_audio_length:.1f} seconds "
        f"({total_audio_length / 60:.2f} minutes)."
    )
    return results
    total_audio_length = sum(r[2] for r in results)
    logger.info(
        f"Total audio synthesized for {len(results)} scenes: {total_audio_length:.1f} seconds "
        f"({total_audio_length / 60:.2f} minutes)."
    )
    return results


def run_voice_generation(
    scenes: List[Scene],
    output_dir: Path,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
) -> List[Tuple[int, Path, float]]:
    """Synchronous entry point to run async voice generation."""
    return asyncio.run(
        generate_all_scene_audios(
            scenes=scenes,
            output_dir=output_dir,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )
    )
