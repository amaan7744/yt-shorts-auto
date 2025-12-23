from pydub import AudioSegment
import re

AUDIO_FILE = "final_audio.wav"
SCRIPT_FILE = "script.txt"
OUT_FILE = "subs.ass"

audio = AudioSegment.from_wav(AUDIO_FILE)
duration = audio.duration_seconds

text = open(SCRIPT_FILE, encoding="utf-8").read().strip()

# Split into short, readable subtitle lines
sentences = re.split(r'(?<=[.!?])\s+', text)
sentences = [s.strip() for s in sentences if s.strip()]

per = duration / len(sentences)

def ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

lines = []

lines.append("[Script Info]")
lines.append("ScriptType: v4.00+")
lines.append("PlayResX: 1080")
lines.append("PlayResY: 1920")
lines.append("ScaledBorderAndShadow: yes")
lines.append("")

lines.append("[V4+ Styles]")
lines.append(
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
    "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
    "Alignment, MarginL, MarginR, MarginV, Encoding"
)
lines.append(
    "Style: Default,Arial,44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
    "0,0,0,0,100,100,0,0,1,2,1,2,40,40,120,1"
)
lines.append("")

lines.append("[Events]")
lines.append("Format: Layer, Start, End, Style, Text")

t = 0.0
for sentence in sentences:
    start = ass_time(t)
    end = ass_time(t + per)
    clean = sentence.replace("{", "").replace("}", "").replace("\n", " ")
    lines.append(f"Dialogue: 0,{start},{end},Default,{clean}")
    t += per

open(OUT_FILE, "w", encoding="utf-8").write("\n".join(lines))

print("[SUBS] Valid ASS subtitles written:", OUT_FILE)

