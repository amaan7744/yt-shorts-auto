#!/usr/bin/env python3
import whisper
import json
from datetime import timedelta

AUDIO = "final_audio.wav"
BEATS_FILE = "beats.json"
OUT = "subs.ass"

# Enhanced styling for YouTube Shorts
STYLES = {
    "default": {
        "fontname": "Montserrat Bold",
        "fontsize": 72,
        "primary_color": "&H00FFFFFF",  # White
        "outline_color": "&H00000000",  # Black outline
        "back_color": "&H80000000",     # Semi-transparent black shadow
        "bold": -1,
        "outline": 4,
        "shadow": 3,
        "alignment": 2,  # Bottom center
        "margin_v": 180
    },
    "cta": {
        "fontname": "Montserrat Black",
        "fontsize": 88,
        "primary_color": "&H0000FFFF",  # Yellow (attention)
        "outline_color": "&H00000000",
        "back_color": "&H80000000",
        "bold": -1,
        "outline": 5,
        "shadow": 4,
        "alignment": 2,
        "margin_v": 160
    }
}

def format_time(seconds):
    """Convert seconds to ASS timestamp format (H:MM:SS.CC)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

def create_ass_header():
    """Generate ASS subtitle header with enhanced styles"""
    header = [
        "[Script Info]",
        "Title: YouTube Shorts Subtitles",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
    ]
    
    # Add default style
    s = STYLES["default"]
    header.append(
        f"Style: Default,{s['fontname']},{s['fontsize']},{s['primary_color']},&H000000FF,"
        f"{s['outline_color']},{s['back_color']},{s['bold']},0,0,0,100,100,0,0,1,"
        f"{s['outline']},{s['shadow']},{s['alignment']},50,50,{s['margin_v']},1"
    )
    
    # Add CTA style
    s = STYLES["cta"]
    header.append(
        f"Style: CTA,{s['fontname']},{s['fontsize']},{s['primary_color']},&H000000FF,"
        f"{s['outline_color']},{s['back_color']},{s['bold']},0,0,0,100,100,0,0,1,"
        f"{s['outline']},{s['shadow']},{s['alignment']},50,50,{s['margin_v']},1"
    )
    
    header.extend([
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ])
    
    return header

def get_word_chunks(words_data, max_words=3):
    """Split words into chunks with precise timing"""
    chunks = []
    current_chunk = []
    
    for word_info in words_data:
        current_chunk.append(word_info)
        
        if len(current_chunk) >= max_words:
            chunks.append(current_chunk)
            current_chunk = []
    
    # Add remaining words
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def determine_style(timestamp, beats):
    """Determine which style to use based on beat intent"""
    for beat in beats:
        if "timestamp" in beat:
            if abs(timestamp - beat["timestamp"]) < 1.5:  # Within 1.5s of beat
                if beat.get("intent") == "attention":
                    return "CTA"
    return "Default"

def clean_text(text):
    """Clean and format text for subtitles"""
    # Remove extra spaces and format
    text = " ".join(text.split())
    # Capitalize properly for subtitles
    return text.upper()

def main():
    print("Loading Whisper model...")
    model = whisper.load_model("medium")  # Medium for better accuracy
    
    print(f"Transcribing audio: {AUDIO}")
    result = model.transcribe(
        AUDIO,
        word_timestamps=True,
        language="en",
        task="transcribe",
        verbose=False
    )
    
    print("Loading beats data...")
    try:
        beats = json.load(open(BEATS_FILE))
    except FileNotFoundError:
        print(f"Warning: {BEATS_FILE} not found, using default styling")
        beats = []
    
    print("Generating subtitles...")
    subtitles = create_ass_header()
    
    for segment in result["segments"]:
        # Get word-level timestamps if available
        if "words" in segment and segment["words"]:
            words_data = segment["words"]
            chunks = get_word_chunks(words_data, max_words=3)
            
            for chunk in chunks:
                # Get timing from first and last word in chunk
                start_time = chunk[0]["start"]
                end_time = chunk[-1]["end"]
                
                # Get text from all words in chunk
                text = " ".join([w["word"].strip() for w in chunk])
                text = clean_text(text)
                
                # Determine style based on timing
                style = determine_style(start_time, beats)
                
                # Add animation tags for dynamic effect
                if style == "CTA":
                    text = f"{{\\fscx120\\fscy120\\t(0,200,\\fscx100\\fscy100)}}{text}"
                
                # Create dialogue line
                dialogue = (
                    f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},"
                    f"{style},,0,0,0,,{text}"
                )
                subtitles.append(dialogue)
        else:
            # Fallback: use segment-level timing
            text = clean_text(segment["text"])
            words = text.split()
            
            # Split into chunks
            chunk_size = 3
            duration = segment["end"] - segment["start"]
            time_per_chunk = duration / max(1, len(words) // chunk_size)
            
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                
                chunk_start = segment["start"] + (i // chunk_size) * time_per_chunk
                chunk_end = min(chunk_start + time_per_chunk, segment["end"])
                
                style = determine_style(chunk_start, beats)
                
                if style == "CTA":
                    chunk_text = f"{{\\fscx120\\fscy120\\t(0,200,\\fscx100\\fscy100)}}{chunk_text}"
                
                dialogue = (
                    f"Dialogue: 0,{format_time(chunk_start)},{format_time(chunk_end)},"
                    f"{style},,0,0,0,,{chunk_text}"
                )
                subtitles.append(dialogue)
    
    # Write to file
    print(f"Writing subtitles to: {OUT}")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(subtitles))
    
    print("✅ Enhanced subtitles generated successfully!")
    print(f"   Total segments: {len(result['segments'])}")
    print(f"   Total subtitle lines: {len(subtitles) - len(create_ass_header())}")
    print(f"   Duration: {result['segments'][-1]['end']:.2f}s")

if __name__ == "__main__":
    main()
