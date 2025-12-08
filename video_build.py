#!/usr/bin/env python
"""
video_build.py — stable vertical video builder

Creates video_raw.mp4 (no audio) by stitching all images from ./frames/.

Usage:
    python video_build.py final_audio.wav
"""

import os
import sys
from typing import List

from moviepy.editor import ImageClip, concatenate_videoclips
from pydub import AudioSegment

FRAMES_DIR = "frames"
OUTPUT_VIDEO = "video_raw.mp4"
TARGET_W, TARGET_H = 1080, 1920
FPS = 30
MIN_CLIP = 3.0
MAX_CLIP = 7.0


def log(msg: str) -> None:
    print(f"[VID] {msg}", flush=True)


def audio_duration(path: str) -> float:
    """Return audio duration in seconds."""
    if not os.path.isfile(path):
        raise SystemExit(f"[VID] Audio file not found: {path}")
    audio = AudioSegment.from_file(path)
    dur = len(audio) / 1000.0
    log(f"Audio duration: {dur:.2f} s")
    return max(dur, MIN_CLIP)


def list_frames() -> List[str]:
    """Return sorted list of frame image paths from frames/."""
    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit(f"[VID] Frames directory not found: {FRAMES_DIR}")

    imgs: List[str] = []
    for name in sorted(os.listdir(FRAMES_DIR)):
        lower = name.lower()
        if lower.endswith((".jpg", ".jpeg", ".png")):
            imgs.append(os.path.join(FRAMES_DIR, name))

    if not imgs:
        raise SystemExit(f"[VID] No images found in {FRAMES_DIR}")
    log(f"Found {len(imgs)} frames.")
    return imgs


def make_clip(img_path: str, dur: float) -> ImageClip:
    """
    Create a vertical 1080x1920 ImageClip with center crop and fixed duration.
    """
    clip = ImageClip(img_path)
    w, h = clip.size

    # Scale so image fully covers 1080x1920
    scale = max(TARGET_W / w, TARGET_H / h)
    clip = clip.resize(scale)

    w2, h2 = clip.size
    clip = clip.crop(
        x_center=w2 / 2,
        y_center=h2 / 2,
        width=TARGET_W,
        height=TARGET_H,
    )

    return clip.set_duration(dur)


def main() -> None:
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "final_audio.wav"
    total = audio_duration(audio_path)
    frames = list_frames()
    n = len(frames)

    # Simple even split for each image
    per = max(MIN_CLIP, min(MAX_CLIP, total / n))
    log(f"Per-image duration: {per:.2f} s")

    clips: List[ImageClip] = []
    for idx, img in enumerate(frames, 1):
        log(f"Frame {idx}/{n} — {img}")
        clips.append(make_clip(img, per))

    if not clips:
        raise SystemExit("[VID] No clips created.")

    final = concatenate_videoclips(clips, method="compose")

    log(f"Rendering {OUTPUT_VIDEO} at {FPS} fps...")
    final.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio=False,
        preset="veryfast",
        threads=2,
        verbose=False,
        logger=None,
    )
    log("Done: video_raw.mp4")


if __name__ == "__main__":
    main()
