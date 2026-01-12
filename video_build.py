#!/usr/bin/env python3
import os, json
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, vfx, CompositeVideoClip
from pydub import AudioSegment
from PIL import Image

FRAMES_DIR = "frames"
BEATS_FILE = "beats.json"
AUDIO_FILE = "final_audio.wav"
OUTPUT = "output.mp4"
TARGET_W, TARGET_H = 1080, 1920
FPS = 60  # Increased for smoother motion
MAX_FRAME_SEC = 1.3
CTA_BOOST_SEC = 0.8
BITRATE = "8000k"  # High bitrate for quality

def audio_len():
    """Get exact audio duration without any limits"""
    return len(AudioSegment.from_file(AUDIO_FILE)) / 1000

def frames():
    return sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )

def optimize_image(img_path):
    """Pre-process image for better quality"""
    img = Image.open(img_path)
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Calculate aspect ratio and resize
    aspect = img.width / img.height
    target_aspect = TARGET_W / TARGET_H
    
    if aspect > target_aspect:
        # Image is wider - fit to height
        new_h = TARGET_H
        new_w = int(TARGET_H * aspect)
    else:
        # Image is taller - fit to width with extra height
        new_w = TARGET_W
        new_h = int(TARGET_W / aspect)
    
    # Use high-quality resampling
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Save optimized version temporarily
    temp_path = img_path.replace('.jpg', '_opt.jpg').replace('.png', '_opt.jpg')
    img.save(temp_path, 'JPEG', quality=98, optimize=True)
    
    return temp_path

def prepare(img, dur, is_cta=False):
    """Prepare clip with enhanced quality settings"""
    # Optimize image first
    opt_img = optimize_image(img)
    
    clip = ImageClip(opt_img).set_duration(dur)
    
    # Smart crop - center focus
    clip = clip.resize(height=TARGET_H)
    if clip.w > TARGET_W:
        clip = clip.crop(x_center=clip.w/2, width=TARGET_W)
    
    # Apply effects based on clip type
    if is_cta:
        # Attention-grabbing zoom + brightness
        clip = clip.fx(vfx.resize, lambda t: 1 + 0.08 * (t/dur))
        clip = clip.fx(vfx.colorx, 1.15)
    else:
        # Smooth Ken Burns effect
        clip = clip.fx(vfx.resize, lambda t: 1 + 0.05 * (t/dur))
    
    # Clean up temp file
    try:
        os.remove(opt_img)
    except:
        pass
    
    return clip

def add_fade_transitions(clips, fade_dur=0.15):
    """Add smooth crossfade transitions between clips"""
    faded = []
    for i, clip in enumerate(clips):
        if i == 0:
            # Fade in first clip
            faded.append(clip.fadein(fade_dur))
        elif i == len(clips) - 1:
            # Fade out last clip
            faded.append(clip.fadeout(fade_dur))
        else:
            # Crossfade middle clips
            faded.append(clip.crossfadein(fade_dur))
    return faded

def main():
    print("Loading beats and frames...")
    beats = json.load(open(BEATS_FILE))
    imgs = frames()
    
    if not imgs:
        print("Error: No frames found!")
        return
    
    # Get exact audio duration
    audio_duration = audio_len()
    print(f"Audio duration: {audio_duration:.2f}s")
    
    # Calculate how much time each frame should get
    num_frames = len(imgs)
    time_per_frame = audio_duration / num_frames
    
    print(f"Creating {num_frames} clips, {time_per_frame:.2f}s each...")
    clips = []
    
    for i, (img, beat) in enumerate(zip(imgs, beats)):
        # Use calculated time per frame, adjusting for attention clips
        if beat.get("intent") == "attention":
            # Attention clips can be slightly longer
            dur = min(time_per_frame * 1.2, time_per_frame + 0.3)
        else:
            dur = time_per_frame
        
        print(f"Processing frame {i+1}/{num_frames} ({dur:.2f}s)...")
        clips.append(prepare(img, dur, beat.get("intent") == "attention"))
    
    # Add fade transitions
    print("Adding transitions...")
    clips = add_fade_transitions(clips)
    
    # Concatenate all clips
    print("Concatenating clips...")
    video = concatenate_videoclips(clips, method="compose")
    
    # Add audio - match exactly to audio duration
    print("Adding audio...")
    audio = AudioFileClip(AUDIO_FILE)
    
    # Adjust video duration to match audio exactly
    if video.duration > audio_duration:
        # Trim video to match audio
        video = video.subclip(0, audio_duration)
    elif video.duration < audio_duration:
        # Extend last frame to match audio duration
        last_frame_extension = audio_duration - video.duration
        print(f"Extending last frame by {last_frame_extension:.2f}s to match audio...")
        extended_last = clips[-1].set_duration(clips[-1].duration + last_frame_extension)
        clips[-1] = extended_last
        video = concatenate_videoclips(clips, method="compose")
    
    # Normalize audio for consistent volume
    audio = audio.fx(vfx.audio_normalize)
    video = video.set_audio(audio)
    
    # Export with optimal YouTube Shorts settings
    print("Rendering final video...")
    video.write_videofile(
        OUTPUT,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate=BITRATE,
        audio_bitrate="320k",  # High quality audio
        preset="slow",  # Better compression quality
        ffmpeg_params=[
            "-crf", "18",  # Lower CRF = higher quality (18-23 is good)
            "-pix_fmt", "yuv420p",  # Compatibility
            "-profile:v", "high",  # H.264 High Profile
            "-level", "4.2",
            "-movflags", "+faststart",  # Fast streaming start
            "-maxrate", "10000k",  # Max bitrate
            "-bufsize", "20000k"  # Buffer size
        ],
        threads=4,  # Use multiple CPU threads
        logger=None
    )
    
    print(f"✓ Video created: {OUTPUT}")
    print(f"  Duration: {video.duration:.2f}s (Audio: {audio_duration:.2f}s)")
    print(f"  Resolution: {TARGET_W}x{TARGET_H}")
    print(f"  FPS: {FPS}")

if __name__ == "__main__":
    main()
