#!/usr/bin/env python

import os
import argparse
import random
import re
import sys
import tempfile
from typing import List, Optional

# Force non-interactive and fix torch loading issues
os.environ["COQUI_TOS_AGREED"] = "1"
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

import torch
from TTS.api import TTS
from pydub import AudioSegment, effects
from pydub.effects import compress_dynamic_range

VOICES_DIR = os.path.abspath("voices")
DEFAULT_MODEL_NAME = os.environ.get(
    "TTS_MODEL_NAME", "tts_models/multilingual/multi-dataset/xtts_v2"
)

def log(msg: str) -> None:
    print(f"[TTS] {msg}", flush=True)

def detect_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

def read_script_text(cli_path: Optional[str]) -> str:
    script_path = cli_path or os.environ.get("TTS_SCRIPT_PATH", "script.txt")
    if not os.path.isfile(script_path):
        log(f"ERROR: Script file not found: {script_path}")
        sys.exit(1)
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    return text

def pick_reference_voice() -> str:
    if not os.path.isdir(VOICES_DIR):
        os.makedirs(VOICES_DIR, exist_ok=True)
        log(f"ERROR: Voices directory was missing. Created {VOICES_DIR}. Place .wav files there.")
        sys.exit(1)

    voices = [os.path.join(VOICES_DIR, f) for f in os.listdir(VOICES_DIR) 
              if f.lower().endswith((".wav", ".mp3"))]
    
    if not voices:
        log(f"ERROR: No .wav or .mp3 files found in {VOICES_DIR}")
        sys.exit(1)

    choice = os.path.abspath(random.choice(voices))
    log(f"Selected reference voice: {os.path.basename(choice)}")
    return choice

def split_text_into_chunks(text: str, max_words: int = 40) -> List[str]:
    text = re.sub(r"\s+", " ", text.strip())
    raw_sents = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = []
    count = 0
    for s in raw_sents:
        words = s.split()
        if count + len(words) <= max_words:
            current.append(s)
            count += len(words)
        else:
            if current: chunks.append(" ".join(current))
            current, count = [s], len(words)
    if current: chunks.append(" ".join(current))
    return chunks

def post_process_audio(seg: AudioSegment) -> AudioSegment:
    """Normalize, compress, and standardise the final output."""
    seg = effects.normalize(seg)
    seg = compress_dynamic_range(seg, threshold=-20.0, ratio=3.0)
    return seg.set_frame_rate(44100).set_channels(1)

def synthesize_xtts(model_name: str, device: str, ref_voice: str, text: str, output_path: str):
    log(f"Loading {model_name} on {device}...")
    
    # Initialize TTS with GPU optimizations if available
    tts = TTS(model_name=model_name, progress_bar=False)
    tts.to(device)

    chunks = split_text_into_chunks(text)
    log(f"Split script into {len(chunks)} chunks for stability.")

    pieces: List[AudioSegment] = []
    
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, chunk in enumerate(chunks, start=1):
            log(f"Synthesizing chunk {i}/{len(chunks)}...")
            tmp_wav = os.path.join(tmpdir, f"chunk_{i}.wav")

            # XTTS v2 requires specific language and speaker_wav parameters for cloning
            tts.tts_to_file(
                text=chunk,
                file_path=tmp_wav,
                speaker_wav=ref_voice,
                language="en",
                split_sentences=False # Already handled manually
            )

            if os.path.exists(tmp_wav):
                pieces.append(AudioSegment.from_file(tmp_wav))

    if not pieces:
        log("ERROR: No audio pieces were generated.")
        return

    # Combine with crossfade to prevent pops
    final_audio = pieces[0]
    silence = AudioSegment.silent(duration=200)
    for next_piece in pieces[1:]:
        final_audio = final_audio.append(silence + next_piece, crossfade=30)

    final_audio = post_process_audio(final_audio)
    final_audio.export(output_path, format="wav")
    log(f"Success! Output saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", default="script.txt")
    parser.add_argument("--output", default="narration.wav")
    args = parser.parse_args()

    device = detect_device()
    script_text = read_script_text(args.script)
    ref_voice = pick_reference_voice()

    synthesize_xtts(
        model_name=DEFAULT_MODEL_NAME,
        device=device,
        ref_voice=ref_voice,
        text=script_text,
        output_path=args.output
    )

if __name__ == "__main__":
    main()
