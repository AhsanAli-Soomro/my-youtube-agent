# 📋 Project Progress & Handover Document

> **Purpose:** This file contains the complete state, architecture, file map, and next steps for the Automated YouTube Documentary Video Creator & Multi-Platform Marketing Agent. Any AI assistant or developer reading this document can immediately pick up right where we left off.

---

## 🤖 Fast Resume Prompt (Copy & Paste to your AI Agent)

Doosre PC par Antigravity ya kisi bhi AI agent ko bas ye copy-paste karein:

```text
README.md aur PROGRESS.md read karo aur mera environment setup kar ke dry-run test chala do.
```

### Complete Detailed Prompt (Optional):
```text
Maine is project ko GitHub se clone kiya hai. Root mein maujood README.md aur PROGRESS.md read karo, virtual environment bana kar requirements.txt install karo, .env configure karo, aur ek 2-minute ka Urdu dry-run test video generate kar ke output dikhao.
```

*(English: "Read README.md and PROGRESS.md, set up the virtual environment, install requirements.txt, ensure .env is ready, and execute a 2-minute Urdu dry-run test video.")*

---

## 1. 🎯 Project Overview

We have built an enterprise-grade, **100% Free, End-to-End Automated Documentary YouTube Creator, Uploader & Multi-Platform Marketing Agent** in **Python**.

Given a topic prompt (or automatically taking the next unused topic from `topics.txt`), the agent:
1. Researches and writes a suspenseful investigative documentary script in authentic **Urdu script**, **Hindi Devanagari**, or **English** (*Info with Ahsan* / *Vox* / *MagnatesMedia* style).
2. Generates complete social marketing copy: YouTube pinned comment question, Facebook storytelling post, X (Twitter) mystery thread, and Telegram broadcast caption.
3. Synthesizes deep voiceover clips via Microsoft `edge-tts` (`ur-PK-AsadNeural` with `-5%` rate and `-2Hz` pitch).
4. Generates 1080p photorealistic dark cinematic illustrations via Pollinations.ai (zero API keys).
5. **Dual Video Rendering (FFmpeg):**
   - **Main 16:9 Long-Form Video (`main_video.mp4`):** Dynamic Ken Burns slow zoom + lower-third subtitle overlay with alpha fading + 12% ambient audio looping.
   - **Vertical 9:16 Teaser Short (`teaser_short.mp4`):** Takes high-intensity hook scenes, crops to 9:16 with blurred background and top/bottom CTA banner (*"WATCH FULL DOCUMENTARY ON CHANNEL 👇"*).
6. **Automated Thumbnail (Pillow):** 16:9 radial vignette, multi-pass drop shadow, thick black contrast stroke, and high-CTR typography.
7. **YouTube Auto-Uploader (YouTube Data API v3):** Uploads `main_video.mp4` with thumbnail and tags, uploads `teaser_short.mp4` as a YouTube Short, and returns published video URLs.
8. **Multi-Platform Marketing Engine (`src/marketing.py`):**
   - Posts pinned discussion comment on YouTube.
   - Posts thumbnail + caption to Facebook Page (Facebook Graph API).
   - Posts connected cliffhanger thread to X / Twitter (X API v2).
   - Broadcasts photo + formatted summary to Telegram Channel (Telegram Bot API).
   - Outputs full campaign preview to `output/marketing_preview.json`.
9. **Topic Queue Management (`src/topic_manager.py`):** Reads `topics.txt`, tracks completion in `completed_topics.txt` so topics never repeat.

---

## 2. 📂 Completed Features & File Inventory

| File Path | Status | Purpose & Description |
| :--- | :---: | :--- |
| `src/config.py` | ✅ Complete | Loads `.env`, auto-discovers `ffmpeg`/`ffprobe`, locates bundled fonts/audio, manages all YouTube & social marketing config flags. |
| `src/topic_manager.py` | ✅ Complete | Manages topic queue from `topics.txt` and records finished runs in `completed_topics.txt`. |
| `src/script_generator.py` | ✅ Complete | Interfaces with Gemini 2.5 Flash. Generates strict JSON documentary script + marks hook scenes (`is_hook_clip`) + crafts social marketing copy. |
| `src/voice_generator.py` | ✅ Complete | Asynchronously synthesizes narration clips per scene via `edge-tts`. Measures exact audio duration using `ffprobe`. |
| `src/image_generator.py` | ✅ Complete | Downloads 1920x1080 scene visuals from Pollinations.ai with exponential backoff retries, dark documentary style modifiers, and 1.5s rate-limit pacing. |
| `src/thumbnail_generator.py` | ✅ Complete | Loads raw background, applies dark radial vignette, renders bold hook typography with drop shadow and outline, saves optimized `< 2MB` `thumbnail.jpg`. |
| `src/video_editor.py` | ✅ Complete | FFmpeg dual renderer: creates 16:9 `main_video.mp4` with Ken Burns & drawtext, plus 9:16 `teaser_short.mp4` with blurred background and CTA banners. |
| `src/uploader.py` | ✅ Complete | YouTube Data API v3 uploader for both Long-form videos and YouTube Shorts, with resumable chunked upload and `DRY_RUN` simulation. |
| `src/marketing.py` | ✅ Complete | Multi-platform distribution engine: YouTube pinned comments, Facebook Pages, X (Twitter) threads, and Telegram broadcasts. |
| `main.py` | ✅ Complete | Central CLI orchestrator connecting all 7 pipeline stages with rich console progress logging and execution summary tables. |
| `topics.txt` | ✅ Complete | Topic queue with 10 high-CTR mystery/history documentary topics. |
| `completed_topics.txt` | ✅ Complete | Historical log of completed runs. |
| `get_youtube_token.py` | ✅ Complete | Interactive OAuth2 helper script that launches local web auth and prints/saves the permanent `YOUTUBE_REFRESH_TOKEN` to `.env`. |
| `assets/fonts/font.ttf` | ✅ Complete | Bundled bold TrueType font for subtitle overlays and thumbnail text. |
| `assets/bg_music.wav` | ✅ Complete | Layered suspenseful dark ambient drone audio loop (44.1kHz stereo). |
| `.env.example` | ✅ Complete | Comprehensive template with all configurable variables and documentation. |
| `.env` | ✅ Complete | Local configuration file (contains user's Gemini API key; ignored by git). |
| `requirements.txt` | ✅ Complete | All pinned Python dependencies including `tweepy`, `edge-tts`, `pillow`, `pydantic`. |
| `.github/workflows/pipeline.yml` | ✅ Complete | GitHub Actions workflow for scheduled daily runs or manual trigger with topic override. |
| `README.md` | ✅ Complete | Full documentation, setup instructions, social API setup guides, and architecture flowcharts. |

---

## 3. 🚦 Current Status & Known Context

1. **Remote Repository:**
   - GitHub Repository: [https://github.com/AhsanAli-Soomro/my-youtube-agent](https://github.com/AhsanAli-Soomro/my-youtube-agent)
   - Branch: `main`
2. **Current Machine State:**
   - Codebase fully updated, syntax validated with `py_compile`.
   - Local `.env` contains the user's active Gemini API key.
   - `ffmpeg` is **not** installed on this initial staging machine (user will run on their target PC).
3. **Active Credentials:**
   - Gemini API Key is saved in `.env`.
   - Social media keys (Facebook, Twitter, Telegram) are optional and cleanly bypassed if blank.
   - System is configured in safe `DRY_RUN=true` mode.

---

## 4. 💻 Environment & Setup Notes (For Target PC)

### Setup Commands on Target PC:

```bash
# 1. Clone repository
git clone https://github.com/AhsanAli-Soomro/my-youtube-agent.git
cd my-youtube-agent

# 2. Install FFmpeg
# On Windows (PowerShell):
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

# 5. Create .env file (copy from .env.example and insert your GEMINI_API_KEY)
```

### Critical Environment Variables (`.env`):
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
LANGUAGE=urdu
VOICE_NAME=ur-PK-AsadNeural
VOICE_RATE=-5%
VOICE_PITCH=-2Hz
UPLOAD_TEASER_SHORT=true
DRY_RUN=true
```

---

## 5. 🎯 Immediate Next Steps

When resuming work on the new computer:

1. **Run Initial Dry-Run Test:**
   ```bash
   python main.py --dry-run
   ```
   *(Picks the next topic from `topics.txt` and generates `main_video.mp4`, `teaser_short.mp4`, `thumbnail.jpg`, `metadata.json`, and `marketing_preview.json`)*.
2. **Inspect Generated Outputs:**
   Check the folder inside `output/`:
   - `main_video.mp4`: Verify Ken Burns zoom, Urdu subtitle box, and 12% ambient audio.
   - `teaser_short.mp4`: Verify 9:16 vertical crop with blurred background and CTA banner.
   - `thumbnail.jpg`: Verify dark vignette and bold contrast typography.
   - `marketing_preview.json`: Review YouTube pinned comment, Facebook post, Twitter thread, and Telegram post.
3. **Configure YouTube & Social Accounts (When Ready for Live Publishing):**
   - Run `python get_youtube_token.py` to authenticate YouTube.
   - (Optional) Fill in Facebook Page, X (Twitter), or Telegram Bot keys in `.env`.
4. **Trigger Live Automated Campaign:**
   ```bash
   python main.py --live
   ```
