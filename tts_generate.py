#!/usr/bin/env python3
import os
import sys
import re
import argparse
import torch
from TTS.api import TTS
from pydub import AudioSegment, effects

# --------------------------------------------------
# HARD RULES
# --------------------------------------------------
VOICE_FILE = "voices/male.wav"   # 🔒 MALE ONLY
SCRIPT_FILE = "script.txt"
OUTPUT_DEFAULT = "final_audio.wav"

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
TARGET_SR = 44100

os.environ["COQUI_TOS_AGREED"] = "1"
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

# --------------------------------------------------
def die(msg: str):
    sys.exit(f"[TTS] ❌ {msg}")

def log(msg: str):
    print(f"[TTS] {msg}", flush=True)

# --------------------------------------------------
def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"

# --------------------------------------------------
def read_script():
    if not os.path.isfile(SCRIPT_FILE):
        die("script.txt missing")

    text = open(SCRIPT_FILE, encoding="utf-8").read().strip()
    if not text:
        die("script is empty")

    text = re.sub(r"\s+", " ", text)
    return text

# --------------------------------------------------
def synthesize(script: str, output: str):
    if not os.path.isfile(VOICE_FILE):
        die(
            "voices/male.wav missing.\n"
            "XTTS CANNOT guarantee male voice without a reference file."
        )

    log("Loading XTTS v2…")
    tts = TTS(model_name=MODEL_NAME, progress_bar=False).to(get_device())

    log("Using locked male voice (no fallback)")
    temp = "temp.wav"

    tts.tts_to_file(
        text=script,
        speaker_wav=VOICE_FILE,   # 🔒 ENFORCED
        language="en",
        file_path=temp,
    )

    audio = AudioSegment.from_file(temp)
    audio = effects.normalize(audio, headroom=2.0)
    audio = audio.set_channels(1).set_frame_rate(TARGET_SR)

    audio.export(output, format="wav")
    os.remove(temp)

    log(f"✅ Male narration ready: {output} ({len(audio)/1000:.1f}s)")

# --------------------------------------------------
def main():
    script = read_script()
    synthesize(script, OUTPUT_DEFAULT)

if __name__ == "__main__":
    main()
