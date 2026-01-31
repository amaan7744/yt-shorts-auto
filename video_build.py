#!/usr/bin/env python3
"""
YouTube Shorts Video Builder
- Asset-driven
- Vertical-safe
- FFmpeg-cover equivalent (NO black bars)
"""

import json
import subprocess
import sys
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920
FPS = 30

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT = Path("output.mp4")

def die(msg):
    print(f"[VIDEO] ❌ {msg}")
    sys.exit(1)

def main():
    if not BEATS_FILE.exists():
        die("beats.json missing")
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    beats = json.loads(BEATS_FILE.read_text())["beats"]

    cmd = ["ffmpeg", "-y"]

    # -----------------------------
    # INPUTS
    # -----------------------------
    for beat in beats:
        asset = ASSET_DIR / f"{beat['asset_key']}.mp4"
        if not asset.exists():
            die(f"Missing asset: {asset}")
        cmd.extend(["-i", str(asset)])

    cmd.extend(["-i", str(AUDIO_FILE)])

    # -----------------------------
    # FILTER COMPLEX
    # -----------------------------
    filters = []
    for i, beat in enumerate(beats):
        dur = beat["estimated_duration"]
        filters.append(
            f"[{i}:v]"
            f"trim=0:{dur},"
            f"setpts=PTS-STARTPTS,"
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT}"
            f"[v{i}];"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(beats)))
    filters.append(f"{concat_inputs}concat=n={len(beats)}:v=1:a=0[v];")

    if SUBS_FILE.exists():
        filters.append(f"[v]ass={SUBS_FILE}[vout]")
        vmap = "[vout]"
    else:
        vmap = "[v]"

    filter_complex = "".join(filters)

    # -----------------------------
    # OUTPUT
    # -----------------------------
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", vmap,
        "-map", f"{len(beats)}:a",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-crf", "18",                # HIGH QUALITY
        "-preset", "slow",           # Better compression, no blur
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    print("[VIDEO] 🎬 Rendering...")
    subprocess.run(cmd, check=True)
    print("[VIDEO] ✅ output.mp4 ready")

if __name__ == "__main__":
    main()
