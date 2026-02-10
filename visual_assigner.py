#!/usr/bin/env python3
"""
Visual Assigner — STRICT MODE (PRODUCTION SAFE)
===============================================

RULES (NON-NEGOTIABLE):
- Script is the ONLY source of truth
- 1 visual per script line
- NO video reuse in the same output
- Semantic keyword scoring (no randomness)
- Deterministic fallback (still no reuse)
- NO timing, NO duration, NO audio logic

This file answers ONE question:
➡️ What visual appears for each script line
"""

import json
import sys
from pathlib import Path

from assets import VIDEO_ASSET_KEYWORDS, HOOK_IMAGE_CATEGORIES

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

def tokenize(text: str) -> set:
    return {
        w.strip(".,!?\"'():").lower()
        for w in text.split()
        if len(w) > 3
    }

# ==================================================
# LOAD SCRIPT
# ==================================================

if not SCRIPT_FILE.exists():
    die("script.txt missing")

lines = [l.strip() for l in SCRIPT_FILE.read_text().splitlines() if l.strip()]

if len(lines) < 2:
    die("Script too short")

HOOK_LINE = lines[0]
STORY_LINES = lines[1:]

print("=" * 70)
print("🎬 VISUAL ASSIGNER — STRICT SEMANTIC MODE")
print("=" * 70)
print(f"📝 Script lines: {len(lines)}")

# ==================================================
# HOOK IMAGE SELECTION (KEYWORD SCORING)
# ==================================================

def select_hook_images(text: str, count: int = 2) -> list:
    words = tokenize(text)

    scored = []
    for img, keywords in HOOK_IMAGE_CATEGORIES.items():
        score = sum(1 for k in keywords if k in words)
        scored.append((score, img))

    scored.sort(reverse=True)

    selected = []
    for score, img in scored:
        if score <= 0:
            break
        if (HOOK_DIR / img).exists():
            selected.append(img)
        if len(selected) == count:
            break

    # Deterministic fallback (still no randomness)
    if len(selected) < count:
        for img in sorted(HOOK_IMAGE_CATEGORIES.keys()):
            if img not in selected and (HOOK_DIR / img).exists():
                selected.append(img)
            if len(selected) == count:
                break

    if len(selected) != count:
        die("Not enough hook images available")

    return selected

hook_images = select_hook_images(HOOK_LINE)

# ==================================================
# VIDEO SELECTION — SEMANTIC + NO REUSE
# ==================================================

def select_video_for_line(text: str, used: set) -> str:
    words = tokenize(text)

    scored = []
    for video, keywords in VIDEO_ASSET_KEYWORDS.items():
        if video in used:
            continue

        score = sum(1 for k in keywords if k in words)
        if score > 0:
            scored.append((score, video))

    # Highest semantic match wins
    if scored:
        scored.sort(reverse=True)
        return scored[0][1]

    # Deterministic fallback: first unused, sorted
    for video in sorted(VIDEO_ASSET_KEYWORDS.keys()):
        if video not in used:
            return video

    die("Ran out of video assets — increase asset pool")

# ==================================================
# BUILD BEATS (ORDER ONLY)
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
    print(f"  [{beat_id:02d}] 🖼️ {img}")
    beat_id += 1

print("\n📍 STORY VISUALS")

for idx, line in enumerate(STORY_LINES, start=2):
    video = select_video_for_line(line, used_videos)

    if not (ASSET_DIR / video).exists():
        die(f"Missing video asset: {video}")

    used_videos.add(video)

    beats.append({
        "beat_id": beat_id,
        "type": "video",
        "asset_file": video,
        "script_line": idx,
        "role": "story",
        "text": line
    })

    print(f"  [{beat_id:02d}] 🎞️ {video} (line {idx})")
    beat_id += 1

# ==================================================
# SAVE OUTPUT
# ==================================================

OUTPUT_FILE.write_text(json.dumps({"beats": beats}, indent=2))

print("\n" + "=" * 70)
print("✅ VISUAL ASSIGNMENT COMPLETE")
print("=" * 70)
print(f"🖼️ Hook images: {len(hook_images)}")
print(f"🎞️ Unique videos used: {len(used_videos)}")
print(f"📦 Total beats: {len(beats)}")
print(f"💾 Saved to: {OUTPUT_FILE}")
print("=" * 70)
