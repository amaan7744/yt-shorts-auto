#!/usr/bin/env python3
"""
Speech Mapper — SCRIPT ↔ AUDIO LOCK
==================================

Uses faster-whisper to extract speech timestamps
and aligns them to script lines in order.

OUTPUT:
speech_map.json
"""

import json
from pathlib import Path
from faster_whisper import WhisperModel

SCRIPT_FILE = Path("script.txt")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT_FILE = Path("speech_map.json")

MODEL_SIZE = "medium"  # change to "small" if CPU is weak

if not SCRIPT_FILE.exists():
    raise RuntimeError("script.txt missing")
if not AUDIO_FILE.exists():
    raise RuntimeError("final_audio.wav missing")

script_lines = [l.strip() for l in SCRIPT_FILE.read_text().splitlines() if l.strip()]
if len(script_lines) != 7:
    raise RuntimeError("script must be exactly 7 lines")

print("🎙 Loading Whisper model...")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

print("🎧 Transcribing audio...")
segments, _ = model.transcribe(
    str(AUDIO_FILE),
    word_timestamps=False,
    vad_filter=True
)

# Collect spoken segments
spoken = [(seg.start, seg.end, seg.text.strip()) for seg in segments]

if not spoken:
    raise RuntimeError("No speech detected")

# Align segments sequentially to script lines
speech_map = []
seg_idx = 0

for i, line in enumerate(script_lines, start=1):
    start = spoken[seg_idx][0]
    end = spoken[seg_idx][1]

    # absorb segments until sentence feels complete
    while seg_idx + 1 < len(spoken) and len(spoken[seg_idx][2]) < len(line):
        seg_idx += 1
        end = spoken[seg_idx][1]

    speech_map.append({
        "line": i,
        "start": round(start, 3),
        "end": round(end, 3),
        "duration": round(end - start, 3),
        "text": line
    })

    seg_idx += 1

OUTPUT_FILE.write_text(json.dumps(speech_map, indent=2))

print("✅ speech_map.json generated")
for m in speech_map:
    print(f"Line {m['line']}: {m['duration']:.2f}s")
