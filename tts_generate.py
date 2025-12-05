#!/usr/bin/env python
import os
import re
import sys
import tempfile
import random
from typing import List

from TTS.api import TTS
from pydub import AudioSegment, effects
from pydub.effects import compress_dynamic_range

SCRIPT_PATH = os.environ.get("TTS_SCRIPT_PATH", "script.txt")
OUTPUT_PATH = os.environ.get("TTS_OUTPUT_PATH", "tts-audio.wav")

# By default, we DO use cloning now.
USE_CLONE = os.environ.get("TTS_USE_CLONE", "1") == "1"
VOICE_PATH = os.environ.get("TTS_VOICE_PATH", "voices/aman.wav")
LANGUAGE = os.environ.get("TTS_LANGUAGE", "en")

SPEED = float(os.environ.get("TTS_SPEED", "0.96"))

# Primary: XTTS v2 clone
CLONE_MODEL = os.environ.get(
    "TTS_CLONE_MODEL",
    "tts_models/multilingual/multi-dataset/xtts_v2",
)

# Fallback: natural multi-speaker English (no clone)
PRIMARY_MODEL = os.environ.get(
    "TTS_PRIMARY_MODEL",
    "tts_models/en/vctk/vits",
)
PRIMARY_SPEAKER = os.environ.get("TTS_PRIMARY_SPEAKER", "p227")

# Last-resort English model
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
    Split text into sentence-based chunks of up to ~max_words words
    so prosody stays natural.
    """
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
    """
    Loudness-normalize, gently compress, and standardize format.
    """
    seg = effects.normalize(seg)
    seg = compress_dynamic_range(
        seg,
        threshold=-20.0,
        ratio=3.0,
        attack=5,
        release=50,
    )
    seg = seg.set_frame_rate(44100).set_channels(1)
    return seg


def join_chunks_with_crossfade(
    pieces: List[AudioSegment],
    pause_ms: int = 160,
    crossfade_ms: int = 20,
) -> AudioSegment:
    """
    Join audio chunks with short pauses and crossfade to avoid clicks and robotic gaps.
    """
    if not pieces:
        return AudioSegment.empty()

    silence = AudioSegment.silent(duration=pause_ms)
    out = pieces[0]

    for p in pieces[1:]:
        segment_with_pause = silence + p
        out = out.append(segment_with_pause, crossfade=crossfade_ms)

    return out


def local_speed(base: float) -> float:
    """
    Slightly vary speaking speed per chunk (±4%) so it doesn't sound like a metronome.
    """
    delta = random.uniform(-0.04, 0.04)
    s = base + delta
    return max(0.85, min(1.15, s))


def synthesize_xtts_clone(chunks: List[str]) -> AudioSegment:
    """
    Primary: XTTS v2 with voice cloning.
    """
    if not os.path.exists(VOICE_PATH):
        raise FileNotFoundError(f"Voice file not found for cloning: {VOICE_PATH}")

    clone_dur = AudioSegment.from_file(VOICE_PATH).duration_seconds
    if clone_dur < 8:
        log(f"WARNING: voice sample too short ({clone_dur:.1f}s). Clone quality may be bad.")

    log(f"Loading clone model: {CLONE_MODEL}")
    tts = TTS(CLONE_MODEL)

    pieces = []
    for i, chunk in enumerate(chunks, 1):
        this_speed = local_speed(SPEED)
        log(
            f"Clone chunk {i}/{len(chunks)}: {len(chunk.split())} words "
            f"at speed {this_speed:.2f}"
        )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        tts.tts_to_file(
            text=chunk,
            file_path=tmp_path,
            speaker_wav=VOICE_PATH,
            language=LANGUAGE,
            speed=this_speed,
        )
        audio = AudioSegment.from_wav(tmp_path)
        pieces.append(audio)
        os.remove(tmp_path)

    out = join_chunks_with_crossfade(pieces, pause_ms=160, crossfade_ms=20)
    return normalize_audio(out)


def synthesize_primary_vctk(chunks: List[str]) -> AudioSegment:
    """
    Fallback 1: natural multi-speaker English (no clone, but decent).
    """
    log(f"Loading primary non-clone model: {PRIMARY_MODEL}")
    tts = TTS(PRIMARY_MODEL)

    pieces = []
    for i, chunk in enumerate(chunks, 1):
        this_speed = local_speed(SPEED)
        log(
            f"VCTK chunk {i}/{len(chunks)}: {len(chunk.split())} words "
            f"at speed {this_speed:.2f}"
        )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            tts.tts_to_file(
                text=chunk,
                file_path=tmp_path,
                speaker=PRIMARY_SPEAKER,
                speed=this_speed,
            )
        except TypeError:
            log("VCTK model doesn't support speaker/speed cleanly, retrying without extras.")
            tts.tts_to_file(
                text=chunk,
                file_path=tmp_path,
            )

        audio = AudioSegment.from_wav(tmp_path)
        pieces.append(audio)
        os.remove(tmp_path)

    out = join_chunks_with_crossfade(pieces, pause_ms=160, crossfade_ms=20)
    return normalize_audio(out)


def synthesize_ljspeech(chunks: List[str]) -> AudioSegment:
    """
    Fallback 2: stable LJSpeech English.
    """
    log(f"Loading fallback model: {FALLBACK_MODEL}")
    tts = TTS(FALLBACK_MODEL)

    pieces = []
    for i, chunk in enumerate(chunks, 1):
        log(f"LJSpeech chunk {i}/{len(chunks)}: {len(chunk.split())} words")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        tts.tts_to_file(
            text=chunk,
            file_path=tmp_path,
        )
        audio = AudioSegment.from_wav(tmp_path)
        pieces.append(audio)
        os.remove(tmp_path)

    out = join_chunks_with_crossfade(pieces, pause_ms=160, crossfade_ms=20)
    return normalize_audio(out)


def main():
    script = load_script(SCRIPT_PATH)
    chunks = split_into_chunks(script, max_words=22)

    if not chunks:
        log("ERROR: no chunks after splitting")
        sys.exit(1)

    log(f"Total chunks for TTS: {len(chunks)}")

    audio = None

    # 1) Clone (XTTS v2) – ONLY if USE_CLONE=1
    if USE_CLONE:
        try:
            log("Trying XTTS cloned voice...")
            audio = synthesize_xtts_clone(chunks)
        except Exception as e:
            log(f"XTTS clone failed: {e}")
            audio = None

    # 2) VCTK neutral voice
    if audio is None:
        try:
            log("Trying VCTK English voice...")
            audio = synthesize_primary_vctk(chunks)
        except Exception as e:
            log(f"VCTK TTS failed: {e}")
            audio = None

    # 3) LJSpeech fallback
    if audio is None:
        try:
            log("Falling back to LJSpeech...")
            audio = synthesize_ljspeech(chunks)
        except Exception as e:
            log(f"LJSpeech TTS failed: {e}")
            sys.exit(1)

    duration_sec = audio.duration_seconds
    log(f"Final audio duration ~{duration_sec:.1f}s")

    if duration_sec < 5:
        log("ERROR: final audio too short (<5s) – likely TTS failure.")
        sys.exit(1)

    if duration_sec > 90:
        log("Warning: final audio very long (>90s). You may want to shorten the script.")

    audio.export(OUTPUT_PATH, format="wav")
    if not os.path.exists(OUTPUT_PATH) or os.path.getsize(OUTPUT_PATH) == 0:
        log("ERROR: output wav not written correctly.")
        sys.exit(1)

    log(f"Saved final TTS audio to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
