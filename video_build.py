#!/usr/bin/env python3
"""
PRO YOUTUBE SHORTS BUILDER — STABLE PRODUCTION EDITION

Fixes:
- No clip freezing
- No image jitter
- No asset quality loss
- Proper constant frame rate
- Safe concat pipeline
- Stable exit codes
- Professional zoom clarity
"""

import json
import subprocess
import tempfile
import shutil
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional


# =====================================================
# CONFIG
# =====================================================

class Config:
    OUTPUT_QUALITY = "4K"

    QUALITY_PRESETS = {
        "4K": (2160, 3840),
        "2K": (1440, 2560),
        "1080P": (1080, 1920)
    }

    WIDTH, HEIGHT = QUALITY_PRESETS[OUTPUT_QUALITY]

    FPS = 30
    CRF_INTERMEDIATE = 16
    CRF_FINAL = 15

    MAX_BITRATE = "25M"
    BUFFER_SIZE = "50M"

    BEATS_FILE = Path("beats.json")
    ASSET_DIR = Path("asset")
    AUDIO_FILE = Path("final_audio.wav")
    SUBS_FILE = Path("subs.ass")

    OUTPUT_DIR = Path("output")
    OUTPUT_FILE = OUTPUT_DIR / "shorts_4k.mp4"

    DEFAULT_DURATION = 2.8


# =====================================================
# UTILS
# =====================================================

def log(icon, msg):
    print(f"{icon} {msg}")
    sys.stdout.flush()


def run(cmd, desc="Processing"):
    log("▶", desc)
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        log("❌", desc + " failed")
        return False


# =====================================================
# EFFECTS
# =====================================================

class Effects:

    @staticmethod
    def zoom(style, duration, fps, w, h):
        frames = int(duration * fps)

        presets = {
            "slow_zoom":
                f"zoompan=z='min(1.08,zoom+0.0005)':d={frames}:s={w}x{h}:fps={fps}",

            "punch_in":
                f"zoompan=z='min(1.15,1+0.15*in/{frames})':d={frames}:s={w}x{h}:fps={fps}",

            "zoom_out":
                f"zoompan=z='max(1,1.1-0.1*in/{frames})':d={frames}:s={w}x{h}:fps={fps}",

            "static":
                f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
        }

        return presets.get(style, presets["slow_zoom"])

    @staticmethod
    def base_quality():
        return "unsharp=5:5:0.7:3:3:0.3,hqdn3d=1:1:4:4"

    @staticmethod
    def color():
        return "eq=saturation=1.1:contrast=1.08"


# =====================================================
# BUILDER
# =====================================================

class ShortsBuilder:

    def __init__(self):
        self.config = Config()
        self.temp = None
        self.clips = []

    def cleanup(self):
        if self.temp and self.temp.exists():
            shutil.rmtree(self.temp, ignore_errors=True)

    # ------------------------

    def validate_inputs(self):
        required = [
            self.config.BEATS_FILE,
            self.config.AUDIO_FILE,
            self.config.ASSET_DIR
        ]

        for r in required:
            if not r.exists():
                log("❌", f"Missing {r}")
                return False

        return True

    # ------------------------

    def load_beats(self):
        data = json.loads(self.config.BEATS_FILE.read_text())
        return data.get("beats", [])

    # ------------------------
    # IMAGE → VIDEO (CRISP ZOOM)
    # ------------------------

    def process_image(self, beat, i, total):
        src = self.config.ASSET_DIR / beat["asset_file"]
        out = self.temp / f"clip_{i:03}.mp4"

        duration = beat.get("duration", self.config.DEFAULT_DURATION)

        vf = ",".join([
            Effects.zoom(
                beat.get("zoom_style", "slow_zoom"),
                duration,
                self.config.FPS,
                self.config.WIDTH,
                self.config.HEIGHT
            ),
            Effects.color(),
            Effects.base_quality(),
            "setsar=1"
        ])

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(src),
            "-vf", vf,
            "-t", str(duration),
            "-r", str(self.config.FPS),
            "-vsync", "cfr",
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", str(self.config.CRF_INTERMEDIATE),
            "-pix_fmt", "yuv420p",
            str(out)
        ]

        return out if run(cmd, f"Image {i+1}/{total}") else None

    # ------------------------
    # VIDEO CLIP
    # ------------------------

    def process_video(self, beat, i, total):
        src = self.config.ASSET_DIR / beat["asset_file"]
        out = self.temp / f"clip_{i:03}.mp4"

        duration = beat.get("duration", self.config.DEFAULT_DURATION)
        trim_start = beat.get("trim_start", 0)

        vf = ",".join([
            f"scale={self.config.WIDTH}:{self.config.HEIGHT}:force_original_aspect_ratio=increase",
            f"crop={self.config.WIDTH}:{self.config.HEIGHT}",
            Effects.color(),
            Effects.base_quality(),
            "fps=30",
            "setsar=1"
        ])

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(trim_start),
            "-i", str(src),
            "-t", str(duration),
            "-vf", vf,
            "-vsync", "cfr",
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", str(self.config.CRF_INTERMEDIATE),
            "-pix_fmt", "yuv420p",
            "-an",
            str(out)
        ]

        return out if run(cmd, f"Video {i+1}/{total}") else None

    # ------------------------

    def create_clips(self, beats):
        log("🎬", "Building clips")

        for i, beat in enumerate(beats):
            if beat.get("type") == "image":
                clip = self.process_image(beat, i, len(beats))
            else:
                clip = self.process_video(beat, i, len(beats))

            if not clip:
                return False

            self.clips.append(clip)

        return True

    # ------------------------
    # SAFE CONCAT (NO FREEZE)
    # ------------------------

    def concat(self):
        log("🔗", "Concatenating")

        list_file = self.temp / "list.txt"
        list_file.write_text("\n".join(f"file '{c}'" for c in self.clips))

        merged = self.temp / "merged.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264",  # re-encode to prevent freeze
            "-preset", "slow",
            "-crf", "16",
            "-pix_fmt", "yuv420p",
            str(merged)
        ]

        return merged if run(cmd, "Merging clips") else None

    # ------------------------
    # FINAL RENDER
    # ------------------------

    def final_render(self, merged):
        self.config.OUTPUT_DIR.mkdir(exist_ok=True)

        vf = f"scale={self.config.WIDTH}:{self.config.HEIGHT},setsar=1"

        if self.config.SUBS_FILE.exists():
            subs = str(self.config.SUBS_FILE.absolute()).replace("\\", "/").replace(":", "\\:")
            vf += f",ass={subs}"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(merged),
            "-i", str(self.config.AUDIO_FILE),
            "-vf", vf,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", str(self.config.CRF_FINAL),
            "-maxrate", self.config.MAX_BITRATE,
            "-bufsize", self.config.BUFFER_SIZE,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "320k",
            "-shortest",
            "-movflags", "+faststart",
            str(self.config.OUTPUT_FILE)
        ]

        return run(cmd, "Final render")

    # ------------------------

    def build(self):
        print("\n=== PRO SHORTS BUILDER ===\n")

        self.temp = Path(tempfile.mkdtemp())

        try:
            if not self.validate_inputs():
                return False

            beats = self.load_beats()
            if not beats:
                return False

            if not self.create_clips(beats):
                return False

            merged = self.concat()
            if not merged:
                return False

            if not self.final_render(merged):
                return False

            log("✅", "Build complete")
            log("📁", str(self.config.OUTPUT_FILE))

            return True

        finally:
            self.cleanup()


# =====================================================
# ENTRY
# =====================================================

def main():
    builder = ShortsBuilder()
    sys.exit(0 if builder.build() else 1)


if __name__ == "__main__":
    main()
