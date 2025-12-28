#!/usr/bin/env python3
import os
import sys
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
OUTPUT_VIDEO = "video_raw.mp4" 
FRAMES_DIR = "frames"
VOICE_AUDIO = "final_audio.wav"
BG_MUSIC = "background_music.mp3" 

# Standard 1080p Vertical Dimensions
TARGET_W, TARGET_H = 1080, 1920
FPS = 30
MAX_DURATION = 35.0
TRANSITION_DUR = 0.5 
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
    """Enhanced 1080p processing with high-quality scaling."""
    # Load image and force it to RGB to avoid color distortion
    clip = ImageClip(img_path).set_duration(duration + TRANSITION_DUR)

    # 1. High-Quality Resize & Crop
    w, h = clip.size
    scale = max(TARGET_W / w, TARGET_H / h)
    
    # We use resize(scale) then crop to ensure 1080x1920 exactly
    clip = clip.resize(scale)
    
    # Precise center crop to maintain 1080p aspect ratio
    clip = clip.crop(
        x_center=clip.w/2, 
        y_center=clip.h/2, 
        width=TARGET_W, 
        height=TARGET_H
    )

    # 2. Alternating Cinematic Motion
    if index % 2 == 0:
        clip = clip.fx(vfx.resize, lambda t: 1.0 + 0.08 * (t / clip.duration))
    else:
        clip = clip.fx(vfx.resize, lambda t: 1.08 - 0.08 * (t / clip.duration))

    # 3. Visual Polish (Color/Contrast)
    clip = clip.fx(vfx.colorx, 1.1) # Boost colors for mobile screens
    clip = clip.crossfadein(TRANSITION_DUR)

    return clip

def main():
    voice_path = sys.argv[1] if len(sys.argv) > 1 else VOICE_AUDIO
    total_duration = get_audio_duration(voice_path)
    frames = list_frames()
    
    frame_duration = total_duration / len(frames)
    
    log(f"Starting 1080p Production: {total_duration:.2f}s")

    clips = []
    for i, img in enumerate(frames):
        clips.append(prepare_professional_clip(img, frame_duration, i))

    video = concatenate_videoclips(clips, method="compose", padding=-TRANSITION_DUR)
    video = video.set_duration(total_duration)

    # --- AUDIO MIXING ---
    voice_clip = AudioFileClip(voice_path).subclip(0, total_duration)
    audio_layers = [voice_clip]

    if os.path.exists(BG_MUSIC):
        bg_music = AudioFileClip(BG_MUSIC).volumex(0.15).fx(vfx.loop, duration=total_duration)
        audio_layers.append(bg_music)

    video = video.set_audio(CompositeAudioClip(audio_layers))

    # --- 1080P HIGH BITRATE RENDER ---
    log(f"Rendering High-Quality 1080p: {OUTPUT_VIDEO}")
    video.write_videofile(
        OUTPUT_VIDEO,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        # Adding bitrate ensures it doesn't compress down to 240p quality
        bitrate="8000k", 
        preset="medium", 
        threads=4,
        logger=None
    )
    log("Production Complete.")

if __name__ == "__main__":
    main()
