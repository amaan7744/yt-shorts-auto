#!/usr/bin/env python3
import re
from pydub import AudioSegment

def format_time(ms):
    s = ms//1000
    cs = (ms%1000)//10
    m = s//60
    s = s%60
    return f"0:{m:02d}:{s:02d}.{cs:02d}"

def main():
    script = open("script.txt","r",encoding="utf-8").read().strip()
    audio = AudioSegment.from_wav("final_audio.wav")
    total = len(audio)

    sentences = [s.strip() for s in re.split(r"[.!?]\s+", script) if s.strip()]
    chunk = total // len(sentences)

    lines = []
    cur = 0
    for s in sentences:
        start = format_time(cur)
        end   = format_time(min(cur+chunk, total-100))
        cur += chunk
        lines.append((start,end,s))

    out = []
    out.append("[Script Info]")
    out.append("PlayResX:1080")
    out.append("PlayResY:1920")
    out.append("")
    out.append("[V4+ Styles]")
    out.append("Style: sub,Arial,46,&H00FFFFFF,&H00000000,&H00101010,&H32000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,80,1")
    out.append("")
    out.append("[Events]")
    out.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    for st,en,txt in lines:
        out.append(f"Dialogue: 0,{st},{en},sub,,0,0,0,,{txt}")

    open("subtitles.ass","w",encoding="utf-8").write("\n".join(out))
    print("[SUBS] subtitles.ass created.")

if __name__ == "__main__":
    main()

