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

def get_hook_images(hook_text):
    """Match hook line words to hook images based on keyword tags"""
    # Extract meaningful words from hook (lowercase, remove punctuation)
    hook_words = [
        w.strip(".,!?\"'").lower()
        for w in hook_text.split()
        if len(w) > 3  # Skip very short words like "the", "was", etc.
    ]
    
    print(f"[VISUAL] Hook words: {hook_words}")
    
    # Find matching images
    matched_images = []
    used_images = set()
    
    # Try to find unique images for different words
    for word in hook_words:
        best_match = None
        best_score = 0
        
        for img, keywords in HOOK_IMAGE_CATEGORIES.items():
            if img in used_images:
                continue
            
            # Count how many keywords this word matches
            score = sum(1 for kw in keywords if word in kw or kw in word)
            
            if score > best_score:
                best_score = score
                best_match = img
        
        if best_match and best_score > 0:
            matched_images.append(best_match)
            used_images.add(best_match)
            print(f"[VISUAL]   '{word}' → {best_match}")
    
    # If we didn't get enough images, add more based on general crime keywords
    if len(matched_images) < 2:
        print(f"[VISUAL] Only {len(matched_images)} matches, adding general crime images...")
        
        # Priority keywords for crime content
        priority_keywords = ["crime", "death", "murder", "body", "scene", "victim"]
        
        for priority in priority_keywords:
            if len(matched_images) >= 3:
                break
            
            for img, keywords in HOOK_IMAGE_CATEGORIES.items():
                if img in used_images:
                    continue
                
                if any(priority in kw for kw in keywords):
                    matched_images.append(img)
                    used_images.add(img)
                    print(f"[VISUAL]   [general: {priority}] → {img}")
                    break
    
    # Last resort: just grab first available images
    if not matched_images:
        print(f"[VISUAL] No keyword matches, using first available images...")
        for img in list(HOOK_IMAGE_CATEGORIES.keys())[:3]:
            matched_images.append(img)
            print(f"[VISUAL]   [fallback] → {img}")
    
    return matched_images

hook_images = get_hook_images(HOOK_LINE)

if not hook_images:
    die("No hook images could be assigned")

print(f"[VISUAL] Selected {len(hook_images)} hook images")

# Clamp hook duration
hook_duration = min(HOOK_MAX_SECONDS, audio_duration * 0.12)
per_image = max(MIN_IMAGE_DURATION, hook_duration / len(hook_images))

# ==================================================
# STORY VIDEO ASSIGNMENT
# ==================================================

def video_for_line(text, used):
    """Find best matching video for a script line"""
    t = text.lower()
    
    # First pass: look for exact phrase matches
    best_match = None
    best_score = 0
    
    for asset, keywords in VIDEO_ASSET_KEYWORDS.items():
        if asset in used:
            continue
        
        # Count matching keywords
        score = sum(1 for kw in keywords if kw in t)
        
        if score > best_score:
            best_score = score
            best_match = asset
    
    if best_match:
        path = ASSET_DIR / best_match
        if not path.exists():
            die(f"Video asset missing on disk: {best_match}")
        print(f"[VISUAL] '{text[:50]}...' → {best_match} (score: {best_score})")
        return best_match
    
    # Second pass: if no matches, use first unused video
    for asset in VIDEO_ASSET_KEYWORDS.keys():
        if asset not in used:
            path = ASSET_DIR / asset
            if path.exists():
                print(f"[VISUAL] '{text[:50]}...' → {asset} [fallback]")
                return asset
    
    die(f"No video available for line: {text}")

# ==================================================
# BUILD BEATS
# ==================================================

beats = []
current_time = 0.0
beat_id = 1

# ---- HOOK (IMAGES ONLY)
print("\n[VISUAL] === HOOK SECTION ===")
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
print("\n[VISUAL] === STORY SECTION ===")
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
print("\n[VISUAL] === FINAL LOOP ===")
final_duration = max(0.5, audio_duration - current_time)
final_asset = list(used_videos)[-1] if used_videos else list(VIDEO_ASSET_KEYWORDS.keys())[0]

beats.append({
    "beat_id": beat_id,
    "type": "video",
    "asset_file": final_asset,
    "start": round(current_time, 3),
    "duration": round(final_duration, 3),
    "text": FINAL_LOOP,
})

print(f"[VISUAL] Final loop: {final_asset} ({final_duration:.2f}s)")

# ==================================================
# WRITE OUTPUT
# ==================================================

OUTPUT_BEATS.write_text(json.dumps({"beats": beats}, indent=2))

print("\n" + "="*60)
print("✅ Visuals assigned successfully")
print("="*60)
print(f"🎞️  Hook images: {len(hook_images)}")
print(f"🎬 Story videos: {len(used_videos)}")
print(f"⏱️  Total duration: {current_time + final_duration:.2f}s")
print(f"🎵 Audio duration: {audio_duration:.2f}s")
print("🔒 beats.json locked to audio & script")
print("="*60)
