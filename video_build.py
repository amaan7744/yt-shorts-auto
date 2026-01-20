#!/usr/bin/env python3
import os
import json
import random
from typing import List, Optional
from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    CompositeVideoClip,
    AudioFileClip,
    concatenate_videoclips,
)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
WIDTH, HEIGHT = 1080, 1920
FPS = 30
GAMEPLAY_DIR = "gameplay/loops"
FRAMES_DIR = "frames"
AUDIO_FILE = "final_audio.wav"
SUBS_FILE = "subs.ass"
OUTPUT = "output.mp4"
PIXEL_MIN_DURATION = 0.8   # Minimum duration per image to prevent flicker
PIXEL_POSITION_Y = int(HEIGHT * 0.15)  # Upper third positioning

# --------------------------------------------------
# UTILS
# --------------------------------------------------
def die(msg: str):
    """Exit with error message"""
    raise SystemExit(f"[VIDEO] ❌ {msg}")

def log(msg: str):
    """Print log message"""
    print(f"[VIDEO] {msg}", flush=True)

# --------------------------------------------------
# VALIDATION
# --------------------------------------------------
def validate_inputs():
    """Validate all required files and directories exist"""
    if not os.path.isfile(AUDIO_FILE):
        die(f"Audio file not found: {AUDIO_FILE}")
    
    if not os.path.isfile(SUBS_FILE):
        die(f"Subtitle file not found: {SUBS_FILE}")
    
    if not os.path.isdir(GAMEPLAY_DIR):
        die(f"Gameplay directory not found: {GAMEPLAY_DIR}")
    
    if not os.path.isdir(FRAMES_DIR):
        die(f"Frames directory not found: {FRAMES_DIR}")
    
    gameplay_files = [f for f in os.listdir(GAMEPLAY_DIR) if f.lower().endswith(".mp4")]
    if not gameplay_files:
        die(f"No MP4 files found in {GAMEPLAY_DIR}")
    
    frame_files = [f for f in os.listdir(FRAMES_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    if not frame_files:
        die(f"No image files found in {FRAMES_DIR}")

# --------------------------------------------------
# LOADERS
# --------------------------------------------------
def load_gameplay(duration: float) -> VideoFileClip:
    """Load and prepare gameplay background video"""
    log("Loading gameplay footage...")
    
    files = [f for f in os.listdir(GAMEPLAY_DIR) if f.lower().endswith(".mp4")]
    selected_file = random.choice(files)
    path = os.path.join(GAMEPLAY_DIR, selected_file)
    
    log(f"Selected: {selected_file}")
    
    try:
        clip = VideoFileClip(path, audio=False).set_fps(FPS)
        
        # Handle duration - loop or trim as needed
        if clip.duration < duration:
            log(f"Looping gameplay (original: {clip.duration:.2f}s, needed: {duration:.2f}s)")
            final_clip = clip.loop(duration=duration)
        else:
            # Random start point for variety
            max_start = max(0, clip.duration - duration)
            start = random.uniform(0, max_start) if max_start > 0 else 0
            log(f"Trimming gameplay from {start:.2f}s")
            final_clip = clip.subclip(start, start + duration)
        
        # Resize to fit screen
        return final_clip.resize((WIDTH, HEIGHT))
        
    except Exception as e:
        die(f"Failed to load gameplay: {str(e)}")

def load_pixel_images(total_duration: float) -> VideoFileClip:
    """Load and prepare pixel art image overlay"""
    log("Loading pixel art frames...")
    
    # Support multiple image formats
    images = sorted([
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])
    
    log(f"Found {len(images)} images")
    
    # Calculate duration per image
    per_img = max(PIXEL_MIN_DURATION, total_duration / len(images))
    log(f"Duration per image: {per_img:.2f}s")
    
    clips: List[ImageClip] = []
    
    try:
        for idx, img_path in enumerate(images):
            clip = (
                ImageClip(img_path)
                .set_duration(per_img)
                .resize(width=WIDTH)
                .set_position(("center", PIXEL_POSITION_Y))
                .set_fps(FPS)
            )
            clips.append(clip)
            
            if (idx + 1) % 10 == 0:
                log(f"Processed {idx + 1}/{len(images)} images")
        
        return concatenate_videoclips(clips, method="compose")
        
    except Exception as e:
        die(f"Failed to process images: {str(e)}")

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    """Main video generation pipeline"""
    log("Starting YouTube Shorts generation...")
    log(f"Output resolution: {WIDTH}x{HEIGHT} @ {FPS}fps")
    
    # Validate all inputs first
    validate_inputs()
    
    # Load audio to determine video duration
    log("Loading audio...")
    try:
        audio = AudioFileClip(AUDIO_FILE)
        duration = audio.duration
        log(f"Audio duration: {duration:.2f}s")
    except Exception as e:
        die(f"Failed to load audio: {str(e)}")
    
    # Prepare gameplay background
    gameplay = load_gameplay(duration)
    
    # Prepare pixel art overlay
    pixel_strip = load_pixel_images(duration)
    
    # Composite layers
    log("Compositing video layers...")
    try:
        video = CompositeVideoClip(
            [gameplay, pixel_strip],
            size=(WIDTH, HEIGHT)
        ).set_audio(audio).set_duration(duration)
    except Exception as e:
        die(f"Failed to composite video: {str(e)}")
    
    # Render final video with subtitles
    log("Rendering final video (this may take a while)...")
    try:
        video.write_videofile(
            OUTPUT,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="medium",  # Changed from 'slow' for better speed/quality balance
            bitrate="8000k",  # High bitrate for quality
            ffmpeg_params=[
                "-vf", f"ass={SUBS_FILE}",
                "-pix_fmt", "yuv420p",
                "-crf", "18",  # High quality (lower = better, 18 is visually lossless)
                "-movflags", "+faststart",
            ],
            threads=4,
            logger=None,
            temp_audiofile="temp_audio.m4a",
            remove_temp=True,
        )
    except Exception as e:
        die(f"Failed to render video: {str(e)}")
    finally:
        # Cleanup
        video.close()
        audio.close()
        gameplay.close()
        pixel_strip.close()
    
    log(f"✅ Successfully created {OUTPUT}")
    log(f"File size: {os.path.getsize(OUTPUT) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("❌ Process interrupted by user")
    except Exception as e:
        die(f"Unexpected error: {str(e)}")
