#!/usr/bin/env python3
"""
YouTube Shorts Video Builder - Ultra-Resilient Edition
Fixes black backgrounds and build failures by ensuring proper asset mapping.
"""

import json
import subprocess
import sys
from pathlib import Path

# Configuration
WIDTH, HEIGHT = 1080, 1920
FPS = 30

# File Paths
BEATS = Path("beats.json")
FRAMES = Path("frames")
AUDIO = Path("final_audio.wav")
SUBS = Path("subs.ass")
OUTPUT = Path("output.mp4")

def die(msg):
    print(f"[VIDEO] ❌ {msg}")
    sys.exit(1)

def build_video():
    # 1. Validation
    if not BEATS.exists(): die("beats.json missing")
    if not AUDIO.exists(): die("final_audio.wav missing")
    if not SUBS.exists(): die("subs.ass missing")

    try:
        data = json.loads(BEATS.read_text())
        beats = data["beats"]
    except Exception as e:
        die(f"Failed to parse beats.json: {e}")

    print(f"[VIDEO] 🎬 Building Short with {len(beats)} scenes...")

    # 2. Build the Command
    cmd = ["ffmpeg", "-y"]

    # Add Image Inputs
    for beat in beats:
        img_path = FRAMES / f"scene_{beat['beat_id']:02d}.png"
        if not img_path.exists():
            print(f"[VIDEO] ⚠️ Warning: {img_path} missing, skipping beat.")
            continue
        
        # -loop 1 + -t defines the duration for each image input
        duration = float(beat.get("estimated_duration", 3.0))
        cmd.extend(["-loop", "1", "-t", f"{duration:.2f}", "-i", str(img_path)])

    # Add Audio Input
    cmd.extend(["-i", str(AUDIO)])

    # 3. Filter Complex
    # We use a single-pass filter to scale, crop, and stack the images
    filter_parts = []
    input_count = 0
    
    for i in range(len(beats)):
        img_path = FRAMES / f"scene_{beat['beat_id']:02d}.png"
        if not img_path.exists(): continue
        
        # Force images to fill 1080x1920 to eliminate black gaps
        filter_parts.append(
            f"[{input_count}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},setsar=1[v{input_count}];"
        )
        input_count += 1
    
    if input_count == 0:
        die("No valid images found in frames/ folder.")

    # Concatenate visual streams
    concat_v = "".join(f"[v{i}]" for i in range(input_count))
    filter_parts.append(f"{concat_v}concat=n={input_count}:v=1:a=0[vconcat];")
    
    # Overlay Subtitles
    filter_parts.append(f"[vconcat]ass={SUBS}[vfinal]")

    # 4. Final Assembly
    cmd.extend([
        "-filter_complex", "".join(filter_parts),
        "-map", "[vfinal]",
        "-map", f"{input_count}:a",  # Maps the audio which is the last input
        "-c:v", "libx264",
        "-preset", "superfast",      # Faster render for GitHub Actions
        "-crf", "22",                # Good balance of size/quality
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",                 # Cut video if audio ends early
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    print("[VIDEO] ⚡ Rendering final video file...")
    try:
        subprocess.run(cmd, check=True)
        print(f"[VIDEO] ✅ SUCCESS → {OUTPUT}")
    except subprocess.CalledProcessError as e:
        die(f"FFmpeg failed with exit code {e.returncode}")

if __name__ == "__main__":
    build_video()
