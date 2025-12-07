#!/usr/bin/env python
"""
Generate a single cloned narration with F5-TTS / E2-F5 using the official CLI.

Behavior:
- Picks ONE random reference voice from voices/:
    voices/aman.wav
    voices/aman(1).wav
    voices/aman(2).wav
    or any *.wav inside voices/ if those don't exist.

- Reads script text from:
    --script-path argument
    OR $TTS_SCRIPT_PATH
    OR script.txt

- Calls:
    f5-tts_infer-cli
      --model F5-TTS (default, can override with $F5_MODEL_NAME)
      --ref_audio <chosen voice>
      --gen_file <script file>
      --remove_silence
      --output_dir <temp dir>

- Post-processes:
    - Loads the generated WAV
    - Converts to mono
    - Normalizes with pydub.effects.normalize()
    - Resamples to 44.1 kHz
    - Saves to final output path:
        --output argument
        OR $TTS_OUTPUT_PATH
        OR tts.wav
"""

import argparse
import os
import random
import sys
import tempfile
import pathlib
import subprocess
from typing import List, Optional

from pydub import AudioSegment, effects

VOICES_DIR = "voices"
DEFAULT_VOICES = ["aman.wav", "aman(1).wav", "aman(2).wav"]

# Default model name for F5/E2
F5_MODEL_NAME = os.environ.get("F5_MODEL_NAME", "F5-TTS")


def log(msg: str) -> None:
    print(f"[TTS] {msg}", flush=True)


def pick_reference_voice() -> str:
    """
    Pick one existing WAV file from voices/.
    Prefer your named samples, fall back to any *.wav.
    """
    base = pathlib.Path(VOICES_DIR)
    if not base.exists():
        raise SystemExit(f"[TTS] Voices directory not found: {VOICES_DIR}")

    candidates: List[pathlib.Path] = []

    # Prefer your known filenames
    for fname in DEFAULT_VOICES:
        f = base / fname
        if f.is_file():
            candidates.append(f)

    # Fallback: any .wav
    if not candidates:
        candidates = list(base.glob("*.wav"))

    if not candidates:
        raise SystemExit("[TTS] No .wav voice files found in voices/")

    choice = random.choice(candidates)
    log(f"Using reference voice: {choice}")
    return str(choice)


def read_script_text(path_override: Optional[str]) -> pathlib.Path:
    """
    Decide which script file to use and verify it's non-empty.
    Returns a pathlib.Path to the script.
    """
    if path_override:
        script_path = pathlib.Path(path_override)
    else:
        env_path = os.environ.get("TTS_SCRIPT_PATH", "script.txt")
        script_path = pathlib.Path(env_path)

    if not script_path.is_file():
        raise SystemExit(f"[TTS] Script file not found: {script_path}")

    text = script_path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"[TTS] Script file is empty: {script_path}")

    log(f"Loaded script from {script_path} ({len(text.split())} words)")
    return script_path


def call_f5_cli(
    ref_audio: str,
    script_file: pathlib.Path,
    output_dir: pathlib.Path,
) -> pathlib.Path:
    """
    Call the f5-tts_infer-cli tool with correct flags.

    Expected behavior:
    - Writes out.wav (or another .wav) in output_dir.
    - We return the final raw wav path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "f5-tts_infer-cli",
        "--model", F5_MODEL_NAME,
        "--ref_audio", ref_audio,
        "--ref_text", "",        # empty reference text; model handles it
        "--gen_file", str(script_file),
        "--remove_silence",      # IMPORTANT: flag only, no "true"
        "--output_dir", str(output_dir),
    ]

    log("Running F5-TTS CLI:")
    log(" ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        raise SystemExit(
            "[TTS] f5-tts_infer-cli not found.\n"
            "Make sure 'f5-tts' is installed in requirements.txt."
        )
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"[TTS] f5-tts_infer-cli failed with exit code {e.returncode}")

    # The CLI typically writes out.wav.
    out_wav = output_dir / "out.wav"
    if not out_wav.is_file():
        wavs = list(output_dir.glob("*.wav"))
        if not wavs:
            raise SystemExit(
                f"[TTS] No WAV produced by f5-tts_infer-cli in {output_dir}"
            )
        out_wav = wavs[0]

    log(f"F5-TTS raw output: {out_wav}")
    return out_wav


def normalize_and_save(
    src_wav: pathlib.Path,
    dst_wav: pathlib.Path,
    target_sr: int = 44100,
) -> None:
    """
    - Load the WAV
    - Convert to mono
    - Normalize using pydub's normalize()
    - Resample to target_sr
    - Export as WAV
    """
    audio = AudioSegment.from_file(src_wav)

    # mono
    audio = audio.set_channels(1)

    # normalize to a safe level (pydub normalize has some headroom internally)
    audio = effects.normalize(audio)

    # set sample rate + 16-bit sample width
    audio = audio.set_frame_rate(target_sr).set_sample_width(2)

    dst_wav.parent.mkdir(parents=True, exist_ok=True)
    audio.export(dst_wav, format="wav")
    log(f"Normalized and saved clean TTS: {dst_wav}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate cloned TTS narration with F5-TTS via CLI."
    )
    parser.add_argument(
        "--script-path",
        dest="script_path",
        default=None,
        help="Path to script file. Default: $TTS_SCRIPT_PATH or script.txt",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Output WAV filename. Default: $TTS_OUTPUT_PATH or tts.wav",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # 1) Script
    script_file = read_script_text(args.script_path)

    # 2) Reference voice
    ref_audio = pick_reference_voice()

    # 3) Temp directory for raw F5 output
    tmp_dir = pathlib.Path(tempfile.mkdtemp(prefix="f5_tts_out_"))

    # 4) Call F5 CLI
    raw_wav = call_f5_cli(ref_audio=ref_audio, script_file=script_file, output_dir=tmp_dir)

    # 5) Decide final output path
    out_path_str = (
        args.output
        or os.environ.get("TTS_OUTPUT_PATH")
        or "tts.wav"
    )
    out_path = pathlib.Path(out_path_str)

    # 6) Normalize + save
    normalize_and_save(raw_wav, out_path)

    log("TTS generation complete.")
    log(f"Final file: {out_path}")


if __name__ == "__main__":
    main()
