#!/usr/bin/env python3
"""
VISUAL ASSIGNER — STRICT NO-EXTENSION ENGINE
===========================================

RULES
✔ Script is source of truth
✔ No visual duration extension
✔ No frame freezing
✔ No zoom/stretch
✔ No reuse inside same video
✔ Exact audio timeline match
✔ Multiple visuals per narration segment if needed
✔ Fail if asset pool insufficient
"""

import json
import subprocess
import sys
from pathlib import Path

from assets import VIDEO_ASSET_KEYWORDS, HOOK_IMAGE_CATEGORIES


SCRIPT_FILE = Path("script.txt")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT_FILE = Path("beats.json")

ASSET_DIR = Path("asset")
HOOK_DIR = ASSET_DIR / "hook_static"


# ==================================================
# UTILS
# ==================================================

def die(msg):
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(1)


def tokenize(text):
    return {
        w.strip(".,!?\"'():").lower()
        for w in text.split()
        if len(w) > 3
    }


def get_media_duration(path: Path):
    """Get video/audio duration using ffprobe"""
    r = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)],
        capture_output=True,text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        die(f"Could not read duration for {path}")


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

audio_duration = get_media_duration(AUDIO_FILE)

print("="*70)
print("🎬 VISUAL ASSIGNER — STRICT NO EXTENSION")
print("="*70)
print("🔊 Audio duration:", round(audio_duration,2))


# ==================================================
# ALLOCATE TIMELINE FROM SCRIPT LENGTH
# ==================================================

weights = [len(l.split()) for l in lines]
total_weight = sum(weights)

segment_durations = [(w/total_weight)*audio_duration for w in weights]

# rounding fix
segment_durations[-1] += audio_duration - sum(segment_durations)


# ==================================================
# LOAD VIDEO DURATIONS
# ==================================================

VIDEO_DURATIONS = {}

for video in VIDEO_ASSET_KEYWORDS.keys():
    path = ASSET_DIR / video
    if not path.exists():
        continue
    VIDEO_DURATIONS[video] = get_media_duration(path)

if not VIDEO_DURATIONS:
    die("No video assets found")


# ==================================================
# SEMANTIC VIDEO SELECTION
# ==================================================

def select_video(text, used):
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

    # deterministic fallback
    for video in sorted(VIDEO_ASSET_KEYWORDS.keys()):
        if video not in used:
            return video

    return None


# ==================================================
# HOOK IMAGE SELECTION
# ==================================================

def select_hook_images(text, count=2):
    words = tokenize(text)

    scored = []
    for img, keywords in HOOK_IMAGE_CATEGORIES.items():
        score = sum(1 for k in keywords if k in words)
        scored.append((score, img))

    scored.sort(reverse=True)

    selected = []
    for _, img in scored:
        if (HOOK_DIR/img).exists():
            selected.append(img)
        if len(selected)==count:
            break

    if len(selected)!=count:
        die("Not enough hook images")

    return selected


# ==================================================
# BUILD TIMELINE
# ==================================================

beats=[]
used_videos=set()
beat_id=1

hook_images = select_hook_images(HOOK_LINE)

# hook duration split
hook_duration = segment_durations[0]/len(hook_images)

for img in hook_images:
    beats.append({
        "beat_id":beat_id,
        "type":"image",
        "asset_file":f"hook_static/{img}",
        "duration":hook_duration,
        "role":"hook"
    })
    beat_id+=1


print("\n📍 STORY TIMELINE")

for line, seg_duration in zip(STORY_LINES, segment_durations[1:]):

    remaining = seg_duration

    while remaining > 0.01:

        video = select_video(line, used_videos)

        if not video:
            die("Not enough unique video assets to cover timeline")

        used_videos.add(video)

        asset_duration = VIDEO_DURATIONS[video]

        use_time = min(asset_duration, remaining)

        beats.append({
            "beat_id":beat_id,
            "type":"video",
            "asset_file":video,
            "duration":use_time,
            "text":line
        })

        print(f"[{beat_id:02d}] {video} ({use_time:.2f}s)")

        beat_id+=1
        remaining -= use_time


# ==================================================
# FINAL VALIDATION
# ==================================================

timeline_total=sum(b["duration"] for b in beats)

if abs(timeline_total-audio_duration)>0.01:
    die("Timeline does not match audio duration")

print("\n⏱️ Timeline:",round(timeline_total,2),"seconds")

OUTPUT_FILE.write_text(json.dumps({"beats":beats},indent=2))

print("\n✅ Timeline ready")
print("Unique videos used:",len(used_videos))
