"""
Automated YouTube Thumbnail Generator using Pillow
Produces high-CTR, dramatic mystery documentary thumbnails with cinematic vignettes,
bold typography, drop shadows, and high-contrast outlines.
"""

import logging
import math
import textwrap
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from src.config import Config

logger = logging.getLogger("youtube_agent.thumbnail")


def _get_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType font with graceful fallback to Pillow default font."""
    resolved_path = font_path or Config.FONT_PATH
    if resolved_path and Path(resolved_path).is_file():
        try:
            return ImageFont.truetype(resolved_path, size=size)
        except Exception as e:
            logger.warning(f"Could not load font from '{resolved_path}' ({e}), falling back...")

    # System fallback search
    for sys_font in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        if Path(sys_font).is_file():
            try:
                return ImageFont.truetype(sys_font, size=size)
            except Exception:
                pass

    return ImageFont.load_default()


def apply_cinematic_vignette(image: Image.Image) -> Image.Image:
    """Apply a dark gradient vignette to enhance dramatic tension and text legibility."""
    width, height = image.size

    # Boost contrast and slight desaturation for documentary look
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.15)

    # Create vignette mask (radial falloff from center)
    mask = Image.new("L", (width, height), 0)
    center_x, center_y = width / 2.0, height / 2.0
    max_radius = math.hypot(center_x, center_y)

    # Pixel array manipulation for smooth radial gradient
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)

    # Draw bottom/left gradient for text placement
    for y in range(height):
        # Darkness increases towards the bottom
        bottom_factor = max(0.0, (y - height * 0.35) / (height * 0.65))
        alpha = int(180 * (bottom_factor ** 1.5))
        v_draw.line([(0, y), (width, y)], fill=(5, 5, 10, alpha))

    # Corner darkness
    for r in range(int(max_radius * 0.5), int(max_radius), 8):
        factor = (r - max_radius * 0.5) / (max_radius * 0.5)
        alpha = int(140 * factor)
        bbox = [
            center_x - r,
            center_y - r * (height / width),
            center_x + r,
            center_y + r * (height / width),
        ]
        v_draw.ellipse(bbox, outline=(0, 0, 0, alpha), width=10)

    # Composite vignette over background
    base = image.convert("RGBA")
    composite = Image.alpha_composite(base, vignette)
    return composite.convert("RGB")


def render_thumbnail_text(
    image: Image.Image,
    text: str,
    font_path: Optional[str] = None,
    text_color: str = "#FFDD00",  # High-CTR YouTube Yellow
    stroke_color: str = "#000000",
) -> Image.Image:
    """Render punchy, bold 2-4 word hook text with heavy drop shadow and outline."""
    canvas = image.convert("RGBA")
    width, height = canvas.size

    clean_text = text.strip().upper()
    # Wrap text into 1 or 2 punchy lines max
    words = clean_text.split()
    if len(words) >= 4:
        lines = [
            " ".join(words[: len(words) // 2]),
            " ".join(words[len(words) // 2 :]),
        ]
    elif len(words) >= 3:
        lines = [" ".join(words[:2]), words[2]]
    else:
        lines = [clean_text]

    formatted_text = "\n".join(lines)

    # Dynamically find the largest font size that fits comfortably
    target_width = width * 0.85
    font_size = int(height * 0.22)  # Starting large font size (~160px on 720p)
    min_size = 48

    font = _get_font(font_path, font_size)

    # Measure text bounding box
    dummy_img = Image.new("RGB", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)

    while font_size > min_size:
        font = _get_font(font_path, font_size)
        bbox = dummy_draw.textbbox((0, 0), formatted_text, font=font, spacing=14)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if text_w <= target_width and text_h <= (height * 0.55):
            break
        font_size -= 6

    # Position: Bottom-center or slightly shifted left for classic YouTube documentary look
    bbox = dummy_draw.textbbox((0, 0), formatted_text, font=font, spacing=14)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pos_x = (width - text_w) / 2
    pos_y = height - text_h - int(height * 0.12)  # 12% padding from bottom

    # 1. Create drop shadow layer
    shadow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)

    shadow_offset = max(6, int(font_size * 0.08))
    shadow_draw.text(
        (pos_x + shadow_offset, pos_y + shadow_offset),
        formatted_text,
        font=font,
        fill=(0, 0, 0, 220),
        spacing=14,
        align="center",
    )
    # Blur shadow for soft realistic depth
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=8))

    # 2. Create crisp text with heavy stroke
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    stroke_width = max(4, int(font_size * 0.07))
    text_draw.text(
        (pos_x, pos_y),
        formatted_text,
        font=font,
        fill=text_color,
        stroke_width=stroke_width,
        stroke_fill=stroke_color,
        spacing=14,
        align="center",
    )

    # 3. Composite layers: Base + Shadow + Text
    combined = Image.alpha_composite(canvas, shadow_layer)
    combined = Image.alpha_composite(combined, text_layer)

    return combined.convert("RGB")


def create_documentary_thumbnail(
    raw_image_path: Path,
    output_path: Path,
    hook_text: str,
    font_path: Optional[str] = None,
    width: int = 1280,
    height: int = 720,
) -> Path:
    """Complete thumbnail generation pipeline: load, resize, vignette, text, optimize."""
    logger.info(f"Generating thumbnail with hook text: '{hook_text}'...")

    if not raw_image_path.is_file():
        raise FileNotFoundError(f"Source image '{raw_image_path}' does not exist.")

    with Image.open(raw_image_path) as img:
        # Resize to standard YouTube 16:9 thumbnail size (1280x720)
        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)

        # Apply cinematic dark vignette
        img_vignette = apply_cinematic_vignette(img_resized)

        # Render high-contrast hook typography
        final_thumb = render_thumbnail_text(
            img_vignette,
            text=hook_text,
            font_path=font_path,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        # YouTube requires thumbnail file size < 2MB
        final_thumb.save(output_path, "JPEG", quality=92, optimize=True)

    logger.info(
        f"Thumbnail successfully created: {output_path} ({output_path.stat().st_size // 1024} KB)"
    )
    return output_path
