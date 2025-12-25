from pydub import AudioSegment
import re

AUDIO_FILE = "final_audio.wav"
SCRIPT_FILE = "script.txt"
OUT_FILE = "subs.ass"

audio = AudioSegment.from_wav(AUDIO_FILE)
total_duration = audio.duration_seconds
text = open(SCRIPT_FILE, encoding="utf-8").read().strip()

sentences = re.split(r'(?<=[.!?])\s+', text)
sentences = [s.strip() for s in sentences if s.strip()]
total_chars = sum(len(s) for s in sentences)

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
    # MOVIE STYLE: White text, thin black outline, slight shadow, centered at bottom
    "Style: Default,Arial,55,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1.5,1,2,60,60,100,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Text"
]

current_time = 0.0
for sentence in sentences:
    char_count = len(sentence)
    sentence_duration = (char_count / total_chars) * total_duration
    
    start = ass_time(current_time)
    end = ass_time(current_time + sentence_duration)
    
    # Clean text and remove any leading/trailing spaces
    clean_text = sentence.strip().replace("{", "").replace("}", "").replace("\n", " ")
    
    lines.append(f"Dialogue: 0,{start},{end},Default,{clean_text}")
    current_time += sentence_duration

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"[SUBS] Movie-style white subtitles written to {OUT_FILE}")
