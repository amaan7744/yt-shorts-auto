#!/usr/bin/env python3
"""
Speech Map Builder
------------------
Creates speech_map.json mapping script lines → audio time.
NO ASR. NO Whisper. Deterministic & CI-safe.
"""

import json
import subprocess
from pathlib import Path

SCRIPT_FILE = Path("script.txt")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT = Path("speech_map.json")

WORDS_PER_SECOND = 3.0

def get_audio_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return float(r.stdout.strip())

def main():
    if not SCRIPT_FILE.exists():
        raise RuntimeError("script.txt missing")
    if not AUDIO_FILE.exists():
        raise RuntimeError("final_audio.wav missing")

    lines = [l.strip() for l in SCRIPT_FILE.read_text().splitlines() if l.strip()]
    audio_duration = get_audio_duration(AUDIO_FILE)

    total_words = sum(len(l.split()) for l in lines)
    seconds_per_word = audio_duration / total_words

    speech_map = []
    current_time = 0.0

    for i, line in enumerate(lines, start=1):
        words = len(line.split())
        duration = words * seconds_per_word

        entry = {
            "line": i,
            "text": line,
            "start": round(current_time, 3),
            "end": round(current_time + duration, 3),
            "duration": round(duration, 3)
        }

        speech_map.append(entry)
        current_time += duration

    OUTPUT.write_text(json.dumps({
        "audio_duration": round(audio_duration, 3),
        "lines": speech_map
    }, indent=2))

    print("✅ speech_map.json generated")
    print(f"⏱️ Audio duration: {audio_duration:.2f}s")

if __name__ == "__main__":
    main()
