#!/usr/bin/env python3
"""
STRICT VIDEO BUILDER — FIXED TIMELINE ENGINE

✔ Correct transition timing
✔ No freezing visuals
✔ Exact beat durations
✔ Subtitles restored
✔ No zoom / no stretch
✔ Stable playback
"""

import json
import subprocess
import tempfile
import shutil
import sys
from pathlib import Path


WIDTH = 2160
HEIGHT = 3840
FPS = 30
TRANSITION = 0.35

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
SUB_FILE = Path("subs.ass")
OUTPUT_FILE = Path("output/shorts_4k.mp4")


# -------------------------------------------------

def log(i, m):
    print(f"{i} {m}")
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


# -------------------------------------------------

class Builder:

    def __init__(self):
        self.temp = None
        self.clips = []

    def cleanup(self):
        if self.temp:
            shutil.rmtree(self.temp, ignore_errors=True)

    # -------------------------------------------------

    def load_beats(self):
        data = json.loads(BEATS_FILE.read_text())
        return data["beats"]

    # -------------------------------------------------
    # IMAGE CLIP
    # -------------------------------------------------

    def process_image(self, beat, i):
        src = ASSET_DIR / beat["asset_file"]
        out = self.temp / f"clip_{i:03}.mp4"

        vf = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )

        cmd = [
            "ffmpeg","-y",
            "-loop","1",
            "-i",str(src),
            "-t",str(beat["duration"]),
            "-vf",vf,
            "-r",str(FPS),
            "-c:v","libx264",
            "-crf","16",
            "-preset","slow",
            "-pix_fmt","yuv420p",
            "-shortest",
            str(out)
        ]

        return out if run(cmd,f"Image {i}") else None

    # -------------------------------------------------
    # VIDEO CLIP (TRIM EXACT)
    # -------------------------------------------------

    def process_video(self, beat, i):
        src = ASSET_DIR / beat["asset_file"]
        out = self.temp / f"clip_{i:03}.mp4"

        vf = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS}"
        )

        cmd = [
            "ffmpeg","-y",
            "-i",str(src),
            "-t",str(beat["duration"]),
            "-vf",vf,
            "-c:v","libx264",
            "-crf","16",
            "-preset","slow",
            "-pix_fmt","yuv420p",
            "-an",
            str(out)
        ]

        return out if run(cmd,f"Video {i}") else None

    # -------------------------------------------------

    def create_clips(self, beats):
        log("🎬","Creating clips")

        for i, beat in enumerate(beats):
            if beat["type"] == "image":
                clip = self.process_image(beat, i)
            else:
                clip = self.process_video(beat, i)

            if not clip:
                return False

            self.clips.append(clip)

        return True

    # -------------------------------------------------
    # CORRECT TIMELINE CONCAT
    # -------------------------------------------------

    def concat_with_transitions(self, beats):
        log("🎞️","Building timeline")

        inputs = []
        for c in self.clips:
            inputs.extend(["-i",str(c)])

        filters = []
        current_time = 0
        last = "[0:v]"

        for i in range(1,len(self.clips)):
            duration_prev = beats[i-1]["duration"]
            current_time += duration_prev - TRANSITION

            label = f"[v{i}]"
            filters.append(
                f"{last}[{i}:v]xfade=transition=fade:"
                f"duration={TRANSITION}:offset={current_time}{label}"
            )
            last = label

        merged = self.temp/"merged.mp4"

        cmd = [
            "ffmpeg","-y",
            *inputs,
            "-filter_complex",";".join(filters),
            "-map",last,
            "-c:v","libx264",
            "-crf","16",
            "-preset","slow",
            "-pix_fmt","yuv420p",
            str(merged)
        ]

        return merged if run(cmd,"Concatenating") else None

    # -------------------------------------------------
    # FINAL RENDER + SUBTITLES
    # -------------------------------------------------

    def final_render(self, merged):
        OUTPUT_FILE.parent.mkdir(exist_ok=True)

        vf = f"scale={WIDTH}:{HEIGHT},setsar=1"

        if SUB_FILE.exists():
            vf += f",ass={SUB_FILE}"

        cmd = [
            "ffmpeg","-y",
            "-i",str(merged),
            "-i",str(AUDIO_FILE),
            "-vf",vf,
            "-map","0:v",
            "-map","1:a",
            "-c:v","libx264",
            "-crf","16",
            "-preset","slow",
            "-c:a","aac",
            "-b:a","320k",
            "-shortest",
            str(OUTPUT_FILE)
        ]

        return run(cmd,"Final render")

    # -------------------------------------------------

    def build(self):
        self.temp = Path(tempfile.mkdtemp())

        try:
            beats = self.load_beats()

            if not self.create_clips(beats):
                return False

            merged = self.concat_with_transitions(beats)
            if not merged:
                return False

            if not self.final_render(merged):
                return False

            log("✅","Build complete")
            return True

        finally:
            self.cleanup()


# -------------------------------------------------

if __name__ == "__main__":
    b = Builder()
    sys.exit(0 if b.build() else 1)
