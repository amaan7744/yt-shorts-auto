#!/usr/bin/env python3
import os
import re
import sys
import random
import argparse
import tempfile
from typing import List, Optional

import torch
from TTS.api import TTS
from pydub import AudioSegment, effects
from pydub.effects import compress_dynamic_range

# --------------------------------------------------
# ENV SAFETY
# --------------------------------------------------
os.environ.setdefault("COQUI_TOS_AGREED", "1")
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
VOICES_DIR = "voices"
SCRIPT_FILE = "script.txt"
OUTPUT_DEFAULT = "final_audio.wav"

MODEL_NAME = os.getenv(
    "TTS_MODEL_NAME",
    "tts_models/multilingual/multi-dataset/xtts_v2"
)

# Timing controls (RETENTION FIXES)
HOOK_SPEED = 1.08          # +8% speed for first 2 seconds
FINAL_SPEED = 0.95         # −5% speed for final line
FINAL_PAUSE_MS = 300       # pause before final beat

CHUNK_MAX_WORDS = 45

# --------------------------------------------------
# LOGGING
# --------------------------------------------------
def log(msg: str):
    print(f"[TTS] {msg}", flush=True)

# --------------------------------------------------
# DEVICE
# --------------------------------------------------
def detect_device():
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
    return re.sub(r"\s+", " ", text)

# --------------------------------------------------
# VOICE
# --------------------------------------------------
def pick_voice() -> str:
    if not os.path.isdir(VOICES_DIR):
        sys.exit("[TTS] ❌ voices/ directory missing")

    voices = [
        os.path.join(VOICES_DIR, f)
        for f in os.listdir(VOICES_DIR)
        if f.lower().endswith((".wav", ".mp3"))
    ]
    if not voices:
        sys.exit("[TTS] ❌ No voice files found")

    voice = random.choice(voices)
    log(f"Using voice: {voice}")
    return voice

# --------------------------------------------------
# TEXT SPLITTING
# --------------------------------------------------
def split_chunks(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current, count = [], [], 0

    for s in sentences:
        words = s.split()
        if count + len(words) <= CHUNK_MAX_WORDS:
            current.append(s)
            count += len(words)
        else:
            chunks.append(" ".join(current))
            current, count = [s], len(words)

    if current:
        chunks.append(" ".join(current))

    return chunks

# --------------------------------------------------
# AUDIO HELPERS
# --------------------------------------------------
def speed(seg: AudioSegment, factor: float) -> AudioSegment:
    return seg._spawn(
        seg.raw_data,
        overrides={"frame_rate": int(seg.frame_rate * factor)}
    ).set_frame_rate(seg.frame_rate)

def normalize(seg: AudioSegment) -> AudioSegment:
    seg = effects.normalize(seg)
    seg = compress_dynamic_range(
        seg,
        threshold=-20.0,
        ratio=3.0,
        attack=5,
        release=50,
    )
    return seg.set_channels(1).set_frame_rate(44100)

# --------------------------------------------------
# SYNTHESIS
# --------------------------------------------------
def synthesize(script: str, output: str):
    device = detect_device()
    voice = pick_voice()

    log(f"Loading XTTS ({MODEL_NAME}) on {device}")
    tts = TTS(model_name=MODEL_NAME, progress_bar=False).to(device)

    chunks = split_chunks(script)
    log(f"Script split into {len(chunks)} chunks")

    audio_chunks: List[AudioSegment] = []

    with tempfile.TemporaryDirectory() as tmp:
        for i, chunk in enumerate(chunks):
            tmp_wav = os.path.join(tmp, f"chunk_{i}.wav")

            tts.tts_to_file(
                text=chunk,
                speaker_wav=voice,
                language="en",
                file_path=tmp_wav,
            )

            seg = AudioSegment.from_file(tmp_wav)

            # 🔥 HOOK SPEED BOOST (first chunk only)
            if i == 0:
                seg = speed(seg, HOOK_SPEED)

            audio_chunks.append(seg)

    # 🔥 FINAL LINE SLOWDOWN
    audio_chunks[-1] = speed(audio_chunks[-1], FINAL_SPEED)

    # 🔥 PAUSE BEFORE FINAL BEAT
    final_pause = AudioSegment.silent(duration=FINAL_PAUSE_MS)

    final_audio = AudioSegment.empty()
    for i, seg in enumerate(audio_chunks):
        final_audio += seg
        if i == len(audio_chunks) - 2:
            final_audio += final_pause

    final_audio = normalize(final_audio)

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    final_audio.export(output, format="wav")

    log(f"✅ Final narration written: {output} ({len(final_audio)/1000:.1f}s)")

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
