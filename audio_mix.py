#!/usr/bin/env python
"""
audio_mix.py

Usage:
    python audio_mix.py tts.wav final_audio.wav

Behavior:
- Loads narration WAV (first arg, default: tts.wav).
- Looks for ambience files in ./ambience/:
    - gentle-rain-07-437321.mp3
    - night-street-rain-263233.mp3
    - soft-wind-318856.mp3
  (or any .mp3 / .wav in that folder)
- Tries to load ambience files in a sensible order:
    1) ones with "night" or "street" in filename
    2) then the rest
- If one fails to load (corrupt / ffmpeg error), it logs and tries the next.
- If ALL fail, it uses narration only (no ambience, no crash).
- Loops ambience to match narration length.
- Attenuates ambience by ~15 dB so it stays under the voice.
- No fade in/out (flat bed).
"""

import os
import sys
from typing import List, Tuple

from pydub import AudioSegment, effects

AMBIENCE_DIR = "ambience"
AMBIENCE_ATTENUATION_DB = 15  # lower = quieter ambience


def log(msg: str) -> None:
    print(f"[MIX] {msg}", flush=True)


def find_ambience_candidates() -> List[str]:
    if not os.path.isdir(AMBIENCE_DIR):
        log(f"Ambience directory not found: {AMBIENCE_DIR}")
        return []

    files: List[str] = []
    for name in os.listdir(AMBIENCE_DIR):
        lower = name.lower()
        if lower.endswith(".mp3") or lower.endswith(".wav"):
            files.append(os.path.join(AMBIENCE_DIR, name))

    if not files:
        log(f"No ambience files found in {AMBIENCE_DIR}")
        return []

    # Prioritize "night" / "street" themed audio for crime vibes
    def priority(path: str) -> Tuple[int, str]:
        low = os.path.basename(path).lower()
        score = 2
        if "night" in low or "street" in low:
            score = 0
        elif "rain" in low:
            score = 1
        return (score, low)

    files.sort(key=priority)
    return files


def load_first_valid_ambience() -> AudioSegment | None:
    candidates = find_ambience_candidates()
    if not candidates:
        return None

    for path in candidates:
        try:
            log(f"Trying ambience: {path}")
            amb = AudioSegment.from_file(path)
            amb = amb.set_channels(1).set_frame_rate(44100)
            log(f"Loaded ambience OK: {path}")
            return amb
        except Exception as e:
            log(f"Failed to load ambience {path}: {e}")

    log("No valid ambience files could be loaded. Will use voice only.")
    return None


def main() -> None:
    in_voice = sys.argv[1] if len(sys.argv) > 1 else "tts.wav"
    out_mix = sys.argv[2] if len(sys.argv) > 2 else "final_audio.wav"

    if not os.path.isfile(in_voice):
        raise SystemExit(f"[MIX] Narration file not found: {in_voice}")

    # Load narration and normalize a bit
    voice = AudioSegment.from_file(in_voice)
    voice = voice.set_channels(1).set_frame_rate(44100)
    voice_norm = effects.normalize(voice)

    # Try to load ambience
    amb = load_first_valid_ambience()

    if amb is None:
        # No ambience could be loaded → just save normalized voice
        log("Exporting narration only (no ambience).")
        tmp_out = out_mix + ".tmp"
        os.makedirs(os.path.dirname(out_mix) or ".", exist_ok=True)
        voice_norm.export(tmp_out, format="wav")
        os.replace(tmp_out, out_mix)
        log(f"Written {out_mix} (voice only, {len(voice_norm) / 1000.0:.1f}s)")
        return

    # Loop ambience to match narration duration
    target_ms = len(voice_norm)
    if len(amb) == 0:
        log("Ambience file has zero length; exporting voice only.")
        tmp_out = out_mix + ".tmp"
        os.makedirs(os.path.dirname(out_mix) or ".", exist_ok=True)
        voice_norm.export(tmp_out, format="wav")
        os.replace(tmp_out, out_mix)
        return

    loops_needed = (target_ms // len(amb)) + 1
    amb_looped = amb * loops_needed
    amb_looped = amb_looped[:target_ms]

    # Attenuate ambience under voice
    amb_looped = amb_looped - AMBIENCE_ATTENUATION_DB

    # Overlay ambience under normalized voice
    mixed = voice_norm.overlay(amb_looped)

    # Export atomic
    tmp_out = out_mix + ".tmp"
    os.makedirs(os.path.dirname(out_mix) or ".", exist_ok=True)
    mixed.export(tmp_out, format="wav")
    os.replace(tmp_out, out_mix)

    log(f"Mixed audio written to {out_mix} ({len(mixed) / 1000.0:.1f} s)")


if __name__ == "__main__":
    main()
