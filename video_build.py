#!/usr/bin/env python3
"""
Final Shorts Video Builder
- 70% gameplay / 30% pixel
- Single encode only
- Subtitles burned here
- Shorts-optimized quality
"""

import os
import random
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

FRAMES_DIR = "frames"
GAMEPLAY_DIR = "gameplay/loops"
AUDIO_FILE = "final_audio.wav"
SUBS_FILE = "subs.ass"

OUTPUT_FILE = "output.mp4"

WIDTH, HEIGHT = 1080, 1920
FPS = 30

GAMEPLAY_RATIO = 0.70   # bottom 70%
PIXEL_RATIO = 0.30      # top 30%

CRF = "14"              # near-lossless for Shorts
PRESET = "slow"

# --------------------------------------------------
# UTILS
# --------------------------------------------------

def log(msg: str):
    print(f"[VIDEO] {msg}", flush=True)

def pick_random_gameplay(duration: float) -> VideoFileClip:
    files = [f for f in os.listdir(GAMEPLAY_DIR) if f.endswith(".mp4")]
    if not files:
        raise SystemExit("❌ No gameplay videos found in gameplay/loops")

    clip = VideoFileClip(
        os.path.join(GAMEPLAY_DIR, random.choice(files))
    ).without_audio()

    if clip.duration <= duration:
        return clip

    start = random.uniform(0, clip.duration - duration)
    return clip.subclip(start, start + duration)

def pick_random_pixel_frame() -> str:
    frames = [
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith(".jpg")
    ]
    if not frames:
        raise SystemExit("❌ No frames found in frames/")
    return random.choice(frames)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    log("Loading audio…")
    if not os.path.isfile(AUDIO_FILE):
        raise SystemExit("❌ final_audio.wav missing")

    audio = AudioFileClip(AUDIO_FILE)
    duration = audio.duration

    gameplay_height = int(HEIGHT * GAMEPLAY_RATIO)
    pixel_height = HEIGHT - gameplay_height

    # ----------------------------
    # GAMEPLAY (PRIMARY RETENTION)
    # ----------------------------
    log("Preparing gameplay layer (primary retention)…")
    gameplay = pick_random_gameplay(duration)
    gameplay = gameplay.resize(height=gameplay_height)
    gameplay = gameplay.set_position(("center", HEIGHT - gameplay_height))

    # ----------------------------
    # PIXEL VISUAL (SECONDARY)
    # ----------------------------
    log("Preparing pixel visual layer…")
    frame = pick_random_pixel_frame()
    pixel = ImageClip(frame)
    pixel = pixel.resize((WIDTH, pixel_height))
    pixel = pixel.set_duration(duration)
    pixel = pixel.set_position(("center", 0))

    # ----------------------------
    # COMPOSITE
    # ----------------------------
    log("Compositing final frame…")
    final = CompositeVideoClip(
        [pixel, gameplay],
        size=(WIDTH, HEIGHT)
    ).set_audio(audio)

    # ----------------------------
    # SINGLE-PASS RENDER
    # ----------------------------
    log("Rendering FINAL Shorts video (single encode)…")
    final.write_videofile(
        OUTPUT_FILE,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset=PRESET,
        ffmpeg_params=[
            "-crf", CRF,
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-vf", f"ass={SUBS_FILE}",
        ],
        threads=4,
    )

    log("✅ output.mp4 created (sharp, Shorts-ready)")

if __name__ == "__main__":
    main()
