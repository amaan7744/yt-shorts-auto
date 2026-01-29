#!/usr/bin/env python3
"""
YouTube Shorts Video Builder
FAILS if visuals are missing
"""

import json
import shutil
import subprocess
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920
FPS = 30

BEATS = Path("beats.json")
FRAMES = Path("frames")
AUDIO = Path("final_audio.wav")
SUBS = Path("subs.ass")
OUTPUT = Path("output.mp4")

def die(msg):
    raise SystemExit(f"[VIDEO] ❌ {msg}")

def load_beats():
    if not BEATS.exists():
        die("beats.json missing")
    return json.loads(BEATS.read_text())["beats"]

def build_frames(beats):
    FRAMES.mkdir(exist_ok=True)

    # Clean old frames
    for f in FRAMES.glob("frame_*.png"):
        f.unlink()

    idx = 0

    for beat in beats:
        img = FRAMES / f"scene_{beat['beat_id']:02d}.png"
        if not img.exists():
            die(f"Missing scene image: {img.name}")

        frames_needed = max(1, int(beat["estimated_duration"] * FPS))

        for _ in range(frames_needed):
            frame = FRAMES / f"frame_{idx:05d}.png"
            shutil.copyfile(img, frame)
            idx += 1

    if idx == 0:
        die("NO FRAMES GENERATED — visuals missing")

    print(f"[VIDEO] Frames generated: {idx}")

def render_video():
    # Hard check before FFmpeg
    frame_files = list(FRAMES.glob("frame_*.png"))
    if not frame_files:
        die("FFmpeg aborted — no frame_*.png files")

    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", "frames/frame_%05d.png",
        "-i", AUDIO,
        "-vf",
        (
            f"scale={WIDTH}:{HEIGHT}:flags=lanczos,"
            "zoompan=z='min(1.08,zoom+0.0004)':d=1:"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
            f"ass={SUBS}"
        ),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-pix_fmt", "yuv420p",
        "-crf", "16",
        "-preset", "slow",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        OUTPUT
    ], check=True)

def main():
    if not AUDIO.exists():
        die("final_audio.wav missing")
    if not SUBS.exists():
        die("subs.ass missing")

    beats = load_beats()
    print(f"[VIDEO] Scenes: {len(beats)}")

    build_frames(beats)
    render_video()

    print(f"[VIDEO] ✅ Visuals confirmed → {OUTPUT}")

if __name__ == "__main__":
    main()
