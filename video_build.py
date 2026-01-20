#!/usr/bin/env python3
"""
YouTube Shorts Video Builder — GAMEPLAY ONLY (100%)
- Gameplay fills entire video
- Gameplay audio removed
- Narration controls duration
- Subtitles always visible
- No flicker, no early cut, no stream bugs
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
AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT_FILE = Path("output.mp4")

# ==================================================
def log(msg):
    print(f"[VIDEO] {msg}", flush=True)

def die(msg):
    sys.exit(f"[VIDEO] ❌ {msg}")

def duration(path: Path) -> float:
    return float(
        subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ]).decode().strip()
    )

# ==================================================
def validate():
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    if not SUBS_FILE.exists():
        die("subs.ass missing")

    if not GAMEPLAY_DIR.exists():
        die("gameplay/loops missing")

    if not list(GAMEPLAY_DIR.glob("*.mp4")):
        die("No gameplay videos found")

# ==================================================
def main():
    validate()

    gameplay_src = random.choice(list(GAMEPLAY_DIR.glob("*.mp4")))
    audio_len = duration(AUDIO_FILE)

    log(f"Using gameplay: {gameplay_src.name}")
    log(f"Narration duration: {audio_len:.2f}s")

    # ------------------------------------------------
    # BUILD FINAL VIDEO (ONE PASS, SAFE)
    # ------------------------------------------------
    cmd = [
        "ffmpeg", "-y",

        # Gameplay (looped)
        "-stream_loop", "-1",
        "-ss", "5",                       # skip menus / intros
        "-i", str(gameplay_src),

        # Narration
        "-i", str(AUDIO_FILE),

        # Force video length = audio length
        "-t", f"{audio_len:.3f}",

        # Video processing
        "-vf",
        (
            f"scale=-1:{HEIGHT},"
            f"crop={WIDTH}:{HEIGHT},"
            f"ass='{SUBS_FILE.resolve()}'"
        ),

        # Remove gameplay audio
        "-map", "0:v:0",
        "-map", "1:a:0",

        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "192k",

        "-movflags", "+faststart",
        OUTPUT_FILE
    ]

    log("Rendering FINAL gameplay-only Short…")
    subprocess.run(cmd, check=True)

    log(f"✅ DONE — {OUTPUT_FILE} (100% gameplay)")

# ==================================================
if __name__ == "__main__":
    main()
