#!/usr/bin/env python3
"""
Shorts-Optimized XTTS Narration Generator
Crime Whisper Mode + Adaptive Emotion (SAFE)

- Single cloned voice only
- No robotic pacing
- No forced pauses
- Emotion via delivery, not silence
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

PLAYBACK_SPEED = 1.06          # Natural, calm
MAX_WORDS_NEUTRAL = 22
MAX_WORDS_WHISPER = 16
MAX_WORDS_FIRM = 20

CROSSFADE_MS = 60              # Natural flow
OUTPUT_RATE = 44100


# ==================================================
# UTILS
# ==================================================

def log(msg: str) -> None:
    print(f"[TTS] {msg}", flush=True)


def detect_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def read_script(path: Optional[str]) -> List[str]:
    script_path = path or "script.txt"
    if not os.path.isfile(script_path):
        log(f"ERROR: Script not found: {script_path}")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    return lines


def pick_voice() -> str:
    voices = sorted([
        os.path.join(VOICES_DIR, f)
        for f in os.listdir(VOICES_DIR)
        if f.lower().endswith((".wav", ".mp3"))
    ])

    if not voices:
        log(f"ERROR: No cloned voices found in {VOICES_DIR}")
        sys.exit(1)

    voice = os.environ.get("TTS_VOICE") or voices[0]
    log(f"Using cloned voice: {os.path.basename(voice)}")
    return os.path.abspath(voice)


# ==================================================
# AUTO TAGGING
# ==================================================

def tag_line(line: str, index: int, total: int) -> str:
    """
    Auto-tag script lines:
    - First line → WHISPER
    - Evidence / contradiction → WHISPER
    - Last line → FIRM
    - Others → NEUTRAL
    """
    lower = line.lower()

    if index == 0:
        return "WHISPER"

    if index == total - 1:
        return "FIRM"

    if any(k in lower for k in [
        "but", "however", "did not", "no signs", "locked", "missing",
        "never found", "didn't match", "inconsistent"
    ]):
        return "WHISPER"

    return "NEUTRAL"


# ==================================================
# TEXT SPLITTING (PACE CONTROL)
# ==================================================

def split_text(text: str, max_words: int) -> List[str]:
    words = text.split()
    chunks = []
    buf = []

    for w in words:
        buf.append(w)
        if len(buf) >= max_words:
            chunks.append(" ".join(buf))
            buf = []

    if buf:
        chunks.append(" ".join(buf))

    return chunks


# ==================================================
# AUDIO POST
# ==================================================

def post_process(audio: AudioSegment) -> AudioSegment:
    audio = effects.normalize(audio)
    audio = compress_dynamic_range(audio, threshold=-22.0, ratio=2.5)
    audio = effects.speedup(audio, playback_speed=PLAYBACK_SPEED)
    return audio.set_frame_rate(OUTPUT_RATE).set_channels(1)


# ==================================================
# SYNTHESIS
# ==================================================

def synthesize(
    model_name: str,
    device: str,
    voice: str,
    script_lines: List[str],
    output_path: str
) -> None:

    log(f"Loading XTTS on {device}")
    tts = TTS(model_name=model_name, progress_bar=False)
    tts.to(device)

    audio_parts: List[AudioSegment] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, line in enumerate(script_lines):
            tag = tag_line(line, idx, len(script_lines))

            if tag == "WHISPER":
                max_words = MAX_WORDS_WHISPER
                line = line.lower()
            elif tag == "FIRM":
                max_words = MAX_WORDS_FIRM
                line = line.upper()
            else:
                max_words = MAX_WORDS_NEUTRAL

            chunks = split_text(line, max_words)

            for i, chunk in enumerate(chunks):
                tmp_wav = os.path.join(tmpdir, f"seg_{idx}_{i}.wav")
                log(f"{tag}: {chunk}")

                tts.tts_to_file(
                    text=chunk,
                    file_path=tmp_wav,
                    speaker_wav=voice,
                    language="en",
                    split_sentences=False
                )

                audio_parts.append(AudioSegment.from_file(tmp_wav))

    if not audio_parts:
        log("ERROR: No audio produced")
        sys.exit(1)

    final = audio_parts[0]
    for part in audio_parts[1:]:
        final = final.append(part, crossfade=CROSSFADE_MS)

    final = post_process(final)
    final.export(output_path, format="wav")

    log(f"✅ Narration complete: {output_path}")


# ==================================================
# MAIN
# ==================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", default="script.txt")
    parser.add_argument("--output", default="final_audio.wav")
    args = parser.parse_args()

    device = detect_device()
    voice = pick_voice()
    script_lines = read_script(args.script)

    synthesize(
        model_name=DEFAULT_MODEL,
        device=device,
        voice=voice,
        script_lines=script_lines,
        output_path=args.output
    )


if __name__ == "__main__":
    main()
