#!/usr/bin/env python3

import os
from typing import List

from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
    vfx,
)
from pydub import AudioSegment

# ---------------- CONFIG ----------------
OUTPUT_VIDEO = "video_raw.mp4"
FRAMES_DIR = "frames"

PRIMARY_AUDIO = "final_audio.wav"
FALLBACK_AUDIO = "narration.wav"

TARGET_W, TARGET_H = 1080, 1920
FPS = 30
MAX_DURATION = 38.0

# Motion tuning
OVERSCAN = 1.10          # zoom in slightly for pan room
FADE_TIME = 0.12         # subtle fades
FAST_START_FRAMES = 2    # first frames move quicker
# --------------------------------------


def log(msg: str):
    print(f"[VID] {msg}", flush=True)


# ---------------- AUDIO ----------------
def get_audio_path() -> str:
    if os.path.isfile(PRIMARY_AUDIO):
        return PRIMARY_AUDIO
    if os.path.isfile(FALLBACK_AUDIO):
        log("⚠️ final_audio.wav missing — using narration.wav")
        return FALLBACK_AUDIO
    raise SystemExit("[VID] No audio file found")


def get_audio_duration(path: str) -> float:
    audio = AudioSegment.from_file(path)
    duration = len(audio) / 1000.0
    return min(duration, MAX_DURATION)


# ---------------- FRAMES ----------------
def list_frames() -> List[str]:
    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit("[VID] frames/ directory missing")

    frames = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )

    if not frames:
        raise SystemExit("[VID] No images found in frames/")
    return frames


# ---------------- VISUAL LOGIC ----------------
def prepare_clip(img_path: str, duration: float, index: int) -> ImageClip:
    """
    Creates a clean, cinematic image clip with
    deterministic motion (NO animated resize).
    """

    clip = ImageClip(img_path).set_duration(duration)

    # Resize ONCE (critical)
    w, h = clip.size
    scale = max(TARGET_W / w, TARGET_H / h) * OVERSCAN
    clip = clip.resize(scale)

    # Compute pan limits
    x_max = max(0, clip.w - TARGET_W)
    y_max = max(0, clip.h - TARGET_H)

    # Motion patterns (rotate for variety)
    pattern = index % 4

    if pattern == 0:       # top-left → center
        x1, y1 = 0, 0
    elif pattern == 1:     # bottom-right → center
        x1, y1 = x_max, y_max
    elif pattern == 2:     # left vertical pan
        x1, y1 = 0, y_max // 2
    else:                  # right vertical pan
        x1, y1 = x_max, y_max // 2

    clip = clip.crop(
        x1=x1,
        y1=y1,
        width=TARGET_W,
        height=TARGET_H
    )

    # Subtle fade (hides cuts)
    clip = clip.fadein(FADE_TIME).fadeout(FADE_TIME)

    return clip


# ---------------- MAIN ----------------
def main():
    audio_path = get_audio_path()
    total_duration = get_audio_duration(audio_path)
    frames = list_frames()

    log(f"Audio duration: {total_duration:.2f}s | Frames: {len(frames)}")

    # Faster pacing at start (viewer hook)
    durations = []
    remaining = total_duration

    for i in range(len(frames)):
        if i < FAST_START_FRAMES:
            d = total_duration * 0.12 / FAST_START_FRAMES
        else:
            d = (remaining) / (len(frames) - i)
        durations.append(d)
        remaining -= d

    clips = [
        prepare_clip(img, durations[i], i)
        for i, img in enumerate(frames)
    ]

    # Slight overlap = smoother motion
    video = concatenate_videoclips(
        clips,
        method="compose",
        padding=-0.10
    )

    video = video.set_duration(total_duration)

    voice = AudioFileClip(audio_path).subclip(0, total_duration)
    video = video.set_audio(CompositeAudioClip([voice]))

    log("Rendering Shorts master")

    video.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="slow",
        threads=4,
        ffmpeg_params=[
            "-crf", "16",
            "-pix_fmt", "yuv420p",
            "-profile:v", "high",
            "-level", "4.2",
            "-movflags", "+faststart",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
        ],
        logger=None,
    )

    log("Done — clean, cinematic output")


if __name__ == "__main__":
    main()
