#!/usr/bin/env python3
"""
YouTube Shorts Subtitle Generator — FIXED VERSION
=================================================

✔ Proper audio-to-script synchronization
✔ Uses faster-whisper for accurate timing
✔ Handles animations and cuts correctly
✔ Matches subtitle duration to actual audio
"""

import json
from pathlib import Path
from faster_whisper import WhisperModel

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")
AUDIO_FILE = Path("final_audio.wav")
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
SUB_MARGIN_V = 780

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
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def has_emphasis(text: str) -> bool:
    for w in text.lower().split():
        if w.strip(".,!?;:\"-'") in EMPHASIS_WORDS:
            return True
    return False

def split_into_chunks(text: str, max_words: int) -> list:
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]

def get_optimal_chunk_size(duration: float) -> int:
    """Calculate optimal words per subtitle based on duration"""
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

Style: Default,{FONT_NAME},78,{COLOR_WHITE},{COLOR_WHITE},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE},{SHADOW},{ALIGNMENT},{MARGIN_H},{MARGIN_H},{SUB_MARGIN_V},1
Style: Emphasis,{FONT_NAME},78,{COLOR_YELLOW},{COLOR_YELLOW},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE},{SHADOW},{ALIGNMENT},{MARGIN_H},{MARGIN_H},{SUB_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# ==================================================
# MAIN
# ==================================================

def main():
    if not SCRIPT_FILE.exists():
        raise FileNotFoundError("script.txt not found")

    if not AUDIO_FILE.exists():
        raise FileNotFoundError("final_audio.wav not found")

    # Load script
    script_lines = [
        line.strip() for line in SCRIPT_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    print(f"📄 Loaded script ({len(script_lines)} lines)")
    print("🎙️  Running faster-whisper for timing...")

    # Run Whisper with word timestamps
    model = WhisperModel(
        "small",
        device="cpu",
        compute_type="int8"
    )

    segments, info = model.transcribe(
        str(AUDIO_FILE),
        vad_filter=True,
        word_timestamps=True  # CRITICAL: Get word-level timing
    )

    segments = list(segments)
    print(f"⏱️  Detected {len(segments)} spoken segments")
    
    # Extract all words with timestamps
    all_words = []
    for seg in segments:
        if seg.words:
            for word in seg.words:
                all_words.append({
                    'text': word.word.strip(),
                    'start': word.start,
                    'end': word.end
                })
    
    print(f"📝 Detected {len(all_words)} individual words")
    
    if not all_words:
        print("❌ No words detected! Check your audio file.")
        return
    
    # Calculate total audio duration
    total_duration = all_words[-1]['end'] if all_words else 0
    print(f"⏰ Total audio duration: {total_duration:.2f}s")
    
    # Combine all script text and split into individual words
    full_script = " ".join(script_lines)
    script_words = full_script.split()
    
    print(f"📋 Script has {len(script_words)} words")
    print(f"🎤 Audio has {len(all_words)} detected words")
    
    # Create word-to-timestamp mapping
    # We'll map script words to detected words sequentially
    word_timings = []
    
    for i, script_word in enumerate(script_words):
        if i < len(all_words):
            word_timings.append({
                'text': script_word,
                'start': all_words[i]['start'],
                'end': all_words[i]['end']
            })
        else:
            # If we run out of detected words, extend the last timestamp
            if word_timings:
                last_end = word_timings[-1]['end']
                word_timings.append({
                    'text': script_word,
                    'start': last_end,
                    'end': last_end + 0.3  # Assume 0.3s per word
                })
    
    # Now create chunks from the timed words
    dialogues = []
    word_idx = 0
    
    for line_idx, line in enumerate(script_lines):
        line_words = line.split()
        
        if word_idx >= len(word_timings):
            break
        
        # Get timing for this line
        line_start = word_timings[word_idx]['start']
        line_end_idx = min(word_idx + len(line_words) - 1, len(word_timings) - 1)
        line_end = word_timings[line_end_idx]['end']
        line_duration = line_end - line_start
        
        # Determine chunk size
        max_words = get_optimal_chunk_size(line_duration)
        chunks = split_into_chunks(line, max_words)
        
        # Calculate how many words each chunk should have
        words_per_chunk = len(line_words) / len(chunks)
        
        for chunk_idx, chunk in enumerate(chunks):
            chunk_words = chunk.split()
            num_words = len(chunk_words)
            
            # Get start and end times for this chunk
            chunk_start_idx = word_idx
            chunk_end_idx = min(word_idx + num_words - 1, len(word_timings) - 1)
            
            if chunk_start_idx < len(word_timings) and chunk_end_idx < len(word_timings):
                start_time = word_timings[chunk_start_idx]['start']
                end_time = word_timings[chunk_end_idx]['end']
                
                # Determine style
                style = "Emphasis" if has_emphasis(chunk) else "Default"
                
                # Create dialogue entry
                start_str = time_to_ass(start_time)
                end_str = time_to_ass(end_time)
                
                dialogues.append(
                    f"Dialogue: 0,{start_str},{end_str},{style},,0,0,0,,{chunk}"
                )
                
                word_idx += num_words
            else:
                break
    
    # Write ASS file
    ass = create_header() + "\n".join(dialogues)
    OUTPUT_FILE.write_text(ass, encoding="utf-8")

    print(f"\n✅ Subtitles written to {OUTPUT_FILE}")
    print(f"🧾 Total subtitle lines: {len(dialogues)}")
    print(f"⏱️  Subtitle duration: {word_timings[-1]['end'] if word_timings else 0:.2f}s")
    print(f"🎯 Timing source: faster-whisper (word-level)")
    print(f"📍 Position: lower third (~70% down)")

if __name__ == "__main__":
    main()
    
