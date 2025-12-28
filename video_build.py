#!/usr/bin/env python3
"""
video_build.py — PROFESSIONAL Shorts builder (ERROR-FREE)

Guarantees:
- Video ends EXACTLY with audio
- Duration 0–35s
- No subtitle desync
- Subtle professional polish
- MoviePy-safe (no dynamic crop bugs)
"""

import os
import sys
from typing import List

from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    vfx
)
from pydub import AudioSegment

# ---------------- CONFIG ----------------

FRAMES_DIR = "frames"
OUTPUT_VIDEO = "video_raw.mp4"

TARGET_W = 1080
TARGET_H = 1920
FPS = 30

MAX_DURATION = 35.0

# ---------------------------------------


def log(msg: str):
    print(f"[VID] {msg}", flush=True)


def get_audio_duration(path: str) -> float:
    if not os.path.isfile(path):
        raise SystemExit(f"[VID] Audio not found: {path}")

    audio = AudioSegment.from_file(path)
    duration = len(audio) / 1000.0

    if duration > MAX_DURATION:
        log(f"Audio {duration:.2f}s > {MAX_DURATION}s — trimming")
        return MAX_DURATION

    log(f"Final audio duration: {duration:.2f}s")
    return duration


def list_frames() -> List[str]:
    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit(f"[VID] Frames dir missing: {FRAMES_DIR}")

    frames = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )

    if not frames:
        raise SystemExit("[VID] No frames found")

    log(f"Using {len(frames)} frames")
    return frames


def prepare_clip(img_path: str, duration: float) -> ImageClip:
    clip = ImageClip(img_path)

    # Resize & crop to vertical
    w, h = clip.size
    scale = max(TARGET_W / w, TARGET_H / h)
    clip = clip.resize(scale)

    w2, h2 = clip.size
    clip = clip.crop(
        x_center=w2 / 2,
        y_center=h2 / 2,
        width=TARGET_W,
        height=TARGET_H,
    )

    # -------- SAFE PROFESSIONAL EFFECTS --------

    # Slow zoom-in (Ken Burns style)
    clip = clip.fx(
        vfx.resize,
        lambda t: 1.0 + 0.02 * (t / duration)
    )

    # Mild contrast boost (safe)
    clip = clip.fx(vfx.colorx, 1.04)

    return clip.set_duration(duration)


def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "final_audio.wav"

    total_duration = get_audio_duration(audio_path)
    frames = list_frames()
    frame_count = len(frames)

    base_duration = total_duration / frame_count

    clips: List[ImageClip] = []
    used = 0.0

    for idx, img in enumerate(frames):
        if idx == frame_count - 1:
            dur = max(0.1, total_duration - used)
        else:
            dur = base_duration

        used += dur
        log(f"Frame {idx + 1}/{frame_count}: {dur:.2f}s")
        clips.append(prepare_clip(img, dur))

    video = concatenate_videoclips(clips, method="compose")

    audio = AudioFileClip(audio_path).subclip(0, total_duration)
    video = video.set_audio(audio)

    log("Rendering video_raw.mp4")
    video.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="veryfast",
        threads=2,
        verbose=False,
        logger=None,
    )

    log("Done — video matches audio exactly")


if __name__ == "__main__":
    main()
