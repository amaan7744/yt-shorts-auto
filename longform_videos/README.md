# 🎬 TrueCrime Auto-YouTube Pipeline

A fully automated, modular Python pipeline that researches viral true crime stories, writes scripts, generates narration, assembles cinematic videos, burns subtitles, and uploads to YouTube — twice a week, hands-free.

---

## 📁 Repository Structure

```
true-crime-pipeline/
│
├── .github/
│   └── workflows/
│       ├── tuesday_upload.yml          # Fires every Tuesday 2PM EST
│       └── friday_upload.yml           # Fires every Friday 2PM EST
│
├── 01_research/
│   └── scraper.py                      # Reddit + News scraper & story scorer
│
├── 02_script/
│   └── script_writer.py                # Groq (Llama 3) script generator
│
├── 03_audio/
│   └── tts_generator.py                # Your TTS code (plug in here)
│
├── 04_visuals/
│   ├── prompt_generator.py             # Groq writes image prompts per scene
│   ├── pollinations_fetch.py           # Free AI image generation (no key needed)
│   ├── asset_manager.py                # Smart clip picker from /assets folder
│   ├── proof_scraper.py                # Scrapes real news/Wikipedia evidence images
│   └── visual_assembler.py             # FFmpeg: layers everything + proof animation
│
├── 05_subtitles/
│   └── whisper_subtitles.py            # Whisper transcription → burned into video
│
├── 06_sfx/
│   └── sfx_matcher.py                  # Matches tension SFX to script beat tags
│
├── 07_render/
│   └── renderer.py                     # FFmpeg final assembly → 1080p MP4
│
├── 08_metadata/
│   └── metadata_generator.py           # Groq generates title, description, tags
│
├── 09_upload/
│   └── youtube_uploader.py             # YouTube Data API v3 auto-upload
│
├── assets/
│   ├── video/                          # YOUR crime b-roll clips go here
│   │   ├── tags.json                   # Maps each clip to mood tags
│   │   └── usage_log.json              # Tracks which clips used per video
│   └── sfx/                            # Your SFX files go here
│       └── tags.json                   # Maps each SFX to scene type
│
├── output/                             # Final rendered videos saved here
├── logs/                               # Pipeline run logs
├── pipeline.py                         # Master orchestrator
├── config.yaml                         # All settings in one place
└── requirements.txt
```

---

## ⚙️ Pipeline Flow — Stage by Stage

### Stage 1 — Research `01_research/scraper.py`

Scrapes stories from:
- **Reddit**: `r/UnresolvedMysteries`, `r/TrueCrime`, `r/criminalminds`, `r/wheredidthesodago`
- **Google News RSS**: "true crime", "murder case", "missing person", "cold case"
- **NewsAPI**: crime/mystery category, US region, sorted by popularity

Each story is scored by:
- Upvote/engagement count
- Recency (last 7 days weighted higher)
- Emotional hook keywords (betrayal, missing, identity, conspiracy)
- Has real evidence/proof images available

Top scoring story wins. A `used_stories.json` dedup log prevents repeating stories across videos.

**Output:** `story.json` — raw story data, sources, image URLs, key facts

---

### Stage 2 — Script `02_script/script_writer.py`

Feeds `story.json` into **Groq API running Llama 3** (ultra-fast inference).

Enforces this structure per video (5–10 min target):
- **Cold open hook** (0:00–0:30) — Most shocking fact first, no context yet
- **Story build** (0:30–5:00) — Chronological tension escalation with scene tags
- **Twist reveal** (5:00–8:30) — The turn the audience didn't see coming
- **Outro** (8:30–end) — Channel CTA, "what do YOU think happened?"

Script outputs structured JSON — every line tagged with:

```json
{
  "timestamp_start": 14.2,
  "narration": "Nobody reported her missing for three full days.",
  "scene_type": "dramatic",
  "mood": "tense",
  "image_prompt": "empty bedroom dark window rain cinematic noir",
  "asset_tags": ["dark", "indoor", "night"],
  "proof_image": null,
  "proof_duration_sec": null
}
```

```json
{
  "timestamp_start": 47.8,
  "narration": "Court documents obtained by investigators revealed something chilling.",
  "scene_type": "proof",
  "mood": "reveal",
  "image_prompt": null,
  "asset_tags": null,
  "proof_image": "court_document_scan.jpg",
  "proof_duration_sec": 5.0
}
```

**Output:** `script.json`

---

### Stage 3 — Audio `03_audio/tts_generator.py`

Your existing TTS code plugs in here. It receives the `narration` field from each `script.json` line and returns:
- Audio file per segment (or single combined file)
- Exact duration per segment (in seconds)

Durations feed back into `script.json` so visuals sync perfectly to speech.

**Output:** `audio_segments/` folder + `audio_final.mp3`

---

### Stage 4 — Visuals `04_visuals/`

Three visual layers work together:

#### Layer 1 — Asset Video Clips `asset_manager.py`
For `scene_type: cinematic` scenes — the AI picks from your personal `/assets/video/` library.

**How clip selection works:**
1. Groq reads the narration text and scene mood tag
2. Matches against `assets/video/tags.json` — each clip has mood tags like `["dark", "outdoor", "rain", "street"]`
3. Picks best matching clip that hasn't been used yet in this video
4. Trims clip to exact narration duration, or loops seamlessly if narration is longer
5. Logs used clip to `usage_log.json` — never repeats in same video

**Your `assets/video/tags.json` format:**
```json
{
  "clip_001.mp4": ["dark", "street", "night", "rain", "outdoor"],
  "clip_002.mp4": ["indoor", "shadows", "room", "dark", "suspense"],
  "clip_003.mp4": ["police", "lights", "outdoor", "night", "tension"],
  "clip_004.mp4": ["forest", "fog", "outdoor", "eerie", "nature"]
}
```

#### Layer 2 — AI Dramatic Images `pollinations_fetch.py`
For `scene_type: dramatic` scenes — Groq generates a cinematic image prompt, sent to **Pollinations.ai** (100% free, no API key, no limits).

```python
# Zero cost, zero signup — just a URL call:
url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1920&height=1080&nologo=true"
```

FFmpeg applies slow Ken Burns push-in on the image to create motion.

#### Layer 3 — Real Proof Images `proof_scraper.py`
For `scene_type: proof` scenes — scrapes real images from:
- News article images (with source credit overlay burned in bottom-right)
- Wikipedia images of suspects, victims, locations
- Newspaper headline screenshots
- Google Images via SerpAPI (free tier)

**Proof Animation (FFmpeg):**
```
1. Background dims to 40% brightness
2. Proof image slides in from RIGHT → lands center screen (3:2 aspect ratio)
3. Rounded corners + drop shadow applied
4. Source credit burned bottom-right: "Source: NYT, 2019"
5. Holds for proof_duration_sec (from script.json)
6. Slides back out to RIGHT → background returns full brightness
```

---

### Stage 5 — Subtitles `05_subtitles/whisper_subtitles.py`

Whisper runs locally on `audio_final.mp3`:
- Generates word-level timestamps
- Styles: white text, dark stroke, bottom-center, 48px bold
- Burns directly into video via FFmpeg `subtitles` filter

No separate SRT file exported — burned in only.

---

### Stage 6 — SFX `06_sfx/sfx_matcher.py`

Reads `mood` tag per scene from `script.json`. Maps to SFX from `/assets/sfx/`:

| Mood Tag | SFX Type |
|---|---|
| `tense` | Low heartbeat drone |
| `reveal` | Sharp news sting / dramatic hit |
| `eerie` | Ambient dark hum |
| `action` | Police radio crackle |
| `sad` | Soft distant piano |
| `hook` | Sudden silence then impact |

SFX layered under narration at 15% volume so voice always sits on top clearly.

Source for free CC0 SFX: [freesound.org](https://freesound.org) — download once, store in `/assets/sfx/`.

---

### Stage 7 — Render `07_render/renderer.py`

FFmpeg assembles everything in one pass:
```
Video clips + AI images (Layer 1 + 2)
    + Proof slide animations (Layer 3)
    + Narration audio
    + SFX layer
    + Burned subtitles
    → output/final_video.mp4 (1080p, H264, AAC)
```

---

### Stage 8 — Metadata `08_metadata/metadata_generator.py`

Groq generates all YouTube metadata from the script:

- **Title**: Click-optimized true crime formula (e.g. *"She Vanished for 3 Days. Her Husband Had No Explanation."*)
- **Description**: 500-word SEO description with timestamps, keywords, sources cited
- **Tags**: 30 tags — mix of broad (`true crime`, `mystery`) and specific to the case
- **Thumbnail prompt**: Detailed image prompt for you to generate manually or automate

All saved to `output/metadata.json`.

---

### Stage 9 — Upload `09_upload/youtube_uploader.py`

YouTube Data API v3:
- Uploads `final_video.mp4`
- Sets title, description, tags from `metadata.json`
- Sets category: `25` (News & Politics — best for true crime reach)
- Visibility: `public`
- Scheduled for **2:00 PM EST** (peak US traffic slot)
- Logs video URL + video ID to `logs/upload_log.json`

---

## 🕐 GitHub Actions Schedule

```yaml
# Tuesday: 2PM EST = 19:00 UTC
cron: "0 19 * * 2"

# Friday: 2PM EST = 19:00 UTC
cron: "0 19 * * 5"
```

Both upload days target **2PM EST** — consistently the highest-traffic window for true crime content on YouTube in the US market (Tuesday and Friday afternoons outperform all other slots for this niche).

---

## 🔑 Full Free Tech Stack

| Tool | Purpose | Cost |
|---|---|---|
| **Groq API (Llama 3)** | Script writing + image prompts + metadata | Free |
| **Pollinations.ai** | AI dramatic image generation | Free forever, no key |
| **Your `/assets/video/`** | Main background video clips | Free (yours) |
| **Whisper (local)** | Subtitle generation | Free |
| **Wikipedia API** | Real images of people/places | Free |
| **NewsAPI** | Story research | Free tier |
| **Reddit PRAW** | Viral story scraping | Free |
| **SerpAPI** | Google image search for proof | Free (100/mo) |
| **Freesound.org** | SFX library (download once) | Free CC0 |
| **FFmpeg** | All video assembly | Free |
| **YouTube Data API v3** | Auto-upload | Free |
| **GitHub Actions** | Automated scheduling | Free (2000 min/mo) |

---

## 🔧 config.yaml

```yaml
# === RESEARCH ===
research:
  subreddits:
    - UnresolvedMysteries
    - TrueCrime
    - criminalminds
  news_keywords:
    - "true crime"
    - "murder case"
    - "missing person"
    - "cold case"
    - "unsolved murder"
  story_lookback_days: 7
  min_score_threshold: 500

# === SCRIPT ===
script:
  target_duration_min: 5
  target_duration_max: 10
  structure: "cold_open_hook_twist"
  groq_model: "llama3-70b-8192"

# === VISUALS ===
visuals:
  video_resolution: "1920x1080"
  proof_aspect_ratio: "3:2"
  proof_slide_direction: "right"
  proof_animation_duration_sec: 0.4
  background_dim_during_proof: 0.4
  ken_burns_zoom_factor: 1.08

# === SUBTITLES ===
subtitles:
  font: "Arial"
  font_size: 48
  color: "white"
  stroke_color: "black"
  stroke_width: 2
  position: "bottom_center"

# === SFX ===
sfx:
  volume_under_narration: 0.15

# === UPLOAD ===
upload:
  schedule_time_est: "14:00"
  youtube_category_id: "25"
  visibility: "public"

# === PATHS ===
paths:
  assets_video: "./assets/video/"
  assets_sfx: "./assets/sfx/"
  output: "./output/"
  logs: "./logs/"
  used_stories: "./logs/used_stories.json"
  clip_usage_log: "./assets/video/usage_log.json"
```

---

## 🚀 How to Set Up

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/true-crime-pipeline.git
cd true-crime-pipeline
pip install -r requirements.txt
```

**2. Add your video assets**
Drop your crime b-roll clips into `/assets/video/` and fill in `tags.json` with mood tags for each clip.

**3. Add your SFX**
Download free CC0 SFX from freesound.org, drop into `/assets/sfx/`, fill in `tags.json`.

**4. Set GitHub Secrets**
```
GROQ_API_KEY
YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN
NEWSAPI_KEY
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
SERPAPI_KEY
```

**5. Push to GitHub**
GitHub Actions handles the rest — fires Tuesday + Friday at 2PM EST automatically.

---

## 📦 requirements.txt

```
groq
praw
newsapi-python
google-api-python-client
google-auth-oauthlib
openai-whisper
requests
Pillow
ffmpeg-python
yt-dlp
serpapi
python-dotenv
pyyaml
```

---

## ✅ Build Order (Recommended)

Build and test each module independently before wiring to `pipeline.py`:

1. `01_research/scraper.py` — Confirm it finds good stories
2. `02_script/script_writer.py` — Confirm script JSON structure is correct
3. `03_audio/tts_generator.py` — Plug in your TTS, confirm timing output
4. `04_visuals/asset_manager.py` — Confirm clip selection + loop/trim logic
5. `04_visuals/pollinations_fetch.py` — Confirm AI images generate correctly
6. `04_visuals/proof_scraper.py` — Confirm real evidence images scrape correctly
7. `04_visuals/visual_assembler.py` — Confirm proof slide animation in FFmpeg
8. `05_subtitles/whisper_subtitles.py` — Confirm subtitles burn correctly
9. `06_sfx/sfx_matcher.py` — Confirm SFX match and layer at correct volume
10. `07_render/renderer.py` — Confirm full video assembles cleanly
11. `08_metadata/metadata_generator.py` — Confirm metadata JSON output
12. `09_upload/youtube_uploader.py` — Test with unlisted video first
13. `pipeline.py` — Wire all stages, test full run end to end
14. `.github/workflows/` — Set schedules, confirm GitHub Actions fires correctly
