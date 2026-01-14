#!/usr/bin/env python3

import os
import json
import subprocess
from typing import List

from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
)

from pydub import AudioSegment

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

FRAMES_DIR = "frames"
CLIPS_DIR = "clips"
BEATS_FILE = "beats.json"

AUDIO_FILE = "final_audio.wav"
OUTPUT_VIDEO = "video_raw.mp4"

FPS = 30
MAX_DURATION = 35.0
AUDIO_SAFETY_MARGIN = 0.2

os.makedirs(CLIPS_DIR, exist_ok=True)

# --------------------------------------------------
# UTIL
# --------------------------------------------------

def log(msg: str):
    print(msg, flush=True)

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

def audio_duration(path: str) -> float:
    audio = AudioSegment.from_file(path)
    return min(len(audio) / 1000.0, MAX_DURATION)

# --------------------------------------------------
# MOTION (SUBTLE, CINEMATIC)
# --------------------------------------------------

def animate_image(img: str, out: str, duration: float):
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", img,
        "-t", f"{duration:.3f}",
        "-vf",
        (
            "scale=1080:1920:flags=lanczos,"
            "format=yuv420p,"
            "noise=alls=8:allf=t+u,"
            "eq=brightness=0.015*sin(2*PI*t/{d}):contrast=1.02,"
            "vignette=PI/6"
        ).format(d=max(duration, 0.1)),
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "16",
        "-pix_fmt", "yuv420p",
        out
    ]
    subprocess.run(cmd, check=True)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    log("Loading beats, frames, and audio...")

    beats = load_beats()
    frames = load_frames()

    if len(frames) != len(beats):
        raise SystemExit("❌ Frame count must equal beat count")

    audio_len = audio_duration(AUDIO_FILE)
    base_duration = audio_len / len(beats)

    clips = []

    for i, (beat, img) in enumerate(zip(beats, frames), 1):
        dur = base_duration
        log(f"Animating beat {i}/{len(beats)} ({dur:.2f}s)")

        out_clip = os.path.join(CLIPS_DIR, f"clip_{i:03d}.mp4")
        animate_image(img, out_clip, dur)
        clips.append(VideoFileClip(out_clip))

    log("Adding loop reinforcement...")
    clips.append(clips[0].subclip(0, 0.4))

    log("Concatenating clips...")
    video = concatenate_videoclips(clips, method="compose")

    log("Adding audio...")
    audio_clip = AudioFileClip(AUDIO_FILE)
    safe_end = min(audio_clip.duration - AUDIO_SAFETY_MARGIN, video.duration)
    audio = audio_clip.subclip(0, safe_end)
    video = video.set_audio(CompositeAudioClip([audio]))

    log("Rendering final video...")
    video.write_videofile(
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

    log("✅ video_raw.mp4 created")

if __name__ == "__main__":
    main()
