from pydub import AudioSegment
import re

AUDIO_FILE = "final_audio.wav"
SCRIPT_FILE = "script.txt"
OUT_FILE = "subs.ass"

# Load audio to get exact duration
audio = AudioSegment.from_wav(AUDIO_FILE)
total_duration = audio.duration_seconds

# Load and clean text
text = open(SCRIPT_FILE, encoding="utf-8").read().strip()
# Split by punctuation but keep the punctuation with the sentence
sentences = re.split(r'(?<=[.!?])\s+', text)
sentences = [s.strip() for s in sentences if s.strip()]

# Calculate total characters to determine timing weight
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
    # Improved Style: Larger font, Bold, Yellow Primary color for better visibility
    "Style: Default,Arial,65,&H0000FFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,2,2,40,40,250,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Text"
]

current_time = 0.0
for sentence in sentences:
    # Calculate duration based on how many characters are in this sentence
    char_count = len(sentence)
    # duration = (sentence_chars / total_chars) * total_audio_time
    sentence_duration = (char_count / total_chars) * total_duration
    
    start = ass_time(current_time)
    end = ass_time(current_time + sentence_duration)
    
    # Clean up text
    clean_text = sentence.replace("{", "").replace("}", "").replace("\n", " ")
    
    lines.append(f"Dialogue: 0,{start},{end},Default,{clean_text}")
    
    current_time += sentence_duration

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"[SUBS] Weighted subtitles written to {OUT_FILE}")
