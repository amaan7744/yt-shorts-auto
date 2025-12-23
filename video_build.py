#!/usr/bin/env python
"""
video_build.py — stable vertical video builder
NO subtitles here. Subtitles are burned later with ffmpeg.
"""

import os
import sys
from typing import List

from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from pydub import AudioSegment

FRAMES_DIR = "frames"
OUTPUT_VIDEO = "video_raw.mp4"

TARGET_W, TARGET_H = 1080, 1920
FPS = 30
MIN_CLIP = 3.0
MAX_CLIP = 7.0
CROSSFADE = 0.25


def log(msg: str) -> None:
    print(f"[VID] {msg}", flush=True)


def audio_duration(path: str) -> float:
    if not os.path.isfile(path):
        raise SystemExit(f"[VID] Audio file not found: {path}")
    audio = AudioSegment.from_file(path)
    dur = len(audio) / 1000.0
    log(f"Audio duration: {dur:.2f} s")
    return max(dur, MIN_CLIP)


def list_frames() -> List[str]:
    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit(f"[VID] Frames directory not found: {FRAMES_DIR}")

    imgs = [
        os.path.join(FRAMES_DIR, f)
        for f in sorted(os.listdir(FRAMES_DIR))
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not imgs:
        raise SystemExit("[VID] No images found")
    log(f"Found {len(imgs)} frames.")
    return imgs


def make_clip(img_path: str, dur: float) -> ImageClip:
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

    return clip.set_duration(dur)


def main() -> None:
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "final_audio.wav"

    total = audio_duration(audio_path)
    frames = list_frames()
    n = len(frames)

    per = max(MIN_CLIP, min(MAX_CLIP, total / n))
    log(f"Per-image duration: {per:.2f} s")

    clips: List[ImageClip] = []
    for idx, img in enumerate(frames, 1):
        log(f"Frame {idx}/{n} — {img}")
        clips.append(make_clip(img, per))

    video = concatenate_videoclips(
        clips,
        method="compose",
        padding=-CROSSFADE,
    )

    audio = AudioFileClip(audio_path)
    video = video.set_audio(audio)

    log(f"Rendering {OUTPUT_VIDEO} at {FPS} fps...")
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

    log("Done:", OUTPUT_VIDEO)


if __name__ == "__main__":
    main()
