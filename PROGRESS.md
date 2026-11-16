# 📋 Project Progress & Handover Document

> **Purpose:** This file contains the complete state, architecture, file map, and next steps for the Automated YouTube Documentary Video Generator & Uploader project. Any AI assistant or developer reading this document can immediately pick up right where we left off.

---

## 1. 🎯 Project Overview

We are building a **100% Free, End-to-End Automated Documentary YouTube Video Generator & Uploader** pipeline in **Python**.

The system takes a single historical, crime, or mystery topic prompt (e.g., *"The Disappearance of Flight 370"*), produces a high-retention investigative documentary video (in **Urdu**, **Hindi**, or **English**) in the style of *Info with Ahsan*, *Vox*, and *MagnatesMedia*, composites a click-worthy thumbnail, and uploads the video directly to YouTube.

### Zero-Cost / 100% Free Tech Stack:
- **Language / Runtime:** Python 3.9+ (Modular async architecture)
- **Script & Scene Director:** Google Gemini Free API (`gemini-2.5-flash`) via `@google/generative-ai` / `google-genai`
- **Voiceover Synthesis:** Microsoft `edge-tts` (Free neural voices: `ur-PK-AsadNeural` for Urdu, `hi-IN-MadhurNeural` for Hindi, `en-US-ChristopherNeural` for English)
- **Visual Assets:** Pollinations.ai 1080p photorealistic illustrations (100% free, no API key required)
- **Video Editing & Rendering:** FFmpeg (Dynamic Ken Burns slow zoom, lower-third subtitle overlay with alpha fading, audio concatenation, 12% ambient background music loop)
- **Thumbnail Generator:** Pillow (16:9, radial vignette, multi-pass drop shadow, thick black contrast stroke, high-CTR YouTube yellow/white typography)
- **YouTube Auto-Uploader:** Official `google-api-python-client` with OAuth2 Refresh Token authentication, resumable chunked video upload, custom thumbnail attachment, and `DRY_RUN` simulation
- **CI/CD Automation:** GitHub Actions (`.github/workflows/auto_publish.yml`) for scheduled and manual workflow dispatch

---

## 2. 📂 Completed Features & File Inventory

All core modules have been fully implemented, tested for Python syntax (`py_compile`), and pushed to GitHub:

| File Path | Status | Purpose & Description |
| :--- | :---: | :--- |
| `src/config.py` | ✅ Complete | Loads `.env`, auto-discovers `ffmpeg`/`ffprobe` binaries across system PATHs, locates bundled fonts and ambient audio, provides pre-flight validation. |
| `src/script_generator.py` | ✅ Complete | Interfaces with Gemini API. Paces video with a 5-second mystery hook, escalating anomalies, and twist climax. Generates strict JSON with Pydantic validation (title, description, tags, thumbnail prompt, hook text, and scene breakdown in authentic Urdu/Hindi script). |
| `src/voice_generator.py` | ✅ Complete | Asynchronously synthesizes narration clips per scene via `edge-tts`. Measures exact audio duration using `ffprobe`. |
| `src/image_generator.py` | ✅ Complete | Downloads 1920x1080 scene visuals from Pollinations.ai with exponential backoff retries, dark documentary style modifiers, and 1.5s rate-limit pacing. |
| `src/thumbnail_generator.py` | ✅ Complete | Loads raw background, applies dark radial vignette, renders bold hook typography with drop shadow and outline, saves optimized `< 2MB` `thumbnail.jpg`. |
| `src/video_editor.py` | ✅ Complete | Renders individual scenes with monotonic Ken Burns zoompan and subtitle overlays, concatenates clips using concat demuxer, and mixes looped background audio at 12% volume into `output.mp4`. |
| `src/uploader.py` | ✅ Complete | YouTube Data API v3 uploader with resumable upload, custom thumbnail attachment, and a comprehensive `DRY_RUN=true` simulation mode. |
| `main.py` | ✅ Complete | Central CLI orchestrator connecting all 6 pipeline stages with rich console progress logging and execution summary tables. |
| `get_youtube_token.py` | ✅ Complete | Interactive OAuth2 helper script that launches local web auth and prints/saves the permanent `YOUTUBE_REFRESH_TOKEN` to `.env`. |
| `assets/fonts/font.ttf` | ✅ Complete | Bundled bold TrueType font for subtitle overlays and thumbnail text. |
| `assets/bg_music.wav` | ✅ Complete | Layered suspenseful dark ambient drone audio loop (44.1kHz stereo). |
| `.env.example` | ✅ Complete | Template with all configurable variables and documentation. |
| `.env` | ✅ Complete | Local configuration file (contains user's Gemini API key; ignored by git). |
| `requirements.txt` | ✅ Complete | All pinned Python dependencies. |
| `.github/workflows/auto_publish.yml` | ✅ Complete | GitHub Actions workflow for scheduled (cron) or manual (`workflow_dispatch`) video production. |
| `README.md` | ✅ Complete | Full documentation, setup instructions, voice tables, and architecture flowcharts. |

---

## 3. 🚦 Current Status & Known Context

1. **Remote Repository:**
   - GitHub Repository: [https://github.com/AhsanAli-Soomro/my-youtube-agent](https://github.com/AhsanAli-Soomro/my-youtube-agent)
   - Branch: `main` (Fully up to date with initial commit `ec5eec2`).
2. **Current Machine State:**
   - This machine was used to scaffold the codebase and push to GitHub.
   - `ffmpeg` is **not** installed on this initial machine, because the user explicitly stated they will run the agent on their **other PC**.
3. **Active Credentials:**
   - User's Gemini API key has been added to `.env` on this machine:
     ```env
     GEMINI_API_KEY=your_gemini_api_key_here
     ```
   - YouTube OAuth credentials (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`) are not yet configured; the system is currently configured for `DRY_RUN=true` mode.

---

## 4. 💻 Environment & Setup Notes (For Target PC)

### System Requirements:
- Python 3.9+
- FFmpeg & FFprobe (Must be accessible in system PATH or configured via `FFMPEG_PATH` in `.env`)

### Setup Commands on Target PC:

```bash
# 1. Clone repository
git clone https://github.com/AhsanAli-Soomro/my-youtube-agent.git
cd my-youtube-agent

# 2. Install FFmpeg
# On Windows (Run in PowerShell):
winget install Gyan.FFmpeg
# On macOS:
brew install ffmpeg
# On Ubuntu/Linux:
sudo apt update && sudo apt install -y ffmpeg

# 3. Create & activate Python virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Create .env file
# (Copy from .env.example and insert your GEMINI_API_KEY)
```

### Critical Environment Variables (`.env`):
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
LANGUAGE=urdu
VOICE_NAME=ur-PK-AsadNeural
VOICE_RATE=-5%
VOICE_PITCH=-2Hz
DRY_RUN=true
```

---

## 5. 🎯 Immediate Next Steps

When resuming work on the new computer:

1. **Run Initial Dry-Run Verification:**
   Execute the complete pipeline in dry-run mode to verify script generation, voiceover synthesis, image fetching, video rendering, and thumbnail generation:
   ```bash
   python main.py --topic "The Mysterious Disappearance of Flight 370" --duration 2 --lang urdu --dry-run
   ```
2. **Inspect Generated Artifacts:**
   Check the newly created folder in `output/` to inspect:
   - `output.mp4` (Check Ken Burns motion, subtitle legibility, and background music mix).
   - `thumbnail.jpg` (Check vignette, typography contrast, and formatting).
   - `metadata.json` (Verify title, description, tags, and Urdu script quality).
3. **Configure YouTube Upload (When Ready for Live Publishing):**
   - Create OAuth Desktop credentials in Google Cloud Console with YouTube Data API v3 enabled.
   - Run the helper script on the target computer:
     ```bash
     python get_youtube_token.py
     ```
   - Follow the browser prompt to grant permissions. The script will save the refresh token to `.env`.
4. **Execute Live Production Run:**
   ```bash
   python main.py --topic "The Dark Secrets of the Bermuda Triangle" --duration 2 --live
   ```
5. **(Optional) Configure GitHub Actions Secrets:**
   Add `GEMINI_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and `YOUTUBE_REFRESH_TOKEN` to GitHub Repository Secrets to enable automated cloud publishing on a schedule.
