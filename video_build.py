#!/usr/bin/env python3
"""
YouTube Shorts Video Builder — RETENTION + AESTHETICS
====================================================

RULES:
✔ Speech-aligned beats
✔ No filler
✔ No reuse
✔ Effects ONLY inside beats
✔ Clean ending with audio
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import random

# ==================================================
# FILES
# ==================================================

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
SUBTITLE_FILE = Path("subs.ass")
OUTPUT = Path("output.mp4")

# ==================================================
# VIDEO SETTINGS
# ==================================================

W, H = 1440, 2560
FPS = 25
CRF = "15"

# Visual polish
ZOOM_END = 1.08
VIDEO_MOTION = 0.002  # very subtle
CROSSFADE = 0.12      # sentence boundary only

# Color
SAT = 1.15
CON = 1.06
BRI = 0.02
SHARP = "unsharp=3:3:0.4"

# ==================================================
# UTILS
# ==================================================

def die(msg):
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(1)

def run(cmd):
    subprocess.run(cmd, check=True)

def get_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         str(path)],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())

# ==================================================
# EFFECTS
# ==================================================

def image_filter(duration):
    frames = int(duration * FPS)
    return (
        f"scale=1600:2840,"
        f"zoompan=z='min(zoom+0.0015,{ZOOM_END})':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={W}x{H}"
    )

def video_filter():
    return (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,"
        f"crop={W}:{H}:0:0"
    )

# ==================================================
# MAIN
# ==================================================

def main():
    if not BEATS_FILE.exists():
        die("beats.json missing")
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    beats = json.loads(BEATS_FILE.read_text())["beats"]
    audio_dur = get_duration(AUDIO_FILE)

    tmp = Path(tempfile.mkdtemp(prefix="clips_"))
    clips = []

    print("\n🎬 Building polished clips (speech-safe)")

    for i, beat in enumerate(beats):
        asset = ASSET_DIR / beat["asset_file"]
        out = tmp / f"clip_{i:03d}.mp4"

        if beat["type"] == "image":
            run([
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(asset),
                "-vf", image_filter(2.5),
                "-t", "2.5",
                "-r", str(FPS),
                str(out)
            ])
        else:
            run([
                "ffmpeg", "-y",
                "-i", str(asset),
                "-vf", video_filter(),
                "-r", str(FPS),
                str(out)
            ])

        clips.append(out)

    # concat (hard cuts, micro fade handled by brain)
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

    vf = [
        f"eq=saturation={SAT}:contrast={CON}:brightness={BRI}",
        SHARP
    ]

    if SUBTITLE_FILE.exists():
        sub = str(SUBTITLE_FILE.absolute()).replace("\\", "/").replace(":", "\\:")
        vf.append(f"ass={sub}")

    run([
        "ffmpeg", "-y",
        "-i", str(merged),
        "-i", str(AUDIO_FILE),
        "-vf", ",".join(vf),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-crf", CRF,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-t", f"{audio_dur:.6f}",
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    print("\n✅ RETENTION + AESTHETICS BUILD COMPLETE")
    print(f"📁 Output: {OUTPUT}")

if __name__ == "__main__":
    main()
