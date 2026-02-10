#!/usr/bin/env python3
"""
Visual Assigner v4 — SCRIPT INTENT LOCKED
========================================

RULES:
- Script structure is the source of truth
- 2 hook images for line 1
- 1 unique video per remaining script line
- NO random choice
- NO reuse
- Uses ONLY assets declared in asset registry
- Keyword + intent weighted selection
- NO duration logic (speech-locked downstream)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

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
STORY_LINES = lines[1:]  # lines 2–7

print("=" * 70)
print("🎬 VISUAL ASSIGNER v4 — SCRIPT INTENT LOCKED")
print("=" * 70)

# ==================================================
# SCRIPT INTENT CLASSIFICATION
# ==================================================

def classify_line_intent(text: str) -> str:
    t = text.lower()

    if "?" in t:
        return "question"
    if any(w in t for w in ["police", "investigation", "official", "authorities"]):
        return "investigation"
    if any(w in t for w in ["found", "discovered", "body", "dead", "death"]):
        return "discovery"
    if any(w in t for w in ["child", "boy", "girl"]):
        return "child"
    if any(w in t for w in ["car", "road", "drive", "vehicle"]):
        return "vehicle"
    if any(w in t for w in ["room", "bedroom", "bathroom", "apartment"]):
        return "interior"
    return "generic"

# ==================================================
# HOOK IMAGE SELECTION (STRICT, NO RANDOM)
# ==================================================

def select_hook_images(text: str, count: int = 2) -> list:
    words = {w.strip(".,!?\"'").lower() for w in text.split() if len(w) > 3}

    scored = []
    for img, keywords in HOOK_IMAGE_CATEGORIES.items():
        score = len(words.intersection(keywords))
        if score > 0:
            scored.append((score, img))

    scored.sort(reverse=True)

    selected = [img for _, img in scored[:count]]

    # Deterministic fallback (first N declared)
    if len(selected) < count:
        for img in HOOK_IMAGE_CATEGORIES.keys():
            if img not in selected:
                selected.append(img)
            if len(selected) == count:
                break

    if len(selected) != count:
        die("Not enough hook images available")

    return selected

# ==================================================
# VIDEO POOL PREPARATION
# ==================================================

unused_videos = set(VIDEO_ASSET_KEYWORDS.keys())

def score_video(text: str, video: str) -> int:
    text_words = set(text.lower().split())
    keywords = set(VIDEO_ASSET_KEYWORDS[video])
    return len(text_words.intersection(keywords))

# ==================================================
# VIDEO SELECTION (NO REUSE, NO RANDOM)
# ==================================================

def select_video_for_line(text: str) -> str:
    global unused_videos

    intent = classify_line_intent(text)

    scored = []
    for video in unused_videos:
        score = score_video(text, video)
        scored.append((score, video))

    scored.sort(reverse=True)

    # Prefer keyword matches
    if scored and scored[0][0] > 0:
        chosen = scored[0][1]
    else:
        # Intent-based fallback (rotation, not alphabetical)
        for video in unused_videos:
            kws = VIDEO_ASSET_KEYWORDS[video]
            if intent == "discovery" and "body" in kws:
                chosen = video
                break
            if intent == "investigation" and "evidence" in kws:
                chosen = video
                break
            if intent == "interior" and "room" in kws:
                chosen = video
                break
            if intent == "vehicle" and "car" in kws:
                chosen = video
                break
        else:
            # Final fallback: first unused (only if absolutely needed)
            chosen = next(iter(unused_videos))

    unused_videos.remove(chosen)
    return chosen

# ==================================================
# BUILD BEATS
# ==================================================

beats = []
beat_id = 1

# ---- HOOK ----
print("\n📍 HOOK VISUALS")
hook_images = select_hook_images(HOOK_LINE)

for img in hook_images:
    beats.append({
        "beat_id": beat_id,
        "type": "image",
        "asset_file": f"hook_static/{img}",
        "script_line": 1,
        "role": "hook"
    })
    print(f"  [{beat_id:02d}] 🖼️  {img}")
    beat_id += 1

# ---- STORY ----
print("\n📍 STORY VISUALS")

for idx, line in enumerate(STORY_LINES, start=2):
    if not unused_videos:
        die("Ran out of unique videos — add more assets")

    video = select_video_for_line(line)

    beats.append({
        "beat_id": beat_id,
        "type": "video",
        "asset_file": video,
        "script_line": idx,
        "role": "story",
        "text": line
    })

    print(f"  [{beat_id:02d}] 🎞️  {video}  ← line {idx}")
    beat_id += 1

# ==================================================
# SAVE
# ==================================================

OUTPUT_FILE.write_text(json.dumps({"beats": beats}, indent=2))

print("\n" + "=" * 70)
print("✅ VISUAL ASSIGNMENT COMPLETE (v4)")
print("=" * 70)
print(f"🖼️  Hook images: {len(hook_images)}")
print(f"🎞️  Story videos: {len(beats) - len(hook_images)}")
print(f"📦 Total beats: {len(beats)}")
print(f"💾 Saved to: {OUTPUT_FILE}")
print("=" * 70)
