#!/usr/bin/env python3
"""
YouTube Shorts Video Builder
- Uses asset videos only
- Audio locked
- No black frames
- No quality drop
"""

import json
import subprocess
import sys
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920
FPS = 30

BEATS = Path("beats.json")
AUDIO = Path("final_audio.wav")
SUBS = Path("subs.ass")
OUTPUT = Path("output.mp4")

ASSET_DIR = Path("asset")

ASSET_MAP = {
    "car_pov": "Car POV.mp4",
    "parked_car": "parked car.mp4",
    "cctv": "cctv.mp4",
    "interrogation": "interogationroom.mp4",
    "hallway": "hallway.mp4",
    "dark_room": "dark room.mp4",
    "closing_door": "closing door.mp4",
    "evidence": "evidence.mp4",
    "mobile_message": "mobilemessage.mp4",
    "shadow": "shadow.mp4",
    "rooftop": "rooftop.mp4",
    "window_pov": "window pov.mp4",
    "yellow_tape": "yellow tape.mp4",
    "dynamics": "dynamics.mp4",
}

def die(msg):
    sys.exit(f"[VIDEO] ❌ {msg}")

def main():
    if not BEATS.exists(): die("beats.json missing")
    if not AUDIO.exists(): die("final_audio.wav missing")
    if not SUBS.exists(): die("subs.ass missing")

    beats = json.loads(BEATS.read_text())["beats"]

    inputs = []
    filters = []
    idx = 0

    for beat in beats:
        key = beat["asset_key"]
        asset_name = ASSET_MAP.get(key, ASSET_MAP["dynamics"])
        asset_path = ASSET_DIR / asset_name

        if not asset_path.exists():
            die(f"Asset missing: {asset_path}")

        dur = float(beat["estimated_duration"])

        inputs.extend(["-i", str(asset_path)])
        filters.append(
            f"[{idx}:v]trim=0:{dur},setpts=PTS-STARTPTS,"
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=cover,"
            f"crop={WIDTH}:{HEIGHT}[v{idx}];"
        )
        idx += 1

    concat = "".join(f"[v{i}]" for i in range(idx))
    filters.append(f"{concat}concat=n={idx}:v=1:a=0[v];")
    filters.append(f"[v]ass={SUBS}[vout]")

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", str(AUDIO),
        "-filter_complex", "".join(filters),
        "-map", "[vout]",
        "-map", f"{idx}:a",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "slow",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT)
    ]

    print("[VIDEO] 🎬 Rendering…")
    subprocess.run(cmd, check=True)
    print("[VIDEO] ✅ output.mp4 ready")

if __name__ == "__main__":
    main()
