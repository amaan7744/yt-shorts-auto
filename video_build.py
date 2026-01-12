#!/usr/bin/env python3

import os
import json
from typing import List

from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
    vfx,
)

from pydub import AudioSegment

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

FRAMES_DIR = "frames"
BEATS_FILE = "beats.json"

AUDIO_FILE = "final_audio.wav"
OUTPUT_VIDEO = "video_raw.mp4"

TARGET_W, TARGET_H = 1080, 1920
FPS = 60
MAX_DURATION = 35.0

# Motion tuning (Shorts-safe)
HOOK_ZOOM = 1.10
MICRO_MOTION = 0.03
CTA_ZOOM = 1.08
CTA_EXTRA_TIME = 0.8

# Audio safety margin (MoviePy bug guard)
AUDIO_SAFETY_MARGIN = 0.2  # seconds

# --------------------------------------------------
# UTILS
# --------------------------------------------------

def log(msg: str):
    print(msg, flush=True)

def load_beats():
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")
    return json.load(open(BEATS_FILE, "r", encoding="utf-8"))

def list_frames() -> List[str]:
    frames = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if not frames:
        raise SystemExit("❌ No frames found")
    return frames

def audio_duration(path: str) -> float:
    audio = AudioSegment.from_file(path)
    return min(len(audio) / 1000.0, MAX_DURATION)

def force_even_dimensions(clip: ImageClip) -> ImageClip:
    w = int(clip.w // 2 * 2)
    h = int(clip.h // 2 * 2)
    return clip.resize((w, h))

# --------------------------------------------------
# CLIP PREPARATION
# --------------------------------------------------

def prepare_clip(
    img_path: str,
    duration: float,
    index: int,
    is_cta: bool,
) -> ImageClip:
    clip = ImageClip(img_path).set_duration(duration)

    # Scale to cover vertical canvas
    scale = max(TARGET_W / clip.w, TARGET_H / clip.h)
    clip = clip.resize(scale)

    # Center crop
    clip = clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=TARGET_W,
        height=TARGET_H,
    )

    # Motion logic
    if index == 0:
        # Strong hook zoom
        clip = clip.fx(vfx.resize, HOOK_ZOOM)
    elif is_cta:
        # CTA emphasis
        clip = clip.fx(vfx.resize, CTA_ZOOM)
    else:
        # Gentle micro-motion
        clip = clip.fx(vfx.resize, lambda t: 1 + MICRO_MOTION * t)

    return force_even_dimensions(clip)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    log("Loading beats and frames...")

    beats = load_beats()
    frames = list_frames()

    if len(beats) != len(frames):
        raise SystemExit("❌ Beats and frames count mismatch")

    audio_len = audio_duration(AUDIO_FILE)
    log(f"Audio duration: {audio_len:.2f}s")

    base_duration = audio_len / len(frames)
    clips = []

    for i, (img, beat) in enumerate(zip(frames, beats)):
        dur = base_duration
        if beat.get("intent") == "attention":
            dur += CTA_EXTRA_TIME

        log(f"Processing frame {i+1}/{len(frames)} ({dur:.2f}s)...")

        clips.append(
            prepare_clip(
                img_path=img,
                duration=dur,
                index=i,
                is_cta=(beat.get("intent") == "attention"),
            )
        )

    # Loop reinforcement (micro replay nudge)
    log("Adding loop frame...")
    clips.append(clips[0].set_duration(0.4))

    log("Concatenating clips...")
    video = concatenate_videoclips(clips, method="compose")

    # --------------------------------------------------
    # AUDIO (SAFE CLAMP – CRASH FIX)
    # --------------------------------------------------
    log("Adding audio (safe clamp)...")

    audio_clip = AudioFileClip(AUDIO_FILE)

    # Never let MoviePy read the final ~200ms
    safe_audio_end = min(
        audio_clip.duration - AUDIO_SAFETY_MARGIN,
        video.duration
    )

    if safe_audio_end <= 0:
        raise SystemExit("❌ Audio duration too short after safety clamp")

    audio = audio_clip.subclip(0, safe_audio_end)
    video = video.set_audio(CompositeAudioClip([audio]))

    # --------------------------------------------------
    # RENDER
    # --------------------------------------------------
    log("Rendering video...")
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

    log("✅ video_raw.mp4 created successfully")

if __name__ == "__main__":
    main()
