#!/usr/bin/env python3

import os
import random
from moviepy.editor import VideoFileClip, AudioFileClip

WIDTH, HEIGHT = 1080, 1920
FPS = 30

GAMEPLAY_DIR = "gameplay/loops"
AUDIO_FILE = "final_audio.wav"
SUBS_FILE = "subs.ass"
OUTPUT = "output.mp4"

def die(msg):
    raise SystemExit(f"[VIDEO] ❌ {msg}")

def log(msg):
    print(f"[VIDEO] {msg}", flush=True)

def pick_gameplay(duration):
    files = [f for f in os.listdir(GAMEPLAY_DIR) if f.endswith(".mp4")]
    if not files:
        die("No gameplay clips found")

    path = os.path.join(GAMEPLAY_DIR, random.choice(files))
    clip = VideoFileClip(path).without_audio().set_fps(FPS)

    if clip.duration < duration:
        return clip.loop(duration=duration)

    start = random.uniform(0, clip.duration - duration)
    return clip.subclip(start, start + duration)

def main():
    if not os.path.isfile(AUDIO_FILE):
        die("final_audio.wav missing")
    if not os.path.isfile(SUBS_FILE):
        die("subs.ass missing")

    log("Loading audio…")
    audio = AudioFileClip(AUDIO_FILE)
    duration = audio.duration

    log("Preparing gameplay background…")
    gameplay = (
        pick_gameplay(duration)
        .resize((WIDTH, HEIGHT))
        .set_audio(audio)
    )

    log("Rendering final Shorts video (subs burned)…")
    gameplay.write_videofile(
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

    log("✅ output.mp4 ready (stable, readable, no flicker)")

if __name__ == "__main__":
    main()
