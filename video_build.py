#!/usr/bin/env python3
"""
YouTube Shorts Video Builder - FIXED VERSION
- Proper audio duration detection
- Accurate beat timing sync
- No early/late endings
- Better error handling
"""
import json
import subprocess
import sys
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920
BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT = Path("output.mp4")

def die(msg):
    print(f"[VIDEO] ❌ {msg}", file=sys.stderr)
    sys.exit(1)

def get_audio_duration(audio_path):
    """Get exact audio duration using ffprobe"""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        duration = float(result.stdout.strip())
        print(f"[VIDEO] 🎵 Audio duration: {duration:.3f}s")
        return duration
    except Exception as e:
        die(f"Failed to get audio duration: {e}")

def get_video_duration(video_path):
    """Get exact video duration using ffprobe"""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"[VIDEO] ⚠️  Warning: Could not get duration for {video_path}: {e}")
        return None

def main():
    # Validation
    if not BEATS_FILE.exists():
        die("beats.json missing")
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")
    if not ASSET_DIR.exists():
        die(f"Asset directory missing: {ASSET_DIR}")

    # Load beats
    try:
        beats_data = json.loads(BEATS_FILE.read_text())
        beats = beats_data.get("beats", [])
        if not beats:
            die("No beats found in beats.json")
    except Exception as e:
        die(f"Failed to parse beats.json: {e}")

    # Get exact audio duration
    audio_duration = get_audio_duration(AUDIO_FILE)

    # Calculate total estimated duration from beats
    total_beat_duration = sum(beat.get("estimated_duration", 0) for beat in beats)
    print(f"[VIDEO] 📊 Total beat duration: {total_beat_duration:.3f}s")
    
    if abs(total_beat_duration - audio_duration) > 0.5:
        print(f"[VIDEO] ⚠️  Warning: Beat duration ({total_beat_duration:.3f}s) differs from audio ({audio_duration:.3f}s)")

    # Verify all assets exist and get their durations
    print(f"[VIDEO] 🔍 Verifying {len(beats)} assets...")
    for i, beat in enumerate(beats):
        asset_key = beat.get("asset_key")
        if not asset_key:
            die(f"Beat {i} missing 'asset_key'")
        
        asset = ASSET_DIR / f"{asset_key}.mp4"
        if not asset.exists():
            die(f"Missing asset: {asset}")
        
        # Check if asset is long enough
        video_dur = get_video_duration(asset)
        beat_dur = beat.get("estimated_duration", 0)
        if video_dur and video_dur < beat_dur:
            print(f"[VIDEO] ⚠️  Asset {asset_key}.mp4 ({video_dur:.2f}s) shorter than beat duration ({beat_dur:.2f}s) - will loop")

    # Build ffmpeg command
    cmd = ["ffmpeg", "-y", "-hide_banner"]

    # Add all video inputs
    for beat in beats:
        asset = ASSET_DIR / f"{beat['asset_key']}.mp4"
        cmd.extend(["-i", str(asset)])

    # Add audio input (last input)
    cmd.extend(["-i", str(AUDIO_FILE)])
    audio_index = len(beats)

    # ----------------------------- 
    # FILTER COMPLEX - FIXED VERSION
    # ----------------------------- 
    filters = []
    
    # Process each video segment
    for i, beat in enumerate(beats):
        dur = beat["estimated_duration"]
        
        # Handle video processing with proper looping if needed
        filters.append(
            f"[{i}:v]"
            f"fps=30,"  # Normalize frame rate first
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"setsar=1,"  # Set sample aspect ratio
            f"loop=loop=-1:size=1:start=0,"  # Loop if needed
            f"trim=duration={dur},"
            f"setpts=PTS-STARTPTS"
            f"[v{i}];"
        )
    
    # Concatenate all segments
    concat_inputs = "".join(f"[v{i}]" for i in range(len(beats)))
    filters.append(
        f"{concat_inputs}concat=n={len(beats)}:v=1:a=0[vconcat];"
    )
    
    # Trim concatenated video to EXACT audio duration
    filters.append(
        f"[vconcat]trim=end={audio_duration},setpts=PTS-STARTPTS[vtrim];"
    )
    
    # Add subtitles if present
    if SUBS_FILE.exists():
        # Escape the path properly for ffmpeg
        subs_path = str(SUBS_FILE).replace('\\', '/').replace(':', '\\:')
        filters.append(f"[vtrim]ass='{subs_path}'[vout]")
        vmap = "[vout]"
        print(f"[VIDEO] 📝 Adding subtitles from {SUBS_FILE}")
    else:
        vmap = "[vtrim]"
        print("[VIDEO] ℹ️  No subtitles file found")

    filter_complex = "".join(filters)

    # ----------------------------- 
    # OUTPUT SETTINGS
    # ----------------------------- 
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", vmap,
        "-map", f"{audio_index}:a",
        
        # Video encoding
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "medium",  # Changed from "slow" for faster encoding
        "-r", "30",  # Force output frame rate
        
        # Audio encoding
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",  # Audio sample rate
        
        # Duration enforcement
        "-t", str(audio_duration),  # Explicit duration limit
        "-shortest",
        
        # Optimization
        "-movflags", "+faststart",
        
        str(OUTPUT)
    ])

    # Print command for debugging
    print("[VIDEO] 🎬 FFmpeg command:")
    print(" ".join(cmd))
    print()

    # Run ffmpeg
    print("[VIDEO] 🎬 Rendering video (audio-locked)...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        die(f"FFmpeg failed with exit code {e.returncode}")

    # Verify output
    if not OUTPUT.exists():
        die("Output file was not created")
    
    output_duration = get_video_duration(OUTPUT)
    print(f"[VIDEO] ✅ output.mp4 ready!")
    print(f"[VIDEO] 📊 Output duration: {output_duration:.3f}s (target: {audio_duration:.3f}s)")
    
    duration_diff = abs(output_duration - audio_duration)
    if duration_diff > 0.1:
        print(f"[VIDEO] ⚠️  Duration mismatch: {duration_diff:.3f}s difference")
    else:
        print(f"[VIDEO] ✅ Duration match perfect! (±{duration_diff:.3f}s)")

if __name__ == "__main__":
    main()
