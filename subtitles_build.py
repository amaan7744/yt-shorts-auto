#!/usr/bin/env python3
"""
subtitles_build.py — SLOW, READABLE, AUDIO-MATCHED
"""

from pydub import AudioSegment
import re

AUDIO_FILE = "final_audio.wav"
SCRIPT_FILE = "script.txt"
OUT_FILE = "subs.ass"

MIN_DURATION = 0.7
MAX_DURATION = 1.3
WORDS_PER_LINE = 5

audio = AudioSegment.from_wav(AUDIO_FILE)
total_duration = audio.duration_seconds

text = open(SCRIPT_FILE, encoding="utf-8").read().strip()
text = re.sub(r"[{}]", "", text)
words = text.split()

lines_words = [
    words[i:i + WORDS_PER_LINE]
    for i in range(0, len(words), WORDS_PER_LINE)
]

def ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

subs = [
    "[Script Info]",
    "ScriptType: v4.00+",
    "PlayResX: 1080",
    "PlayResY: 1920",
    "ScaledBorderAndShadow: yes",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    "Style: Default,Arial,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,0.6,2.2,2,80,80,240,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Text"
]

current = 0.0
per_line = total_duration / len(lines_words)

for group in lines_words:
    dur = max(MIN_DURATION, min(per_line, MAX_DURATION))
    start = ass_time(current)
    end = ass_time(min(current + dur, total_duration))
    subs.append(f"Dialogue: 0,{start},{end},Default,{' '.join(group)}")
    current += dur

# Hard lock end
subs[-1] = subs[-1].rsplit(",", 1)[0] + f",{ass_time(total_duration)}"

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(subs))

print("[SUBS] Slow, readable subtitles generated.")
