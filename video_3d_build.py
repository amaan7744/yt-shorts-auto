#!/usr/bin/env python3
"""
3D Video Generator - Integrates with existing workflow
Converts script.txt + final_audio.wav into 3D animated video
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List

# Set environment for headless rendering
os.environ["PYOPENGL_PLATFORM"] = "egl"

try:
    from moderngl_renderer import ModernGL3DRenderer
    from video_compositor import VideoCompositor
except ImportError:
    print("⚠️ 3D modules not available, skipping 3D generation")
    sys.exit(0)


class Video3DGenerator:
    """Generate 3D video from existing script and audio"""
    
    def __init__(self):
        self.renderer = ModernGL3DRenderer(width=1080, height=1920)
        self.compositor = VideoCompositor(output_dir=".")
    
    def load_beats(self) -> List[Dict]:
        """Load timing data from beats.json"""
        if not Path("beats.json").exists():
            print("⚠️ beats.json not found")
            return []
        
        with open("beats.json", "r") as f:
            data = json.load(f)
            return data.get("beats", [])
    
    def generate_3d_video(self) -> str:
        """Generate 3D video from script"""
        
        # Load beats
        beats = self.load_beats()
        if not beats:
            print("⚠️ No beats found, using script.txt directly")
            if Path("script.txt").exists():
                script_text = Path("script.txt").read_text().strip()
                beats = [{"text": script_text, "estimated_duration": 15}]
            else:
                print("❌ No script.txt found")
                sys.exit(1)
        
        print(f"🎨 Generating 3D video with {len(beats)} scenes")
        
        # Generate frames for each beat
        all_frames = []
        for idx, beat in enumerate(beats):
            text = beat.get("text", "")
            duration = beat.get("estimated_duration", 4)
            frames_needed = int(duration * 30)  # 30 FPS
            
            print(f"  Scene {idx + 1}: {frames_needed} frames")
            
            # Alternate between particle and wave effects
            if idx % 2 == 0:
                frames = self.renderer.create_particle_system_video(
                    text=text,
                    duration_frames=frames_needed,
                    particle_count=800
                )
            else:
                frames = self.renderer.create_3d_waves_video(
                    text=text,
                    duration_frames=frames_needed
                )
            
            all_frames.extend(frames)
        
        # Save as video
        print("💾 Saving 3D video...")
        output_path = "video_3d.mp4"
        self.renderer.save_frames_as_video(all_frames, output_path, fps=30)
        
        print(f"✅ 3D video saved: {output_path}")
        return output_path
    
    def combine_with_audio(self, video_path: str, audio_path: str) -> str:
        """Combine 3D video with existing audio"""
        
        if not Path(audio_path).exists():
            print(f"⚠️ Audio file not found: {audio_path}")
            return video_path
        
        print("🎵 Combining with audio...")
        
        from moviepy.editor import VideoFileClip, AudioFileClip
        
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        
        # Match video length to audio
        if video.duration > audio.duration:
            video = video.subclip(0, audio.duration)
        
        video = video.set_audio(audio)
        
        final_path = "output_3d.mp4"
        video.write_videofile(
            final_path,
            codec='libx264',
            audio_codec='aac',
            fps=30,
            preset='ultrafast'  # Fast for CI
        )
        
        print(f"✅ Final video: {final_path}")
        return final_path


def main():
    """Main entry point"""
    print("🎬 3D Video Generator")
    
    generator = Video3DGenerator()
    
    # Generate 3D video
    video_path = generator.generate_3d_video()
    
    # Combine with audio if available
    if Path("final_audio.wav").exists():
        final_path = generator.combine_with_audio(video_path, "final_audio.wav")
        
        # Replace output.mp4 for your workflow
        if Path(final_path).exists():
            import shutil
            shutil.copy(final_path, "output.mp4")
            print("✅ Replaced output.mp4 with 3D version")
    
    print("🎉 Done!")


if __name__ == "__main__":
    main()
