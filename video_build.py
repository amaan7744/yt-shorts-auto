#!/usr/bin/env python
"""
video_build.py — stable vertical video builder

- Reads images from ./frames/
- Attaches audio from final_audio.wav
- Outputs video_raw.mp4
- Subtitles are burned later via FFmpeg (ASS)
"""

import os
import sys
from typing import List

from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from pydub import AudioSegment

FRAMES_DIR = "frames"
OUTPUT_VIDEO = "video_raw.mp4"

TARGET_W = 1080
TARGET_H = 1920
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
    duration = len(audio) / 1000.0

    log(f"Audio duration: {duration:.2f}s")
    return max(duration, MIN_CLIP)


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
    frame_count = len(frames)

    per_image = max(MIN_CLIP, min(MAX_CLIP, total_duration / frame_count))
    log(f"Per-image duration: {per_image:.2f}s")

    clips: List[ImageClip] = []

    for idx, img in enumerate(frames, 1):
        log(f"Processing frame {idx}/{frame_count}: {img}")
        clips.append(make_clip(img, per_image))

    video = concatenate_videoclips(
        clips,
        method="compose",
        padding=-CROSSFADE,
    )

    audio = AudioFileClip(audio_path)
    video = video.set_audio(audio)

    log(f"Rendering {OUTPUT_VIDEO} ({FPS} fps)")
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

    log(f"Done: {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
