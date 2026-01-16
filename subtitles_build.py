#!/usr/bin/env python3
"""
TikTok-Style Kinetic Subtitle Generator
Generates brain-rot style word-by-word highlighted subtitles using Whisper AI
"""

import whisper
import os
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Config:
    """Subtitle generation configuration"""
    # Files
    AUDIO_FILE: str = "final_audio.wav"
    OUTPUT_FILE: str = "subs.ass"
    
    # Style - Brain-rot/TikTok aesthetic
    FONT_NAME: str = "Montserrat Bold"
    FONT_SIZE: int = 66
    
    # Colors (ASS format: &HAABBGGRR)
    COLOR_DEFAULT: str = "&H00FFFFFF"  # White
    COLOR_HIGHLIGHT: str = "&H0000FF00"  # Green
    COLOR_OUTLINE: str = "&H00000000"  # Black
    COLOR_SHADOW: str = "&H64000000"  # Semi-transparent black
    
    # Layout (for 1080x1920 vertical video)
    PLAY_RES_X: int = 1080
    PLAY_RES_Y: int = 1920
    MARGIN_VERTICAL: int = 720  # ~58% from top (above gameplay)
    MARGIN_HORIZONTAL: int = 60
    
    # Style settings
    OUTLINE_WIDTH: int = 3
    SHADOW_DEPTH: int = 2
    ALIGNMENT: int = 8  # Top center
    
    # Whisper model
    WHISPER_MODEL: str = "small"


# ═══════════════════════════════════════════════════════════════════
# TIME FORMATTING
# ═══════════════════════════════════════════════════════════════════

def format_ass_timestamp(seconds: float) -> str:
    """
    Convert seconds to ASS timestamp format (H:MM:SS.CS)
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


# ═══════════════════════════════════════════════════════════════════
# ASS FILE GENERATION
# ═══════════════════════════════════════════════════════════════════

def generate_ass_header(cfg: Config) -> List[str]:
    """
    Generate ASS subtitle file header with style definitions
    
    Args:
        cfg: Configuration object
        
    Returns:
        List of header lines
    """
    return [
        "[Script Info]",
        "Title: TikTok Style Word Highlight Subtitles",
        "ScriptType: v4.00+",
        f"PlayResX: {cfg.PLAY_RES_X}",
        f"PlayResY: {cfg.PLAY_RES_Y}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{cfg.FONT_NAME},{cfg.FONT_SIZE},"
        f"{cfg.COLOR_DEFAULT},{cfg.COLOR_HIGHLIGHT},{cfg.COLOR_OUTLINE},"
        f"{cfg.COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{cfg.OUTLINE_WIDTH},"
        f"{cfg.SHADOW_DEPTH},{cfg.ALIGNMENT},{cfg.MARGIN_HORIZONTAL},"
        f"{cfg.MARGIN_HORIZONTAL},{cfg.MARGIN_VERTICAL},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]


def create_karaoke_line(words: List[Dict], cfg: Config) -> str:
    """
    Create a karaoke-style subtitle line with word-by-word highlighting
    
    Args:
        words: List of word dictionaries with 'word', 'start', 'end' keys
        cfg: Configuration object
        
    Returns:
        ASS-formatted karaoke line
    """
    karaoke_segments = []
    
    for word in words:
        # Calculate duration in centiseconds (minimum 1cs)
        duration_cs = max(1, int((word["end"] - word["start"]) * 100))
        
        # Clean and format word text
        text = word["word"].strip().upper()
        
        # Add karaoke tag: {\kDURATION}WORD
        # This makes the word turn green when active
        karaoke_segments.append(f"{{\\k{duration_cs}}}{text}")
    
    return " ".join(karaoke_segments)


# ═══════════════════════════════════════════════════════════════════
# MAIN PROCESSING
# ═══════════════════════════════════════════════════════════════════

def generate_subtitles(cfg: Config) -> None:
    """
    Main subtitle generation pipeline
    
    Args:
        cfg: Configuration object
    """
    # Validate input file
    audio_path = Path(cfg.AUDIO_FILE)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {cfg.AUDIO_FILE}")
    
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║       TikTok-Style Subtitle Generator v2.0               ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")
    
    # Load Whisper model
    print(f"📥 Loading Whisper '{cfg.WHISPER_MODEL}' model...")
    model = whisper.load_model(cfg.WHISPER_MODEL)
    print("✓ Model loaded successfully\n")
    
    # Transcribe with word-level timestamps
    print(f"🎙️  Transcribing audio: {cfg.AUDIO_FILE}")
    print("   (This may take a few minutes...)")
    
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        language="en",
        verbose=False,
    )
    
    total_segments = len(result["segments"])
    print(f"✓ Transcription complete: {total_segments} segments detected\n")
    
    # Generate ASS subtitle file
    print("🎬 Generating kinetic subtitles...")
    
    subtitle_lines = generate_ass_header(cfg)
    processed_segments = 0
    
    for segment in result["segments"]:
        # Skip segments without word timestamps
        if not segment.get("words"):
            continue
        
        words = segment["words"]
        start_time = words[0]["start"]
        end_time = words[-1]["end"]
        
        # Create karaoke-style line
        karaoke_text = create_karaoke_line(words, cfg)
        
        # Add dialogue line to subtitle file
        subtitle_lines.append(
            f"Dialogue: 0,{format_ass_timestamp(start_time)},"
            f"{format_ass_timestamp(end_time)},Default,,0,0,0,,{karaoke_text}"
        )
        
        processed_segments += 1
    
    print(f"✓ Processed {processed_segments} subtitle segments\n")
    
    # Write output file
    print(f"💾 Writing subtitle file: {cfg.OUTPUT_FILE}")
    
    output_path = Path(cfg.OUTPUT_FILE)
    with output_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(subtitle_lines))
    
    file_size = output_path.stat().st_size
    print(f"✓ File written: {file_size:,} bytes\n")
    
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  ✅ TikTok-style kinetic subtitles generated successfully ║")
    print("╚═══════════════════════════════════════════════════════════╝")


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def main():
    """Application entry point"""
    try:
        config = Config()
        generate_subtitles(config)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
