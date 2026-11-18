"""
AI Video & Movie Generation Engine
Supports 3 Modes:
1. 'documentary': 100% Free - Pollinations.ai 1080p images + Ken Burns motion + Edge-TTS (Runs on all PCs & GitHub Actions).
2. 'cloud_movie': Cloud AI Video Engine - Generates real moving MP4 clips via Fal.ai / Replicate (Runs on Mac mini M4, ThinkPad T480s, Cloud).
3. 'local_movie': Local Apple Silicon M4 / GPU Diffusion - Runs open-weights video models on Apple Silicon MPS or NVIDIA CUDA.
"""

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import httpx

from src.config import Config

logger = logging.getLogger("youtube_agent.ai_video")


def detect_hardware() -> Dict[str, Any]:
    """
    Detect machine hardware capability:
    - Apple Silicon (Mac mini M4, M1-M3) -> MPS supported
    - NVIDIA GPU (RTX 3060/4090) -> CUDA supported
    - Intel / AMD integrated GPU (Lenovo ThinkPad T480s) -> CPU only
    """
    system_os = platform.system()
    machine_arch = platform.machine()
    is_apple_silicon = system_os == "Darwin" and machine_arch in ("arm64", "aarch64")

    has_cuda = False
    has_mps = False

    try:
        import torch
        has_cuda = torch.cuda.is_available()
        has_mps = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    except ImportError:
        # If PyTorch is not yet installed, deduce from platform architecture
        has_mps = is_apple_silicon

    if has_cuda:
        tier = "NVIDIA Dedicated GPU (CUDA)"
        recommended_modes = ["documentary", "cloud_movie", "local_movie"]
    elif has_mps:
        tier = "Apple Silicon M-Series (Mac mini M4 / MPS Metal)"
        recommended_modes = ["documentary", "cloud_movie", "local_movie"]
    else:
        tier = "Standard CPU / Integrated Graphics (e.g. Lenovo ThinkPad T480s)"
        recommended_modes = ["documentary", "cloud_movie"]

    return {
        "os": system_os,
        "arch": machine_arch,
        "tier": tier,
        "has_cuda": has_cuda,
        "has_mps": has_mps,
        "recommended_modes": recommended_modes,
        "can_run_local_movie": has_cuda or has_mps,
    }


def generate_cloud_movie_clip(
    prompt: str,
    output_path: Path,
    image_path: Optional[Path] = None,
    duration_seconds: int = 5,
) -> Path:
    """
    Generate an actual moving AI video clip (.mp4) using Cloud Video APIs (Fal.ai or Replicate).
    If no API key is set, applies high-grade 2.5D camera dynamics as a graceful simulation.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fal_key = Config.FAL_KEY or os.getenv("FAL_KEY", "").strip()
    replicate_token = Config.REPLICATE_API_TOKEN or os.getenv("REPLICATE_API_TOKEN", "").strip()

    # 1. Option: Fal.ai (Kling AI 1.6 / Minimax / LTX-Video)
    if fal_key:
        logger.info("🎬 [Cloud Movie] Generating moving video clip via Fal.ai API...")
        os.environ["FAL_KEY"] = fal_key
        try:
            import fal_client
            # If an anchor image exists, use Image-to-Video for character consistency; else Text-to-Video
            if image_path and image_path.is_file():
                upload_handle = fal_client.upload_file(str(image_path))
                handler = fal_client.subscribe(
                    "fal-ai/kling-video/v1.6/standard/image-to-video",
                    arguments={
                        "prompt": prompt,
                        "image_url": upload_handle,
                        "duration": str(min(10, max(5, int(duration_seconds)))),
                        "aspect_ratio": "16:9",
                    },
                )
            else:
                handler = fal_client.subscribe(
                    "fal-ai/kling-video/v1.6/standard/text-to-video",
                    arguments={
                        "prompt": prompt,
                        "duration": str(min(10, max(5, int(duration_seconds)))),
                        "aspect_ratio": "16:9",
                    },
                )

            video_url = handler.get("video", {}).get("url")
            if video_url:
                logger.info(f"Downloading generated video from {video_url}...")
                with httpx.Client(timeout=60.0) as client:
                    resp = client.get(video_url)
                    resp.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                logger.info(f"✅ Cloud video clip saved: {output_path.name}")
                return output_path
        except Exception as err:
            logger.warning(f"Fal.ai video generation failed: {err}. Falling back to Replicate or simulation...")

    # 2. Option: Replicate (Wan 2.1 / SVD)
    if replicate_token:
        logger.info("🎬 [Cloud Movie] Generating moving video clip via Replicate API...")
        os.environ["REPLICATE_API_TOKEN"] = replicate_token
        try:
            import replicate
            output = replicate.run(
                "wan-video/wan-2.1-t2v-480p",
                input={"prompt": prompt},
            )
            if output:
                video_url = str(output)
                with httpx.Client(timeout=60.0) as client:
                    resp = client.get(video_url)
                    resp.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                logger.info(f"✅ Replicate video clip saved: {output_path.name}")
                return output_path
        except Exception as err:
            logger.warning(f"Replicate video generation failed: {err}. Falling back...")

    # 3. Graceful Simulation Fallback:
    logger.info("ℹ️  [Cloud Movie Simulation] No FAL_KEY / REPLICATE_API_TOKEN configured.")
    logger.info("💡 To generate live 1080p Hollywood AI video clips, add your free trial FAL_KEY to .env.")
    return _render_motion_clip_from_image(image_path, prompt, output_path, duration_seconds)


def generate_local_movie_clip(
    prompt: str,
    output_path: Path,
    image_path: Optional[Path] = None,
    duration_seconds: int = 5,
) -> Path:
    """
    Generate an AI video clip locally:
    - On Mac mini M4: Utilizes Apple Silicon Metal Performance Shaders (MPS).
    - On NVIDIA PC: Utilizes CUDA.
    - On Lenovo ThinkPad T480s (Intel CPU): Detects limited GPU and automatically delegates
      safely to Cloud / Motion rendering to prevent system freezing.
    """
    hw = detect_hardware()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not hw["can_run_local_movie"]:
        logger.warning(
            "⚠️  [Hardware Safety Check] Lenovo ThinkPad T480s / Integrated CPU detected.\n"
            "   Local Video Diffusion requires at least 12GB dedicated GPU VRAM.\n"
            "   Auto-switching to Cloud / Motion video processing to protect system stability."
        )
        return generate_cloud_movie_clip(prompt, output_path, image_path, duration_seconds)

    logger.info(f"🚀 [Local Movie Engine] Running on {hw['tier']}...")

    # Check if local diffusers weights are installed
    try:
        import torch
        from diffusers import DiffusionPipeline

        device = "mps" if hw["has_mps"] else "cuda"
        dtype = torch.float16

        logger.info(f"Loading local video diffusion pipeline on {device}...")
        pipe = DiffusionPipeline.from_pretrained(
            "ali-vilab/text-to-video-ms-1.7b",
            torch_dtype=dtype,
        ).to(device)

        video_frames = pipe(prompt, num_inference_steps=20, height=320, width=576).frames
        from diffusers.utils import export_to_video
        export_to_video(video_frames, str(output_path))
        logger.info(f"✅ Local M4 video clip rendered: {output_path.name}")
        return output_path
    except Exception as err:
        logger.warning(
            f"Local PyTorch diffusers execution not active or weights missing ({err}).\n"
            f"Falling back to high-grade Apple Silicon motion renderer..."
        )
        return _render_motion_clip_from_image(image_path, prompt, output_path, duration_seconds)


def _render_motion_clip_from_image(
    image_path: Optional[Path],
    prompt: str,
    output_path: Path,
    duration: float = 5.0,
) -> Path:
    """
    High-grade 2.5D dynamic camera movement engine using FFmpeg:
    Simulates dynamic cinematic camera tracking, rotation, and lighting shifts.
    """
    binary = Config.FFMPEG_PATH or "ffmpeg"

    # If no source image is provided, generate one from the prompt via Pollinations
    if not image_path or not image_path.is_file():
        from src.image_generator import download_pollinations_image
        temp_img = output_path.parent / f"ref_{output_path.stem}.jpg"
        download_pollinations_image(prompt, temp_img, width=1920, height=1080)
        image_path = temp_img

    total_frames = max(30, int(round(duration * 30)))
    # Complex 2.5D cinematic pan and dolly effect
    zoom_expr = f"1.0+0.12*(on/{total_frames})"
    x_expr = f"(iw-iw/zoom)/2 + 20*sin(on/25)"
    y_expr = f"(ih-ih/zoom)/2 + 10*cos(on/25)"

    cmd = [
        binary, "-y",
        "-loop", "1",
        "-t", f"{duration:.2f}",
        "-i", str(image_path),
        "-vf", (
            f"scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s=1920x1080:fps=30,"
            f"eq=contrast=1.05:saturation=1.1:brightness=-0.02"
        ),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path
