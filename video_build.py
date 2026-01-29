#!/usr/bin/env python3
"""
Script-Locked Video Builder
- Every beat = one visual
- Visuals ALWAYS match narration
- No gameplay
- No random 3D effects
- GitHub Actions safe
"""

import os
import sys
import json
import subprocess
from pathlib import Path

FPS = 30
WIDTH, HEIGHT = 1080, 1920

AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT = Path("output.mp4")
FRAMES_DIR = Path("frames")

# ----------------------------
def log(msg):
    print(f"[VIDEO] {msg}", flush=True)

def die(msg):
    sys.exit(f"[VIDEO] ❌ {msg}")

# ----------------------------
def load_beats():
    if Path("beats.json").exists():
        with open("beats.json") as f:
            return json.load(f)["beats"]

    if Path("script.txt").exists():
        text = Path("script.txt").read_text()
        return [{"text": s.strip(), "estimated_duration": 4}
                for s in text.split(".") if s.strip()]

    die("No beats.json or script.txt found")

# ----------------------------
def sentence_to_prompt(sentence: str) -> str:
    s = sentence.lower()

    if "car" in s and ("dead" in s or "died" in s):
        return (
            "3D cartoon style, night scene, man slumped dead in driver seat of car, "
            "streetlight outside, cinematic lighting, dark mood"
        )

    if "murder" in s or "killed" in s:
        return (
            "3D cartoon style, dark bedroom crime scene, bed, knife on floor, "
            "blood stain, moody lighting"
        )

    if "police" in s or "arrest" in s:
        return (
            "3D cartoon style, police officers arresting suspect at night, "
            "dramatic lighting"
        )

    return (
        "3D cartoon crime scene illustration, cinematic lighting, dark tone"
    )

# ----------------------------
def generate_image(prompt: str, out_path: Path):
    """
    Replace this with:
    - HuggingFace API
    - Local SD / Flux
    """
    log(f"IMAGE → {prompt}")
    out_path.write_text(prompt)  # placeholder

# ----------------------------
def build_frames(beats):
    FRAMES_DIR.mkdir(exist_ok=True)

    frame_idx = 0
    for beat in beats:
        prompt = sentence_to_prompt(beat["text"])
        duration = beat.get("estimated_duration", 4)
        frames = int(duration * FPS)

        img_path = FRAMES_DIR / f"scene_{frame_idx:04d}.png"
        generate_image(prompt, img_path)

        for _ in range(frames):
            (FRAMES_DIR / f"frame_{frame_idx:05d}.png").symlink_to(img_path)
            frame_idx += 1

# ----------------------------
def compose_video():
    log("Composing video…")

    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", "frames/frame_%05d.png",
        "-i", str(AUDIO_FILE),
        "-vf", f"ass={SUBS_FILE}",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-shortest",
        OUTPUT
    ], check=True)

# ----------------------------
def main():
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")
    if not SUBS_FILE.exists():
        die("subs.ass missing")

    beats = load_beats()
    log(f"{len(beats)} beats loaded")

    build_frames(beats)
    compose_video()

    log("✅ FINAL VIDEO READY")

# ----------------------------
if __name__ == "__main__":
    main()
