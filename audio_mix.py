#!/usr/bin/env python3
import os
import glob
from pydub import AudioSegment

VOICE_PATH = "narration.wav"
AMBIENCE_DIR = "ambience"
CACHE_DIR = "ambience_wav"
OUTPUT = "final_audio.wav"

# MIXING TUNING (Shorts-safe)
VOICE_GAIN = -1       # keep voice clean
AMBIENCE_GAIN = -12   # audible but subtle
FADE_MS = 800         # perception fix

os.makedirs(CACHE_DIR, exist_ok=True)

def log(msg):
    print(f"[AUDIO] {msg}", flush=True)

def convert_to_wav(src):
    """
    Converts ANY audio file to clean WAV once.
    Prevents FFmpeg MP3 seek errors forever.
    """
    base = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(CACHE_DIR, base + ".wav")

    if os.path.exists(out):
        return out

    log(f"Converting to WAV: {src}")
    audio = AudioSegment.from_file(src)
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

    voice = AudioSegment.from_file(VOICE_PATH).apply_gain(VOICE_GAIN)

    amb_files = find_ambience()
    if not amb_files:
        log("No ambience found, exporting voice only")
        voice.export(OUTPUT, format="wav")
        return

    # USE ONLY ONE ambience (no stacking)
    amb_src = amb_files[0]
    amb_wav = convert_to_wav(amb_src)

    ambience = AudioSegment.from_file(amb_wav).apply_gain(AMBIENCE_GAIN)

    # Loop ambience safely
    loops = int(len(voice) / len(ambience)) + 1
    ambience = (ambience * loops)[:len(voice)]

    # Fade is CRITICAL for perception
    ambience = ambience.fade_in(FADE_MS).fade_out(FADE_MS)

    final = ambience.overlay(voice)
    final.export(OUTPUT, format="wav")

    log("Final audio written:", OUTPUT)

if __name__ == "__main__":
    main()
