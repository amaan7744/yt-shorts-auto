#!/usr/bin/env python
import os
import re
import sys
import math
import tempfile
from typing import List

from TTS.api import TTS
from pydub import AudioSegment, effects


SCRIPT_PATH = os.environ.get("TTS_SCRIPT_PATH", "script.txt")
OUTPUT_PATH = os.environ.get("TTS_OUTPUT_PATH", "tts-audio.wav")

# Config via env
USE_CLONE = os.environ.get("TTS_USE_CLONE", "1") == "1"
VOICE_PATH = os.environ.get("TTS_VOICE_PATH", "voices/aman.wav")
LANGUAGE = os.environ.get("TTS_LANGUAGE", "en")
SPEED = float(os.environ.get("TTS_SPEED", "0.96"))

# Models
CLONE_MODEL = os.environ.get(
    "TTS_CLONE_MODEL",
    "tts_models/multilingual/multi-dataset/xtts_v2",
)
FALLBACK_MODEL = os.environ.get(
    "TTS_FALLBACK_MODEL",
    "tts_models/en/ljspeech/tacotron2-DDC",
)


def log(msg: str):
    print(f"[TTS] {msg}", flush=True)


def load_script(path: str) -> str:
    if not os.path.exists(path):
        log(f"ERROR: script file not found: {path}")
        sys.exit(1)
    text = open(path, "r", encoding="utf-8").read().strip()
    if not text:
        log("ERROR: script is empty")
        sys.exit(1)
    return text


def split_into_chunks(text: str, max_words: int = 22) -> List[str]:
    """
    Split text into sentence-based chunks of up to ~max_words words to avoid
    super long TTS calls and get cleaner prosody.
    """
    # Replace newlines with spaces so we don't get weird pauses
    text = text.replace("\r", " ").replace("\n", " ")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current = []
    count = 0

    for s in sentences:
        words = s.split()
        if not words:
            continue
        if count + len(words) > max_words and current:
            chunks.append(" ".join(current))
            current = []
            count = 0
        current.extend(words)
        count += len(words)

    if current:
        chunks.append(" ".join(current))

    return chunks


def normalize_audio(seg: AudioSegment) -> AudioSegment:
    seg = effects.normalize(seg)
    seg = seg.set_frame_rate(44100).set_channels(1)
    return seg


def synthesize_with_clone(chunks: List[str]) -> AudioSegment:
    """
    Use xtts_v2 with voice cloning, chunk by chunk.
    """
    if not os.path.exists(VOICE_PATH):
        raise FileNotFoundError(f"Voice file not found: {VOICE_PATH}")

    log(f"Loading clone model: {CLONE_MODEL}")
    tts = TTS(CLONE_MODEL)

    pieces = []
    for i, chunk in enumerate(chunks, 1):
        log(f"Cloned chunk {i}/{len(chunks)}: {len(chunk.split())} words")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        tts.tts_to_file(
            text=chunk,
            file_path=tmp_path,
            speaker_wav=VOICE_PATH,
            language=LANGUAGE,
            speed=SPEED,
        )
        audio = AudioSegment.from_wav(tmp_path)
        pieces.append(audio)
        os.remove(tmp_path)

    # Add small pauses between chunks so it doesn’t sound rushed
    silence = AudioSegment.silent(duration=160)  # 160 ms
    out = AudioSegment.empty()
    for i, p in enumerate(pieces):
        if i > 0:
            out += silence
        out += p
    return normalize_audio(out)


def synthesize_with_fallback(chunks: List[str]) -> AudioSegment:
    """
    Use stable English model without cloning.
    """
    log(f"Loading fallback model: {FALLBACK_MODEL}")
    tts = TTS(FALLBACK_MODEL)

    pieces = []
    for i, chunk in enumerate(chunks, 1):
        log(f"Fallback chunk {i}/{len(chunks)}: {len(chunk.split())} words")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        tts.tts_to_file(
            text=chunk,
            file_path=tmp_path,
        )
        audio = AudioSegment.from_wav(tmp_path)
        pieces.append(audio)
        os.remove(tmp_path)

    silence = AudioSegment.silent(duration=160)
    out = AudioSegment.empty()
    for i, p in enumerate(pieces):
        if i > 0:
            out += silence
        out += p
    return normalize_audio(out)


def main():
    script = load_script(SCRIPT_PATH)
    chunks = split_into_chunks(script, max_words=22)

    if not chunks:
        log("ERROR: no chunks after splitting")
        sys.exit(1)

    log(f"Total chunks for TTS: {len(chunks)}")

    audio = None

    if USE_CLONE and os.path.exists(VOICE_PATH):
        log("Attempting cloned TTS first...")
        try:
            audio = synthesize_with_clone(chunks)
        except Exception as e:
            log(f"Clone TTS failed: {e}")
            audio = None
    else:
        if USE_CLONE:
            log(f"Clone requested but voice file missing: {VOICE_PATH}")
        else:
            log("Clone disabled via TTS_USE_CLONE=0")

    # Fallback if clone failed or disabled
    if audio is None:
        log("Falling back to non-cloned English TTS...")
        try:
            audio = synthesize_with_fallback(chunks)
        except Exception as e:
            log(f"Fallback TTS failed: {e}")
            sys.exit(1)

    # Sanity checks
    duration_sec = audio.duration_seconds
    log(f"Final audio duration ~{duration_sec:.1f}s")

    if duration_sec < 5:
        log("ERROR: final audio too short (<5s) – likely TTS failure.")
        sys.exit(1)

    if duration_sec > 90:
        log("Warning: final audio very long (>90s). You may want to adjust script length.")

    audio.export(OUTPUT_PATH, format="wav")
    if not os.path.exists(OUTPUT_PATH) or os.path.getsize(OUTPUT_PATH) == 0:
        log("ERROR: output wav not written correctly.")
        sys.exit(1)

    log(f"Saved final TTS audio to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
