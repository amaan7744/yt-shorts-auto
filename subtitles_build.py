#!/usr/bin/env python3
"""
YouTube Shorts Subtitle Generator - FROM SCRIPT.TXT
Reads script.txt and generates subs.ass file
No Whisper. No ASR. Just direct script-to-subtitles.

Uses timing from case.json beats to create perfectly timed subtitles.
"""

import json
from pathlib import Path

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")
BEATS_FILE = Path("beats.json")
OUTPUT_FILE = Path("subs.ass")

# ==================================================
# VIDEO CONFIG
# ==================================================

PLAY_RES_X = 1440
PLAY_RES_Y = 2560

FONT_NAME = "Montserrat Black"
COLOR_WHITE = "&H00FFFFFF"
COLOR_YELLOW = "&H0000FFFF"
COLOR_OUTLINE = "&H20000000"
COLOR_SHADOW = "&H80000000"

OUTLINE = 6
SHADOW = 3

ALIGNMENT = 2
MARGIN_H = 80
HOOK_MARGIN_V = 500
STORY_MARGIN_V = 1600

# ==================================================
# EMPHASIS WORDS
# ==================================================

EMPHASIS_WORDS = {
    "murder", "murdered", "killing", "killed", "death", "died", "dying",
    "body", "bodies", "victim", "victims", "blood", "brutal", "violence",
    "crime", "scene", "investigation", "found", "discovered", "evidence",
    "missing", "disappeared", "vanished", "never", "nothing", "no one",
    "mysterious", "mystery", "suspicious", "strange", "unknown",
}

# ==================================================
# HELPERS
# ==================================================

def time_to_ass(seconds: float) -> str:
    """Convert seconds to ASS format: h:mm:ss.cc"""
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def has_emphasis(text: str) -> bool:
    """Check if text has emphasis words"""
    words = text.lower().split()
    for word in words:
        clean = word.strip(".,!?;:\"-'")
        if clean in EMPHASIS_WORDS:
            return True
    return False

def get_font_size(word_count: int) -> int:
    """Adaptive font size"""
    if word_count <= 1:
        return 100
    elif word_count == 2:
        return 92
    elif word_count == 3:
        return 84
    elif word_count == 4:
        return 78
    elif word_count == 5:
        return 72
    else:
        return 66

def split_into_chunks(text: str, max_words: int) -> list:
    """Split text into chunks"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
    return chunks

def get_optimal_chunk_size(duration: float) -> int:
    """Determine chunk size from duration"""
    if duration > 5:
        return 4
    elif duration > 3:
        return 3
    elif duration > 1.5:
        return 2
    else:
        return 1

# ==================================================
# ASS HEADER
# ==================================================

def create_header() -> str:
    return f"""[Script Info]
Title: YouTube Shorts Pro Subtitles
ScriptType: v4.00+
PlayResX: {PLAY_RES_X}
PlayResY: {PLAY_RES_Y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding

Style: Default,{FONT_NAME},84,{COLOR_WHITE},{COLOR_WHITE},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE},{SHADOW},{ALIGNMENT},{MARGIN_H},{MARGIN_H},{STORY_MARGIN_V},1

Style: Hook,{FONT_NAME},80,{COLOR_WHITE},{COLOR_WHITE},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE + 2},{SHADOW + 1},{ALIGNMENT},{MARGIN_H},{MARGIN_H},{HOOK_MARGIN_V},1

Style: Emphasis,{FONT_NAME},84,{COLOR_YELLOW},{COLOR_YELLOW},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE},{SHADOW},{ALIGNMENT},{MARGIN_H},{MARGIN_H},{STORY_MARGIN_V},1

Style: EmphasisHook,{FONT_NAME},80,{COLOR_YELLOW},{COLOR_YELLOW},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE + 2},{SHADOW + 1},{ALIGNMENT},{MARGIN_H},{MARGIN_H},{HOOK_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# ==================================================
# MAIN
# ==================================================

def main():
    print("=" * 70)
    print("🎬 SUBTITLE GENERATOR - FROM SCRIPT.TXT")
    print("=" * 70)
    print()
    
    # Load script
    if not SCRIPT_FILE.exists():
        print(f"❌ {SCRIPT_FILE} not found")
        print("   Run script.py first to generate script.txt")
        return
    
    script_lines = SCRIPT_FILE.read_text(encoding="utf-8").strip().split("\n")
    print(f"📄 Loaded {SCRIPT_FILE} ({len(script_lines)} lines)")
    
    # Load beats for timing (optional but recommended)
    beats = []
    if BEATS_FILE.exists():
        try:
            beats = json.loads(BEATS_FILE.read_text())["beats"]
            print(f"⏱️  Loaded timing from {BEATS_FILE} ({len(beats)} beats)")
        except:
            print(f"⚠️  Could not load {BEATS_FILE}, using auto-timing")
    
    # Generate subtitles
    print("📝 Generating subtitles...")
    
    dialogues = []
    current_time = 0.0
    
    # Estimate words per second (3 wps is standard)
    total_words = sum(len(line.split()) for line in script_lines)
    total_duration = total_words / 3
    
    # If we have beats, use them for timing
    if beats:
        time_idx = 0
        for line_idx, line in enumerate(script_lines):
            if not line.strip():
                continue
            
            # Get duration for this line
            if time_idx < len(beats):
                duration = float(beats[time_idx].get("duration", 3.0))
            else:
                # Estimate remaining time
                remaining_lines = len(script_lines) - line_idx
                remaining_time = max(total_duration - current_time, 3.0)
                duration = remaining_time / remaining_lines
            
            time_idx += 1
            
            # Determine if hook (first line is hook)
            is_hook = line_idx == 0
            
            # Split into chunks
            max_words = get_optimal_chunk_size(duration)
            chunks = split_into_chunks(line, max_words)
            
            if not chunks:
                chunks = [line]
            
            # Distribute duration across chunks
            chunk_duration = duration / len(chunks)
            
            # Create subtitles for each chunk
            for chunk in chunks:
                start = current_time
                end = start + chunk_duration
                
                # Styling
                has_emp = has_emphasis(chunk)
                style = "EmphasisHook" if (is_hook and has_emp) else ("Hook" if is_hook else ("Emphasis" if has_emp else "Default"))
                
                # Font size
                size = get_font_size(len(chunk.split()))
                
                # Create dialogue
                start_str = time_to_ass(start - 0.05)
                end_str = time_to_ass(end + 0.05)
                
                dialogue = f"Dialogue: 0,{start_str},{end_str},{style},,0,0,0,,{chunk}"
                dialogues.append(dialogue)
                
                current_time = end
    
    # If no beats, just use word-based timing
    else:
        words_per_second = 3.0
        
        for line_idx, line in enumerate(script_lines):
            if not line.strip():
                continue
            
            word_count = len(line.split())
            duration = word_count / words_per_second
            
            is_hook = line_idx == 0
            max_words = get_optimal_chunk_size(duration)
            chunks = split_into_chunks(line, max_words)
            
            if not chunks:
                chunks = [line]
            
            chunk_duration = duration / len(chunks)
            
            for chunk in chunks:
                start = current_time
                end = start + chunk_duration
                
                has_emp = has_emphasis(chunk)
                style = "EmphasisHook" if (is_hook and has_emp) else ("Hook" if is_hook else ("Emphasis" if has_emp else "Default"))
                
                size = get_font_size(len(chunk.split()))
                
                start_str = time_to_ass(start - 0.05)
                end_str = time_to_ass(end + 0.05)
                
                dialogue = f"Dialogue: 0,{start_str},{end_str},{style},,0,0,0,,{chunk}"
                dialogues.append(dialogue)
                
                current_time = end
    
    print(f"✅ Generated {len(dialogues)} subtitle lines")
    
    # Write ASS file
    print("💾 Writing ASS file...")
    
    ass_content = create_header()
    ass_content += "\n".join(dialogues)
    
    OUTPUT_FILE.write_text(ass_content, encoding="utf-8")
    print(f"✅ Written to {OUTPUT_FILE}")
    
    # Summary
    print()
    print("=" * 70)
    print("✅ SUBTITLES GENERATED")
    print("=" * 70)
    print()
    print("📊 STATISTICS:")
    print(f"   • Script lines: {len(script_lines)}")
    print(f"   • Subtitle lines: {len(dialogues)}")
    print(f"   • Total duration: ~{current_time:.1f} seconds")
    print()
    print("🎨 STYLING:")
    print(f"   • Font: {FONT_NAME}")
    print(f"   • Default: White with black shadow")
    print(f"   • Emphasis: Yellow with black shadow")
    print(f"   • Hook: Upper position ({HOOK_MARGIN_V}px)")
    print(f"   • Story: Lower position ({STORY_MARGIN_V}px)")
    print()
    print("📁 OUTPUT:")
    print(f"   • File: {OUTPUT_FILE}")
    print(f"   • Format: ASS v4.00+")
    print()
    print("📍 NEXT STEPS:")
    print("   1. Import subs.ass into DaVinci Resolve / Premiere Pro")
    print("   2. Adjust positioning if needed")
    print("   3. Export final video with subtitles")
    print()
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
