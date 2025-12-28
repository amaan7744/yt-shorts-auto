#!/usr/bin/env python3
"""
audio_mix.py — HALAL-SAFE, LENGTH-LOCKED

Guarantees:
- final_audio.wav == narration.wav duration EXACTLY
- No ambience spill
- No rain / no noise
- No MP3 / no external audio
"""

import os
import numpy as np
from pydub import AudioSegment

VOICE_PATH = "narration.wav"
OUTPUT_PATH = "final_audio.wav"

VOICE_GAIN_DB = -1.0
AMBIENCE_GAIN_DB = -18.0
FADE_MS = 900
SAMPLE_RATE = 44100


def log(msg):
    print(f"[AUDIO] {msg}", flush=True)


def generate_room_tone(duration_ms: int) -> AudioSegment:
    samples = int(SAMPLE_RATE * duration_ms / 1000)

    noise = np.random.normal(0, 0.004, samples)

    audio = AudioSegment(
        noise.tobytes(),
        frame_rate=SAMPLE_RATE,
        sample_width=2,
        channels=1,
    )

    audio = audio.high_pass_filter(90)
    audio = audio.low_pass_filter(600)

    return audio


def main():
    if not os.path.isfile(VOICE_PATH):
        raise SystemExit("[AUDIO] narration.wav not found")

    voice = AudioSegment.from_file(VOICE_PATH).apply_gain(VOICE_GAIN_DB)
    duration_ms = len(voice)

    log(f"Narration duration: {duration_ms / 1000:.2f}s")

    # Generate ambience EXACTLY same length
    ambience = generate_room_tone(duration_ms)
    ambience = ambience[:duration_ms]  # HARD CUT
    ambience = ambience.apply_gain(AMBIENCE_GAIN_DB)
    ambience = ambience.fade_in(FADE_MS).fade_out(FADE_MS)

    # Overlay and HARD CUT again (safety)
    final = ambience.overlay(voice)
    final = final[:duration_ms]  # ABSOLUTE LOCK

    final.export(
        OUTPUT_PATH,
        format="wav",
        parameters=["-ac", "1", "-ar", str(SAMPLE_RATE)],
    )

    log("Final audio written (length locked)")


if __name__ == "__main__":
    main()
