#!/usr/bin/env python3

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

OUTPUT = "output.mp4"

WIDTH, HEIGHT = 1080, 1920
FPS = 30

GAMEPLAY_RATIO = 0.70   # 70% gameplay
PIXEL_RATIO = 0.30      # 30% pixel

CRF = "14"              # Near-lossless for Shorts
PRESET = "slow"

# --------------------------------------------------
# UTILS
# --------------------------------------------------

def log(msg: str):
    print(f"[VIDEO] {msg}", flush=True)

def pick_gameplay(duration: float) -> VideoFileClip:
    files = [f for f in os.listdir(GAMEPLAY_DIR) if f.endswith(".mp4")]
    if not files:
        raise SystemExit("❌ No gameplay clips found")

    clip = VideoFileClip(
        os.path.join(GAMEPLAY_DIR, random.choice(files))
    ).without_audio()

    if clip.duration <= duration:
        return clip

    start = random.uniform(0, clip.duration - duration)
    return clip.subclip(start, start + duration)

def pick_pixel_frame() -> str:
    frames = [
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith(".jpg")
    ]
    if not frames:
        raise SystemExit("❌ No pixel frames found")
    return random.choice(frames)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    log("Loading audio…")
    audio = AudioFileClip(AUDIO_FILE)
    duration = audio.duration

    gameplay_h = int(HEIGHT * GAMEPLAY_RATIO)
    pixel_h = HEIGHT - gameplay_h

    log("Preparing gameplay layer (primary retention)…")
    gameplay = pick_gameplay(duration)
    gameplay = gameplay.resize(
        height=gameplay_h,
        resample="lanczos"
    )
    gameplay = gameplay.set_position(("center", HEIGHT - gameplay_h))

    log("Preparing pixel background (secondary)…")
    frame = pick_pixel_frame()
    pixel = ImageClip(frame)
    pixel = pixel.resize((WIDTH, pixel_h))
    pixel = pixel.set_duration(duration)
    pixel = pixel.set_position(("center", 0))

    log("Compositing final frame…")
    final = CompositeVideoClip(
        [pixel, gameplay],
        size=(WIDTH, HEIGHT)
    ).set_audio(audio)

    log("Rendering SINGLE-PASS Shorts video (no re-encode)…")
    final.write_videofile(
        OUTPUT,
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

    log("✅ output.mp4 ready (sharp, Shorts-optimized)")

if __name__ == "__main__":
    main()
