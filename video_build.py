#!/usr/bin/env python3
"""
High-Quality YouTube Shorts Video Builder
- Script-locked visuals
- HF image generation
- Cinematic motion
- Shorts-optimized encoding
"""

import json
import subprocess
from pathlib import Path
from image_generator import generate_image

# ===============================
# CONFIG
# ===============================

WIDTH, HEIGHT = 1080, 1920
FPS = 30

AUDIO = Path("final_audio.wav")
SUBS = Path("subs.ass")
BEATS = Path("beats.json")

FRAMES = Path("frames")
FRAMES.mkdir(exist_ok=True)

OUTPUT = Path("output.mp4")

# ===============================
def log(msg):
    print(f"[VIDEO] {msg}", flush=True)

def die(msg):
    raise SystemExit(f"[VIDEO] ❌ {msg}")

# ===============================
def load_beats():
    if not BEATS.exists():
        die("beats.json missing")

    return json.loads(BEATS.read_text())["beats"]

# ===============================
def build_frames(beats):
    idx = 0

    for beat in beats:
        img = FRAMES / f"scene_{beat['beat_id']:02d}.png"

        generate_image(beat["image_prompt"], img)

        frames_needed = int(beat["estimated_duration"] * FPS)

        for _ in range(frames_needed):
            (FRAMES / f"frame_{idx:05d}.png").symlink_to(img)
            idx += 1

# ===============================
def render_video():
    log("Rendering final video")

    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", "frames/frame_%05d.png",
        "-i", AUDIO,
        "-vf",
        (
            f"scale={WIDTH}:{HEIGHT}:flags=lanczos,"
            "zoompan=z='min(1.1,zoom+0.0005)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
            f"ass={SUBS}"
        ),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-crf", "16",
        "-preset", "slow",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        OUTPUT
    ], check=True)

# ===============================
def main():
    if not AUDIO.exists():
        die("final_audio.wav missing")
    if not SUBS.exists():
        die("subs.ass missing")

    beats = load_beats()
    log(f"{len(beats)} scenes")

    build_frames(beats)
    render_video()

    log(f"✅ FINAL VIDEO READY → {OUTPUT}")

# ===============================
if __name__ == "__main__":
    main()
