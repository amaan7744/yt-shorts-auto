#!/usr/bin/env python3
"""
Visual Assigner (FINAL – AUDIO FIRST, DETERMINISTIC)

RESPONSIBILITY:
- Assign visuals AFTER audio exists
- Hook = images only
- Story = 5s videos only
- Assets chosen ONLY from registry
- NO randomness
- NO invented filenames
- Audio duration controls the end
"""

import json
import sys
import subprocess
from pathlib import Path

from assets import (
    VIDEO_ASSET_KEYWORDS,
    HOOK_IMAGE_CATEGORIES,
)

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT_BEATS = Path("beats.json")

ASSET_DIR = Path("asset")
HOOK_DIR = ASSET_DIR / "hook_static"

# ==================================================
# CONSTANTS (LOCKED)
# ==================================================

HOOK_MAX_SECONDS = 3.0
MIN_IMAGE_DURATION = 0.4
VIDEO_DURATION = 5.0

# ==================================================
# UTILS
# ==================================================

def die(msg):
    print(f"[VISUAL] ❌ {msg}", file=sys.stderr)
    sys.exit(1)

def ffprobe_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return float(r.stdout.strip())

# ==================================================
# LOAD SCRIPT
# ==================================================

if not SCRIPT_FILE.exists():
    die("script.txt missing")
if not AUDIO_FILE.exists():
    die("final_audio.wav missing")

lines = [l.strip() for l in SCRIPT_FILE.read_text().splitlines() if l.strip()]
if len(lines) < 6:
    die("Script too short")

# STRUCTURE (LOCKED)
HOOK_LINE = lines[0]
BODY_LINES = lines[1:-1]   # facts → official story → CTA
FINAL_LOOP = lines[-1]

# ==================================================
# AUDIO
# ==================================================

audio_duration = ffprobe_duration(AUDIO_FILE)

# ==================================================
# HOOK IMAGE ASSIGNMENT
# ==================================================

hook_words = [
    w.strip(".,!?").lower()
    for w in HOOK_LINE.split()
    if len(w) > 3
]

hook_images = []
for word in hook_words:
    for img, tags in HOOK_IMAGE_CATEGORIES.items():
        if word in tags:
            hook_images.append(img)
            break

if not hook_images:
    die("No hook images matched hook words")

# Clamp hook duration
hook_duration = min(HOOK_MAX_SECONDS, audio_duration * 0.12)
per_image = max(MIN_IMAGE_DURATION, hook_duration / len(hook_images))

# ==================================================
# STORY VIDEO ASSIGNMENT
# ==================================================

def video_for_line(text, used):
    t = text.lower()
    for asset, tags in VIDEO_ASSET_KEYWORDS.items():
        if asset in used:
            continue
        if any(tag in t for tag in tags):
            path = ASSET_DIR / asset
            if not path.exists():
                die(f"Video asset missing on disk: {asset}")
            return asset
    die(f"No video matches line: {text}")

# ==================================================
# BUILD BEATS
# ==================================================

beats = []
current_time = 0.0
beat_id = 1

# ---- HOOK (IMAGES ONLY)
for img in hook_images:
    beats.append({
        "beat_id": beat_id,
        "type": "image",
        "asset_file": img,
        "start": round(current_time, 3),
        "duration": round(per_image, 3),
    })
    current_time += per_image
    beat_id += 1

# ---- STORY (5s VIDEOS)
used_videos = set()

for line in BODY_LINES:
    asset = video_for_line(line, used_videos)
    used_videos.add(asset)

    beats.append({
        "beat_id": beat_id,
        "type": "video",
        "asset_file": asset,
        "start": round(current_time, 3),
        "duration": VIDEO_DURATION,
        "text": line,
    })

    current_time += VIDEO_DURATION
    beat_id += 1

# ---- FINAL LOOP (VIDEO REUSE ALLOWED)
beats.append({
    "beat_id": beat_id,
    "type": "video",
    "asset_file": list(used_videos)[-1],
    "start": round(current_time, 3),
    "duration": max(0.5, audio_duration - current_time),
    "text": FINAL_LOOP,
})

# ==================================================
# WRITE OUTPUT
# ==================================================

OUTPUT_BEATS.write_text(json.dumps({"beats": beats}, indent=2))

print("✅ Visuals assigned")
print(f"🎞️ Hook images: {len(hook_images)}")
print(f"🎬 Story videos: {len(used_videos)}")
print("🔒 beats.json locked to audio & script")
