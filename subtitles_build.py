#!/usr/bin/env python3

import whisper
import os

AUDIO = "final_audio.wav"
OUT = "subs.ass"

# --------------------------------------------------
# STYLE CONFIG (BRAIN-ROT / TIKTOK)
# --------------------------------------------------

FONT = "Montserrat Bold"
FONT_SIZE = 66

WHITE = "&H00FFFFFF"
GREEN = "&H0000FF00"
OUTLINE = "&H00000000"
BACK = "&H64000000"

# Vertical placement: just above gameplay
# PlayResY = 1920 → ~58%
MARGIN_V = 720

# --------------------------------------------------
# TIME UTILS
# --------------------------------------------------

def ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

# --------------------------------------------------
# ASS HEADER
# --------------------------------------------------

def ass_header():
    return [
        "[Script Info]",
        "Title: TikTok Style Word Highlight Subs",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{FONT},{FONT_SIZE},{WHITE},{GREEN},{OUTLINE},{BACK},-1,0,0,0,100,100,0,0,1,3,2,8,60,60,{MARGIN_V},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    print("[SUBS] Loading Whisper model…")
    model = whisper.load_model("small")

    print("[SUBS] Transcribing with word timestamps…")
    result = model.transcribe(
        AUDIO,
        word_timestamps=True,
        language="en",
        verbose=False,
    )

    subs = ass_header()

    for seg in result["segments"]:
        if not seg.get("words"):
            continue

        words = seg["words"]

        start = words[0]["start"]
        end = words[-1]["end"]

        ass_words = []

        for w in words:
            dur_cs = max(1, int((w["end"] - w["start"]) * 100))
            text = w["word"].strip().upper()

            # Karaoke: word turns GREEN while active
            ass_words.append(f"{{\\k{dur_cs}}}{text}")

        line = " ".join(ass_words)

        subs.append(
            f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{line}"
        )

    print(f"[SUBS] Writing {OUT}")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(subs))

    print("[SUBS] ✅ TikTok-style kinetic subtitles generated")

if __name__ == "__main__":
    main()
