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

# Small motion to help compression (DO NOT increase)
MICRO_MOTION = 0.025
# ----------------------------------------


def log(msg: str):
    print(f"[VID] {msg}", flush=True)


def get_audio_duration(path: str) -> float:
    if not os.path.isfile(path):
        raise SystemExit(f"[VID] Missing audio file: {path}")

    audio = AudioSegment.from_file(path)
    duration = len(audio) / 1000.0

    if duration > MAX_DURATION:
        log(f"Audio {duration:.2f}s > {MAX_DURATION}s — trimming")
    else:
        log(f"Audio duration: {duration:.2f}s")

    return min(duration, MAX_DURATION)


def list_frames() -> List[str]:
    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit(f"[VID] Missing frames directory: {FRAMES_DIR}")

    frames = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )

    if not frames:
        raise SystemExit("[VID] No frame images found")

    log(f"Using {len(frames)} frames")
    return frames


def prepare_clip(img_path: str, duration: float, index: int) -> ImageClip:
    """
    Quality-safe image → video clip
    - Single resize
    - Single crop
    - Micro motion only
    """
    clip = ImageClip(img_path).set_duration(duration)

    # --- ONE high-quality resize ---
    w, h = clip.size
    scale = max(TARGET_W / w, TARGET_H / h)
    clip = clip.resize(scale)

    # --- Exact 1080x1920 crop ---
    clip = clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=TARGET_W,
        height=TARGET_H,
    )

    # --- Micro motion (compression-safe) ---
    if index % 2 == 0:
        clip = clip.fx(
            vfx.resize,
            lambda t: 1.0 + MICRO_MOTION * (t / duration)
        )
    else:
        clip = clip.fx(
            vfx.resize,
            lambda t: 1.0 - MICRO_MOTION * (t / duration)
        )

    return clip


def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else VOICE_AUDIO

    total_duration = get_audio_duration(audio_path)
    frames = list_frames()
    per_frame = total_duration / len(frames)

    log(f"Per-frame duration: {per_frame:.2f}s")

    clips = [
        prepare_clip(img, per_frame, i)
        for i, img in enumerate(frames)
    ]

    # --- Concatenate clips ---
    video = concatenate_videoclips(clips, method="compose")
    video = video.set_duration(total_duration)

    # --- Attach audio (hard-cut to video length) ---
    voice = AudioFileClip(audio_path).subclip(0, total_duration)
    video = video.set_audio(CompositeAudioClip([voice]))

    # --- FINAL HIGH-QUALITY RENDER ---
    log("Rendering 1080p Shorts master (CRF-based FFmpeg encode)")

    video.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="slow",
        threads=4,
        ffmpeg_params=[
            # Quality-first encode
            "-crf", "16",

            # High-quality scaling + light sharpening
            "-vf",
            "scale=1080:1920:flags=lanczos,"
            "unsharp=5:5:0.8:3:3:0.4",

            # YouTube-friendly flags
            "-pix_fmt", "yuv420p",
            "-profile:v", "high",
            "-level", "4.2",
            "-movflags", "+faststart",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-colorspace", "bt709",
        ],
        logger=None,
    )

    log("Done — true 1080p master preserved")


if __name__ == "__main__":
    main()
