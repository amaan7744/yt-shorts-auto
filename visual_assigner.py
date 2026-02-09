#!/usr/bin/env python3
"""
Visual Assigner — SCRIPT-LOCKED (NO TIME GUESSING)
=================================================

RULES:
- Script structure is the source of truth
- 2 images for hook (line 1)
- 1 video per remaining script line
- No fillers, no reuse, no duration math
- Timing is handled downstream (speech-locked)

This file ONLY assigns WHAT appears, not WHEN.
"""

import json
import sys
from pathlib import Path

from assets import (
    VIDEO_ASSET_KEYWORDS,
    HOOK_IMAGE_CATEGORIES,
)

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")
OUTPUT_FILE = Path("beats.json")

ASSET_DIR = Path("asset")
HOOK_DIR = ASSET_DIR / "hook_static"

# ==================================================
# UTILS
# ==================================================

def die(msg):
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(1)

# ==================================================
# LOAD SCRIPT
# ==================================================

if not SCRIPT_FILE.exists():
    die("script.txt not found")

lines = [l.strip() for l in SCRIPT_FILE.read_text().splitlines() if l.strip()]

if len(lines) != 7:
    die(f"Script must contain exactly 7 lines, got {len(lines)}")

HOOK_LINE = lines[0]
STORY_LINES = lines[1:]  # body + CTA + loop

print("=" * 70)
print("🎬 VISUAL ASSIGNER — SCRIPT LOCKED")
print("=" * 70)
print(f"📝 Script lines: {len(lines)} (1 hook + 6 story)")

# ==================================================
# HOOK IMAGE SELECTION (DETERMINISTIC)
# ==================================================

def select_hook_images(text: str, count: int = 2) -> list:
    words = [
        w.strip(".,!?\"'").lower()
        for w in text.split()
        if len(w) > 3
    ]

    selected = []
    used = set()

    # Keyword match first
    for word in words:
        for img, keywords in HOOK_IMAGE_CATEGORIES.items():
            if img in used:
                continue
            if any(kw in word or word in kw for kw in keywords):
                selected.append(img)
                used.add(img)
                break
        if len(selected) == count:
            break

    # Deterministic fallback
    if len(selected) < count:
        for img in sorted(HOOK_IMAGE_CATEGORIES.keys()):
            if img not in used:
                selected.append(img)
            if len(selected) == count:
                break

    if len(selected) != count:
        die("Not enough hook images available")

    return selected

hook_images = select_hook_images(HOOK_LINE)

# ==================================================
# VIDEO SELECTION (ONE LINE = ONE VIDEO)
# ==================================================

def select_video_for_line(text: str, used: set) -> str:
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

    # Deterministic fallback
    if not best_video:
        for video in sorted(VIDEO_ASSET_KEYWORDS.keys()):
            if video not in used:
                best_video = video
                break

    if not best_video:
        die("Ran out of available videos")

    if not (ASSET_DIR / best_video).exists():
        die(f"Missing video asset: {best_video}")

    return best_video

# ==================================================
# BUILD BEATS (ORDER ONLY, NO TIMING)
# ==================================================

beats = []
beat_id = 1
used_videos = set()

print("\n📍 HOOK VISUALS")
for img in hook_images:
    beats.append({
        "beat_id": beat_id,
        "type": "image",
        "asset_file": f"hook_static/{img}",
        "script_line": 1,
        "role": "hook"
    })
    print(f"  [{beat_id:02d}] 🖼️  hook_static/{img}")
    beat_id += 1

print("\n📍 STORY VISUALS")
for idx, line in enumerate(STORY_LINES, start=2):
    video = select_video_for_line(line, used_videos)
    used_videos.add(video)

    beats.append({
        "beat_id": beat_id,
        "type": "video",
        "asset_file": video,
        "script_line": idx,
        "role": "story",
        "text": line
    })

    print(f"  [{beat_id:02d}] 🎞️  {video} — line {idx}")
    beat_id += 1

# ==================================================
# SAVE OUTPUT
# ==================================================

OUTPUT_FILE.write_text(json.dumps({"beats": beats}, indent=2))

print("\n" + "=" * 70)
print("✅ VISUAL ASSIGNMENT COMPLETE")
print("=" * 70)
print(f"🖼️  Hook images: {len(hook_images)}")
print(f"🎞️  Story videos: {len(used_videos)}")
print(f"📦 Total beats: {len(beats)}")
print(f"💾 Saved to: {OUTPUT_FILE}")
print("=" * 70)
