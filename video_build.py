#!/usr/bin/env python3
"""
High-Retention YouTube Shorts Video Builder
- 70% Gameplay / 30% Pixel Visuals
- Audio duration is the single source of truth
- Gameplay audio removed
- Subtitles burned reliably
- No flicker, no early cutoff
"""

import os
import sys
import random
import subprocess
from pathlib import Path

# ==================================================
# CONFIG
# ==================================================
WIDTH, HEIGHT = 1080, 1920
FPS = 30

GAMEPLAY_DIR = Path("gameplay/loops")
PIXEL_DIR = Path("frames")

AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT_FILE = Path("output.mp4")

GAMEPLAY_RATIO = 0.70   # 70%
PIXEL_RATIO = 0.30      # 30%

# ==================================================
# UTILS
# ==================================================
def log(msg: str):
    print(f"[VIDEO] {msg}", flush=True)

def die(msg: str):
    sys.exit(f"[VIDEO] ❌ {msg}")

def ffprobe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    return float(subprocess.check_output(cmd).decode().strip())

# ==================================================
# VALIDATION
# ==================================================
def validate_inputs():
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    if not SUBS_FILE.exists():
        die("subs.ass missing")

    if not GAMEPLAY_DIR.exists():
        die("gameplay/loops missing")

    if not PIXEL_DIR.exists():
        die("frames directory missing")

    gameplay_files = list(GAMEPLAY_DIR.glob("*.mp4"))
    if not gameplay_files:
        die("No gameplay videos found")

    pixel_files = list(PIXEL_DIR.glob("*.jpg"))
    if len(pixel_files) < 3:
        die("Not enough pixel frames (need at least 3)")

# ==================================================
# MAIN BUILD
# ==================================================
def main():
    validate_inputs()

    gameplay_files = list(GAMEPLAY_DIR.glob("*.mp4"))
    pixel_files = sorted(PIXEL_DIR.glob("*.jpg"))

    gameplay_src = random.choice(gameplay_files)
    audio_duration = ffprobe_duration(AUDIO_FILE)

    gameplay_duration = audio_duration * GAMEPLAY_RATIO
    pixel_duration = audio_duration * PIXEL_RATIO

    log(f"Audio duration: {audio_duration:.2f}s")
    log(f"Gameplay duration: {gameplay_duration:.2f}s")
    log(f"Pixel duration: {pixel_duration:.2f}s")

    # ---------------------------
    # TEMP FILES
    # ---------------------------
    tmp_gameplay = "tmp_gameplay.mp4"
    tmp_pixel = "tmp_pixel.mp4"

    # ---------------------------
    # GAMEPLAY VIDEO (NO AUDIO)
    # ---------------------------
    log("Building gameplay layer (muted, cropped, stable)…")
    subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-ss", "5",
        "-i", str(gameplay_src),
        "-t", f"{gameplay_duration:.3f}",
        "-vf",
        f"scale=-1:{HEIGHT},crop={WIDTH}:{HEIGHT}",
        "-an",  # 🔴 REMOVE GAMEPLAY AUDIO
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        tmp_gameplay
    ], check=True)

    # ---------------------------
    # PIXEL VIDEO (SLIDESHOW)
    # ---------------------------
    log("Building pixel layer (cinematic, no flicker)…")

    frame_time = pixel_duration / len(pixel_files)
    concat_txt = "pixel_list.txt"

    with open(concat_txt, "w") as f:
        for img in pixel_files:
            f.write(f"file '{img.resolve()}'\n")
            f.write(f"duration {frame_time:.3f}\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_txt,
        "-vf",
        f"scale={WIDTH}:{HEIGHT},format=yuv420p",
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        tmp_pixel
    ], check=True)

    # ---------------------------
    # FINAL MERGE + SUBS + AUDIO
    # ---------------------------
    log("Compositing final video (subs + TTS audio locked)…")

    subprocess.run([
        "ffmpeg", "-y",
        "-i", tmp_gameplay,
        "-i", tmp_pixel,
        "-i", str(AUDIO_FILE),
        "-filter_complex",
        (
            f"[0:v][1:v]concat=n=2:v=1:a=0,"
            f"ass='{SUBS_FILE.resolve()}'"
        ),
        "-map", "0:v",
        "-map", "2:a",
        "-t", f"{audio_duration:.3f}",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        OUTPUT_FILE
    ], check=True)

    # ---------------------------
    # CLEANUP
    # ---------------------------
    os.remove(tmp_gameplay)
    os.remove(tmp_pixel)
    os.remove(concat_txt)

    log(f"✅ FINAL VIDEO READY: {OUTPUT_FILE}")

# ==================================================
if __name__ == "__main__":
    main()
