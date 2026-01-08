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
MAX_DURATION = 35.0

HOOK_ZOOM = 1.12
MICRO_MOTION = 0.03
# ----------------------------------------


def get_audio_path() -> str:
    if os.path.isfile(PRIMARY_AUDIO):
        return PRIMARY_AUDIO
    if os.path.isfile(FALLBACK_AUDIO):
        return FALLBACK_AUDIO
    raise SystemExit("❌ No audio file found")


def audio_duration(path: str) -> float:
    audio = AudioSegment.from_file(path)
    return min(len(audio) / 1000.0, MAX_DURATION)


def list_frames() -> List[str]:
    frames = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if not frames:
        raise SystemExit("❌ No frames found")
    return frames


def force_even_resize(clip: ImageClip) -> ImageClip:
    """
    Enforce even dimensions for libx264 safety.
    """
    w = int(clip.w // 2 * 2)
    h = int(clip.h // 2 * 2)
    return clip.resize((w, h))


def prepare_clip(img_path: str, duration: float, index: int) -> ImageClip:
    clip = ImageClip(img_path).set_duration(duration)

    # Initial scale to cover target
    scale = max(TARGET_W / clip.w, TARGET_H / clip.h)
    clip = clip.resize(scale)

    # Center crop to exact vertical format
    clip = clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=TARGET_W,
        height=TARGET_H,
    )

    # Strong motion on first frame (hook)
    if index == 0:
        clip = clip.fx(vfx.resize, lambda t: HOOK_ZOOM - 0.1 * t)
    else:
        clip = clip.fx(vfx.resize, lambda t: 1 + MICRO_MOTION * t)

    # 🔒 CRITICAL: force even dimensions AFTER motion
    clip = force_even_resize(clip)

    return clip


def main():
    audio_path = get_audio_path()
    total_duration = audio_duration(audio_path)
    frames = list_frames()

    per_frame = total_duration / len(frames)

    clips = [
        prepare_clip(img, per_frame, i)
        for i, img in enumerate(frames)
    ]

    # Loop ending (reuse first frame briefly)
    clips.append(clips[0].set_duration(0.4))

    video = concatenate_videoclips(clips, method="compose")
    video = video.set_duration(total_duration)

    audio = AudioFileClip(audio_path).subclip(0, total_duration)
    video = video.set_audio(CompositeAudioClip([audio]))

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


if __name__ == "__main__":
    main()
