#!/usr/bin/env python3
import os
import glob
from pydub import AudioSegment

VOICE_PATH = "narration.wav"
AMBIENCE_DIR = "ambience"
CACHE_DIR = "ambience_wav"
OUTPUT = "final_audio.wav"

AMBIENCE_DB = -12
VOICE_DB = -1
FADE_MS = 800

os.makedirs(CACHE_DIR, exist_ok=True)

def convert_to_wav(path):
    base = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(CACHE_DIR, base + ".wav")

    if os.path.exists(out):
        return out

    print(f"[AUDIO] Converting to WAV: {path}")
    audio = AudioSegment.from_file(path)
    audio = audio.set_frame_rate(44100).set_channels(2)
    audio.export(out, format="wav")
    return out

def find_ambience():
    files = []
    for ext in ("*.wav", "*.mp3"):
        files.extend(glob.glob(os.path.join(AMBIENCE_DIR, ext)))
    return files

def main():
    if not os.path.isfile(VOICE_PATH):
        raise SystemExit(f"[AUDIO] Voice file not found: {VOICE_PATH}")

    voice = AudioSegment.from_file(VOICE_PATH).apply_gain(VOICE_DB)

    amb_files = find_ambience()
    if not amb_files:
        print("[AUDIO] No ambience found")
        voice.export(OUTPUT, format="wav")
        return

    # Pick ONE ambience
    amb_src = amb_files[0]
    amb_wav = convert_to_wav(amb_src)

    ambience = AudioSegment.from_file(amb_wav).apply_gain(AMBIENCE_DB)

    loops = int(len(voice) / len(ambience)) + 1
    ambience = (ambience * loops)[:len(voice)]
    ambience = ambience.fade_in(FADE_MS).fade_out(FADE_MS)

    final = ambience.overlay(voice)
    final.export(OUTPUT, format="wav")

    print("[AUDIO] Final audio written:", OUTPUT)

if __name__ == "__main__":
    main()
