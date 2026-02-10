#!/usr/bin/env python3
"""
PRO SHORTS VIDEO BUILDER — AUDIO IS SOURCE OF TRUTH

✔ True cover framing
✔ Ken Burns motion on images
✔ Visual normalization
✔ No frozen frames
✔ Shorts-optimized color
"""

import json
import subprocess
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
CRF_INTERMEDIATE = "17"
CRF_FINAL = "15"

# ==================================================
# UTILS
# ==================================================

def die(msg):
    raise RuntimeError(msg)

def run(cmd):
    print("▶", " ".join(cmd))
    subprocess.run(cmd, check=True)

# ==================================================
# MAIN
# ==================================================

def main():
    if not BEATS_FILE.exists():
        die("beats.json missing")
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    beats = json.loads(BEATS_FILE.read_text())["beats"]

    tmp = Path(tempfile.mkdtemp(prefix="build_"))
    clips = []

    print("🎬 Building pro-grade clips")

    # ----------------------------------------------
    # BUILD CLIPS (NORMALIZED, ANIMATED)
    # ----------------------------------------------

    for i, beat in enumerate(beats):
        src = ASSET_DIR / beat["asset_file"]
        out = tmp / f"clip_{i:03d}.mp4"

        if beat["type"] == "image":
            vf = (
                f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},"
                f"zoompan=z='min(1.06,zoom+0.0006)':d=62,"
                f"fps={FPS},"
                f"eq=saturation=1.1:contrast=1.05"
            )

            run([
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(src),
                "-vf", vf,
                "-t", "2.5",
                "-c:v", "libx264",
                "-crf", CRF_INTERMEDIATE,
                "-pix_fmt", "yuv420p",
                str(out)
            ])

        else:
            vf = (
                f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},"
                f"eq=saturation=1.05:contrast=1.04"
            )

            run([
                "ffmpeg", "-y",
                "-i", str(src),
                "-vf", vf,
                "-r", str(FPS),
                "-c:v", "libx264",
                "-crf", CRF_INTERMEDIATE,
                "-pix_fmt", "yuv420p",
                str(out)
            ])

        clips.append(out)

    # ----------------------------------------------
    # CONCAT (NO RE-ENCODE)
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
    # FINAL MASTER (AUDIO LOCKED)
    # ----------------------------------------------

    vf = [
        "eq=saturation=1.12:contrast=1.08:brightness=0.01"
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
        "-crf", CRF_FINAL,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    print("✅ PRO VIDEO BUILD COMPLETE")
    print(f"📁 Output → {OUTPUT}")

if __name__ == "__main__":
    main()
