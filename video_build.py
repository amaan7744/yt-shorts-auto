#!/usr/bin/env python3

import os
import json
import random
from typing import List

from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    CompositeVideoClip,
    AudioFileClip,
    concatenate_videoclips,
)

# --------------------------------------------------
# CONFIG (LOCKED)
# --------------------------------------------------

WIDTH, HEIGHT = 1080, 1920
FPS = 30

GAMEPLAY_DIR = "gameplay/loops"
FRAMES_DIR = "frames"
AUDIO_FILE = "final_audio.wav"
SUBS_FILE = "subs.ass"

OUTPUT = "output.mp4"

PIXEL_MIN_DURATION = 0.8   # 🔒 NO FLICKER
PIXEL_AREA_HEIGHT = int(HEIGHT * 0.3)  # 30%
GAMEPLAY_AREA_HEIGHT = HEIGHT          # full background

# --------------------------------------------------
# UTILS
# --------------------------------------------------

def die(msg: str):
    raise SystemExit(f"[VIDEO] ❌ {msg}")

def log(msg: str):
    print(f"[VIDEO] {msg}", flush=True)

# --------------------------------------------------
# LOADERS
# --------------------------------------------------

def load_gameplay(duration: float) -> VideoFileClip:
    files = [f for f in os.listdir(GAMEPLAY_DIR) if f.endswith(".mp4")]
    if not files:
        die("No gameplay clips found")

    path = os.path.join(GAMEPLAY_DIR, random.choice(files))
    clip = VideoFileClip(path).without_audio().set_fps(FPS)

    if clip.duration < duration:
        return clip.loop(duration=duration)

    start = random.uniform(0, clip.duration - duration)
    return clip.subclip(start, start + duration)

def load_pixel_images(total_duration: float) -> VideoFileClip:
    images = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith(".jpg")
    )
    if not images:
        die("No pixel images found")

    per_img = max(PIXEL_MIN_DURATION, total_duration / len(images))
    clips: List[ImageClip] = []

    for img in images:
        clip = (
            ImageClip(img)
            .set_duration(per_img)
            .resize(width=WIDTH)
            .set_position(("center", int(HEIGHT * 0.15)))  # upper third
            .set_fps(FPS)
        )
        clips.append(clip)

    return concatenate_videoclips(clips, method="compose")

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if not os.path.isfile(AUDIO_FILE):
        die("final_audio.wav missing")
    if not os.path.isfile(SUBS_FILE):
        die("subs.ass missing")

    log("Loading audio…")
    audio = AudioFileClip(AUDIO_FILE)
    duration = audio.duration

    log("Preparing gameplay layer (primary retention)…")
    gameplay = (
        load_gameplay(duration)
        .resize((WIDTH, HEIGHT))
        .set_position(("center", "center"))
    )

    log("Preparing pixel overlay (secondary visual)…")
    pixel_strip = load_pixel_images(duration)

    log("Compositing layers…")
    video = CompositeVideoClip(
        [gameplay, pixel_strip],
        size=(WIDTH, HEIGHT)
    ).set_audio(audio)

    log("Rendering final Shorts video (subtitles burned)…")
    video.write_videofile(
        OUTPUT,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="slow",
        ffmpeg_params=[
            "-vf", f"ass={SUBS_FILE}",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ],
        threads=4,
        logger=None,
    )

    log("✅ output.mp4 created (stable, no flicker, subtitles included)")

if __name__ == "__main__":
    main()
