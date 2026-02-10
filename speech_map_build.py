#!/usr/bin/env python3
"""
Speech Map Builder — SOURCE OF TRUTH

Generates speech_map.json from final_audio.wav
One entry per script line
STRICT format expected by video_build.py
"""

import json
import subprocess
from pathlib import Path

SCRIPT_FILE = Path("script.txt")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT_FILE = Path("speech_map.json")

WORDS_PER_SECOND = 3.0  # conservative, stable


def die(msg):
    raise RuntimeError(msg)


def get_audio_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())


def main():
    if not SCRIPT_FILE.exists():
        die("script.txt missing")

    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    lines = [l.strip() for l in SCRIPT_FILE.read_text().splitlines() if l.strip()]
    if not lines:
        die("script.txt empty")

    audio_duration = get_audio_duration(AUDIO_FILE)

    # Estimate durations per line by word count
    word_counts = [len(l.split()) for l in lines]
    total_words = sum(word_counts)

    if total_words == 0:
        die("No words detected")

    timings = []
    cursor = 0.0

    for idx, wc in enumerate(word_counts, start=1):
        dur = (wc / total_words) * audio_duration
        start = cursor
        end = start + dur

        timings.append({
            "line": idx,
            "start": round(start, 3),
            "end": round(end, 3),
        })

        cursor = end

    # Hard lock last end to audio duration
    timings[-1]["end"] = round(audio_duration, 3)

    OUTPUT_FILE.write_text(json.dumps(timings, indent=2))
    print(f"✅ speech_map.json written ({len(timings)} lines)")


if __name__ == "__main__":
    main()
