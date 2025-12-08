#!/usr/bin/env python
"""
audio_mix.py

Usage:
    python audio_mix.py tts.wav final_audio.wav

Behavior:
- Loads narration WAV (first arg, default: tts.wav).
- Chooses ONE ambience track from ./ambience/:
    - gentle-rain-07-437321.mp3
    - night-street-rain-263233.mp3
    - soft-wind-318856.mp3
- Loops ambience to match narration length.
- Attenuates ambience to sit quietly under the voice (about -15 dB).
- No fade in/out (flat bed the whole time).
- Exports mixed file as WAV (second arg, default: final_audio.wav).
"""

import os
import sys
import random
from typing import List

from pydub import AudioSegment, effects

AMBIENCE_DIR = "ambience"

# Relative level of ambience vs narration
AMBIENCE_ATTENUATION_DB = 15  # lower = quieter ambience


def log(msg: str) -> None:
    print(f"[MIX] {msg}", flush=True)


def pick_ambience_file() -> str:
    if not os.path.isdir(AMBIENCE_DIR):
        raise SystemExit(f"[MIX] Ambience directory not found: {AMBIENCE_DIR}")

    candidates: List[str] = []
    for name in os.listdir(AMBIENCE_DIR):
        lower = name.lower()
        if lower.endswith(".mp3") or lower.endswith(".wav"):
            candidates.append(os.path.join(AMBIENCE_DIR, name))

    if not candidates:
        raise SystemExit(f"[MIX] No ambience audio files found in {AMBIENCE_DIR}")

    # For crime/night stories, we slightly bias to "night-street-rain" if present
    street = [p for p in candidates if "night-street" in os.path.basename(p)]
    if street:
        chosen = random.choice(street)
    else:
        chosen = random.choice(candidates)

    log(f"Using ambience: {chosen}")
    return chosen


def main() -> None:
    # CLI args
    in_voice = sys.argv[1] if len(sys.argv) > 1 else "tts.wav"
    out_mix = sys.argv[2] if len(sys.argv) > 2 else "final_audio.wav"

    if not os.path.isfile(in_voice):
        raise SystemExit(f"[MIX] Narration file not found: {in_voice}")

    # Load narration
    voice = AudioSegment.from_file(in_voice)
    voice = voice.set_channels(1).set_frame_rate(44100)

    # Load ambience
    amb_path = pick_ambience_file()
    amb = AudioSegment.from_file(amb_path)
    amb = amb.set_channels(1).set_frame_rate(44100)

    # Loop ambience to cover full narration duration
    target_ms = len(voice)
    if len(amb) == 0:
        raise SystemExit("[MIX] Ambience file is empty or unreadable")

    loops_needed = (target_ms // len(amb)) + 1
    amb_looped = amb * loops_needed
    amb_looped = amb_looped[:target_ms]

    # Lower ambience level under narration
    amb_looped = amb_looped - AMBIENCE_ATTENUATION_DB

    # Optional: light normalization of voice to keep level consistent
    voice_norm = effects.normalize(voice)

    # Overlay ambience under voice
    mixed = voice_norm.overlay(amb_looped)

    # Export
    tmp_out = out_mix + ".tmp"
    os.makedirs(os.path.dirname(out_mix) or ".", exist_ok=True)
    mixed.export(tmp_out, format="wav")
    os.replace(tmp_out, out_mix)

    log(f"Mixed audio written to {out_mix} ({len(mixed) / 1000.0:.1f} s)")


if __name__ == "__main__":
    main()
