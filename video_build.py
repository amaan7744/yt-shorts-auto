#!/usr/bin/env python3

import os
import json
import subprocess
from typing import List

from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
)

from pydub import AudioSegment

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

FRAMES_DIR = "frames"
CLIPS_DIR = "clips"
BEATS_FILE = "beats.json"

AUDIO_FILE = "final_audio.wav"
OUTPUT_VIDEO = "video_raw.mp4"

TARGET_W, TARGET_H = 1080, 1920
FPS = 30
MAX_DURATION = 35.0

CTA_EXTRA_TIME = 0.8
AUDIO_SAFETY_MARGIN = 0.2

os.makedirs(CLIPS_DIR, exist_ok=True)

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

# --------------------------------------------------
# AI-STYLE IMAGE ANIMATION (NO GEOMETRY CHANGE)
# --------------------------------------------------

def animate_image(input_img: str, output_mp4: str, duration: float):
    """
    Creates subtle AI-style motion:
    - animated grain
    - light breathing
    - micro contrast shift
    NO zoom, NO pan, NO resize
    """
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", input_img,
        "-t", str(duration),
        "-vf",
        (
            "scale=1080:1920:flags=lanczos,"
            "format=yuv420p,"
            "noise=alls=8:allf=t+u,"
            "eq=brightness=0.015*sin(2*PI*t/{}):contrast=1.02,"
            "vignette=PI/6"
        ).format(duration),
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "16",
        "-pix_fmt", "yuv420p",
        output_mp4
    ]

    subprocess.run(cmd, check=True)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    log("Loading beats, frames, and audio...")

    beats = load_beats()
    frames = list_frames()

    if len(beats) != len(frames):
        raise SystemExit("❌ Beats and frames count mismatch")

    audio_len = audio_duration(AUDIO_FILE)
    log(f"Audio duration: {audio_len:.2f}s")

    base_duration = audio_len / len(frames)
    clips = []

    # --------------------------------------------------
    # BUILD ANIMATED CLIPS
    # --------------------------------------------------

    for i, (img, beat) in enumerate(zip(frames, beats), 1):
        dur = base_duration
        if beat.get("intent") == "attention":
            dur += CTA_EXTRA_TIME

        out_clip = os.path.join(CLIPS_DIR, f"clip_{i:03d}.mp4")

        log(f"Animating frame {i}/{len(frames)} ({dur:.2f}s)...")
        animate_image(img, out_clip, dur)

        clips.append(VideoFileClip(out_clip))

    # --------------------------------------------------
    # LOOP REINFORCEMENT
    # --------------------------------------------------

    log("Adding loop reinforcement...")
    clips.append(clips[0].subclip(0, 0.4))

    log("Concatenating clips...")
    video = concatenate_videoclips(clips, method="compose")

    # --------------------------------------------------
    # AUDIO (SAFE CLAMP)
    # --------------------------------------------------

    log("Adding audio...")
    audio_clip = AudioFileClip(AUDIO_FILE)

    safe_audio_end = min(
        audio_clip.duration - AUDIO_SAFETY_MARGIN,
        video.duration
    )

    if safe_audio_end <= 0:
        raise SystemExit("❌ Audio too short after clamp")

    audio = audio_clip.subclip(0, safe_audio_end)
    video = video.set_audio(CompositeAudioClip([audio]))

    # --------------------------------------------------
    # RENDER
    # --------------------------------------------------

    log("Rendering final video...")
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
    
