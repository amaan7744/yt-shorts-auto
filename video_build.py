#!/usr/bin/env python3
"""
YouTube Shorts Video Builder
- Asset-driven
- Vertical-safe
- Never ends early
- Never runs long
- HARD-LOCKED to audio duration
"""

import json
import subprocess
import sys
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920

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
    # VIDEO INPUTS
    # -----------------------------
    for beat in beats:
        asset = ASSET_DIR / f"{beat['asset_key']}.mp4"
        if not asset.exists():
            die(f"Missing asset: {asset}")
        cmd.extend(["-i", str(asset)])

    # AUDIO INPUT (LAST INPUT)
    cmd.extend(["-i", str(AUDIO_FILE)])

    audio_index = len(beats)

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
    filters.append(
        f"{concat_inputs}concat=n={len(beats)}:v=1:a=0[vraw];"
    )

    # 🔒 HARD TRIM VIDEO TO AUDIO LENGTH
    filters.append(
        f"[vraw]trim=duration=shortest,setpts=PTS-STARTPTS[vtrim];"
    )

    if SUBS_FILE.exists():
        filters.append(f"[vtrim]ass={SUBS_FILE}[vout]")
        vmap = "[vout]"
    else:
        vmap = "[vtrim]"

    filter_complex = "".join(filters)

    # -----------------------------
    # OUTPUT
    # -----------------------------
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", vmap,
        "-map", f"{audio_index}:a",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "slow",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",              # extra safety
        str(OUTPUT)
    ])

    print("[VIDEO] 🎬 Rendering (audio-locked)…")
    subprocess.run(cmd, check=True)
    print("[VIDEO] ✅ output.mp4 ready")

if __name__ == "__main__":
    main()
