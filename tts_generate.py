#!/usr/bin/env python
"""
Single-pass cloned narration with E2-F5 / F5-TTS.

- Picks one reference voice from voices/ (aman.wav / aman(1).wav / aman(2).wav).
- Reads script from script.txt (or $TTS_SCRIPT_PATH).
- Generates ONE clean narration file: tts-audio.wav (or $TTS_OUTPUT_PATH).
- Normalizes, resamples to 44.1 kHz, light fade in/out, atomic write.

Requires:
    pip install f5-tts torch torchaudio
"""

import argparse
import os
import random
import sys
from typing import List, Optional, Tuple

import torch
import torchaudio
from f5_tts import F5TTS  # library for E2/F5 TTS


VOICES_DIR = "voices"
DEFAULT_VOICE_FILES = [
    "aman.wav",
    "aman(1).wav",
    "aman(2).wav",
]


# ------------------------- DEVICE & MODEL ------------------------- #

def detect_device(explicit: Optional[str] = None) -> str:
    if explicit is not None:
        return explicit
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def build_tts(model_name: str, device: Optional[str] = None) -> Tuple[F5TTS, str]:
    used_device = detect_device(device)
    print(f"[TTS] Loading model '{model_name}' on '{used_device}'...", flush=True)
    tts = F5TTS(model_name, device=used_device)
    print("[TTS] Model ready.", flush=True)
    return tts, used_device


# ------------------------- VOICE PICKING ------------------------- #

def discover_voice_files(voices_dir: str = VOICES_DIR) -> List[str]:
    if not os.path.isdir(voices_dir):
        raise FileNotFoundError(f"Voices directory not found: {voices_dir}")

    candidates: List[str] = []
    for name in os.listdir(voices_dir):
        if name.lower().endswith(".wav"):
            candidates.append(os.path.join(voices_dir, name))

    if candidates:
        return sorted(candidates)

    raise RuntimeError(f"No .wav files found in '{voices_dir}'.")


def pick_random_voice() -> str:
    # Prefer your 3 known voices; fall back to any .wav in voices/
    paths = []
    for fname in DEFAULT_VOICE_FILES:
        full = os.path.join(VOICES_DIR, fname)
        if os.path.isfile(full):
            paths.append(full)

    if not paths:
        paths = discover_voice_files(VOICES_DIR)

    choice = random.choice(paths)
    print(f"[TTS] Selected reference voice: {os.path.basename(choice)}", flush=True)
    return choice


# ------------------------- AUDIO POST-PROCESSING ------------------------- #

def postprocess_and_save(
    wav: torch.Tensor,
    sr: int,
    out_path: str,
    target_sr: int = 44100,
    peak_margin: float = 0.95,
    fade_ms: float = 10.0,
) -> None:
    """
    - Convert to mono tensor
    - Normalize to safe peak
    - Optional fade in/out
    - Resample to target_sr
    - Atomic write
    """
    if not isinstance(wav, torch.Tensor):
        wav = torch.tensor(wav)

    if wav.dim() == 1:
        wav = wav.unsqueeze(0)
    elif wav.dim() == 2 and wav.shape[0] > wav.shape[1]:
        wav = wav.transpose(0, 1)

    if wav.size(0) > 1:
        wav = wav.mean(dim=0, keepdim=True)

    max_val = wav.abs().max()
    if max_val > 0:
        wav = wav / max_val * peak_margin

    if sr != target_sr:
        wav = torchaudio.functional.resample(wav, sr, target_sr)
        sr = target_sr

    fade_samples = int(fade_ms * sr / 1000.0)
    if fade_samples > 0 and wav.size(1) > 2 * fade_samples:
        ramp = torch.linspace(0.0, 1.0, fade_samples)
        wav[:, :fade_samples] *= ramp
        wav[:, -fade_samples:] *= torch.flip(ramp, dims=[0])

    tmp_path = out_path + ".tmp"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    torchaudio.save(tmp_path, wav, sr)
    os.replace(tmp_path, out_path)
    print(f"[TTS] Saved clean audio: {out_path}", flush=True)


# ------------------------- ARG PARSING ------------------------- #

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single-pass E2-F5 / F5-TTS cloned narration."
    )
    parser.add_argument(
        "--script-text",
        dest="script_text",
        default=None,
        help="Main text to synthesize. If omitted, read from script.txt or $TTS_SCRIPT_PATH.",
    )
    parser.add_argument(
        "--output",
        dest="output_main",
        default=None,
        help="Audio output path. If omitted, uses $TTS_OUTPUT_PATH or 'tts-audio.wav'.",
    )
    parser.add_argument(
        "--model",
        dest="model_name",
        default="F5TTS_v1_Base",
        help="Model name (e.g. F5TTS_v1_Base, F5TTS_Base, E2TTS_Base).",
    )
    parser.add_argument(
        "--device",
        dest="device",
        default=None,
        help="Force device: cuda | cpu | mps. Default: auto-detect.",
    )
    parser.add_argument(
        "--nfe-step",
        dest="nfe_step",
        type=int,
        default=32,
        help="Flow-matching steps (16–64). Higher = smoother, slower.",
    )
    parser.add_argument(
        "--cfg-strength",
        dest="cfg_strength",
        type=float,
        default=2.0,
        help="Conditioning strength (1.5–3.0). Higher = closer to reference style.",
    )
    parser.add_argument(
        "--speed",
        dest="speed",
        type=float,
        default=1.0,
        help="Speaking speed multiplier (0.9–1.1 usually).",
    )
    parser.add_argument(
        "--target-rms",
        dest="target_rms",
        type=float,
        default=0.11,
        help="Target loudness. 0.08–0.18 is typical.",
    )
    parser.add_argument(
        "--remove-silence",
        dest="remove_silence",
        action="store_true",
        help="Trim leading/trailing silence from generated audio.",
    )
    return parser.parse_args()


def read_script_text(cli_text: Optional[str]) -> str:
    if cli_text is not None:
        text = cli_text.strip()
    else:
        script_path = os.environ.get("TTS_SCRIPT_PATH", "script.txt")
        if not os.path.isfile(script_path):
            print(f"[TTS] Script file not found: {script_path}", file=sys.stderr)
            sys.exit(1)
        with open(script_path, "r", encoding="utf-8") as f:
            text = f.read().strip()

    if not text:
        print("[TTS] Script text is empty.", file=sys.stderr)
        sys.exit(1)
    return text


# ------------------------- MAIN ------------------------- #

def main() -> None:
    args = parse_args()

    ref_audio = pick_random_voice()
    tts, used_device = build_tts(args.model_name, args.device)

    script_text = read_script_text(args.script_text)
    main_out = args.output_main or os.environ.get("TTS_OUTPUT_PATH", "tts-audio.wav")

    print("[TTS] Generating single-pass narration...")
    wav, sr, _ = tts.infer(
        ref_file=ref_audio,
        ref_text="",               # let model auto-ASR the reference
        gen_text=script_text,
        nfe_step=args.nfe_step,
        cfg_strength=args.cfg_strength,
        speed=args.speed,
        target_rms=args.target_rms,
        remove_silence=args.remove_silence,
    )

    postprocess_and_save(
        wav=wav,
        sr=sr,
        out_path=main_out,
        target_sr=44100,
        peak_margin=0.95,
        fade_ms=10.0,
    )

    print("[TTS] Completed successfully.")
    print(f"  Device     : {used_device}")
    print(f"  Voice used : {ref_audio}")
    print(f"  Output     : {main_out}")


if __name__ == "__main__":
    main()
