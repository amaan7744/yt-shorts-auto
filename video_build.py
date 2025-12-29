#!/usr/bin/env python3
import os
import sys
from typing import List
from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
    vfx
)
from pydub import AudioSegment

# ---------------- CONFIG ----------------
OUTPUT_VIDEO = "video_raw.mp4"
FRAMES_DIR = "frames"
VOICE_AUDIO = "final_audio.wav"

TARGET_W, TARGET_H = 1080, 1920
FPS = 30
MAX_DURATION = 35.0
MICRO_MOTION = 0.025  # 2.5% ONLY
# ----------------------------------------

def log(msg):
    print(f"[VID] {msg}", flush=True)

def audio_duration(path):
    audio = AudioSegment.from_file(path)
    return min(len(audio) / 1000.0, MAX_DURATION)

def list_frames():
    frames = sorted([
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])
    if not frames:
        raise SystemExit("No frames found")
    return frames

def prepare_clip(path, duration, index):
    clip = ImageClip(path).set_duration(duration)

    # SINGLE high-quality resize
    w, h = clip.size
    scale = max(TARGET_W / w, TARGET_H / h)
    clip = clip.resize(scale)

    clip = clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=TARGET_W,
        height=TARGET_H
    )

    # Micro motion ONLY (compression-safe)
    if index % 2 == 0:
        clip = clip.fx(vfx.resize, lambda t: 1.0 + MICRO_MOTION * (t / duration))
    else:
        clip = clip.fx(vfx.resize, lambda t: 1.0 - MICRO_MOTION * (t / duration))

    return clip

def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else VOICE_AUDIO

    total = audio_duration(audio_path)
    frames = list_frames()
    per = total / len(frames)

    log(f"Audio: {total:.2f}s | Frames: {len(frames)}")

    clips = [
        prepare_clip(img, per, i)
        for i, img in enumerate(frames)
    ]

    video = concatenate_videoclips(clips, method="compose")
    video = video.set_duration(total)

    voice = AudioFileClip(audio_path).subclip(0, total)
    video = video.set_audio(CompositeAudioClip([voice]))

    log("Rendering 1080p HIGH-QUALITY master")

    video.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="12000k",        # STRONG MASTER
        preset="slow",
        threads=4,
        ffmpeg_params=[
            "-pix_fmt", "yuv420p",
            "-profile:v", "high",
            "-level", "4.2",
            "-movflags", "+faststart"
        ],
        logger=None
    )

    log("Done — quality preserved")

if __name__ == "__main__":
    main()
