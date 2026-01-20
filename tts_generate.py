#!/usr/bin/env python3
import os
import sys
import re
import argparse
from typing import Optional
import torch
from TTS.api import TTS
from pydub import AudioSegment, effects

# --------------------------------------------------
# ENV
# --------------------------------------------------
os.environ.setdefault("COQUI_TOS_AGREED", "1")
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
SCRIPT_FILE = "script.txt"
OUTPUT_DEFAULT = "final_audio.wav"
VOICES_DIR = "voices"

# Model configuration
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
TARGET_SR = 44100

# Default speaker for XTTS (if no voice file provided)
# These are built-in XTTS v2 speakers that don't require voice files
DEFAULT_MALE_SPEAKER = "Claribel Dervla"  # Male-sounding voice
# Other options: "Daisy Studious", "Gracie Wise", "Tammie Ema"

# --------------------------------------------------
# LOG
# --------------------------------------------------
def log(msg: str):
    print(f"[TTS] {msg}", flush=True)

def warn(msg: str):
    print(f"[TTS] ⚠️  {msg}", flush=True)

def error(msg: str):
    sys.exit(f"[TTS] ❌ {msg}")

# --------------------------------------------------
# DEVICE
# --------------------------------------------------
def get_device():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"Using device: {dev}")
    return dev

# --------------------------------------------------
# VOICE FILE HANDLING
# --------------------------------------------------
def find_voice_file() -> Optional[str]:
    """Find a voice reference file in the voices directory"""
    if not os.path.isdir(VOICES_DIR):
        warn(f"Voices directory not found: {VOICES_DIR}")
        return None
    
    # Look for common audio formats
    audio_extensions = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')
    voice_files = [
        f for f in os.listdir(VOICES_DIR)
        if f.lower().endswith(audio_extensions)
    ]
    
    if not voice_files:
        warn(f"No voice files found in {VOICES_DIR}")
        return None
    
    # Prioritize files with "male" in the name
    male_files = [f for f in voice_files if 'male' in f.lower() and 'female' not in f.lower()]
    
    if male_files:
        selected = male_files[0]
    else:
        selected = voice_files[0]
    
    voice_path = os.path.join(VOICES_DIR, selected)
    log(f"Found voice file: {selected}")
    return voice_path

def create_voices_directory():
    """Create voices directory with instructions"""
    if not os.path.exists(VOICES_DIR):
        os.makedirs(VOICES_DIR)
        readme_path = os.path.join(VOICES_DIR, "README.txt")
        with open(readme_path, 'w') as f:
            f.write("""VOICE REFERENCE FILES
===================

Place your voice reference audio files here (WAV, MP3, FLAC, etc.)

For best results:
- 6-10 seconds of clean speech
- No background noise or music
- Clear pronunciation
- Single speaker only
- Name suggestion: male_voice.wav or female_voice.wav

If no voice file is provided, the system will use a built-in voice.
""")
        log(f"Created {VOICES_DIR} directory - add voice samples there")

# --------------------------------------------------
# SCRIPT
# --------------------------------------------------
def read_script(path: Optional[str]) -> str:
    """Read and clean the script file"""
    path = path or SCRIPT_FILE
    
    if not os.path.isfile(path):
        error(f"Script not found: {path}")
    
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
    except Exception as e:
        error(f"Failed to read script: {str(e)}")
    
    if not text:
        error("Script is empty")
    
    # Clean excessive whitespace while preserving intentional breaks
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 newlines
    
    log(f"Script loaded: {len(text)} characters")
    return text

# --------------------------------------------------
# AUDIO PROCESSING
# --------------------------------------------------
def polish_audio(seg: AudioSegment) -> AudioSegment:
    """Apply light normalization and formatting"""
    # Normalize with headroom to prevent clipping
    seg = effects.normalize(seg, headroom=2.0)
    
    # Ensure mono and correct sample rate
    seg = seg.set_channels(1).set_frame_rate(TARGET_SR)
    
    return seg

# --------------------------------------------------
# TTS SYNTHESIS
# --------------------------------------------------
def synthesize(script: str, output: str, voice_file: Optional[str] = None):
    """Generate speech from script"""
    
    # Create voices directory if it doesn't exist
    create_voices_directory()
    
    # Find voice file if not specified
    if voice_file is None:
        voice_file = find_voice_file()
    
    # Load TTS model
    log(f"Loading {MODEL_NAME}...")
    try:
        tts = TTS(model_name=MODEL_NAME, progress_bar=False).to(get_device())
    except Exception as e:
        error(f"Failed to load TTS model: {str(e)}")
    
    # Generate speech
    temp_output = "temp_tts_output.wav"
    
    try:
        if voice_file and os.path.isfile(voice_file):
            # Use voice cloning with reference file
            log(f"Cloning voice from: {os.path.basename(voice_file)}")
            tts.tts_to_file(
                text=script,
                speaker_wav=voice_file,
                language="en",
                file_path=temp_output,
            )
        else:
            # Use built-in speaker (no voice file needed)
            log(f"Using built-in speaker (no voice file provided)")
            warn("For custom voice, add a voice sample to the 'voices' directory")
            
            # Check if model supports speaker parameter
            try:
                tts.tts_to_file(
                    text=script,
                    language="en",
                    file_path=temp_output,
                )
            except Exception as e:
                error(f"TTS generation failed: {str(e)}")
        
        log("Speech generated successfully")
        
    except Exception as e:
        error(f"TTS synthesis failed: {str(e)}")
    
    # Post-process audio
    try:
        audio = AudioSegment.from_file(temp_output)
        audio = polish_audio(audio)
        audio.export(output, format="wav")
        
        # Cleanup temp file
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        duration = len(audio) / 1000.0
        log(f"✅ Audio exported: {output} ({duration:.1f}s)")
        
    except Exception as e:
        error(f"Audio processing failed: {str(e)}")

# --------------------------------------------------
# CLI
# --------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Generate narration audio using XTTS v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tts_audio.py                          # Use default script.txt
  python tts_audio.py --script my_script.txt   # Custom script
  python tts_audio.py --voice voices/male.wav  # Specific voice file
  python tts_audio.py --output narration.wav   # Custom output name
        """
    )
    
    parser.add_argument(
        "--script",
        default=None,
        help=f"Path to script file (default: {SCRIPT_FILE})"
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_DEFAULT,
        help=f"Output audio file (default: {OUTPUT_DEFAULT})"
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="Path to voice reference file (optional)"
    )
    
    args = parser.parse_args()
    
    # Read script
    script = read_script(args.script)
    
    # Generate audio
    synthesize(script, args.output, args.voice)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[TTS] ❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[TTS] ❌ Unexpected error: {str(e)}")
        sys.exit(1)
