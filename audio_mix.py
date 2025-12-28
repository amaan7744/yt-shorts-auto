#!/usr/bin/env python3
import os
import glob
from pydub import AudioSegment

VOICE_PATH = "narration.wav"
AMBIENCE_DIR = "ambience"
OUTPUT = "final_audio.wav"

# TUNING (important)
AMBIENCE_DB = -12     # audible but subtle
VOICE_DB = -1         # slight headroom
FADE_MS = 800         # smooth start/end

def find_ambience():
    if not os.path.isdir(AMBIENCE_DIR):
        print("[AUDIO] ambience/ folder not found")
        return []

    files = []
    for ext in ("*.wav", "*.mp3"):
        files.extend(glob.glob(os.path.join(AMBIENCE_DIR, ext)))

    return files


def main():
    if not os.path.isfile(VOICE_PATH):
        raise SystemExit(f"[AUDIO] Voice file not found: {VOICE_PATH}")

    # Load narration
    voice = AudioSegment.from_file(VOICE_PATH).apply_gain(VOICE_DB)

    ambience_files = find_ambience()
    if not ambience_files:
        print("[AUDIO] No ambience found, exporting voice only")
        voice.export(OUTPUT, format="wav")
        return

    # Pick ONE ambience track randomly
    amb_path = ambience_files[0]
    ambience = AudioSegment.from_file(amb_path).apply_gain(AMBIENCE_DB)

    print(f"[AUDIO] Using ambience: {amb_path}")

    # Loop ambience to match voice length
    loops = int(len(voice) / len(ambience)) + 1
    ambience = (ambience * loops)[:len(voice)]

    # Fade ambience (critical for perception)
    ambience = ambience.fade_in(FADE_MS).fade_out(FADE_MS)

    # Duck voice slightly over ambience
    final = ambience.overlay(voice)

    final.export(OUTPUT, format="wav")
    print("[AUDIO] Final audio written:", OUTPUT)


if __name__ == "__main__":
    main()
