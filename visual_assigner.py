#!/usr/bin/env python3
"""
VISUAL ASSIGNER — PRODUCTION TIMELINE MODE
==========================================

✔ Script is source of truth
✔ Semantic keyword scoring
✔ No visual reuse
✔ Deterministic fallback
✔ Durations derived from audio
✔ Total visual time == audio duration
✔ Builder-ready timeline

This file decides:
- what visual appears
- how long it stays
"""

import json
import subprocess
import sys
from pathlib import Path

from assets import VIDEO_ASSET_KEYWORDS, HOOK_IMAGE_CATEGORIES


# ==========================================================
# FILES
# ==========================================================

SCRIPT_FILE = Path("script.txt")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT_FILE = Path("beats.json")

ASSET_DIR = Path("asset")
HOOK_DIR = ASSET_DIR / "hook_static"


# ==========================================================
# UTILS
# ==========================================================

def die(msg):
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(1)


def tokenize(text: str) -> set:
    return {
        w.strip(".,!?\"'():").lower()
        for w in text.split()
        if len(w) > 3
    }


def get_audio_duration(path: Path) -> float:
    """Get audio duration using ffprobe"""
    if not path.exists():
        die("Audio file missing")

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(path)
        ],
        capture_output=True,
        text=True
    )

    try:
        return float(result.stdout.strip())
    except:
        die("Could not detect audio duration")


# ==========================================================
# LOAD SCRIPT
# ==========================================================

if not SCRIPT_FILE.exists():
    die("script.txt missing")

lines = [l.strip() for l in SCRIPT_FILE.read_text().splitlines() if l.strip()]

if len(lines) < 2:
    die("Script too short")

HOOK_LINE = lines[0]
STORY_LINES = lines[1:]

print("=" * 70)
print("🎬 VISUAL ASSIGNER — TIMELINE MODE")
print("=" * 70)
print(f"📝 Script lines: {len(lines)}")

# ==========================================================
# AUDIO DURATION
# ==========================================================

audio_duration = get_audio_duration(AUDIO_FILE)
print(f"🔊 Audio duration: {audio_duration:.2f}s")

# allocate duration by text length proportion
weights = [len(l.split()) for l in lines]
total_weight = sum(weights)

durations = [
    (w / total_weight) * audio_duration
    for w in weights
]

# rounding fix to ensure perfect total match
diff = audio_duration - sum(durations)
durations[-1] += diff


# ==========================================================
# HOOK IMAGE SELECTION
# ==========================================================

def select_hook_images(text: str, count=2):
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

    # deterministic fallback
    if len(selected) < count:
        for img in sorted(HOOK_IMAGE_CATEGORIES.keys()):
            if img not in selected and (HOOK_DIR / img).exists():
                selected.append(img)
            if len(selected) == count:
                break

    if len(selected) != count:
        die("Not enough hook images")

    return selected


# ==========================================================
# VIDEO SELECTION — NO REUSE
# ==========================================================

def select_video_for_line(text: str, used: set):
    words = tokenize(text)

    scored = []
    for video, keywords in VIDEO_ASSET_KEYWORDS.items():
        if video in used:
            continue

        score = sum(1 for k in keywords if k in words)
        if score > 0:
            scored.append((score, video))

    if scored:
        scored.sort(reverse=True)
        return scored[0][1]

    for video in sorted(VIDEO_ASSET_KEYWORDS.keys()):
        if video not in used:
            return video

    die("Ran out of video assets")


# ==========================================================
# BUILD TIMELINE
# ==========================================================

beats = []
beat_id = 1
used_videos = set()

hook_images = select_hook_images(HOOK_LINE)

print("\n📍 HOOK VISUALS")

# split hook duration across hook images
hook_duration = durations[0] / len(hook_images)

for img in hook_images:
    beats.append({
        "beat_id": beat_id,
        "type": "image",
        "asset_file": f"hook_static/{img}",
        "duration": hook_duration,
        "script_line": 1,
        "role": "hook"
    })
    print(f"  [{beat_id:02d}] 🖼️ {img} ({hook_duration:.2f}s)")
    beat_id += 1


print("\n📍 STORY VISUALS")

for idx, (line, duration) in enumerate(
    zip(STORY_LINES, durations[1:]), start=2
):

    video = select_video_for_line(line, used_videos)

    if not (ASSET_DIR / video).exists():
        die(f"Missing video asset: {video}")

    used_videos.add(video)

    beats.append({
        "beat_id": beat_id,
        "type": "video",
        "asset_file": video,
        "duration": duration,
        "script_line": idx,
        "role": "story",
        "text": line
    })

    print(f"  [{beat_id:02d}] 🎞️ {video} ({duration:.2f}s)")
    beat_id += 1


# ==========================================================
# FINAL VALIDATION
# ==========================================================

timeline_total = sum(b["duration"] for b in beats)

if abs(timeline_total - audio_duration) > 0.01:
    die("Timeline duration mismatch with audio")

print(f"\n⏱️ Timeline duration: {timeline_total:.2f}s (perfect match)")

# ==========================================================
# SAVE
# ==========================================================

OUTPUT_FILE.write_text(json.dumps({"beats": beats}, indent=2))

print("\n" + "=" * 70)
print("✅ VISUAL TIMELINE READY")
print("=" * 70)
print(f"🎞️ Unique videos: {len(used_videos)}")
print(f"📦 Beats: {len(beats)}")
print(f"💾 Saved: {OUTPUT_FILE}")
print("=" * 70)
