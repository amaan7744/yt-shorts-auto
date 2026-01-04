#!/usr/bin/env python3
import os
import sys
from typing import List, Optional

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

PRIMARY_AUDIO = "final_audio.wav"
FALLBACK_AUDIO = "narration.wav"

TARGET_W, TARGET_H = 1080, 1920
FPS = 30
MAX_DURATION = 35.0

# Motion tuning
MICRO_MOTION = 0.025
LOOP_ZOOM_FACTOR = 1.03   # ensures visual loop
# ----------------------------------------


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


# ---------------- CLIP PREP ----------------
def prepare_clip(
    img_path: str,
    duration: float,
    index: int,
    total_frames: int
) -> ImageClip:
    clip = ImageClip(img_path).set_duration(duration)

    # Resize to fill
    w, h = clip.size
    scale = max(TARGET_W / w, TARGET_H / h)
    clip = clip.resize(scale)

    # Center crop
    clip = clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=TARGET_W,
        height=TARGET_H,
    )

    # Retention-aware micro motion
    progress = index / max(total_frames - 1, 1)

    # Slightly faster motion at start, slower at end
    motion_strength = MICRO_MOTION * (1.2 - 0.4 * progress)

    if index % 2 == 0:
        clip = clip.fx(vfx.resize, lambda t: 1.0 + motion_strength * (t / duration))
    else:
        clip = clip.fx(vfx.resize, lambda t: 1.0 - motion_strength * (t / duration))

    return clip


# ---------------- LOOP VISUAL ----------------
def apply_loop_visuals(video):
    """
    Subtle global zoom so last frame visually aligns with first.
    Increases rewatch probability.
    """
    return video.fx(
        vfx.resize,
        lambda t: 1 + (LOOP_ZOOM_FACTOR - 1) * (t / video.duration)
    )


# ---------------- MAIN ----------------
def main():
    audio_path = get_audio_path()
    total_duration = get_audio_duration(audio_path)
    frames = list_frames()

    per_frame = total_duration / len(frames)
    log(f"Audio: {total_duration:.2f}s | Frames: {len(frames)}")

    clips = [
        prepare_clip(img, per_frame, i, len(frames))
        for i, img in enumerate(frames)
    ]

    video = concatenate_videoclips(clips, method="compose")
    video = video.set_duration(total_duration)

    # Apply loop-aware visuals
    video = apply_loop_visuals(video)

    voice = AudioFileClip(audio_path).subclip(0, total_duration)
    video = video.set_audio(CompositeAudioClip([voice]))

    log("Rendering 1080x1920 Shorts master")

    video.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="slow",
        threads=4,
        ffmpeg_params=[
            "-crf", "16",
            "-vf",
            "scale=1080:1920:flags=lanczos,"
            "unsharp=5:5:0.8:3:3:0.4",
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

    log("Done — loop-ready, retention-optimized video")


if __name__ == "__main__":
    main()
