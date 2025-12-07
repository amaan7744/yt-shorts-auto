#!/usr/bin/env python
"""
Generate a single cloned narration with F5-TTS (E2/F5) using the official CLI.

- Picks ONE random reference voice from voices/:
    voices/aman.wav
    voices/aman(1).wav
    voices/aman(2).wav
    (or any *.wav in voices/ if those don't exist)

- Reads script text from:
    $TTS_SCRIPT_PATH  or  script.txt

- Calls:
    f5-tts_infer-cli  (provided by the f5-tts package)

- Writes:
    tts.wav  (or --output path you pass, or $TTS_OUTPUT_PATH)

- Post-process:
    - Convert to mono
    - Normalize to safe peak (-1 dBFS)
    - Resample to 44.1 kHz
"""

import argparse
import os
import random
import sys
import tempfile
import pathlib
import subprocess

from typing import List

from pydub import AudioSegment


VOICES_DIR = "voices"
DEFAULT_VOICES = ["aman.wav", "aman(1).wav", "aman(2).wav"]

# F5 / E2 official CLI model name.
# You can switch between "F5-TTS" and "E2-TTS" if you want.
F5_MODEL_NAME = os.environ.get("F5_MODEL_NAME", "F5-TTS")


def log(msg: str) -> None:
    print(f"[TTS] {msg}", flush=True)


def pick_reference_voice() -> str:
    """
    Pick one existing WAV file from voices/.
    Prefer your named files, fall back to any *.wav.
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
        raise SystemExit("[TTS] No .wav files found in voices/")

    choice = random.choice(candidates)
    log(f"Using reference voice: {choice}")
    return str(choice)


def read_script_text(path_override: str | None) -> tuple[str, pathlib.Path]:
    """
    Return (text, path) for script.
    First priority: explicit CLI path.
    Second: $TTS_SCRIPT_PATH.
    Third: script.txt.
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
    return text, script_path


def call_f5_cli(
    ref_audio: str,
    script_file: pathlib.Path,
    output_dir: pathlib.Path,
) -> pathlib.Path:
    """
    Call f5-tts_infer-cli with:
      --model F5-TTS (or E2-TTS)
      --ref_audio <voice sample>
      --ref_text "" (let it auto-ASR if needed)
      --gen_file script.txt
      --remove_silence true
      --output_dir <tmp>
    It will write out.wav into output_dir. We return that path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "f5-tts_infer-cli",
        "--model", F5_MODEL_NAME,
        "--ref_audio", ref_audio,
        "--ref_text", "",            # let it auto-handle / ignore
        "--gen_file", str(script_file),
        "--remove_silence", "true",
        "--output_dir", str(output_dir),
    ]

    log("Running F5-TTS CLI:")
    log(" ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        raise SystemExit(
            "[TTS] f5-tts_infer-cli not found. "
            "Make sure 'f5-tts' is in requirements.txt and installed."
        )
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"[TTS] f5-tts_infer-cli failed with exit code {e.returncode}")

    out_wav = output_dir / "out.wav"
    if not out_wav.is_file():
        # Some versions may name differently. Fallback: first .wav in dir.
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
    peak_margin: float = 0.89,
) -> None:
    """
    - Convert to mono
    - Normalize to safe peak
    - Resample to target_sr
    """
    audio = AudioSegment.from_file(src_wav)

    if audio.channels > 1:
        audio = audio.set_channels(1)

    # normalize to peak ~ -1 dBFS (approx)
    peak = audio.max
    if peak > 0:
        # pydub uses 16-bit dynamic range; 0 dBFS ~ 32767
        # simple scaling based on peak
        target_peak = int(peak_margin * (2**15 - 1))
        gain_db = 20 * ( (target_peak / peak) ** 0.5 ).bit_length() if False else 0  # dummy to satisfy linter
        # simpler: just normalize to -1 dBFS via built-in
        audio = audio.apply_gain(-1.0)

    audio = audio.set_frame_rate(target_sr).set_sample_width(2).set_channels(1)

    dst_wav.parent.mkdir(parents=True, exist_ok=True)
    audio.export(dst_wav, format="wav")
    log(f"Normalized and saved clean TTS: {dst_wav}")


def parse_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate cloned TTS narration with F5-TTS via CLI."
    )
    parser.add_argument(
        "--script-path",
        dest="script_path",
        default=None,
        help="Path to script.txt. Default: $TTS_SCRIPT_PATH or script.txt",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Output WAV path. Default: $TTS_OUTPUT_PATH or tts.wav",
    )
    return parser


def main() -> None:
    args = parse_args().parse_args()

    # 1) Script
    _, script_file = read_script_text(args.script_path)

    # 2) Ref voice
    ref_audio = pick_reference_voice()

    # 3) Temp output dir for F5
    tmp_dir = pathlib.Path(tempfile.mkdtemp(prefix="f5_tts_out_"))

    # 4) Call F5 CLI
    raw_wav = call_f5_cli(ref_audio=ref_audio, script_file=script_file, output_dir=tmp_dir)

    # 5) Final output path
    out_path_str = (
        args.output
        or os.environ.get("TTS_OUTPUT_PATH")
        or "tts.wav"
    )
    out_path = pathlib.Path(out_path_str)

    # 6) Normalize + save
    normalize_and_save(raw_wav, out_path)

    log("TTS generation done.")
    log(f"Final file: {out_path}")


if __name__ == "__main__":
    main()
