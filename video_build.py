#!/usr/bin/env python3
"""
Stable YouTube Shorts Builder
- 100% Gameplay
- Audio is master timeline
- Gameplay audio removed
- Subtitles ALWAYS burned
- No flicker, no early cutoff
- GitHub Actions safe
"""

import os
import sys
import random
import subprocess
from pathlib import Path

# ===============================
# CONFIG
# ===============================
WIDTH, HEIGHT = 1080, 1920
FPS = 30

GAMEPLAY_DIR = Path("gameplay/loops")
AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT = Path("output.mp4")

TMP_VIDEO = Path("tmp_gameplay.mp4")

# ===============================
def log(msg):
    print(f"[VIDEO] {msg}", flush=True)

def die(msg):
    sys.exit(f"[VIDEO] ❌ {msg}")

def duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]).decode().strip())

# ===============================
def validate():
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")
    if not SUBS_FILE.exists():
        die("subs.ass missing")
    if not GAMEPLAY_DIR.exists():
        die("gameplay/loops missing")

    vids = list(GAMEPLAY_DIR.glob("*.mp4"))
    if not vids:
        die("No gameplay videos found")

    return vids

# ===============================
def main():
    gameplay_files = validate()
    src = random.choice(gameplay_files)

    audio_len = duration(AUDIO_FILE)
    log(f"Audio duration: {audio_len:.2f}s")
    log(f"Gameplay source: {src.name}")

    # ------------------------------------------------
    # STEP 1 — PREPARE GAMEPLAY (NO AUDIO)
    # ------------------------------------------------
    log("Preparing gameplay base video…")

    subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-ss", "5",
        "-i", str(src),
        "-t", f"{audio_len:.3f}",
        "-vf",
        f"scale=-1:{HEIGHT},crop={WIDTH}:{HEIGHT}",
        "-an",
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        TMP_VIDEO
    ], check=True)

    # ------------------------------------------------
    # STEP 2 — FINAL MUX (AUDIO + SUBS)
    # ------------------------------------------------
    log("Muxing audio + subtitles…")

    subprocess.run([
        "ffmpeg", "-y",
        "-i", TMP_VIDEO,
        "-i", AUDIO_FILE,
        "-vf", f"ass={SUBS_FILE}",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        OUTPUT
    ], check=True)

    TMP_VIDEO.unlink(missing_ok=True)
    log(f"✅ FINAL VIDEO READY: {OUTPUT}")

# ===============================
if __name__ == "__main__":
    main()
