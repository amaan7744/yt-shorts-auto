#!/usr/bin/env python3
import numpy as np
from pydub import AudioSegment
import os

VOICE_PATH = "narration.wav"
OUTPUT = "final_audio.wav"

VOICE_GAIN = -1
AMBIENCE_GAIN = -16   # very subtle
FADE_MS = 1000        # smooth, calm

def log(msg):
    print(f"[AUDIO] {msg}", flush=True)

def generate_halal_ambience(duration_ms):
    """
    Halal-safe ambience:
    - No music
    - No rhythm
    - No human sound
    - No sharp noise
    Just soft air / room tone.
    """
    sample_rate = 44100
    samples = int(sample_rate * duration_ms / 1000)

    # Very soft noise
    noise = np.random.normal(0, 0.008, samples)

    audio = AudioSegment(
        noise.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=1
    )

    # Strong low-pass to remove harshness
    audio = audio.low_pass_filter(600)
    audio = audio.high_pass_filter(80)

    return audio

def main():
    if not os.path.isfile(VOICE_PATH):
        raise SystemExit("Voice file missing")

    voice = AudioSegment.from_file(VOICE_PATH).apply_gain(VOICE_GAIN)

    ambience = generate_halal_ambience(len(voice))
    ambience = ambience.apply_gain(AMBIENCE_GAIN)
    ambience = ambience.fade_in(FADE_MS).fade_out(FADE_MS)

    final = ambience.overlay(voice)
    final.export(OUTPUT, format="wav")

    log("Halal-safe final audio written")

if __name__ == "__main__":
    main()
