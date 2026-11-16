"""
Visual Asset Generator using Pollinations.ai (100% Free, No API Key)
Downloads 1920x1080 cinematic documentary illustrations with rate limiting and exponential backoff.
"""

import asyncio
import logging
import urllib.parse
from pathlib import Path
from typing import List, Tuple, Optional
import httpx

from src.config import Config
from src.script_generator import Scene

logger = logging.getLogger("youtube_agent.images")

STYLE_MODIFIERS = (
    ", dark cinematic documentary style, dramatic chiaroscuro lighting, "
    "ultra detailed 8k, historical mystery archive aesthetic, photorealistic, 16:9, no text, no watermark"
)


def build_pollinations_url(
    prompt: str,
    width: int = 1920,
    height: int = 1080,
    seed: Optional[int] = None,
) -> str:
    """Format and URL-encode the Pollinations image generation endpoint."""
    full_prompt = prompt.strip()
    if not any(mod in full_prompt.lower() for mod in ["cinematic", "documentary", "8k"]):
        full_prompt += STYLE_MODIFIERS

    encoded_prompt = urllib.parse.quote(full_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
    if seed is not None:
        url += f"&seed={seed}"
    return url


async def download_image_with_retry(
    client: httpx.AsyncClient,
    prompt: str,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
    max_retries: int = 4,
    seed: Optional[int] = None,
) -> bool:
    """Download an image from Pollinations.ai with exponential backoff retries."""
    url = build_pollinations_url(prompt, width, height, seed)

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Fetching image (attempt {attempt}/{max_retries}): {output_path.name}")
            response = await client.get(url, timeout=45.0, follow_redirects=True)

            if response.status_code == 200 and len(response.content) > 1000:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(
                    f"Saved visual asset: {output_path.name} ({len(response.content) // 1024} KB)"
                )
                return True
            else:
                logger.warning(
                    f"Pollinations returned status {response.status_code} "
                    f"({len(response.content)} bytes) on attempt {attempt}"
                )
        except Exception as exc:
            logger.warning(f"Image download error on attempt {attempt}/{max_retries}: {exc}")

        # Exponential backoff before retry
        wait_time = 1.5 * (2 ** (attempt - 1))
        await asyncio.sleep(wait_time)

    # Fallback: create a dark cinematic gradient background if remote generation completely fails
    logger.error(
        f"Failed to fetch image from Pollinations after {max_retries} attempts for '{output_path.name}'. "
        f"Generating emergency fallback background..."
    )
    _generate_fallback_image(output_path, width, height, prompt)
    return False


def _generate_fallback_image(output_path: Path, width: int, height: int, prompt_hint: str):
    """Generate a clean dark gradient fallback image if network is unreachable."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (width, height), color=(15, 18, 24))
    draw = ImageDraw.Draw(img)

    # Draw dark moody vignette
    for y in range(height):
        ratio = y / height
        shade = int(15 + ratio * 20)
        draw.line([(0, y), (width, y)], fill=(shade, shade + 3, shade + 8))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=90)


async def generate_all_scene_images(
    scenes: List[Scene],
    output_dir: Path,
    width: int = 1920,
    height: int = 1080,
    inter_request_delay: float = 1.5,
) -> List[Tuple[int, Path]]:
    """Download images for all scenes sequentially with a polite rate-limit delay."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    async with httpx.AsyncClient() as client:
        for idx, scene in enumerate(scenes, start=1):
            target_file = output_dir / f"scene_{idx:03d}.jpg"
            logger.info(f"Generating scene image {idx}/{len(scenes)}: '{scene.image_prompt[:60]}...'")

            await download_image_with_retry(
                client=client,
                prompt=scene.image_prompt,
                output_path=target_file,
                width=width,
                height=height,
                seed=1000 + idx,
            )
            results.append((idx, target_file))

            # Respect rate limit pause between requests
            if idx < len(scenes):
                await asyncio.sleep(inter_request_delay)

    return results


async def generate_thumbnail_background(
    thumbnail_prompt: str,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """Download the raw background image for the thumbnail."""
    async with httpx.AsyncClient() as client:
        await download_image_with_retry(
            client=client,
            prompt=thumbnail_prompt + ", high contrast, cinematic poster composition, 8k",
            output_path=output_path,
            width=width,
            height=height,
            seed=42,
        )
    return output_path


def run_image_generation(
    scenes: List[Scene],
    output_dir: Path,
    width: int = 1920,
    height: int = 1080,
) -> List[Tuple[int, Path]]:
    """Synchronous entry point to run async image generation."""
    return asyncio.run(
        generate_all_scene_images(
            scenes=scenes,
            output_dir=output_dir,
            width=width,
            height=height,
        )
    )
