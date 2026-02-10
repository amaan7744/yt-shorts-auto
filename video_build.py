#!/usr/bin/env python3
"""
Video Builder — AUDIO IS SOURCE OF TRUTH

- No speech_map.json
- No timing guesses
- Video always ends with audio
- No frozen frames
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# ==================================================
# FILES
# ==================================================

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT = Path("output.mp4")

# ==================================================
# SETTINGS
# ==================================================

W, H = 1440, 2560
FPS = 25
CRF = "15"

# ==================================================
# UTILS
# ==================================================

def die(msg):
    raise RuntimeError(msg)

def run(cmd):
    subprocess.run(cmd, check=True)

def duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())

# ==================================================
# MAIN
# ==================================================

def main():
    if not BEATS_FILE.exists():
        die("beats.json missing")
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    beats = json.loads(BEATS_FILE.read_text())["beats"]
    audio_dur = duration(AUDIO_FILE)

    tmp = Path(tempfile.mkdtemp(prefix="build_"))
    clips = []

    print(f"🎧 Audio duration: {audio_dur:.2f}s")

    # ----------------------------------------------
    # BUILD VISUAL CLIPS (NO DURATIONS)
    # ----------------------------------------------

    for i, beat in enumerate(beats):
        src = ASSET_DIR / beat["asset_file"]
        out = tmp / f"clip_{i:03d}.mp4"

        if beat["type"] == "image":
            run([
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(src),
                "-vf", f"scale={W}:{H}:force_original_aspect_ratio=cover",
                "-t", "2.5",
                "-r", str(FPS),
                str(out)
            ])
        else:
            run([
                "ffmpeg", "-y",
                "-i", str(src),
                "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                       f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black",
                "-r", str(FPS),
                str(out)
            ])

        clips.append(out)

    # ----------------------------------------------
    # CONCAT ALL CLIPS (LOOPABLE)
    # ----------------------------------------------

    concat = tmp / "concat.txt"
    concat.write_text("\n".join(f"file '{c}'" for c in clips))

    merged = tmp / "merged.mp4"

    run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat),
        "-c", "copy",
        str(merged)
    ])

    # ----------------------------------------------
    # FINAL ENCODE (AUDIO LOCKED)
    # ----------------------------------------------

    vf = [
        "eq=saturation=1.15:contrast=1.05:brightness=0.02"
    ]

    if SUBS_FILE.exists():
        sub = str(SUBS_FILE.absolute()).replace("\\", "/").replace(":", "\\:")
        vf.append(f"ass={sub}")

    run([
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(merged),
        "-i", str(AUDIO_FILE),
        "-vf", ",".join(vf),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-crf", CRF,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    print("✅ Video build complete")
    print(f"📁 Output: {OUTPUT}")

if __name__ == "__main__":
    main()
