import whisper
from datetime import timedelta

AUDIO_FILE = "final_audio.wav"
OUT_FILE = "subs.ass"

def format_ass_time(seconds):
    """Converts seconds to ASS format (H:MM:SS.cc)"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = td.total_seconds() % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"

def build_subs():
    # 1. Load the model (base is fast and accurate enough for English)
    print("[1/3] Loading Whisper model...")
    model = whisper.load_model("base")

    # 2. Transcribe with word-level timestamps
    print("[2/3] Transcribing audio (this may take a moment)...")
    result = model.transcribe(AUDIO_FILE, verbose=False, word_timestamps=True)

    # 3. Create the ASS Header
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

    # 4. Group segments into lines
    print("[3/3] Building subtitle events...")
    for segment in result['segments']:
        start = format_ass_time(segment['start'])
        end = format_ass_time(segment['end'])
        text = segment['text'].strip()
        
        subs.append(f"Dialogue: 0,{start},{end},Default,{text}")

    # Write to file
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(subs))

    print(f"\n[DONE] Precise subtitles saved to {OUT_FILE}")

if __name__ == "__main__":
    build_subs()
