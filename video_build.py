#!/usr/bin/env python3
"""
YouTube Shorts Video Builder
BLACK-SCREEN IMPOSSIBLE VERSION
"""

import json
import subprocess
from pathlib import Path
import tempfile

WIDTH, HEIGHT = 1080, 1920
FPS = 30

BEATS = Path("beats.json")
FRAMES = Path("frames")
AUDIO = Path("final_audio.wav")
SUBS = Path("subs.ass")
OUTPUT = Path("output.mp4")

def die(msg):
    raise SystemExit(f"[VIDEO] ❌ {msg}")

def load_beats():
    if not BEATS.exists():
        die("beats.json missing")
    return json.loads(BEATS.read_text())["beats"]

def build_video_segments(beats):
    segments = []

    for beat in beats:
        img = FRAMES / f"scene_{beat['beat_id']:02d}.png"
        if not img.exists():
            die(f"Missing image {img.name}")

        duration = max(0.5, float(beat["estimated_duration"]))

        out = Path(tempfile.mktemp(suffix=".mp4"))

        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img),
            "-t", f"{duration:.2f}",
            "-vf",
            (
                f"scale={WIDTH}:{HEIGHT}:flags=lanczos,"
                "zoompan=z='min(1.05,zoom+0.0005)':d=1"
            ),
            "-r", str(FPS),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            out
        ], check=True)

        segments.append(out)

    return segments

def concat_segments(segments):
    list_file = Path("segments.txt")
    with open(list_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg.resolve()}'\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        "video_only.mp4"
    ], check=True)

def mux_audio_and_subs():
    subprocess.run([
        "ffmpeg", "-y",
        "-i", "video_only.mp4",
        "-i", AUDIO,
        "-vf", f"ass={SUBS}",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "16",
        "-preset", "slow",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        OUTPUT
    ], check=True)

def main():
    if not AUDIO.exists():
        die("final_audio.wav missing")
    if not SUBS.exists():
        die("subs.ass missing")

    beats = load_beats()
    print(f"[VIDEO] Scenes: {len(beats)}")

    segments = build_video_segments(beats)
    concat_segments(segments)
    mux_audio_and_subs()

    print(f"[VIDEO] ✅ VISUAL VIDEO READY → {OUTPUT}")

if __name__ == "__main__":
    main()
