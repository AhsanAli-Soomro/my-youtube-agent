"""
Configuration and Environment Management Module
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Root directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"


def _find_binary(name: str, env_var: Optional[str] = None) -> Optional[str]:
    """Find the path of a binary like ffmpeg or ffprobe across PATH and common locations."""
    if env_var and os.getenv(env_var):
        candidate = Path(os.getenv(env_var))
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    which_path = shutil.which(name)
    if which_path:
        return which_path

    common_locations = [
        Path(f"/opt/homebrew/bin/{name}"),
        Path(f"/usr/local/bin/{name}"),
        Path(f"/usr/bin/{name}"),
        Path(f"/bin/{name}"),
        Path(f"C:/ffmpeg/bin/{name}.exe"),
        Path(f"C:/Program Files/ffmpeg/bin/{name}.exe"),
    ]

    for loc in common_locations:
        if loc.is_file() and os.access(loc, os.X_OK):
            return str(loc)

    return None


def _find_default_font() -> str:
    """Find a bold font for video subtitles and thumbnail text."""
    # 1. Local font in assets
    local_font_candidates = [
        FONTS_DIR / "font.ttf",
        FONTS_DIR / "Montserrat-Bold.ttf",
        FONTS_DIR / "BebasNeue-Regular.ttf",
        FONTS_DIR / "Roboto-Bold.ttf",
    ]
    for font_path in local_font_candidates:
        if font_path.is_file():
            return str(font_path)

    # 2. Operating system fonts
    os_candidates = [
        # macOS
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Black.ttf"),
        Path("/System/Library/Fonts/Helvetica.ttc"),
        Path("/Library/Fonts/Arial Bold.ttf"),
        # Linux / Ubuntu (GitHub Actions)
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        # Windows
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/impact.ttf"),
    ]

    for candidate in os_candidates:
        if candidate.is_file():
            return str(candidate)

    # Fallback to font.ttf path even if not yet downloaded
    return str(FONTS_DIR / "font.ttf")


def _find_bg_music() -> str:
    """Find default background music audio file."""
    candidates = [
        ASSETS_DIR / "bg_music.mp3",
        ASSETS_DIR / "bg_music.wav",
        ASSETS_DIR / "music" / "bg_music.mp3",
        ASSETS_DIR / "music" / "bg_music.wav",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return str(ASSETS_DIR / "bg_music.wav")


class Config:
    """Application runtime configuration with type-casting and defaults."""

    # Google Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    # Documentary Content
    LANGUAGE: str = os.getenv("LANGUAGE", "urdu").strip().lower()
    DEFAULT_TOPIC: str = os.getenv(
        "DEFAULT_TOPIC", "The Mysterious Disappearance of Flight 370"
    ).strip()
    TARGET_DURATION_MINUTES: int = int(os.getenv("TARGET_DURATION_MINUTES", "2"))

    # Voiceover (Edge TTS)
    VOICE_NAME: str = os.getenv("VOICE_NAME", "ur-PK-AsadNeural").strip()
    VOICE_RATE: str = os.getenv("VOICE_RATE", "-5%").strip()
    VOICE_PITCH: str = os.getenv("VOICE_PITCH", "-2Hz").strip()

    # Video Settings
    VIDEO_WIDTH: int = int(os.getenv("VIDEO_WIDTH", "1920"))
    VIDEO_HEIGHT: int = int(os.getenv("VIDEO_HEIGHT", "1080"))
    VIDEO_FPS: int = int(os.getenv("VIDEO_FPS", "30"))
    BG_MUSIC_VOLUME: float = float(os.getenv("BG_MUSIC_VOLUME", "0.12"))

    # YouTube Data API
    YOUTUBE_CLIENT_ID: str = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    YOUTUBE_CLIENT_SECRET: str = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    YOUTUBE_REFRESH_TOKEN: str = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()
    YOUTUBE_PRIVACY_STATUS: str = os.getenv("YOUTUBE_PRIVACY_STATUS", "private").strip().lower()
    YOUTUBE_CATEGORY_ID: str = os.getenv("YOUTUBE_CATEGORY_ID", "27").strip()
    UPLOAD_TEASER_SHORT: bool = os.getenv("UPLOAD_TEASER_SHORT", "true").strip().lower() in ("true", "1", "yes")

    # Multi-Platform Marketing & Distribution
    ENABLE_YOUTUBE_COMMENT: bool = os.getenv("ENABLE_YOUTUBE_COMMENT", "true").strip().lower() in ("true", "1", "yes")

    # Facebook Page Graph API
    FACEBOOK_PAGE_ID: str = os.getenv("FACEBOOK_PAGE_ID", "").strip()
    FACEBOOK_PAGE_ACCESS_TOKEN: str = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    ENABLE_FACEBOOK_POST: bool = os.getenv("ENABLE_FACEBOOK_POST", "true").strip().lower() in ("true", "1", "yes")

    # X (Twitter) API v2 (Free Tier OAuth 1.0a User Context)
    TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY", "").strip()
    TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET", "").strip()
    TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
    TWITTER_ACCESS_SECRET: str = os.getenv("TWITTER_ACCESS_SECRET", "").strip()
    ENABLE_TWITTER_THREAD: bool = os.getenv("ENABLE_TWITTER_THREAD", "true").strip().lower() in ("true", "1", "yes")

    # Telegram Channel Broadcast (Bot API)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    ENABLE_TELEGRAM_BROADCAST: bool = os.getenv("ENABLE_TELEGRAM_BROADCAST", "true").strip().lower() in ("true", "1", "yes")

    # Module A: Real-Time Trend Hijacking Settings
    TREND_COUNTRY_CODES: List[str] = [c.strip().upper() for c in os.getenv("TREND_COUNTRY_CODES", "US,PK,IN,GB").split(",") if c.strip()]
    TREND_MAX_TOPICS: int = int(os.getenv("TREND_MAX_TOPICS", "3"))

    # Module B: Automated A/B Title & Thumbnail Optimizer Settings
    AB_TEST_MIN_AGE_HOURS: float = float(os.getenv("AB_TEST_MIN_AGE_HOURS", "6.0"))
    AB_TEST_MAX_AGE_HOURS: float = float(os.getenv("AB_TEST_MAX_AGE_HOURS", "72.0"))
    AB_TEST_MIN_CTR_PERCENT: float = float(os.getenv("AB_TEST_MIN_CTR_PERCENT", "5.0"))
    AB_TEST_MIN_VIEWS_VELOCITY: float = float(os.getenv("AB_TEST_MIN_VIEWS_VELOCITY", "10.0"))

    # Operational Flags
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").strip().lower() in ("true", "1", "yes")

    # Binary & Asset Paths
    FFMPEG_PATH: Optional[str] = _find_binary("ffmpeg", "FFMPEG_PATH")
    FFPROBE_PATH: Optional[str] = _find_binary("ffprobe", "FFPROBE_PATH")
    FONT_PATH: str = _find_default_font()
    BG_MUSIC_PATH: str = _find_bg_music()

    @classmethod
    def validate_for_execution(cls, dry_run: Optional[bool] = None) -> list[str]:
        """Validate critical configuration settings and return list of missing items."""
        is_dry = cls.DRY_RUN if dry_run is None else dry_run
        issues = []

        if not cls.GEMINI_API_KEY:
            issues.append("GEMINI_API_KEY is not set. Get a free API key at https://aistudio.google.com/")

        if not cls.FFMPEG_PATH:
            issues.append(
                "ffmpeg binary not found in PATH or standard directories. "
                "Install it (e.g., `brew install ffmpeg` on macOS or `apt install ffmpeg` on Linux)."
            )

        if not cls.FFPROBE_PATH:
            issues.append(
                "ffprobe binary not found in PATH or standard directories. "
                "Ensure ffprobe is installed alongside ffmpeg."
            )

        if not is_dry:
            if not cls.YOUTUBE_CLIENT_ID or not cls.YOUTUBE_CLIENT_SECRET or not cls.YOUTUBE_REFRESH_TOKEN:
                issues.append(
                    "YouTube OAuth credentials missing (YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, "
                    "YOUTUBE_REFRESH_TOKEN). Run `python get_youtube_token.py` or set DRY_RUN=true."
                )

        return issues
