#!/usr/bin/env python3
"""
video_build.py — Shorts-safe vertical video builder

Guarantees:
- Video duration ALWAYS matches audio duration
- No early cutoffs
- Stable for GitHub Actions
"""

import os
import sys
import random
from typing import List

from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from pydub import AudioSegment

FRAMES_DIR = "frames"
OUTPUT_VIDEO = "video_raw.mp4"

TARGET_W = 1080
TARGET_H = 1920
FPS = 30

# Shorts-friendly timing
MIN_CLIP = 1.8
MAX_CLIP = 3.5
MAX_VIDEO_DURATION = 35.0  # Shorts cap


def log(msg: str) -> None:
    print(f"[VID] {msg}", flush=True)


def audio_duration(path: str) -> float:
    if not os.path.isfile(path):
        raise SystemExit(f"[VID] Audio file not found: {path}")

    audio = AudioSegment.from_file(path)
    duration = len(audio) / 1000.0

    capped = min(duration, MAX_VIDEO_DURATION)
    log(f"Audio duration: {duration:.2f}s (using {capped:.2f}s)")
    return capped


def list_frames() -> List[str]:
    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit(f"[VID] Frames directory not found: {FRAMES_DIR}")

    frames = [
        os.path.join(FRAMES_DIR, f)
        for f in sorted(os.listdir(FRAMES_DIR))
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not frames:
        raise SystemExit("[VID] No frame images found")

    log(f"Found {len(frames)} frames")
    return frames


def make_clip(img_path: str, duration: float) -> ImageClip:
    clip = ImageClip(img_path)
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

    return clip.set_duration(duration)


def main() -> None:
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "final_audio.wav"

    total_duration = audio_duration(audio_path)
    frames = list_frames()

    clips: List[ImageClip] = []
    remaining = total_duration

    log(f"Target video duration: {total_duration:.2f}s")

    for idx, img in enumerate(frames):
        if remaining <= 0:
            break

        # For last frame OR when few seconds remain → absorb remainder
        if idx == len(frames) - 1 or remaining <= MAX_CLIP:
            dur = remaining
        else:
            dur = random.uniform(MIN_CLIP, MAX_CLIP)
            dur = min(dur, remaining)

        log(f"Frame {idx + 1}: {dur:.2f}s")
        clips.append(make_clip(img, dur))
        remaining -= dur

    # SAFETY: if frames ran out early, extend last frame
    if remaining > 0 and clips:
        log(f"Extending last frame by {remaining:.2f}s to match audio")
        clips[-1] = clips[-1].set_duration(clips[-1].duration + remaining)
        remaining = 0

    video = concatenate_videoclips(
        clips,
        method="compose"  # hard cuts (best for Shorts)
    )

    audio = AudioFileClip(audio_path).subclip(0, total_duration)
    video = video.set_audio(audio)

    log(f"Rendering {OUTPUT_VIDEO}")
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

    log("Done — video length matches audio exactly")


if __name__ == "__main__":
    main()
