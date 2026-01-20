#!/usr/bin/env python3
import os
import sys
import re
import argparse
from typing import Optional

import torch
from TTS.api import TTS
from pydub import AudioSegment, effects

# --------------------------------------------------
# ENV
# --------------------------------------------------
os.environ.setdefault("COQUI_TOS_AGREED", "1")
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
SCRIPT_FILE = "script.txt"
OUTPUT_DEFAULT = "final_audio.wav"

# LOCKED VOICE (NO RANDOMIZATION)
VOICE_FILE = "voices/male_main.wav"   # <-- YOU MUST SET THIS

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

TARGET_SR = 44100

# --------------------------------------------------
# LOG
# --------------------------------------------------
def log(msg: str):
    print(f"[TTS] {msg}", flush=True)

# --------------------------------------------------
# DEVICE
# --------------------------------------------------
def device():
    return "cuda" if torch.cuda.is_available() else "cpu"

# --------------------------------------------------
# SCRIPT
# --------------------------------------------------
def read_script(path: Optional[str]) -> str:
    path = path or SCRIPT_FILE
    if not os.path.isfile(path):
        sys.exit(f"[TTS] ❌ Script not found: {path}")
    text = open(path, encoding="utf-8").read().strip()
    if not text:
        sys.exit("[TTS] ❌ Script empty")

    # Clean spacing only (NO pacing tricks)
    return re.sub(r"\s+", " ", text)

# --------------------------------------------------
# AUDIO CLEANUP (LIGHT TOUCH ONLY)
# --------------------------------------------------
def polish(seg: AudioSegment) -> AudioSegment:
    seg = effects.normalize(seg, headroom=2.0)
    return seg.set_channels(1).set_frame_rate(TARGET_SR)

# --------------------------------------------------
# SYNTHESIS (SINGLE PASS)
# --------------------------------------------------
def synthesize(script: str, output: str):
    if not os.path.isfile(VOICE_FILE):
        sys.exit(f"[TTS] ❌ Voice file not found: {VOICE_FILE}")

    log(f"Using fixed voice: {VOICE_FILE}")
    log(f"Loading XTTS on {device()}")

    tts = TTS(model_name=MODEL_NAME, progress_bar=False).to(device())

    # SINGLE synthesis → NO voice drift
    tts.tts_to_file(
        text=script,
        speaker_wav=VOICE_FILE,
        language="en",
        file_path=output,
    )

    audio = AudioSegment.from_file(output)
    audio = polish(audio)

    audio.export(output, format="wav")
    log(f"✅ Final narration written: {output} ({len(audio)/1000:.1f}s)")

# --------------------------------------------------
# CLI
# --------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--script", default=None)
    p.add_argument("--output", default=OUTPUT_DEFAULT)
    args = p.parse_args()

    script = read_script(args.script)
    synthesize(script, args.output)

if __name__ == "__main__":
    main()
