#!/usr/bin/env python3
"""
TikTok / Brain-Rot Kinetic Subtitles
3–4 words per frame
Green = currently read
White = not yet read
"""

import whisper
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict

# ==================================================
# CONFIG
# ==================================================

@dataclass
class Config:
    AUDIO_FILE: str = "final_audio.wav"
    OUTPUT_FILE: str = "subs.ass"

    FONT_NAME: str = "Montserrat Bold"
    FONT_SIZE: int = 64

    # ASS colors (AABBGGRR)
    COLOR_ACTIVE: str = "&H0000FF00"   # GREEN (current word)
    COLOR_INACTIVE: str = "&H00FFFFFF" # WHITE (not read)
    COLOR_OUTLINE: str = "&H00000000"
    COLOR_SHADOW: str = "&H64000000"

    PLAY_RES_X: int = 1080
    PLAY_RES_Y: int = 1920

    # Position: above gameplay (brain-rot safe)
    MARGIN_V: int = 720
    MARGIN_H: int = 60
    ALIGNMENT: int = 8  # top center

    OUTLINE: int = 3
    SHADOW: int = 2

    WORDS_PER_LINE: int = 4
    WHISPER_MODEL: str = "small"

# ==================================================
# TIME
# ==================================================

def ass_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int((t % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

# ==================================================
# ASS HEADER
# ==================================================

def ass_header(cfg: Config) -> List[str]:
    return [
        "[Script Info]",
        "Title: Brain-Rot Kinetic Subtitles",
        "ScriptType: v4.00+",
        f"PlayResX: {cfg.PLAY_RES_X}",
        f"PlayResY: {cfg.PLAY_RES_Y}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,"
        " OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut,"
        " ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow,"
        " Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{cfg.FONT_NAME},{cfg.FONT_SIZE},"
        f"{cfg.COLOR_ACTIVE},{cfg.COLOR_INACTIVE},{cfg.COLOR_OUTLINE},"
        f"{cfg.COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,"
        f"{cfg.OUTLINE},{cfg.SHADOW},{cfg.ALIGNMENT},"
        f"{cfg.MARGIN_H},{cfg.MARGIN_H},{cfg.MARGIN_V},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

# ==================================================
# SUBTITLE LINE CREATION
# ==================================================

def build_karaoke(words: List[Dict]) -> str:
    parts = []
    for w in words:
        dur = max(1, int((w["end"] - w["start"]) * 100))
        text = w["word"].strip().upper()
        parts.append(f"{{\\k{dur}}}{text}")
    return " ".join(parts)

def chunk_words(words: List[Dict], n: int) -> List[List[Dict]]:
    return [words[i:i + n] for i in range(0, len(words), n)]

# ==================================================
# MAIN
# ==================================================

def main():
    cfg = Config()

    audio = Path(cfg.AUDIO_FILE)
    if not audio.exists():
        raise FileNotFoundError(cfg.AUDIO_FILE)

    print("[SUBS] Loading Whisper…")
    model = whisper.load_model(cfg.WHISPER_MODEL)

    print("[SUBS] Transcribing…")
    result = model.transcribe(
        str(audio),
        word_timestamps=True,
        language="en",
        verbose=False,
    )

    subs = ass_header(cfg)
    lines = 0

    for seg in result["segments"]:
        if not seg.get("words"):
            continue

        chunks = chunk_words(seg["words"], cfg.WORDS_PER_LINE)

        for chunk in chunks:
            start = chunk[0]["start"]
            end = chunk[-1]["end"]
            text = build_karaoke(chunk)

            subs.append(
                f"Dialogue: 0,{ass_time(start)},{ass_time(end)},"
                f"Default,,0,0,0,,{text}"
            )
            lines += 1

    with open(cfg.OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(subs))

    print(f"[SUBS] ✅ Generated {lines} kinetic subtitle lines")

if __name__ == "__main__":
    main()
