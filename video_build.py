#!/usr/bin/env python3
"""
YouTube Shorts Video Builder - Optimized Single-Pass Edition
Ensures 9:16 aspect ratio and high-quality encoding.
"""

import json
import subprocess
from pathlib import Path
import sys

# Configuration
WIDTH, HEIGHT = 1080, 1920
FPS = 30

BEATS = Path("beats.json")
FRAMES = Path("frames")
AUDIO = Path("final_audio.wav")
SUBS = Path("subs.ass")
OUTPUT = Path("output.mp4")

def die(msg):
    sys.exit(f"[VIDEO] ❌ {msg}")

def load_beats():
    if not BEATS.exists():
        die("beats.json missing")
    try:
        data = json.loads(BEATS.read_text())
        return data["beats"]
    except Exception as e:
        die(f"Failed to parse beats.json: {e}")

def build_video():
    beats = load_beats()
    print(f"[VIDEO] 🎬 Processing {len(beats)} scenes...")

    if not AUDIO.exists(): die("final_audio.wav missing")
    if not SUBS.exists(): die("subs.ass missing")

    # 1. Build the FFmpeg command
    # We use a filter_complex to stitch images together without temporary files
    cmd = ["ffmpeg", "-y"]

    # Add image inputs
    for beat in beats:
        img_path = FRAMES / f"scene_{beat['beat_id']:02d}.png"
        if not img_path.exists():
            die(f"Missing image: {img_path}")
        # -loop 1 combined with -t ensures the image acts as a video segment
        cmd.extend(["-loop", "1", "-t", f"{beat['estimated_duration']:.2f}", "-i", str(img_path)])

    # Add audio input
    cmd.extend(["-i", str(AUDIO)])

    # 2. Construct Filter Complex
    # This scales each image to 1080x1920 and applies a subtle zoom-in (Ken Burns effect)
    filter_parts = []
    for i in range(len(beats)):
        # Scale, Crop to 9:16, and apply subtle zoom
        filter_parts.append(
            f"[{i}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},zoompan=z='min(zoom+0.0006,1.1)':d=125:s={WIDTH}x{HEIGHT},setsar=1[v{i}];"
        )
    
    # Concatenate all processed image streams
    concat_v = "".join(f"[v{i}]" for i in range(len(beats)))
    filter_parts.append(f"{concat_v}concat=n={len(beats)}:v=1:a=0[vconcat];")
    
    # Apply subtitles to the concatenated stream
    filter_parts.append(f"[vconcat]ass={SUBS}[vfinal]")

    # 3. Final Command Assembly
    full_filter = "".join(filter_parts)
    
    cmd.extend([
        "-filter_complex", full_filter,
        "-map", "[vfinal]",
        "-map", f"{len(beats)}:a", # Map the audio file (the last input)
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest", # End video when audio ends
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    print("[VIDEO] ⚡ Rendering final Short...")
    try:
        subprocess.run(cmd, check=True)
        print(f"[VIDEO] ✅ SUCCESS → {OUTPUT}")
    except subprocess.CalledProcessError as e:
        die(f"FFmpeg render failed: {e}")

if __name__ == "__main__":
    build_video()
