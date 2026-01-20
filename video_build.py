#!/usr/bin/env python3

import os
import random
import subprocess
from moviepy.editor import VideoFileClip, AudioFileClip

WIDTH, HEIGHT = 1080, 1920
FPS = 30

GAMEPLAY_DIR = "gameplay/loops"
AUDIO_FILE = "final_audio.wav"
SUBS_FILE = "subs.ass"
OUTPUT = "output.mp4"
TMP_VIDEO = "tmp_gameplay.mp4"

def die(msg):
    raise SystemExit(f"[VIDEO] ❌ {msg}")

def log(msg):
    print(f"[VIDEO] {msg}", flush=True)

def normalize_gameplay(input_path: str):
    """
    Re-encode gameplay to constant FPS + clean timestamps
    THIS IS THE CRITICAL FIX
    """
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"scale={WIDTH}:{HEIGHT},fps={FPS}",
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            TMP_VIDEO,
        ],
        check=True,
    )

def pick_and_fix_gameplay():
    files = [f for f in os.listdir(GAMEPLAY_DIR) if f.endswith(".mp4")]
    if not files:
        die("No gameplay clips found")

    src = os.path.join(GAMEPLAY_DIR, random.choice(files))
    log(f"Normalizing gameplay: {os.path.basename(src)}")
    normalize_gameplay(src)

    return VideoFileClip(TMP_VIDEO).set_fps(FPS)

def main():
    if not os.path.isfile(AUDIO_FILE):
        die("final_audio.wav missing")
    if not os.path.isfile(SUBS_FILE):
        die("subs.ass missing")

    audio = AudioFileClip(AUDIO_FILE)
    audio_duration = audio.duration

    log(f"Audio duration: {audio_duration:.2f}s")

    gameplay = pick_and_fix_gameplay()

    # 🔒 FORCE VIDEO TO MATCH AUDIO
    if gameplay.duration < audio_duration:
        gameplay = gameplay.loop(duration=audio_duration)
    else:
        gameplay = gameplay.subclip(0, audio_duration)

    final = gameplay.set_audio(audio)

    log("Rendering final video (audio-locked)…")
    final.write_videofile(
        OUTPUT,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="slow",
        ffmpeg_params=[
            "-vf", f"ass={SUBS_FILE}",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
        ],
        threads=4,
        logger=None,
    )

    os.remove(TMP_VIDEO)
    log("✅ output.mp4 rendered (audio fully preserved)")

if __name__ == "__main__":
    main()
