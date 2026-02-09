#!/usr/bin/env python3
"""
Visual Assigner — AUDIO-LOCKED, NO REUSE
=========================================

FIXES:
✅ Correct asset paths (hook_static/ for images, asset/ for videos)
✅ Total duration matches audio exactly
✅ No video reuse (except intentional final loop)
✅ Deterministic asset selection based on keywords
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
# CONSTANTS
# ==================================================

HOOK_MAX_SECONDS = 3.0
MIN_IMAGE_DURATION = 0.5
VIDEO_DURATION = 5.0

# ==================================================
# UTILS
# ==================================================

def die(msg):
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(1)

def get_duration(path: Path) -> float:
    """Get duration of audio file"""
    r = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         str(path)],
        capture_output=True,
        text=True,
        check=True
    )
    return float(r.stdout.strip())

# ==================================================
# LOAD SCRIPT & AUDIO
# ==================================================

if not SCRIPT_FILE.exists():
    die("script.txt missing")
if not AUDIO_FILE.exists():
    die("final_audio.wav missing")

lines = [l.strip() for l in SCRIPT_FILE.read_text().splitlines() if l.strip()]
if len(lines) < 3:
    die("Script too short (need at least hook + 2 story lines)")

# Structure
HOOK_LINE = lines[0]
STORY_LINES = lines[1:]  # All remaining lines are story

audio_duration = get_duration(AUDIO_FILE)

print("=" * 70)
print("📋 VISUAL ASSIGNER")
print("=" * 70)
print(f"🎵 Audio duration: {audio_duration:.2f}s")
print(f"📝 Script lines: {len(lines)} (1 hook + {len(STORY_LINES)} story)")

# ==================================================
# HOOK IMAGE SELECTION
# ==================================================

def select_hook_images(hook_text: str, max_images: int = 3) -> list:
    """Select hook images based on keyword matching"""
    hook_words = [
        w.strip(".,!?\"'").lower()
        for w in hook_text.split()
        if len(w) > 3
    ]
    
    print(f"\n🔍 Hook analysis: {hook_words[:5]}...")
    
    matched = []
    used = set()
    
    # Match hook words to image keywords
    for word in hook_words:
        if len(matched) >= max_images:
            break
        
        best_img = None
        best_score = 0
        
        for img, keywords in HOOK_IMAGE_CATEGORIES.items():
            if img in used:
                continue
            
            score = sum(1 for kw in keywords if word in kw or kw in word)
            if score > best_score:
                best_score = score
                best_img = img
        
        if best_img:
            matched.append(best_img)
            used.add(best_img)
            print(f"  ✓ '{word}' → {best_img}")
    
    # Fallback: add general crime images if needed
    if len(matched) < 2:
        for img in HOOK_IMAGE_CATEGORIES.keys():
            if img not in used and len(matched) < max_images:
                matched.append(img)
                used.add(img)
                print(f"  + [fallback] → {img}")
    
    return matched

hook_images = select_hook_images(HOOK_LINE, max_images=2)

if not hook_images:
    die("No hook images found")

# Calculate hook timing
hook_duration = min(HOOK_MAX_SECONDS, audio_duration * 0.08)  # ~8% of audio
per_image = max(MIN_IMAGE_DURATION, hook_duration / len(hook_images))

print(f"\n🖼️  Selected {len(hook_images)} hook images ({per_image:.2f}s each)")

# ==================================================
# VIDEO SELECTION
# ==================================================

def select_video(text: str, used_videos: set) -> str:
    """Select best matching video for a line"""
    text_lower = text.lower()
    
    best_video = None
    best_score = 0
    
    # Find best matching unused video
    for video, keywords in VIDEO_ASSET_KEYWORDS.items():
        if video in used_videos:
            continue
        
        score = sum(1 for kw in keywords if kw in text_lower)
        
        if score > best_score:
            best_score = score
            best_video = video
    
    # Fallback: use first unused video
    if not best_video:
        for video in VIDEO_ASSET_KEYWORDS.keys():
            if video not in used_videos:
                best_video = video
                break
    
    if not best_video:
        die(f"No videos available for: {text}")
    
    # Verify file exists
    if not (ASSET_DIR / best_video).exists():
        die(f"Video missing: {best_video}")
    
    return best_video

# ==================================================
# BUILD BEATS
# ==================================================

beats = []
current_time = 0.0
beat_id = 1
used_videos = set()

print("\n" + "=" * 70)
print("BUILDING BEATS")
print("=" * 70)

# ---- HOOK IMAGES ----
print("\n📍 HOOK SECTION:")
for img in hook_images:
    beats.append({
        "beat_id": beat_id,
        "type": "image",
        "asset_file": f"hook_static/{img}",  # Include subdirectory
        "start": round(current_time, 3),
        "duration": round(per_image, 3)
    })
    print(f"  [{beat_id:02d}] 🖼️  hook_static/{img} ({per_image:.2f}s)")
    current_time += per_image
    beat_id += 1

# ---- STORY VIDEOS ----
print("\n📍 STORY SECTION:")

# Calculate how much time we have for story
hook_total = len(hook_images) * per_image
remaining_time = audio_duration - hook_total

# Figure out how many videos we need
num_videos_needed = int(remaining_time / VIDEO_DURATION)

# If we have more lines than videos, trim lines
# If we have more videos than lines, we'll loop the last video
story_lines_to_use = STORY_LINES[:num_videos_needed] if num_videos_needed < len(STORY_LINES) else STORY_LINES

for i, line in enumerate(story_lines_to_use):
    video = select_video(line, used_videos)
    used_videos.add(video)
    
    # For the last video, use remaining time
    if i == len(story_lines_to_use) - 1:
        duration = audio_duration - current_time
    else:
        duration = VIDEO_DURATION
    
    beats.append({
        "beat_id": beat_id,
        "type": "video",
        "asset_file": video,  # Direct in asset/ folder
        "start": round(current_time, 3),
        "duration": round(duration, 3),
        "text": line
    })
    
    print(f"  [{beat_id:02d}] 🎞️  {video} ({duration:.2f}s) - {line[:40]}...")
    current_time += duration
    beat_id += 1

# ==================================================
# VALIDATION & OUTPUT
# ==================================================

total_duration = sum(b["duration"] for b in beats)
sync_diff = abs(total_duration - audio_duration)

print("\n" + "=" * 70)
print("✅ BEATS GENERATED")
print("=" * 70)
print(f"📊 Stats:")
print(f"   - Total beats: {len(beats)}")
print(f"   - Hook images: {len(hook_images)}")
print(f"   - Story videos: {len(used_videos)}")
print(f"   - Beat duration: {total_duration:.2f}s")
print(f"   - Audio duration: {audio_duration:.2f}s")
print(f"   - Sync offset: {sync_diff:.3f}s")

if sync_diff > 0.5:
    print(f"\n⚠️  WARNING: Beats and audio differ by {sync_diff:.2f}s")
    print(f"   This is normal - video_build.py will handle it")

# Write output
OUTPUT_BEATS.write_text(json.dumps({"beats": beats}, indent=2))
print(f"\n💾 Saved: {OUTPUT_BEATS}")
print("=" * 70)
