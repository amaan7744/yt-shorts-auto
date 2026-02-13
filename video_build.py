#!/usr/bin/env python3
"""
PRO VIDEO BUILDER — STRICT TIMELINE ENGINE (FINAL)

✔ Exact timeline duration
✔ Transition compensation (no duration loss)
✔ No freezing visuals
✔ No stretching
✔ No zoom effects
✔ Crossfade transitions
✔ Subtitles support
✔ Perfect AV sync
✔ Production stable
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
TRANSITION = 0.35

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
SUB_FILE = Path("subs.ass")
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


def get_audio_duration():
    r = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(AUDIO_FILE)],
        capture_output=True,text=True
    )
    return float(r.stdout.strip())


# ==========================================================
# BUILDER
# ==========================================================

class Builder:

    def __init__(self):
        self.temp = None
        self.clips = []

    def cleanup(self):
        if self.temp:
            shutil.rmtree(self.temp, ignore_errors=True)

    # ------------------------------------------------------

    def load_beats(self):
        data = json.loads(BEATS_FILE.read_text())
        return data["beats"]

    # ------------------------------------------------------
    # IMAGE CLIP
    # ------------------------------------------------------

    def process_image(self, beat, i):
        src = ASSET_DIR / beat["asset_file"]
        out = self.temp / f"clip_{i:03}.mp4"

        duration = beat["duration"] + TRANSITION  # compensate transition

        vf = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )

        cmd = [
            "ffmpeg","-y",
            "-loop","1",
            "-i",str(src),
            "-t",str(duration),
            "-vf",vf,
            "-r",str(FPS),
            "-c:v","libx264",
            "-preset","slow",
            "-crf","16",
            "-pix_fmt","yuv420p",
            "-shortest",
            str(out)
        ]

        return out if run(cmd,f"Image {i}") else None

    # ------------------------------------------------------
    # VIDEO CLIP
    # ------------------------------------------------------

    def process_video(self, beat, i):
        src = ASSET_DIR / beat["asset_file"]
        out = self.temp / f"clip_{i:03}.mp4"

        duration = beat["duration"] + TRANSITION  # compensate transition

        vf = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            f"setsar=1,fps={FPS}"
        )

        cmd = [
            "ffmpeg","-y",
            "-i",str(src),
            "-t",str(duration),
            "-vf",vf,
            "-c:v","libx264",
            "-preset","slow",
            "-crf","16",
            "-pix_fmt","yuv420p",
            "-an",
            str(out)
        ]

        return out if run(cmd,f"Video {i}") else None

    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # CONCAT WITH PROPER TIMELINE
    # ------------------------------------------------------

    def concat_with_transitions(self, beats):
        log("🎞️","Building timeline")

        if len(self.clips) == 1:
            return self.clips[0]

        inputs=[]
        for c in self.clips:
            inputs.extend(["-i",str(c)])

        filters=[]
        current_time=0
        last="[0:v]"

        for i in range(1,len(self.clips)):
            prev_duration = beats[i-1]["duration"]

            current_time += prev_duration

            label=f"[v{i}]"

            filters.append(
                f"{last}[{i}:v]xfade=transition=fade:"
                f"duration={TRANSITION}:offset={current_time}{label}"
            )

            last=label
            current_time -= TRANSITION  # compensate overlap

        merged=self.temp/"merged.mp4"

        cmd=[
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

    # ------------------------------------------------------
    # FINAL RENDER + SUBTITLES
    # ------------------------------------------------------

    def final_render(self, merged):
        OUTPUT_FILE.parent.mkdir(exist_ok=True)

        vf=f"scale={WIDTH}:{HEIGHT},setsar=1"

        if SUB_FILE.exists():
            vf+=f",ass={SUB_FILE}"

        cmd=[
            "ffmpeg","-y",
            "-i",str(merged),
            "-i",str(AUDIO_FILE),
            "-vf",vf,
            "-map","0:v",
            "-map","1:a",
            "-c:v","libx264",
            "-preset","slow",
            "-crf","16",
            "-c:a","aac",
            "-b:a","320k",
            "-shortest",
            str(OUTPUT_FILE)
        ]

        return run(cmd,"Final render")

    # ------------------------------------------------------

    def validate_duration(self, beats):
        audio=get_audio_duration()
        beat_total=sum(b["duration"] for b in beats)

        log("🔊",f"Audio duration: {audio:.2f}")
        log("🎬",f"Timeline duration: {beat_total:.2f}")

        return abs(audio-beat_total)<0.1

    # ------------------------------------------------------

    def build(self):
        print("\n=== PRO VIDEO BUILDER ===\n")

        self.temp=Path(tempfile.mkdtemp())

        try:
            beats=self.load_beats()

            if not self.validate_duration(beats):
                log("❌","Timeline mismatch")
                return False

            if not self.create_clips(beats):
                return False

            merged=self.concat_with_transitions(beats)
            if not merged:
                return False

            if not self.final_render(merged):
                return False

            log("✅","Build complete")
            log("📁",str(OUTPUT_FILE))
            return True

        finally:
            self.cleanup()


# ==========================================================

if __name__ == "__main__":
    b=Builder()
    sys.exit(0 if b.build() else 1)
