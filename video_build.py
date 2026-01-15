#!/usr/bin/env python3

import os
import json
import random
import subprocess
from typing import List

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

FRAMES_DIR = "frames"
CLIPS_DIR = "clips"
GAMEPLAY_DIR = "gameplay/loops"

BEATS_FILE = "beats.json"
AUDIO_FILE = "final_audio.wav"
OUTPUT_VIDEO = "video_raw.mp4"

WIDTH, HEIGHT = 1080, 1920
FPS = 30

TARGET_DURATION = 30.0
AUDIO_SAFETY_MARGIN = 0.25

os.makedirs(CLIPS_DIR, exist_ok=True)

# --------------------------------------------------
# UTILS
# --------------------------------------------------

def log(msg: str):
    print(f"[VIDEO] {msg}", flush=True)

def load_beats():
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")
    with open(BEATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_frames() -> List[str]:
    frames = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith(".jpg")
    )
    if not frames:
        raise SystemExit("❌ No frames found in frames/")
    return frames

# --------------------------------------------------
# GAMEPLAY
# --------------------------------------------------

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
# PIXEL IMAGE → VIDEO
# --------------------------------------------------

def animate_image(img: str, out: str, duration: float):
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", img,
        "-t", f"{duration:.3f}",
        "-vf",
        (
            "scale=1080:960:flags=lanczos,"
            "noise=alls=10:allf=t+u,"
            "zoompan=z='min(zoom+0.0006,1.07)':d=1,"
            "eq=brightness=0.015*sin(2*PI*t/{d})"
        ).format(d=max(duration, 0.1)),
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        out
    ]
    subprocess.run(cmd, check=True)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    beats = load_beats()
    frames = load_frames()

    audio = AudioFileClip(AUDIO_FILE)
    audio_duration = min(audio.duration, TARGET_DURATION)

    per_frame_duration = audio_duration / len(frames)

    pixel_clips = []

    log("Animating pixel frames...")
    for i, img in enumerate(frames):
        out = os.path.join(CLIPS_DIR, f"pixel_{i:03d}.mp4")
        animate_image(img, out, per_frame_duration)
        pixel_clips.append(VideoFileClip(out))

    pixel_video = concatenate_videoclips(pixel_clips)
    pixel_video = pixel_video.resize((WIDTH, HEIGHT // 2))
    pixel_video = pixel_video.set_position(("center", 0))

    log("Selecting gameplay...")
    gameplay = pick_gameplay(audio_duration)
    gameplay = gameplay.resize((WIDTH, HEIGHT // 2))
    gameplay = gameplay.set_position(("center", HEIGHT // 2))

    log("Compositing layers...")
    final = CompositeVideoClip(
        [pixel_video, gameplay],
        size=(WIDTH, HEIGHT)
    )

    safe_audio = audio.subclip(
        0, min(audio_duration, final.duration - AUDIO_SAFETY_MARGIN)
    )
    final = final.set_audio(CompositeAudioClip([safe_audio]))

    log("Rendering HD Shorts video...")
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

    log("✅ video_raw.mp4 ready (HD, 9:16, Shorts-safe)")

if __name__ == "__main__":
    main()
