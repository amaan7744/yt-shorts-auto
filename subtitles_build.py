#!/usr/bin/env python3
"""
YouTube Shorts – Premium True Crime Subtitles
• BIG white text
• Thick black outline
• Strong shadow (compression-proof)
• Subtle motion pop
• Stronger hook animation (first ~2s)
• 3–4 words per line
• Lower-middle placement (~70% down)
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

    # FONT (compression-safe)
    FONT_NAME: str = "Arial Black"
    FONT_SIZE: int = 84

    # ASS colors (AABBGGRR)
    COLOR_TEXT: str = "&H00FFFFFF"     # White
    COLOR_OUTLINE: str = "&H00000000"  # Black
    COLOR_SHADOW: str = "&H64000000"   # Dark shadow

    PLAY_RES_X: int = 1080
    PLAY_RES_Y: int = 1920

    # Placement: lower-middle (≈70% down)
    ALIGNMENT: int = 8  # center
    MARGIN_H: int = 80
    MARGIN_V: int = 1350

    # Thickness (VERY IMPORTANT)
    OUTLINE: int = 6
    SHADOW: int = 3

    WORDS_PER_LINE: int = 4  # change to 3 if you want more aggressive pacing
    WHISPER_MODEL: str = "small"

# ==================================================
# TIME FORMAT
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
        "Title: YouTube Shorts True Crime Subtitles",
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
        f"{cfg.COLOR_TEXT},{cfg.COLOR_TEXT},{cfg.COLOR_OUTLINE},"
        f"{cfg.COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,"
        f"{cfg.OUTLINE},{cfg.SHADOW},{cfg.ALIGNMENT},"
        f"{cfg.MARGIN_H},{cfg.MARGIN_H},{cfg.MARGIN_V},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

# ==================================================
# MOTION TRANSFORMS
# ==================================================

def hook_transform() -> str:
    """
    Stronger pop for hook (first ~2 seconds)
    """
    return (
        r"{\an8\pos(540,1350)\fscx85\fscy85"
        r"\t(0,140,\fscx105\fscy105)"
        r"\t(140,260,\fscx100\fscy100)}"
    )

def normal_transform() -> str:
    """
    Subtle pop for rest of video
    """
    return (
        r"{\an8\pos(540,1350)\fscx92\fscy92"
        r"\t(0,120,\fscx100\fscy100)}"
    )

# ==================================================
# WORD CHUNKING
# ==================================================

def chunk_words(words: List[Dict], n: int) -> List[List[Dict]]:
    return [words[i:i + n] for i in range(0, len(words), n)]

def chunk_text(words: List[Dict]) -> str:
    return " ".join(w["word"].strip().upper() for w in words)

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
            text = chunk_text(chunk)

            # Hook = first ~2 seconds
            motion = hook_transform() if start < 2.2 else normal_transform()

            subs.append(
                f"Dialogue: 0,{ass_time(start)},{ass_time(end)},"
                f"Default,,0,0,0,,{motion}{text}"
            )
            lines += 1

    Path(cfg.OUTPUT_FILE).write_text("\n".join(subs), encoding="utf-8")
    print(f"[SUBS] ✅ Generated {lines} subtitle lines")

if __name__ == "__main__":
    main()
