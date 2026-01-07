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

HOOK_ZOOM = 1.12        # strong initial punch
MICRO_MOTION = 0.03    # continuous movement
# ----------------------------------------

def get_audio():
    if os.path.isfile(PRIMARY_AUDIO):
        return PRIMARY_AUDIO
    if os.path.isfile(FALLBACK_AUDIO):
        return FALLBACK_AUDIO
    raise SystemExit("❌ No audio file found")

def audio_duration(path: str) -> float:
    return min(len(AudioSegment.from_file(path)) / 1000.0, MAX_DURATION)

def list_frames() -> List[str]:
    files = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".png"))
    )
    if not files:
        raise SystemExit("❌ No frames found")
    return files

def prep_clip(path: str, dur: float, idx: int) -> ImageClip:
    clip = ImageClip(path).set_duration(dur)

    # Resize + crop
    scale = max(TARGET_W / clip.w, TARGET_H / clip.h)
    clip = clip.resize(scale)
    clip = clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=TARGET_W,
        height=TARGET_H,
    )

    # Strong hook motion on first frame
    if idx == 0:
        clip = clip.fx(vfx.resize, lambda t: HOOK_ZOOM - 0.1 * t)
    else:
        clip = clip.fx(vfx.resize, lambda t: 1 + MICRO_MOTION * t)

    return clip

def main():
    audio_path = get_audio()
    total_dur = audio_duration(audio_path)
    frames = list_frames()

    per_frame = total_dur / len(frames)

    clips = [prep_clip(f, per_frame, i) for i, f in enumerate(frames)]

    # LOOP: end on first frame again
    clips.append(clips[0].set_duration(0.4))

    video = concatenate_videoclips(clips, method="compose").set_duration(total_dur)

    audio = AudioFileClip(audio_path).subclip(0, total_dur)
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
