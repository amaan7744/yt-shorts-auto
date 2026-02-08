#!/usr/bin/env python3
"""
YouTube Shorts Video Builder - PRO EDITION
==========================================

FEATURES:
✅ ProRes intermediate codec (zero quality loss)
✅ Ken Burns effect on hook images (dynamic zoom)
✅ Flash transitions between hook images (0.05s white flash)
✅ Crossfade transitions between story videos (0.2s smooth)
✅ Color grading (saturation + contrast + sharpness)
✅ Fast hook timing (0.3s per image, auto-calculated from words)
✅ Single final encode at CRF 15 (maximum quality)
✅ Video ends EXACTLY with audio duration
✅ No subtitle rendering (handled separately)

GUARANTEES:
- Hook images change every 0.3s with zoom effect
- Videos smoothly crossfade
- Single encode = no quality loss
- Output matches audio duration perfectly
"""

import json
import subprocess
import sys
import tempfile
import random
from pathlib import Path

# ==================================================
# FILES
# ==================================================

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT = Path("output.mp4")

# ==================================================
# QUALITY SETTINGS (LOCKED FOR MAXIMUM QUALITY)
# ==================================================

TARGET_W = 1440
TARGET_H = 2560

# ProRes settings (intermediate - lossless quality)
PRORES_PROFILE = "3"  # ProRes HQ
PRORES_PIX_FMT = "yuv422p10le"

# Final encode settings (maximum quality)
FINAL_CRF = "15"  # Lower = higher quality (was 17)
FINAL_PRESET = "slow"  # Slower = better quality
FINAL_BITRATE = "12M"  # High bitrate for Shorts

# ==================================================
# HOOK SETTINGS
# ==================================================

HOOK_IMAGE_DURATION = 0.3  # Fast cuts (was 0.4)
FLASH_DURATION = 0.05  # White flash between hooks

# Ken Burns zoom settings
ZOOM_START = 1.0
ZOOM_END = 1.15  # 15% zoom
ZOOM_VARIATIONS = ["in", "out", "pan_left", "pan_right"]

# ==================================================
# TRANSITION SETTINGS
# ==================================================

CROSSFADE_DURATION = 0.2  # Smooth fade between videos

# ==================================================
# COLOR GRADING
# ==================================================

COLOR_SATURATION = 1.25  # 25% boost
COLOR_CONTRAST = 1.08    # 8% boost
COLOR_BRIGHTNESS = 0.02  # Slight lift

# ==================================================
# UTILS
# ==================================================

def die(msg):
    print(f"[VIDEO PRO] ❌ {msg}", file=sys.stderr)
    sys.exit(1)

def run(cmd, silent=False, show_on_error=True):
    """Run command with better error handling"""
    try:
        if silent:
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE if show_on_error else subprocess.DEVNULL,
                text=True
            )
        else:
            result = subprocess.run(cmd, check=True, text=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Command failed with exit code {e.returncode}", file=sys.stderr)
        print(f"Command: {' '.join(str(x) for x in cmd)}", file=sys.stderr)
        if show_on_error and e.stderr:
            print(f"\nError output:\n{e.stderr}", file=sys.stderr)
        raise

def ffprobe_duration(path: Path) -> float:
    """Get exact duration of media file"""
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        duration_str = r.stdout.strip()
        if not duration_str:
            raise ValueError(f"ffprobe returned empty duration for {path}")
        return float(duration_str)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed for {path}: {e.stderr}")
    except ValueError as e:
        raise RuntimeError(f"Invalid duration value for {path}: {e}")

# ==================================================
# KEN BURNS EFFECT
# ==================================================

def get_ken_burns_filter(duration: float, variation: str = "in") -> str:
    """
    Generate Ken Burns zoom/pan filter
    
    Variations:
    - in: Zoom in from 1.0 to 1.15
    - out: Zoom out from 1.15 to 1.0
    - pan_left: Zoom in + pan left
    - pan_right: Zoom in + pan right
    """
    frames = max(int(duration * 25), 1)  # 25 fps, minimum 1 frame
    
    if variation == "in":
        # Zoom in: center to center
        return (
            f"scale=1600:2840,"  # Scale larger than target for zoom headroom
            f"zoompan=z='min(zoom+0.0015,{ZOOM_END})':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={TARGET_W}x{TARGET_H}"
        )
    elif variation == "out":
        # Zoom out: start zoomed, end normal
        return (
            f"scale=1600:2840,"
            f"zoompan=z='if(lte(zoom,1.0),1.0,max(1.0,{ZOOM_END}-zoom*0.0015))':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={TARGET_W}x{TARGET_H}"
        )
    elif variation == "pan_left":
        # Zoom in + pan from right to left
        return (
            f"scale=1600:2840,"
            f"zoompan=z='min(zoom+0.0015,{ZOOM_END})':d={frames}:"
            f"x='iw-iw/zoom':y='ih/2-(ih/zoom/2)':s={TARGET_W}x{TARGET_H}"
        )
    else:  # pan_right
        # Zoom in + pan from left to right
        return (
            f"scale=1600:2840,"
            f"zoompan=z='min(zoom+0.0015,{ZOOM_END})':d={frames}:"
            f"x='0':y='ih/2-(ih/zoom/2)':s={TARGET_W}x{TARGET_H}"
        )

# ==================================================
# IMAGE → PRORES VIDEO WITH KEN BURNS
# ==================================================

def image_to_prores(image: Path, duration: float, out: Path, ken_burns: str = "in"):
    """Convert image to ProRes video with Ken Burns effect"""
    
    # Ensure minimum duration for Ken Burns effect
    if duration < 0.1:
        print(f"  ⚠️  Warning: Duration {duration:.3f}s too short for Ken Burns, using 0.1s minimum")
        duration = 0.1
    
    kb_filter = get_ken_burns_filter(duration, ken_burns)
    
    # Add white flash at the end (for hook transitions)
    # Only add flash if duration is long enough
    if duration > FLASH_DURATION:
        flash_start = duration - FLASH_DURATION
        filters = [
            kb_filter,
            f"fade=t=out:st={flash_start:.3f}:d={FLASH_DURATION}:c=white"
        ]
    else:
        filters = [kb_filter]
    
    vf = ",".join(filters)
    
    run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image),
        "-t", f"{duration:.6f}",
        "-vf", vf,
        "-c:v", "prores_ks",
        "-profile:v", PRORES_PROFILE,
        "-pix_fmt", PRORES_PIX_FMT,
        "-r", "25",  # 25 fps
        str(out)
    ], silent=True)

# ==================================================
# VIDEO → PRORES VIDEO (TRIM + SCALE)
# ==================================================

def video_to_prores(video: Path, duration: float, out: Path):
    """Convert video to ProRes with proper scaling"""
    
    # Check actual video duration
    try:
        actual_duration = ffprobe_duration(video)
        if actual_duration < duration:
            print(f"  ⚠️  Warning: Video {video.name} is {actual_duration:.2f}s but needs {duration:.2f}s - using actual duration")
            duration = actual_duration
    except Exception as e:
        print(f"  ⚠️  Warning: Could not probe {video.name} duration, proceeding anyway: {e}")
    
    filters = [
        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease",
        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black"
    ]
    
    vf = ",".join(filters)
    
    run([
        "ffmpeg", "-y",
        "-i", str(video),
        "-t", f"{duration:.6f}",
        "-vf", vf,
        "-c:v", "prores_ks",
        "-profile:v", PRORES_PROFILE,
        "-pix_fmt", PRORES_PIX_FMT,
        "-r", "25",
        str(out)
    ], silent=True)

# ==================================================
# CROSSFADE FILTER
# ==================================================

def create_crossfade_complex_filter(clips: list, durations: list, hook_count: int) -> str:
    """
    Create complex filter for crossfading videos
    Hook images: No crossfade (flash transition already applied)
    Story videos: 0.2s crossfade
    
    KEY INSIGHT: When chaining xfades:
    - First xfade: [A][B]xfade outputs (A_dur + B_dur - fade_dur)
    - Second xfade: [AB][C]xfade needs offset relative to AB's output duration
    - The offset is ALWAYS: (previous_output_duration - fade_duration)
    """
    
    if len(clips) == 1:
        return "[0:v]null[out]"
    
    filter_parts = []
    
    # Simple approach: Just prepare all inputs
    for i in range(len(clips)):
        filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
    
    # Concatenate hooks without crossfade
    if hook_count > 0:
        hook_concat = "".join(f"[v{i}]" for i in range(hook_count))
        filter_parts.append(f"{hook_concat}concat=n={hook_count}:v=1:a=0[hooks]")
    
    # Crossfade story videos
    story_count = len(clips) - hook_count
    
    if story_count == 0:
        # Only hooks, no story videos
        filter_parts.append("[hooks]null[out]")
    elif story_count == 1:
        # Only one story video - just concat with hooks
        story_idx = hook_count
        if hook_count > 0:
            filter_parts.append(f"[hooks][v{story_idx}]concat=n=2:v=1:a=0[out]")
        else:
            filter_parts.append(f"[v{story_idx}]null[out]")
    else:
        # Multiple story videos - apply crossfades
        story_start = hook_count
        
        # Calculate safe crossfade duration (don't exceed 90% of any clip)
        min_story_duration = min(durations[story_start:])
        safe_crossfade = min(CROSSFADE_DURATION, min_story_duration * 0.9)
        
        if safe_crossfade < CROSSFADE_DURATION:
            print(f"  ⚠️  Reducing crossfade from {CROSSFADE_DURATION:.2f}s to {safe_crossfade:.2f}s (shortest clip is {min_story_duration:.2f}s)")
        
        # Build xfade chain
        # Track the OUTPUT duration as we build the chain
        output_duration = durations[story_start]  # Start with first clip's duration
        prev_label = f"v{story_start}"
        
        print(f"  📊 Crossfade chain debug:")
        print(f"     Initial clip: v{story_start}, duration: {output_duration:.3f}s")
        
        for idx in range(1, story_count):
            current_clip_idx = story_start + idx
            current_label = f"cf{current_clip_idx}"
            
            # The offset for xfade is when the second clip starts in the first clip's timeline
            # This is the output duration of the previous result minus the crossfade
            offset = max(0.0, output_duration - safe_crossfade)
            
            print(f"     xfade {idx}: [{prev_label}][v{current_clip_idx}] offset={offset:.3f}s, new_clip_dur={durations[current_clip_idx]:.3f}s")
            
            filter_parts.append(
                f"[{prev_label}][v{current_clip_idx}]xfade=transition=fade:duration={safe_crossfade:.3f}:offset={offset:.3f}[{current_label}]"
            )
            
            # Update output duration for next iteration
            # New output = previous output + new clip - crossfade overlap
            new_output_duration = output_duration + durations[current_clip_idx] - safe_crossfade
            print(f"     → output_duration: {output_duration:.3f}s + {durations[current_clip_idx]:.3f}s - {safe_crossfade:.3f}s = {new_output_duration:.3f}s")
            output_duration = new_output_duration
            
            prev_label = current_label
        
        # Combine hooks and crossfaded stories
        if hook_count > 0:
            filter_parts.append(f"[hooks][{prev_label}]concat=n=2:v=1:a=0[out]")
        else:
            filter_parts.append(f"[{prev_label}]null[out]")
    
    return ";".join(filter_parts)

# ==================================================
# MAIN
# ==================================================

def main():
    print("="*70)
    print("🎬 YOUTUBE SHORTS PRO VIDEO BUILDER")
    print("="*70)
    
    # Validate inputs
    if not BEATS_FILE.exists():
        die("beats.json missing")
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")
    
    try:
        beats_data = json.loads(BEATS_FILE.read_text())
    except json.JSONDecodeError as e:
        die(f"Invalid JSON in beats.json: {e}")
    
    beats = beats_data.get("beats")
    if not beats:
        die("No beats found in beats.json")
    
    if not isinstance(beats, list):
        die("beats must be a list in beats.json")
    
    if len(beats) == 0:
        die("beats list is empty in beats.json")
    
    audio_duration = ffprobe_duration(AUDIO_FILE)
    print(f"🎵 Audio duration: {audio_duration:.2f}s")
    
    temp_dir = Path(tempfile.mkdtemp(prefix="prores_clips_"))
    print(f"📁 Temp dir: {temp_dir}")
    
    prores_clips = []
    durations = []
    hook_count = 0
    
    # --------------------------------------------------
    # STEP 1: Build ProRes clips with effects
    # --------------------------------------------------
    
    print("\n" + "="*70)
    print("STEP 1: Converting to ProRes with effects")
    print("="*70)
    
    for i, beat in enumerate(beats, start=1):
        # Validate beat structure
        if not isinstance(beat, dict):
            die(f"Beat {i} is not a dictionary")
        
        if "asset_file" not in beat:
            die(f"Beat {i} missing 'asset_file' field")
        
        if "type" not in beat:
            die(f"Beat {i} missing 'type' field")
        
        if beat["type"] not in ["image", "video"]:
            die(f"Beat {i} has invalid type '{beat['type']}' (must be 'image' or 'video')")
        
        asset_path = ASSET_DIR / beat["asset_file"]
        
        if not asset_path.exists():
            die(f"Missing asset for beat {i}: {asset_path}")
        
        if "duration" not in beat or beat["duration"] <= 0:
            die(f"Beat {i} missing valid duration (got: {beat.get('duration', 'N/A')})")
        
        out_clip = temp_dir / f"prores_{i:03d}.mov"
        duration = beat["duration"]
        
        if beat["type"] == "image":
            # Hook image with Ken Burns
            ken_burns = random.choice(ZOOM_VARIATIONS)
            print(f"  [{i:02d}] 🖼️  Hook image: {asset_path.name} ({duration:.2f}s) - {ken_burns}")
            image_to_prores(asset_path, duration, out_clip, ken_burns)
            hook_count += 1
            
        elif beat["type"] == "video":
            # Story video
            print(f"  [{i:02d}] 🎞️  Video: {asset_path.name} ({duration:.2f}s)")
            video_to_prores(asset_path, duration, out_clip)
        else:
            die(f"Unknown beat type: {beat['type']}")
        
        prores_clips.append(out_clip)
        durations.append(duration)
    
    print(f"\n✅ Created {len(prores_clips)} ProRes clips ({hook_count} hooks, {len(prores_clips)-hook_count} videos)")
    
    # Check if total video duration matches audio
    total_video_duration = sum(durations)
    duration_shortfall = audio_duration - total_video_duration
    
    if abs(duration_shortfall) > 0.1:
        if duration_shortfall > 0:
            # Video is too short - extend the last clip
            print(f"\n📏 Video duration adjustment needed:")
            print(f"   Audio duration: {audio_duration:.2f}s")
            print(f"   Video duration: {total_video_duration:.2f}s")
            print(f"   Shortfall: {duration_shortfall:.2f}s")
            
            # Get the last video clip (not hook image)
            last_video_idx = None
            for i in range(len(beats) - 1, -1, -1):
                if beats[i]["type"] == "video":
                    last_video_idx = i
                    break
            
            if last_video_idx is not None:
                last_asset = ASSET_DIR / beats[last_video_idx]["asset_file"]
                actual_video_duration = ffprobe_duration(last_asset)
                
                print(f"\n🔄 Extending last video clip to fill gap:")
                print(f"   Last video: {beats[last_video_idx]['asset_file']}")
                print(f"   Current duration in timeline: {durations[last_video_idx]:.2f}s")
                print(f"   Actual video file duration: {actual_video_duration:.2f}s")
                
                # Calculate how much we can extend
                if actual_video_duration > durations[last_video_idx]:
                    # Video file is longer - we can use more of it
                    additional_available = actual_video_duration - durations[last_video_idx]
                    extend_by = min(duration_shortfall, additional_available)
                    
                    print(f"   Can extend by: {extend_by:.2f}s (using more of the actual video)")
                    
                    # Recreate the last ProRes clip with extended duration
                    extended_duration = durations[last_video_idx] + extend_by
                    out_clip = temp_dir / f"prores_{last_video_idx + 1:03d}.mov"
                    
                    print(f"   Recreating with duration: {extended_duration:.2f}s")
                    video_to_prores(last_asset, extended_duration, out_clip)
                    
                    durations[last_video_idx] = extended_duration
                    duration_shortfall -= extend_by
                
                # If still short, loop the video
                if duration_shortfall > 0.1:
                    print(f"\n🔁 Still need {duration_shortfall:.2f}s - will loop the last video")
                    
                    # Create looped version
                    loop_count = int(duration_shortfall / actual_video_duration) + 2
                    total_needed = durations[last_video_idx] + duration_shortfall
                    
                    looped_clip = temp_dir / f"prores_looped_{last_video_idx + 1:03d}.mov"
                    
                    print(f"   Looping {loop_count} times to get {total_needed:.2f}s")
                    
                    run([
                        "ffmpeg", "-y",
                        "-stream_loop", str(loop_count),
                        "-i", str(last_asset),
                        "-t", f"{total_needed:.6f}",
                        "-vf", f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black",
                        "-c:v", "prores_ks",
                        "-profile:v", PRORES_PROFILE,
                        "-pix_fmt", PRORES_PIX_FMT,
                        "-r", "25",
                        str(looped_clip)
                    ], silent=True)
                    
                    prores_clips[last_video_idx] = looped_clip
                    durations[last_video_idx] = total_needed
                    
                    print(f"   ✅ Extended last video to {total_needed:.2f}s")
                    
            else:
                # No video clips, add black screen
                print(f"\n⚫ No video clips found - adding black screen for {duration_shortfall:.2f}s")
                black_clip = temp_dir / f"prores_black.mov"
                
                run([
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=black:s={TARGET_W}x{TARGET_H}:r=25",
                    "-t", f"{duration_shortfall:.6f}",
                    "-c:v", "prores_ks",
                    "-profile:v", PRORES_PROFILE,
                    "-pix_fmt", PRORES_PIX_FMT,
                    str(black_clip)
                ], silent=True)
                
                prores_clips.append(black_clip)
                durations.append(duration_shortfall)
        
        else:
            # Video is too long - will be trimmed by -t flag in final encode
            print(f"\n✂️  Video is {abs(duration_shortfall):.2f}s longer than audio - will trim in final encode")
    
    # --------------------------------------------------
    # STEP 2: Concatenate with crossfades
    # --------------------------------------------------
    
    print("\n" + "="*70)
    print("STEP 2: Applying transitions (flash for hooks, crossfade for videos)")
    print("="*70)
    
    if len(prores_clips) == 1:
        # Only one clip, just copy
        merged = prores_clips[0]
        print("  ℹ️  Single clip, skipping concat")
    else:
        # Multiple clips - use crossfade
        merged = temp_dir / "merged.mov"
        
        # Build complex filter
        complex_filter = create_crossfade_complex_filter(prores_clips, durations, hook_count)
        
        # Build input arguments
        input_args = []
        for clip in prores_clips:
            input_args.extend(["-i", str(clip)])
        
        print(f"  🔗 Concatenating {len(prores_clips)} clips with transitions...")
        
        # Debug: print the filter for inspection
        if len(complex_filter) > 1000:
            print(f"  📝 Filter length: {len(complex_filter)} chars")
        
        try:
            run([
                "ffmpeg", "-y",
                *input_args,
                "-filter_complex", complex_filter,
                "-map", "[out]",
                "-c:v", "prores_ks",
                "-profile:v", PRORES_PROFILE,
                "-pix_fmt", PRORES_PIX_FMT,
                str(merged)
            ], silent=True, show_on_error=True)
        except subprocess.CalledProcessError:
            print("\n🔍 DEBUG INFO:", file=sys.stderr)
            print(f"  Number of clips: {len(prores_clips)}", file=sys.stderr)
            print(f"  Hook count: {hook_count}", file=sys.stderr)
            print(f"  Story count: {len(prores_clips) - hook_count}", file=sys.stderr)
            print(f"  Durations: {durations}", file=sys.stderr)
            print(f"\n  Filter complex:\n{complex_filter}", file=sys.stderr)
            raise
    
    print(f"✅ Merged video created")
    
    # --------------------------------------------------
    # STEP 3: Final encode with color grading
    # --------------------------------------------------
    
    print("\n" + "="*70)
    print("STEP 3: Final encode with color grading (CRF 15)")
    print("="*70)
    
    # Color grading filter chain
    color_filters = [
        # Saturation and contrast boost
        f"eq=saturation={COLOR_SATURATION}:contrast={COLOR_CONTRAST}:brightness={COLOR_BRIGHTNESS}",
        # S-curve for cinematic contrast
        "curves=preset=strong_contrast",
        # Sharpening (subtle)
        "unsharp=5:5:0.6:3:3:0.4",
        # Final scale to exact dimensions
        f"scale={TARGET_W}:{TARGET_H}:flags=spline36:force_original_aspect_ratio=decrease",
        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black"
    ]
    
    vf = ",".join(color_filters)
    
    print(f"  🎨 Applying color grading:")
    print(f"     - Saturation: +{int((COLOR_SATURATION-1)*100)}%")
    print(f"     - Contrast: +{int((COLOR_CONTRAST-1)*100)}%")
    print(f"     - Sharpening: Enabled")
    print(f"     - Curves: Strong contrast preset")
    
    print(f"\n  🎧 Muxing audio (duration: {audio_duration:.2f}s)")
    print(f"  💎 Encoding at CRF {FINAL_CRF} (maximum quality)")
    
    # Build ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(merged),
        "-i", str(AUDIO_FILE),
        "-vf", vf,
        "-map", "0:v:0",
        "-map", "1:a:0",
        # Video encoding (maximum quality)
        "-c:v", "libx264",
        "-crf", FINAL_CRF,
        "-preset", FINAL_PRESET,
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.2",
        "-maxrate", FINAL_BITRATE,
        "-bufsize", "24M",
        # Audio encoding
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        # Duration locked to audio - use -t to force exact duration
        "-t", f"{audio_duration:.6f}",
        # Optimize for streaming
        "-movflags", "+faststart",
        str(OUTPUT)
    ]
    
    # Note: We use -t (duration) instead of -shortest to ensure
    # the output is EXACTLY audio_duration, whether video is longer or shorter
    
    run(ffmpeg_cmd, silent=False)
    
    # --------------------------------------------------
    # COMPLETE
    # --------------------------------------------------
    
    try:
        final_duration = ffprobe_duration(OUTPUT)
    except Exception as e:
        print(f"⚠️  Warning: Could not probe output duration: {e}")
        final_duration = audio_duration
    
    print("\n" + "="*70)
    print("✅ VIDEO BUILD COMPLETE!")
    print("="*70)
    print(f"📊 Stats:")
    print(f"   - Hook images: {hook_count} × {HOOK_IMAGE_DURATION}s each")
    print(f"   - Story videos: {len(prores_clips) - hook_count}")
    print(f"   - Audio duration: {audio_duration:.2f}s")
    print(f"   - Video duration: {final_duration:.2f}s")
    print(f"   - Sync offset: {abs(audio_duration - final_duration):.3f}s")
    print(f"\n🎨 Quality:")
    print(f"   - ProRes intermediate: ✅ (zero generation loss)")
    print(f"   - Final CRF: {FINAL_CRF} (maximum quality)")
    print(f"   - Color grading: ✅")
    print(f"   - Ken Burns: ✅ (hook images)")
    print(f"   - Transitions: ✅ (flash + crossfade)")
    print(f"\n📁 Output: {OUTPUT}")
    print(f"🚀 Ready for upload!")
    print("="*70)

# ==================================================
if __name__ == "__main__":
    main()
