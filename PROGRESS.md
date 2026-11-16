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

---

## 1. 🎯 Project Overview

We have built an enterprise-grade, **100% Free, End-to-End Automated Documentary YouTube Creator, Uploader, Trend Hijacker & A/B Optimizer** in **Python**.

### Complete System Pipeline:
1. **Module A (Trend Hunter):** Real-time RSS & Reddit scraper that filters breaking mysteries/anomalies via Gemini and prepends them to `topics.txt`.
2. **Script & Scene Director (Gemini 2.5 Flash):** Researches and writes a suspenseful investigative documentary script in authentic Urdu script, Devanagari Hindi, or English, generating 3 pre-computed A/B test title/thumbnail variants (`variant_a`, `variant_b`, `variant_c`).
3. **Voiceover Synthesis (Edge-TTS):** Neural narration (`ur-PK-AsadNeural` with `-5%` rate and `-2Hz` pitch).
4. **Visual Generation (Pollinations.ai):** 1080p photorealistic dark cinematic illustrations (zero API keys).
5. **Dual Video Renderer (FFmpeg):**
   - **16:9 Long-Form Video (`main_video.mp4`):** Ken Burns zoom + subtitles with fade transitions + 12% ambient audio.
   - **9:16 Vertical Teaser Short (`teaser_short.mp4`):** High-intensity hook clips formatted with blurred 9:16 background, sharp center visual, and top/bottom CTA banners.
6. **Thumbnail Generator (Pillow):** Renders all 3 A/B test thumbnail variants with radial vignette, drop shadows, and high-contrast typography.
7. **YouTube Auto-Uploader (YouTube Data API v3):** Uploads long-form video with thumbnail & tags, uploads teaser as a YouTube Short (`#Shorts`), and registers the video into `data/published_videos.json`.
8. **Multi-Platform Marketing Engine (`src/marketing.py`):**
   - YouTube pinned discussion question.
   - Facebook Page storytelling post + photo.
   - X (Twitter) connected cliffhanger thread.
   - Telegram Channel photo broadcast + markdown caption.
9. **Module B (A/B Optimizer):** Monitors videos 6 to 72 hours old. If CTR < 5% or view velocity is low, autonomously swaps live YouTube Title and Thumbnail to untested variants.

---

## 2. 📂 Completed Features & File Inventory

| File Path | Status | Purpose & Description |
| :--- | :---: | :--- |
| `src/config.py` | ✅ Complete | Loads `.env`, auto-discovers binaries, assets, growth settings, and all social marketing API flags. |
| `src/topic_manager.py` | ✅ Complete | Manages topic queue from `topics.txt` and records finished runs in `completed_topics.txt`. |
| `src/trend_hunter.py` | ✅ Complete | **Module A:** Fetches Google Trends RSS + Reddit hot feeds, filters with Gemini, prepends top viral angles to `topics.txt`. |
| `src/ab_optimizer.py` | ✅ Complete | **Module B:** Checks 6-72hr old videos, tracks performance in `data/published_videos.json`, and swaps live titles/thumbnails. |
| `src/script_generator.py` | ✅ Complete | Generates documentary script, marks hook clips (`is_hook_clip`), produces social marketing copy, and outputs 3 A/B content variants. |
| `src/voice_generator.py` | ✅ Complete | Asynchronously synthesizes narration clips per scene via `edge-tts`. Measures exact audio duration using `ffprobe`. |
| `src/image_generator.py` | ✅ Complete | Downloads 1920x1080 scene visuals from Pollinations.ai with exponential backoff retries and 1.5s rate-limit pacing. |
| `src/thumbnail_generator.py` | ✅ Complete | Pillow vignette & typography compositor. Supports rendering multiple A/B hook variants. |
| `src/video_editor.py` | ✅ Complete | FFmpeg dual renderer: creates 16:9 `main_video.mp4` and 9:16 vertical `teaser_short.mp4`. |
| `src/uploader.py` | ✅ Complete | YouTube Data API v3 uploader for both Long-form videos and YouTube Shorts, with resumable chunked upload. |
| `src/marketing.py` | ✅ Complete | Multi-platform distribution engine: YouTube pinned comments, Facebook Pages, X (Twitter) threads, and Telegram broadcasts. |
| `main.py` | ✅ Complete | Central CLI orchestrator connecting all modules with flags: `--dry-run`, `--live`, `--hunt-trends`, `--optimize-ab`. |
| `hunt_trends.py` | ✅ Complete | Standalone 1-line CLI runner for Module A (Trend Hunter). |
| `optimize_ab.py` | ✅ Complete | Standalone 1-line CLI runner for Module B (A/B Optimizer). |
| `data/published_videos.json` | ✅ Complete | Local state file tracking uploaded video IDs, variant metadata, and swap history. |
| `topics.txt` | ✅ Complete | Topic queue with curated and trend-injected mystery topics. |
| `completed_topics.txt` | ✅ Complete | Historical log of completed topics. |
| `get_youtube_token.py` | ✅ Complete | Updated OAuth2 helper requesting `youtube.upload`, `youtube.force-ssl`, and `yt-analytics.readonly`. |
| `package.json` | ✅ Complete | NPM script shortcuts: `npm run hunt-trends`, `npm run optimize-ab`, `npm run dry-run`. |
| `.github/workflows/pipeline.yml` | ✅ Complete | Daily video production and marketing workflow. |
| `.github/workflows/growth_optimizer.yml` | ✅ Complete | 6-hour cron workflow executing Trend Hunting and A/B Optimization. |
| `README.md` | ✅ Complete | Comprehensive documentation and API configuration guide. |

---

## 3. 🖥️ Second PC Setup & Handover Checklist

### 1. File Connections to Main Pipeline
- **`src/trend_hunter.py`** connects to **`topics.txt`**: When run, it feeds new high-performing topics into the top of the queue so `main.py` picks them up automatically.
- **`src/ab_optimizer.py`** connects to **`data/published_videos.json`**: When `main.py` finishes uploading or testing a video, it automatically registers the video's 3 pre-generated A/B variants. Then `ab_optimizer.py` checks them every 6 hours and updates live YouTube metadata if needed.

### 2. Required `.env` Variables & Google Cloud OAuth Scopes
Ensure your `.env` on the second PC includes:
```env
# 1. Gemini AI Key (Required)
GEMINI_API_KEY=your_gemini_api_key_here

# 2. YouTube OAuth Credentials (For live uploading & A/B swapping)
YOUTUBE_CLIENT_ID=your_client_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your_client_secret
YOUTUBE_REFRESH_TOKEN=your_refresh_token

# 3. Growth Modules Configuration
TREND_COUNTRY_CODES=US,PK,IN,GB
TREND_MAX_TOPICS=3
AB_TEST_MIN_AGE_HOURS=6.0
AB_TEST_MAX_AGE_HOURS=72.0
AB_TEST_MIN_CTR_PERCENT=5.0
AB_TEST_MIN_VIEWS_VELOCITY=10.0

# 4. Mode
DRY_RUN=true
```

> [!IMPORTANT]
> **Google Cloud Console Scopes:**
> When running `python get_youtube_token.py` on the second PC, the helper script now automatically requests all 3 required scopes:
> - `https://www.googleapis.com/auth/youtube.upload` (Video uploads)
> - `https://www.googleapis.com/auth/youtube.force-ssl` (Title & thumbnail A/B swapping + comments)
> - `https://www.googleapis.com/auth/yt-analytics.readonly` (Performance & CTR monitoring)
>
> In Google Cloud Console, ensure both **YouTube Data API v3** and **YouTube Analytics API** are enabled.

### 3. Local Data & State Files
The following state files are initialized in the repository and ready on the second PC:
- `topics.txt`: Topic queue (trend hunter prepends to this file).
- `completed_topics.txt`: Prevents duplicate topics.
- `data/published_videos.json`: Tracks video variants and A/B test histories.

### 4. Exact Terminal Commands to Test on the Second PC

#### A. Test Module A (Real-Time Trend Hunter):
```bash
python hunt_trends.py
# Or via main CLI:
python main.py --hunt-trends
# Or via npm:
npm run hunt-trends
```
*Expected Result:* Fetches headlines from Google Trends (US/PK/IN/GB) and Reddit, scores them with Gemini, and prepends the top 3 viral mystery topics to `topics.txt`.

#### B. Test Module B (A/B Title & Thumbnail Optimizer):
```bash
python optimize_ab.py
# Or via main CLI:
python main.py --optimize-ab
# Or via npm:
npm run optimize-ab
```
*Expected Result:* Inspects `data/published_videos.json`, evaluates performance windows (6–72h), and simulates title/thumbnail swaps for underperforming videos.

#### C. Run Full End-to-End Production & Marketing (Dry Run):
```bash
python main.py --dry-run
```
*Expected Result:* Picks the top trending topic from `topics.txt`, generates long-form 16:9 video, 9:16 teaser short, all 3 A/B thumbnail variants (`thumbnail_a.jpg`, `thumbnail_b.jpg`, `thumbnail_c.jpg`), registers the video for A/B tracking in `data/published_videos.json`, and outputs `marketing_preview.json`.
