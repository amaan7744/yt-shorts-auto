#!/usr/bin/env python3
"""
Shorts Video Builder
Gameplay = primary layer (fullscreen)
Pixel images = flash overlays (pattern interrupts)
"""

import os
import json
import random
import subprocess
from typing import List

from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

FRAMES_DIR = "frames"
GAMEPLAY_DIR = "gameplay/loops"

BEATS_FILE = "beats.json"
AUDIO_FILE = "final_audio.wav"
OUTPUT_VIDEO = "output.mp4"

WIDTH, HEIGHT = 1080, 1920
FPS = 30

TARGET_DURATION = 20.0   # HARD CAP FOR SHORTS
FLASH_DURATION = 0.45    # seconds per image flash
FLASH_OPACITY = 0.92

AUDIO_SAFETY_MARGIN = 0.2

# --------------------------------------------------
# UTILS
# --------------------------------------------------

def log(msg: str):
    print(f"[VIDEO] {msg}", flush=True)

def load_beats():
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")
    return json.load(open(BEATS_FILE, "r", encoding="utf-8"))

def load_frames() -> List[str]:
    frames = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith(".jpg")
    )
    if not frames:
        raise SystemExit("❌ No frames found")
    return frames

def pick_gameplay(duration: float) -> VideoFileClip:
    files = [f for f in os.listdir(GAMEPLAY_DIR) if f.endswith(".mp4")]
    if not files:
        raise SystemExit("❌ No gameplay clips found")

    path = os.path.join(GAMEPLAY_DIR, random.choice(files))
    clip = VideoFileClip(path).without_audio()

    if clip.duration <= duration:
        return clip.subclip(0, clip.duration)

    start = random.uniform(0, clip.duration - duration)
    return clip.subclip(start, start + duration)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    log("Loading audio…")
    audio = AudioFileClip(AUDIO_FILE)
    audio_duration = min(audio.duration, TARGET_DURATION)

    log("Preparing gameplay layer (primary retention)…")
    gameplay = pick_gameplay(audio_duration)
    gameplay = gameplay.resize((WIDTH, HEIGHT))

    gameplay = gameplay.set_duration(audio_duration)

    log("Loading pixel frames (overlay interrupts)…")
    frames = load_frames()
    beats = load_beats()

    overlays = []

    # Flash images at beat transitions (NOT constant)
    beat_times = []
    cursor = 1.8  # first flash after hook
    spacing = max(3.0, audio_duration / max(len(frames), 1))

    for _ in frames:
        if cursor + FLASH_DURATION >= audio_duration - 0.5:
            break
        beat_times.append(cursor)
        cursor += spacing

    for img, t in zip(frames, beat_times):
        clip = (
            ImageClip(img)
            .resize((WIDTH, HEIGHT))
            .set_start(t)
            .set_duration(FLASH_DURATION)
            .fadein(0.08)
            .fadeout(0.12)
            .set_opacity(FLASH_OPACITY)
        )
        overlays.append(clip)

    log("Compositing layers…")
    final = CompositeVideoClip(
        [gameplay] + overlays,
        size=(WIDTH, HEIGHT)
    )

    safe_audio = audio.subclip(
        0, min(audio_duration, final.duration - AUDIO_SAFETY_MARGIN)
    )
    final = final.set_audio(safe_audio)

    log("Rendering FINAL Shorts video (no re-encode later)…")
    final.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="slow",
        ffmpeg_params=[
            "-crf", "16",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ],
        logger=None,
    )

    log("✅ output.mp4 created (sharp, Shorts-ready)")

if __name__ == "__main__":
    main()
