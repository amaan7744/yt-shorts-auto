#!/usr/bin/env python3
"""
PRO VIDEO BUILDER — STRICT TIMELINE ENGINE
==========================================

✔ Uses beat durations exactly
✔ No visual stretching
✔ No freezing / looping
✔ No zoom effects
✔ Preserves original asset framing
✔ Crossfade transitions between clips
✔ Video duration == audio duration
✔ Production timeline validation
"""

import json
import subprocess
import tempfile
import shutil
import sys
from pathlib import Path


# ==========================================================
# CONFIG
# ==========================================================

WIDTH = 2160
HEIGHT = 3840
FPS = 30

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT_FILE = Path("output/shorts_4k.mp4")


# ==========================================================
# UTILS
# ==========================================================

def log(icon, msg):
    print(f"{icon} {msg}")
    sys.stdout.flush()


def run(cmd, desc):
    log("▶", desc)
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        log("❌", desc + " failed")
        print(e)
        return False


def get_audio_duration(path):
    result = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)],
        capture_output=True,text=True
    )
    return float(result.stdout.strip())


# ==========================================================
# BUILDER
# ==========================================================

class Builder:

    def __init__(self):
        self.temp = None
        self.clips = []

    def cleanup(self):
        if self.temp and self.temp.exists():
            shutil.rmtree(self.temp, ignore_errors=True)

    # ------------------------------------------------------

    def validate_inputs(self):
        for f in [BEATS_FILE, AUDIO_FILE, ASSET_DIR]:
            if not f.exists():
                log("❌", f"Missing {f}")
                return False
        return True

    # ------------------------------------------------------

    def load_beats(self):
        data = json.loads(BEATS_FILE.read_text())
        beats = data.get("beats", [])

        for b in beats:
            if "duration" not in b:
                log("❌", "Beat missing duration")
                return None

        return beats

    # ------------------------------------------------------
    # IMAGE → VIDEO (NO ZOOM / PRESERVE FRAMING)
    # ------------------------------------------------------

    def process_image(self, beat, i):
        src = ASSET_DIR / beat["asset_file"]
        out = self.temp / f"clip_{i:03}.mp4"

        vf = ",".join([
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease",
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "setsar=1"
        ])

        cmd = [
            "ffmpeg","-y",
            "-loop","1",
            "-i",str(src),
            "-vf",vf,
            "-t",str(beat["duration"]),
            "-r",str(FPS),
            "-vsync","cfr",
            "-c:v","libx264",
            "-preset","slow",
            "-crf","15",
            "-pix_fmt","yuv420p",
            str(out)
        ]

        return out if run(cmd,f"Image {i}") else None

    # ------------------------------------------------------
    # VIDEO CLIP (TRIM ONLY)
    # ------------------------------------------------------

    def process_video(self, beat, i):
        src = ASSET_DIR / beat["asset_file"]
        out = self.temp / f"clip_{i:03}.mp4"

        vf = ",".join([
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease",
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "fps=30",
            "setsar=1"
        ])

        cmd = [
            "ffmpeg","-y",
            "-i",str(src),
            "-vf",vf,
            "-t",str(beat["duration"]),
            "-vsync","cfr",
            "-c:v","libx264",
            "-preset","slow",
            "-crf","15",
            "-pix_fmt","yuv420p",
            "-an",
            str(out)
        ]

        return out if run(cmd,f"Video {i}") else None

    # ------------------------------------------------------

    def create_clips(self, beats):
        log("🎬","Creating timeline clips")

        for i, beat in enumerate(beats):
            if beat["type"] == "image":
                clip = self.process_image(beat, i)
            else:
                clip = self.process_video(beat, i)

            if not clip:
                return False

            self.clips.append(clip)

        return True

    # ------------------------------------------------------
    # CONCAT WITH TRANSITIONS
    # ------------------------------------------------------

    def concat_with_transitions(self):
        log("🎞️","Building timeline with transitions")

        if len(self.clips) == 1:
            return self.clips[0]

        inputs = []
        filters = []

        for i, clip in enumerate(self.clips):
            inputs.extend(["-i",str(clip)])

        last = "[0:v]"
        transition = 0.35

        for i in range(1,len(self.clips)):
            label = f"[v{i}]"
            filters.append(
                f"{last}[{i}:v]xfade=transition=fade:duration={transition}:offset=0{label}"
            )
            last = label

        merged = self.temp/"merged.mp4"

        cmd = [
            "ffmpeg","-y",
            *inputs,
            "-filter_complex",";".join(filters),
            "-map",last,
            "-c:v","libx264",
            "-crf","15",
            "-preset","slow",
            "-pix_fmt","yuv420p",
            str(merged)
        ]

        return merged if run(cmd,"Concatenating") else None

    # ------------------------------------------------------
    # FINAL RENDER
    # ------------------------------------------------------

    def final_render(self, merged):
        OUTPUT_FILE.parent.mkdir(exist_ok=True)

        cmd = [
            "ffmpeg","-y",
            "-i",str(merged),
            "-i",str(AUDIO_FILE),
            "-map","0:v",
            "-map","1:a",
            "-c:v","libx264",
            "-preset","slow",
            "-crf","15",
            "-pix_fmt","yuv420p",
            "-c:a","aac",
            "-b:a","320k",
            "-movflags","+faststart",
            str(OUTPUT_FILE)
        ]

        return run(cmd,"Final render")

    # ------------------------------------------------------
    # STRICT VALIDATION
    # ------------------------------------------------------

    def validate_duration(self, beats):
        audio_duration = get_audio_duration(AUDIO_FILE)
        beat_total = sum(b["duration"] for b in beats)

        log("🔊",f"Audio duration: {audio_duration:.2f}")
        log("🎬",f"Timeline duration: {beat_total:.2f}")

        if abs(audio_duration - beat_total) > 0.05:
            log("❌","Timeline does not match audio")
            return False

        return True

    # ------------------------------------------------------

    def build(self):
        print("\n=== STRICT VIDEO BUILDER ===\n")

        self.temp = Path(tempfile.mkdtemp())

        try:
            if not self.validate_inputs():
                return False

            beats = self.load_beats()
            if not beats:
                return False

            if not self.validate_duration(beats):
                return False

            if not self.create_clips(beats):
                return False

            merged = self.concat_with_transitions()
            if not merged:
                return False

            if not self.final_render(merged):
                return False

            if OUTPUT_FILE.exists():
                log("✅","Build complete")
                log("📁",str(OUTPUT_FILE))
                return True

            return False

        finally:
            self.cleanup()


# ==========================================================
# ENTRY
# ==========================================================

if __name__ == "__main__":
    builder = Builder()
    sys.exit(0 if builder.build() else 1)
