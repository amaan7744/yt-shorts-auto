#!/usr/bin/env python3
"""
Shorts-Optimized XTTS Narration Generator
Fast-paced, retention-focused, brand-consistent.
"""

import os
import argparse
import re
import sys
import tempfile
from typing import List, Optional

# Environment safety
os.environ["COQUI_TOS_AGREED"] = "1"
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

import torch
from TTS.api import TTS
from pydub import AudioSegment, effects
from pydub.effects import compress_dynamic_range


# ==================================================
# CONFIG
# ==================================================

VOICES_DIR = os.path.abspath("voices")
DEFAULT_MODEL = os.environ.get(
    "TTS_MODEL_NAME",
    "tts_models/multilingual/multi-dataset/xtts_v2"
)

PLAYBACK_SPEED = 1.08        # Shorts pacing
MAX_WORDS_PER_CHUNK = 22     # Rhythm control
CROSSFADE_MS = 60            # No dead air
OUTPUT_RATE = 44100


# ==================================================
# UTILITIES
# ==================================================

def log(msg: str) -> None:
    print(f"[TTS] {msg}", flush=True)


def detect_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def read_script(path: Optional[str]) -> str:
    script_path = path or "script.txt"
    if not os.path.isfile(script_path):
        log(f"ERROR: Script not found: {script_path}")
        sys.exit(0)

    with open(script_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def pick_voice() -> str:
    if not os.path.isdir(VOICES_DIR):
        os.makedirs(VOICES_DIR, exist_ok=True)
        log(f"ERROR: Place reference voice files in {VOICES_DIR}")
        sys.exit(0)

    voices = sorted([
        os.path.join(VOICES_DIR, f)
        for f in os.listdir(VOICES_DIR)
        if f.lower().endswith((".wav", ".mp3"))
    ])

    if not voices:
        log(f"ERROR: No voice files found in {VOICES_DIR}")
        sys.exit(0)

    choice = os.environ.get("TTS_VOICE") or voices[0]
    log(f"Using reference voice: {os.path.basename(choice)}")
    return os.path.abspath(choice)


def split_text(text: str, max_words: int) -> List[str]:
    text = re.sub(r"\s+", " ", text.strip())
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    buffer = []
    count = 0

    for s in sentences:
        words = s.split()
        if count + len(words) <= max_words:
            buffer.append(s)
            count += len(words)
        else:
            if buffer:
                chunks.append(" ".join(buffer))
            buffer = [s]
            count = len(words)

    if buffer:
        chunks.append(" ".join(buffer))

    return chunks


def post_process(audio: AudioSegment) -> AudioSegment:
    audio = effects.normalize(audio)
    audio = compress_dynamic_range(audio, threshold=-20.0, ratio=3.0)
    audio = effects.speedup(audio, playback_speed=PLAYBACK_SPEED)
    return audio.set_frame_rate(OUTPUT_RATE).set_channels(1)


# ==================================================
# SYNTHESIS
# ==================================================

def synthesize(
    model_name: str,
    device: str,
    voice: str,
    text: str,
    output_path: str
) -> None:

    log(f"Loading XTTS model on {device}...")
    tts = TTS(model_name=model_name, progress_bar=False)
    tts.to(device)

    chunks = split_text(text, MAX_WORDS_PER_CHUNK)
    log(f"Text split into {len(chunks)} chunks")

    audio_parts: List[AudioSegment] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, chunk in enumerate(chunks, start=1):
            tmp_wav = os.path.join(tmpdir, f"chunk_{i}.wav")

            # Hook emphasis (subtle, safe)
            if i == 1:
                chunk = chunk.upper()

            log(f"Synthesizing chunk {i}/{len(chunks)}")
            tts.tts_to_file(
                text=chunk,
                file_path=tmp_wav,
                speaker_wav=voice,
                language="en",
                split_sentences=False
            )

            if os.path.exists(tmp_wav):
                audio_parts.append(AudioSegment.from_file(tmp_wav))

    if not audio_parts:
        log("ERROR: No audio generated")
        sys.exit(0)

    final_audio = audio_parts[0]
    for part in audio_parts[1:]:
        final_audio = final_audio.append(part, crossfade=CROSSFADE_MS)

    final_audio = post_process(final_audio)
    final_audio.export(output_path, format="wav")

    log(f"Success! Narration saved to {output_path}")


# ==================================================
# MAIN
# ==================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", default="script.txt")
    parser.add_argument("--output", default="narration.wav")
    args = parser.parse_args()

    device = detect_device()
    script = read_script(args.script)
    voice = pick_voice()

    synthesize(
        model_name=DEFAULT_MODEL,
        device=device,
        voice=voice,
        text=script,
        output_path=args.output
    )


if __name__ == "__main__":
    main()
