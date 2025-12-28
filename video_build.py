#!/usr/bin/env python3
import os
import sys
import random
from typing import List
from moviepy.editor import (
    ImageClip, 
    concatenate_videoclips, 
    AudioFileClip, 
    CompositeAudioClip,
    vfx
)
from pydub import AudioSegment

# ---------------- CONFIG ----------------
FRAMES_DIR = "frames"
VOICE_AUDIO = "final_audio.wav"
BG_MUSIC = "background_music.mp3" # Optional: Place a music file here
OUTPUT_VIDEO = "video_final.mp4"

TARGET_W, TARGET_H = 1080, 1920
FPS = 30
MAX_DURATION = 35.0
TRANSITION_DUR = 0.5  # Seconds for crossfade
# ----------------------------------------

def log(msg: str):
    print(f"[EXPERT-VID] {msg}", flush=True)

def get_audio_duration(path: str) -> float:
    if not os.path.isfile(path):
        raise SystemExit(f"Error: Audio not found at {path}")
    audio = AudioSegment.from_file(path)
    return min(len(audio) / 1000.0, MAX_DURATION)

def list_frames() -> List[str]:
    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit(f"Error: {FRAMES_DIR} directory missing")
    frames = sorted([
        os.path.join(FRAMES_DIR, f) for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])
    if not frames:
        raise SystemExit("Error: No images found in frames folder")
    return frames

def prepare_professional_clip(img_path: str, duration: float, index: int) -> ImageClip:
    """Applies cinematic motion and color grading to a single image."""
    # Add transition padding to duration so we don't lose time during crossfades
    clip = ImageClip(img_path).set_duration(duration + TRANSITION_DUR)

    # 1. Professional Crop & Resize
    w, h = clip.size
    scale = max(TARGET_W / w, TARGET_H / h)
    clip = clip.resize(scale)
    clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_W, height=TARGET_H)

    # 2. Alternating Ken Burns Effect
    # Even clips zoom IN, Odd clips zoom OUT
    if index % 2 == 0:
        clip = clip.fx(vfx.resize, lambda t: 1.0 + 0.05 * (t / clip.duration))
    else:
        clip = clip.fx(vfx.resize, lambda t: 1.05 - 0.05 * (t / clip.duration))

    # 3. Premium Color Polish
    clip = clip.fx(vfx.colorx, 1.05)     # Subtle contrast boost
    clip = clip.fx(vfx.lum_contrast, 0, 0.05, 128) # Slight pop

    # 4. Seamless Transition
    clip = clip.crossfadein(TRANSITION_DUR)

    return clip

def main():
    voice_path = sys.argv[1] if len(sys.argv) > 1 else VOICE_AUDIO
    total_duration = get_audio_duration(voice_path)
    frames = list_frames()
    
    # Calculate timing (account for the transition overlap)
    frame_duration = total_duration / len(frames)
    
    log(f"Building {total_duration:.2f}s video with {len(frames)} frames...")

    clips = []
    for i, img in enumerate(frames):
        log(f"Processing Frame {i+1}: {img}")
        clips.append(prepare_professional_clip(img, frame_duration, i))

    # Compose with 'padding' to enable the crossfade overlaps
    video = concatenate_videoclips(clips, method="compose", padding=-TRANSITION_DUR)
    video = video.set_duration(total_duration)

    # --- AUDIO ENGINE ---
    log("Layering Audio...")
    voice_clip = AudioFileClip(voice_path).subclip(0, total_duration)
    
    audio_layers = [voice_clip]

    if os.path.exists(BG_MUSIC):
        bg_music = AudioFileClip(BG_MUSIC).volumex(0.1) # 10% volume
        # Loop music if it's shorter than the video
        bg_music = bg_music.fx(vfx.loop, duration=total_duration)
        audio_layers.append(bg_music)
        log("Background music mixed at 10% volume.")
    else:
        log("No background_music.mp3 found, skipping music layer.")

    final_audio = CompositeAudioClip(audio_layers)
    video = video.set_audio(final_audio)

    # --- RENDER ---
    log(f"Starting Professional Render: {OUTPUT_VIDEO}")
    video.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        preset="medium", # Better compression than 'veryfast'
        threads=4,
        logger=None
    )
    log("Video Production Complete.")

if __name__ == "__main__":
    main()
