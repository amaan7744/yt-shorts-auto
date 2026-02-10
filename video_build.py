#!/usr/bin/env python3
"""
Video Builder — SPEECH LOCKED (FINAL)

RULES:
- speech_map.json is the ONLY timing source
- One visual per script line
- Video always ends exactly with audio
"""

import json
import subprocess
import tempfile
from pathlib import Path

BEATS_FILE = Path("beats.json")
SPEECH_FILE = Path("speech_map.json")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT = Path("output.mp4")
ASSET_DIR = Path("asset")

W, H = 1440, 2560
FPS = 25
CRF = "15"


def die(msg):
    raise RuntimeError(msg)


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    if not BEATS_FILE.exists():
        die("beats.json missing")

    if not SPEECH_FILE.exists():
        die("speech_map.json missing")

    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    beats = json.loads(BEATS_FILE.read_text())["beats"]
    speech_map = json.loads(SPEECH_FILE.read_text())

    # 🔒 Validate speech map schema
    if not isinstance(speech_map, list):
        die("speech_map.json must be a list")

    speech = {}
    for s in speech_map:
        if not isinstance(s, dict):
            die("speech_map entries must be objects")
        if not all(k in s for k in ("line", "start", "end")):
            die(f"Invalid speech_map entry: {s}")
        speech[s["line"]] = s

    tmp = Path(tempfile.mkdtemp(prefix="video_build_"))
    clips = []

    print("🎬 Building clips (speech-locked)")

    for beat in beats:
        line_no = beat["script_line"]
        if line_no not in speech:
            die(f"No speech timing for line {line_no}")

        seg = speech[line_no]
        duration = max(0.05, seg["end"] - seg["start"])

        asset = ASSET_DIR / beat["asset_file"]
        out = tmp / f"clip_{line_no:02d}.mp4"

        if beat["type"] == "image":
            run([
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(asset),
                "-t", f"{duration:.3f}",
                "-vf",
                f"scale=1600:2840,zoompan=z='min(zoom+0.0015,1.08)':d={int(duration*FPS)}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}",
                "-r", str(FPS),
                str(out)
            ])
        else:
            run([
                "ffmpeg", "-y",
                "-i", str(asset),
                "-t", f"{duration:.3f}",
                "-vf",
                f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black",
                "-r", str(FPS),
                str(out)
            ])

        clips.append(out)

    # concat
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

    # final mux
    run([
        "ffmpeg", "-y",
        "-i", str(merged),
        "-i", str(AUDIO_FILE),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-crf", CRF,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    print("✅ Video built successfully")


if __name__ == "__main__":
    main()
