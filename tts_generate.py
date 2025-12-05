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

# Config via env
USE_CLONE = os.environ.get("TTS_USE_CLONE", "0") == "1"
VOICE_PATH = os.environ.get("TTS_VOICE_PATH", "voices/aman.wav")
LANGUAGE = os.environ.get("TTS_LANGUAGE", "en")

# Slightly slower than 1.0 for clearer narration
SPEED = float(os.environ.get("TTS_SPEED", "0.96"))

# Primary model: natural, multi-speaker English
PRIMARY_MODEL = os.environ.get(
    "TTS_PRIMARY_MODEL",
    "tts_models/en/vctk/vits",
)

# Speaker ID for PRIMARY_MODEL (VCTK voice)
PRIMARY_SPEAKER = os.environ.get("TTS_PRIMARY_SPEAKER", "p227")

# Optional clone model (if you want to enable it later)
CLONE_MODEL = os.environ.get(
    "TTS_CLONE_MODEL",
    "tts_models/multilingual/multi-dataset/xtts_v2",
)

# Last-resort fallback
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
    to keep prosody natural.
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
        threshold=-20.0,  # start compressing above -20 dBFS
        ratio=3.0,        # 3:1 compression
        attack=5,         # attack in ms
        release=50        # release in ms
    )
    seg = seg.set_frame_rate(44100).set_channels(1)
    return seg


def join_chunks_with_crossfade(
    pieces: List[AudioSegment],
    pause_ms: int = 160,
    crossfade_ms: int = 20
) -> AudioSegment:
    """
    Join all audio chunks with short pauses and a small crossfade to avoid clicks.
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
    Slightly vary speaking speed to avoid sounding like a metronome.
    ±4% variation around base, clamped to a sane range.
    """
    delta = random.uniform(-0.04, 0.04)
    s = base + delta
    return max(0.85, min(1.15, s))


def synthesize_with_primary(chunks: List[str]) -> AudioSegment:
    """
    Use a natural multi-speaker English model with a fixed speaker.
    """
    log(f"Loading primary model: {PRIMARY_MODEL}")
    tts = TTS(PRIMARY_MODEL)

    pieces = []
    for i, chunk in enumerate(chunks, 1):
        this_speed = local_speed(SPEED)
        log(
            f"Primary chunk {i}/{len(chunks)}: {len(chunk.split())} words "
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
            log("Primary model doesn't support speaker/speed, retrying without those params.")
            tts.tts_to_file(
                text=chunk,
                file_path=tmp_path,
            )

        audio = AudioSegment.from_wav(tmp_path)
        pieces.append(audio)
        os.remove(tmp_path)

    out = join_chunks_with_crossfade(pieces, pause_ms=160, crossfade_ms=20)
    return normalize_audio(out)


def synthesize_with_clone(chunks: List[str]) -> AudioSegment:
    """
    Optional: use xtts_v2 with voice cloning, chunk by chunk.
    """
    if not os.path.exists(VOICE_PATH):
        raise FileNotFoundError(f"Voice file not found: {VOICE_PATH}")

    log(f"Loading clone model: {CLONE_MODEL}")
    tts = TTS(CLONE_MODEL)

    pieces = []
    for i, chunk in enumerate(chunks, 1):
        this_speed = local_speed(SPEED)
        log(
            f"Cloned chunk {i}/{len(chunks)}: {len(chunk.split())} words "
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


def synthesize_with_fallback(chunks: List[str]) -> AudioSegment:
    """
    Stable English fallback – last resort if primary + clone fail.
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

    # 1) Primary model (natural multi-speaker EN)
    try:
        log("Trying primary natural English model...")
        audio = synthesize_with_primary(chunks)
    except Exception as e:
        log(f"Primary model TTS failed: {e}")
        audio = None

    # 2) Optional cloned voice (only if explicitly enabled)
    if audio is None and USE_CLONE:
        try:
            log("Trying cloned voice model...")
            audio = synthesize_with_clone(chunks)
        except Exception as e:
            log(f"Clone TTS failed: {e}")
            audio = None

    # 3) Fallback
    if audio is None:
        try:
            log("Falling back to stable English model...")
            audio = synthesize_with_fallback(chunks)
        except Exception as e:
            log(f"Fallback TTS failed: {e}")
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
