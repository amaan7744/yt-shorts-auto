#!/usr/bin/env python

import os

# Make Coqui TTS non-interactive and compatible with newer torch.load
os.environ.setdefault("COQUI_TOS_AGREED", "1")
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

"""
Natural voice-cloned TTS using Coqui XTTS-v2.

- Picks ONE random reference voice from voices/ (wav or mp3).
- Reads narration text from script.txt (or $TTS_SCRIPT_PATH).
- Splits into short chunks for stable XTTS prosody.
- Synthesizes each chunk with XTTS-v2 using speaker_wav (true cloning).
- Joins chunks with short pauses + crossfade to avoid clicks.
- Normalizes + lightly compresses audio, resamples to 44.1 kHz mono.
- Writes a single clean WAV file (atomic write) to:
    - CLI:     --output /path/to/tts.wav
    - or env:  $TTS_OUTPUT_PATH
    - or default: tts.wav
"""

import argparse
import random
import re
import sys
import tempfile
from typing import List, Optional

import torch
from TTS.api import TTS
from pydub import AudioSegment, effects
from pydub.effects import compress_dynamic_range


VOICES_DIR = "voices"
DEFAULT_MODEL_NAME = os.environ.get(
    "TTS_MODEL_NAME", "tts_models/multilingual/multi-dataset/xtts_v2"
)


# ------------------------- logging ------------------------- #

def log(msg: str) -> None:
    print(f"[TTS] {msg}", flush=True)


# ------------------------- device ------------------------- #

def detect_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    # GitHub Actions typically has only CPU
    return "cpu"


# ------------------------- script reading ------------------------- #

def read_script_text(cli_path: Optional[str]) -> str:
    script_path = cli_path or os.environ.get("TTS_SCRIPT_PATH", "script.txt")

    if not os.path.isfile(script_path):
        log(f"ERROR: Script file not found: {script_path}")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        log(f"ERROR: Script file is empty: {script_path}")
        sys.exit(1)

    wc = len(text.split())
    log(f"Loaded script from {script_path} ({wc} words)")
    return text


# ------------------------- voice selection ------------------------- #

def find_voice_files() -> List[str]:
    if not os.path.isdir(VOICES_DIR):
        log(f"ERROR: Voices directory not found: {VOICES_DIR}")
        sys.exit(1)

    voices: List[str] = []
    for name in os.listdir(VOICES_DIR):
        lower = name.lower()
        if lower.endswith(".wav") or lower.endswith(".mp3"):
            voices.append(os.path.join(VOICES_DIR, name))

    if not voices:
        log(f"ERROR: No .wav or .mp3 files found in {VOICES_DIR}")
        sys.exit(1)

    voices.sort()
    return voices


def pick_reference_voice() -> str:
    voices = find_voice_files()
    choice = random.choice(voices)
    log(f"Using reference voice: {choice}")
    return choice


# ------------------------- text chunking ------------------------- #

def split_text_into_chunks(text: str, max_words: int = 45) -> List[str]:
    """
    Split into sentence-based chunks of <= max_words to keep XTTS stable.
    """
    # Clean weird whitespace
    text = re.sub(r"\s+", " ", text.strip())
    # Split on sentence boundaries
    raw_sents = re.split(r"(?<=[.!?])\s+", text)
    sents = [s.strip() for s in raw_sents if s.strip()]

    if not sents:
        return [text]

    chunks: List[str] = []
    current: List[str] = []
    count = 0

    for s in sents:
        words = s.split()
        if count + len(words) <= max_words:
            current.append(s)
            count += len(words)
        else:
            if current:
                chunks.append(" ".join(current))
            current = [s]
            count = len(words)

    if current:
        chunks.append(" ".join(current))

    # Fallback
    if not chunks:
        return [text]

    return chunks


# ------------------------- audio helpers ------------------------- #

def normalize_audio(seg: AudioSegment) -> AudioSegment:
    """
    Loudness normalization + gentle compression + standard format.
    """
    seg = effects.normalize(seg)
    seg = compress_dynamic_range(
        seg,
        threshold=-20.0,  # start compressing above -20 dBFS
        ratio=3.0,        # 3:1 compression
        attack=5,         # ms
        release=50,       # ms
    )
    seg = seg.set_frame_rate(44100).set_channels(1)
    return seg


def join_chunks_with_crossfade(
    pieces: List[AudioSegment],
    pause_ms: int = 160,
    crossfade_ms: int = 20,
) -> AudioSegment:
    """
    Join chunks with tiny pauses and crossfade to avoid clicks/pops.
    """
    if not pieces:
        return AudioSegment.empty()

    silence = AudioSegment.silent(duration=pause_ms)
    out = pieces[0]

    for p in pieces[1:]:
        segment_with_pause = silence + p
        out = out.append(segment_with_pause, crossfade=crossfade_ms)

    return out


# ------------------------- core synthesis ------------------------- #

def synthesize_xtts(
    model_name: str,
    device: str,
    ref_voice: str,
    text: str,
    output_path: str,
) -> None:
    log(f"Loading XTTS model: {model_name} on {device}")
    tts = TTS(model_name=model_name, progress_bar=False).to(device)

    chunks = split_text_into_chunks(text, max_words=45)
    log(f"Script split into {len(chunks)} chunks")

    pieces: List[AudioSegment] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, chunk in enumerate(chunks, start=1):
            chunk_wc = len(chunk.split())
            log(f"Synthesizing chunk {i}/{len(chunks)} ({chunk_wc} words)")

            tmp_wav = os.path.join(tmpdir, f"chunk_{i}.wav")

            # Core XTTS voice cloning call
            tts.tts_to_file(
                text=chunk,
                speaker_wav=ref_voice,
                language="en",
                file_path=tmp_wav,
            )

            if not os.path.exists(tmp_wav) or os.path.getsize(tmp_wav) == 0:
                log(f"ERROR: XTTS produced empty audio for chunk {i}")
                sys.exit(1)

            audio = AudioSegment.from_file(tmp_wav)
            pieces.append(audio)

    if not pieces:
        log("ERROR: No audio chunks were produced.")
        sys.exit(1)

    log("Joining chunks with crossfade + pauses...")
    joined = join_chunks_with_crossfade(pieces, pause_ms=160, crossfade_ms=20)

    log("Normalizing + compressing audio...")
    final = normalize_audio(joined)

    # Atomic write to avoid broken files
    tmp_out = output_path + ".tmp"
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    final.export(tmp_out, format="wav")
    os.replace(tmp_out, output_path)

    total_sec = len(final) / 1000.0
    log(f"Done. Wrote {output_path} ({total_sec:.1f}s)")


# ------------------------- CLI ------------------------- #

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="XTTS-v2 voice-cloned TTS generator.")
    p.add_argument(
        "--script-path",
        dest="script_path",
        default=None,
        help="Path to script text file (default: $TTS_SCRIPT_PATH or script.txt).",
    )
    p.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Output WAV path (default: $TTS_OUTPUT_PATH or tts.wav).",
    )
    p.add_argument(
        "--model",
        dest="model_name",
        default=DEFAULT_MODEL_NAME,
        help=f"TTS model name (default: {DEFAULT_MODEL_NAME}).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    device = detect_device()
    script_text = read_script_text(args.script_path)
    ref_voice = pick_reference_voice()

    output_path = args.output or os.environ.get("TTS_OUTPUT_PATH", "tts.wav")
    model_name = args.model_name

    synthesize_xtts(
        model_name=model_name,
        device=device,
        ref_voice=ref_voice,
        text=script_text,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()
