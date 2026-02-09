#!/usr/bin/env python3
"""
Visual Assigner — CONTENT ONLY (SPEECH-LOCKED PIPELINE)
======================================================

RESPONSIBILITY:
✔ Assign visuals to script lines
✔ Preserve hook → story structure
✔ Never assign durations
✔ Never reuse assets
✔ Never add filler
✔ Never drop lines

Timing is handled STRICTLY by the video builder.
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
# UTILS
# ==================================================

def die(msg):
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(1)

def get_audio_duration(path: Path) -> float:
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
# LOAD INPUTS
# ==================================================

if not SCRIPT_FILE.exists():
    die("script.txt missing")

if not AUDIO_FILE.exists():
    die("final_audio.wav missing")

lines = [l.strip() for l in SCRIPT_FILE.read_text().splitlines() if l.strip()]

if len(lines) < 2:
    die("Script too short (need hook + story)")

HOOK_LINE = lines[0]
STORY_LINES = lines[1:]

audio_duration = get_audio_duration(AUDIO_FILE)

print("=" * 70)
print("📋 VISUAL ASSIGNER — CONTENT ONLY")
print("=" * 70)
print(f"🎵 Audio duration: {audio_duration:.2f}s")
print(f"📝 Script lines: {len(lines)} (1 hook + {len(STORY_LINES)} story)")

# ==================================================
# HOOK IMAGE SELECTION
# ==================================================

def select_hook_images(text: str, max_images: int = 2) -> list:
    words = [
        w.strip(".,!?\"'").lower()
        for w in text.split()
        if len(w) > 3
    ]

    matched = []
    used = set()

    print("\n🔍 Selecting hook images:")

    for word in words:
        if len(matched) >= max_images:
            break

        best_img = None
        best_score = 0

        for img, keywords in HOOK_IMAGE_CATEGORIES.items():
            if img in used:
                continue

            score = sum(1 for kw in keywords if kw in word or word in kw)
            if score > best_score:
                best_score = score
                best_img = img

        if best_img:
            matched.append(best_img)
            used.add(best_img)
            print(f"  ✓ '{word}' → {best_img}")

    # Fallback if weak keyword match
    if len(matched) < max_images:
        for img in HOOK_IMAGE_CATEGORIES:
            if img not in used and len(matched) < max_images:
                matched.append(img)
                used.add(img)
                print(f"  + [fallback] → {img}")

    return matched

hook_images = select_hook_images(HOOK_LINE)

if not hook_images:
    die("No hook images selected")

# ==================================================
# VIDEO SELECTION
# ==================================================

def select_video(text: str, used: set) -> str:
    text_lower = text.lower()
    best_video = None
    best_score = 0

    for video, keywords in VIDEO_ASSET_KEYWORDS.items():
        if video in used:
            continue

        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_video = video

    if not best_video:
        for video in VIDEO_ASSET_KEYWORDS:
            if video not in used:
                best_video = video
                break

    if not best_video:
        die("Ran out of videos — add more assets")

    if not (ASSET_DIR / best_video).exists():
        die(f"Missing video file: {best_video}")

    return best_video

# ==================================================
# BUILD BEATS (NO DURATIONS)
# ==================================================

beats = []
beat_id = 1
used_videos = set()

print("\n" + "=" * 70)
print("BUILDING BEATS (NO TIMING)")
print("=" * 70)

# ---- HOOK ----
print("\n📍 HOOK:")
for img in hook_images:
    beats.append({
        "beat_id": beat_id,
        "type": "image",
        "asset_file": f"hook_static/{img}",
        "role": "hook"
    })
    print(f"  [{beat_id:02d}] 🖼️  hook_static/{img}")
    beat_id += 1

# ---- STORY ----
print("\n📍 STORY:")
for line in STORY_LINES:
    video = select_video(line, used_videos)
    used_videos.add(video)

    beats.append({
        "beat_id": beat_id,
        "type": "video",
        "asset_file": video,
        "text": line,
        "role": "story"
    })

    print(f"  [{beat_id:02d}] 🎞️  {video} — {line[:50]}...")
    beat_id += 1

# ==================================================
# OUTPUT
# ==================================================

OUTPUT_BEATS.write_text(json.dumps({"beats": beats}, indent=2))

print("\n" + "=" * 70)
print("✅ BEATS GENERATED (CONTENT-LOCKED)")
print("=" * 70)
print(f"📊 Total beats: {len(beats)}")
print(f"🖼️  Hook images: {len(hook_images)}")
print(f"🎞️  Story videos: {len(used_videos)}")
print(f"⏱️  Timing: deferred to video builder")
print(f"\n💾 Saved: {OUTPUT_BEATS}")
print("=" * 70)
