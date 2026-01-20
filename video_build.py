#!/usr/bin/env python3

import os
import random
import subprocess
import sys

# ==================================================
# CONFIG - SHORTS OPTIMIZED
# ==================================================
WIDTH, HEIGHT = 1080, 1920
FPS = 30
GAMEPLAY_DIR = "gameplay/loops"
AUDIO_FILE = "final_audio.wav"
SUBS_FILE = "subs.ass"
OUTPUT = "output.mp4"

def log(msg):
    print(f"[VIDEO] {msg}", flush=True)

def get_duration(file):
    """Accurately gets duration using ffprobe."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file]
    return float(subprocess.check_output(cmd).decode().strip())

def main():
    if not os.path.exists(GAMEPLAY_DIR):
        print(f"❌ {GAMEPLAY_DIR} missing"); return

    # 1. Pick a random clip
    files = [f for f in os.listdir(GAMEPLAY_DIR) if f.endswith(".mp4")]
    if not files: print("❌ No gameplay clips"); return
    bg_video = os.path.join(GAMEPLAY_DIR, random.choice(files))
    
    # 2. Get Audio Duration
    audio_dur = get_duration(AUDIO_FILE)
    log(f"Audio Duration: {audio_dur}s")

    # 3. Build the FFmpeg Command (The "Magic" Filter)
    # This command:
    # - Scales and Crops the video to 9:16 (removing side UI/text)
    # - Loops the video if it's too short
    # - Syncs audio and video precisely
    # - Burn in subtitles
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", "00:00:05",           # Skip first 5s of gameplay (often has menus)
        "-stream_loop", "-1",        # Loop video infinitely until audio ends
        "-i", bg_video,              # Input Video
        "-i", AUDIO_FILE,            # Input Audio
        "-t", str(audio_dur),        # Force output to match Audio Duration
        "-filter_complex", (
            f"[0:v]scale=-1:{HEIGHT}," # Scale height to 1920
            f"crop={WIDTH}:{HEIGHT},"  # Crop width to 1080 (Removes side text/UI)
            f"ass={SUBS_FILE}"         # Burn in subtitles
        ),
        "-c:v", "libx264",
        "-preset", "slow",           # Slow = Higher Quality
        "-crf", "18",                # 18-20 = Near Lossless (High Quality)
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",                 # Extra safety to stop at shortest stream
        "-pix_fmt", "yuv420p",
        OUTPUT
    ]

    log("Rendering high-quality short...")
    try:
        subprocess.run(cmd, check=True)
        log(f"✅ DONE: {OUTPUT}")
    except subprocess.CalledProcessError as e:
        log(f"❌ Rendering failed: {e}")

if __name__ == "__main__":
    main()
