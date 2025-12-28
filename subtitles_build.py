#!/usr/bin/env python3
"""
subtitles_build.py — YouTube Shorts optimized ASS subtitles

Features:
- Word-group based timing (better retention)
- White text with soft black shadow
- Shorts-safe positioning (no UI clash)
- Clean, readable, professional
"""

from pydub import AudioSegment
import re
import math

AUDIO_FILE = "final_audio.wav"
SCRIPT_FILE = "script.txt"
OUT_FILE = "subs.ass"

# ---------------- CONFIG ----------------
WORDS_PER_GROUP = 3          # 2–4 is ideal
MIN_DURATION = 0.35          # seconds
MAX_DURATION = 0.9           # seconds
# --------------------------------------


audio = AudioSegment.from_wav(AUDIO_FILE)
total_duration = audio.duration_seconds

text = open(SCRIPT_FILE, encoding="utf-8").read().strip()

# Clean text
text = re.sub(r"[{}]", "", text)
words = text.split()

# Group words
groups = [
    words[i:i + WORDS_PER_GROUP]
    for i in range(0, len(words), WORDS_PER_GROUP)
]

total_groups = len(groups)
group_duration = total_duration / total_groups


def ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


lines = [
    "[Script Info]",
    "ScriptType: v4.00+",
    "PlayResX: 1080",
    "PlayResY: 1920",
    "ScaledBorderAndShadow: yes",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    # Shorts-optimized style: white text, soft black shadow, centered lower-middle
    "Style: Default,Arial,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,0.8,2.5,2,80,80,220,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Text"
]

current_time = 0.0

for group in groups:
    dur = max(MIN_DURATION, min(group_duration, MAX_DURATION))
    start = ass_time(current_time)
    end = ass_time(min(current_time + dur, total_duration))

    text_line = " ".join(group)
    lines.append(f"Dialogue: 0,{start},{end},Default,{text_line}")

    current_time += dur

# Hard lock end time
if current_time < total_duration:
    lines[-1] = lines[-1].rsplit(",", 1)[0] + f",{ass_time(total_duration)}"

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"[SUBS] Shorts-optimized subtitles written to {OUT_FILE}")
