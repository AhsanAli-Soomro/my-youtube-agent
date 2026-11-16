"""
Voiceover Generation Module using Edge-TTS (100% Free)
Generates high quality, natural voiceovers for each scene clip and measures exact durations.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
import edge_tts

from src.config import Config
from src.script_generator import Scene

logger = logging.getLogger("youtube_agent.voice")


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
    """Synthesize voiceover for a single scene and measure its duration."""
    v_voice = voice or Config.VOICE_NAME
    v_rate = rate or Config.VOICE_RATE
    v_pitch = pitch or Config.VOICE_PITCH

    filename = output_dir / f"scene_{scene_index:03d}.mp3"

    logger.debug(
        f"Synthesizing scene {scene_index} (voice={v_voice}, rate={v_rate}, pitch={v_pitch})..."
    )

    communicate = edge_tts.Communicate(
        text=narration,
        voice=v_voice,
        rate=v_rate,
        pitch=v_pitch,
    )

    await communicate.save(str(filename))

    duration = get_audio_duration_ffprobe(str(filename), ffprobe_bin)
    logger.info(
        f"Scene {scene_index:03d} audio synthesized: {duration:.2f}s -> {filename.name}"
    )

    return scene_index, filename, duration


async def generate_all_scene_audios(
    scenes: List[Scene],
    output_dir: Path,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
) -> List[Tuple[int, Path, float]]:
    """Synthesize voiceover for all scenes in parallel with concurrency limiting."""
    output_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(4)  # Limit concurrent TTS network streams

    async def _worker(idx: int, scene: Scene):
        async with semaphore:
            return await synthesize_scene_audio(
                scene_index=idx,
                narration=scene.narration,
                output_dir=output_dir,
                voice=voice,
                rate=rate,
                pitch=pitch,
            )

    tasks = [_worker(i + 1, scene) for i, scene in enumerate(scenes)]
    results = await asyncio.gather(*tasks)

    # Sort results by scene index to maintain chronological order
    results.sort(key=lambda x: x[0])
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
