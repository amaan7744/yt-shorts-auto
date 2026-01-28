"""
Video Compositor
Combines 3D visuals with audio and effects
"""

from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip,
    TextClip, ColorClip, concatenate_videoclips,
    CompositeAudioClip, vfx
)
from moviepy.video.fx import fadein, fadeout
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np


class VideoCompositor:
    """Compose final video with audio, effects, and transitions"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def compose_final_video(
        self,
        video_path: str,
        audio_paths: List[str],
        script_data: Dict,
        add_effects: bool = True
    ) -> str:
        """
        Create final video with all elements
        
        Args:
            video_path: Path to 3D video
            audio_paths: List of audio file paths
            script_data: Script data with timing
            add_effects: Whether to add transitions and effects
        
        Returns:
            Path to final video
        """
        print("🎬 Starting video composition...")
        
        # Load base video
        video = VideoFileClip(video_path)
        
        # Combine audio files
        audio_clip = self._create_audio_track(audio_paths, script_data)
        
        # Set audio to video
        video = video.set_audio(audio_clip)
        
        # Add text overlays if needed
        if script_data.get('add_text_overlay', True):
            video = self._add_text_overlays(video, script_data)
        
        # Add effects
        if add_effects:
            video = self._add_effects(video)
        
        # Add intro/outro if specified
        if script_data.get('add_intro', False):
            video = self._add_intro(video, script_data.get('title', 'Video'))
        
        if script_data.get('add_outro', False):
            video = self._add_outro(video, script_data.get('cta', 'Subscribe!'))
        
        # Export final video
        output_path = self.output_dir / f"{script_data['title'].replace(' ', '_')}_FINAL.mp4"
        
        video.write_videofile(
            str(output_path),
            codec='libx264',
            audio_codec='aac',
            fps=30,
            preset='medium',
            bitrate='8000k'
        )
        
        print(f"✅ Final video exported: {output_path}")
        return str(output_path)
    
    def _create_audio_track(self, audio_paths: List[str], script_data: Dict) -> AudioFileClip:
        """Combine multiple audio clips into single track"""
        
        audio_clips = []
        current_time = 0
        
        for audio_path in audio_paths:
            clip = AudioFileClip(audio_path)
            # Set start time
            clip = clip.set_start(current_time)
            audio_clips.append(clip)
            current_time += clip.duration
        
        # Combine all audio
        if len(audio_clips) > 1:
            final_audio = CompositeAudioClip(audio_clips)
        else:
            final_audio = audio_clips[0]
        
        return final_audio
    
    def _add_text_overlays(self, video: VideoFileClip, script_data: Dict) -> CompositeVideoClip:
        """Add text overlays with animations"""
        
        overlays = [video]
        current_time = 0
        
        for scene in script_data.get('scenes', []):
            # Create text clip
            txt_clip = TextClip(
                scene['text'],
                fontsize=60,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2,
                size=(video.w - 100, None),
                method='caption',
                align='center'
            )
            
            # Position and timing
            txt_clip = txt_clip.set_position(('center', 'bottom'))
            txt_clip = txt_clip.set_start(current_time)
            txt_clip = txt_clip.set_duration(scene.get('duration', 4))
            
            # Add fade in/out
            txt_clip = txt_clip.crossfadein(0.3).crossfadeout(0.3)
            
            overlays.append(txt_clip)
            current_time += scene.get('duration', 4)
        
        return CompositeVideoClip(overlays)
    
    def _add_effects(self, video: VideoFileClip) -> VideoFileClip:
        """Add visual effects to video"""
        
        # Add fade in at start
        video = video.fx(fadein, 0.5)
        
        # Add fade out at end
        video = video.fx(fadeout, 0.5)
        
        # Optional: Add zoom effect
        # video = video.resize(lambda t: 1 + 0.02 * t)
        
        return video
    
    def _add_intro(self, video: VideoFileClip, title: str) -> VideoFileClip:
        """Add intro screen"""
        
        # Create intro clip (2 seconds)
        intro_duration = 2
        
        # Background
        intro_bg = ColorClip(
            size=(video.w, video.h),
            color=(20, 20, 40),
            duration=intro_duration
        )
        
        # Title text
        title_clip = TextClip(
            title,
            fontsize=70,
            color='white',
            font='Arial-Bold',
            size=(video.w - 100, None),
            method='caption',
            align='center'
        )
        title_clip = title_clip.set_position('center')
        title_clip = title_clip.set_duration(intro_duration)
        
        # Animate title
        title_clip = title_clip.crossfadein(0.5).crossfadeout(0.5)
        
        # Combine
        intro = CompositeVideoClip([intro_bg, title_clip])
        
        # Concatenate with main video
        final_video = concatenate_videoclips([intro, video])
        
        return final_video
    
    def _add_outro(self, video: VideoFileClip, cta_text: str) -> VideoFileClip:
        """Add outro screen with CTA"""
        
        # Create outro clip (2 seconds)
        outro_duration = 2
        
        # Background
        outro_bg = ColorClip(
            size=(video.w, video.h),
            color=(20, 20, 40),
            duration=outro_duration
        )
        
        # CTA text
        cta_clip = TextClip(
            cta_text,
            fontsize=60,
            color='white',
            font='Arial-Bold',
            size=(video.w - 100, None),
            method='caption',
            align='center'
        )
        cta_clip = cta_clip.set_position('center')
        cta_clip = cta_clip.set_duration(outro_duration)
        cta_clip = cta_clip.crossfadein(0.5)
        
        # Combine
        outro = CompositeVideoClip([outro_bg, cta_clip])
        
        # Concatenate with main video
        final_video = concatenate_videoclips([video, outro])
        
        return final_video
    
    def add_background_music(
        self,
        video_path: str,
        music_path: str,
        volume: float = 0.2
    ) -> str:
        """
        Add background music to video
        
        Args:
            video_path: Path to video
            music_path: Path to music file
            volume: Music volume (0.0 to 1.0)
        
        Returns:
            Path to output video
        """
        video = VideoFileClip(video_path)
        music = AudioFileClip(music_path)
        
        # Adjust music length to match video
        if music.duration > video.duration:
            music = music.subclip(0, video.duration)
        else:
            # Loop music if it's shorter
            loops_needed = int(video.duration / music.duration) + 1
            music = concatenate_audioclips([music] * loops_needed)
            music = music.subclip(0, video.duration)
        
        # Adjust volume
        music = music.volumex(volume)
        
        # Mix with existing audio
        if video.audio:
            final_audio = CompositeAudioClip([video.audio, music])
        else:
            final_audio = music
        
        video = video.set_audio(final_audio)
        
        # Export
        output_path = str(Path(video_path).parent / f"{Path(video_path).stem}_with_music.mp4")
        video.write_videofile(output_path, codec='libx264', audio_codec='aac')
        
        return output_path
    
    def create_short_clips(
        self,
        video_path: str,
        clip_duration: int = 15,
        overlap: int = 5
    ) -> List[str]:
        """
        Split long video into multiple short clips
        
        Args:
            video_path: Source video path
            clip_duration: Duration of each clip in seconds
            overlap: Overlap between clips in seconds
        
        Returns:
            List of clip paths
        """
        video = VideoFileClip(video_path)
        
        clips = []
        start = 0
        clip_num = 0
        
        while start < video.duration:
            end = min(start + clip_duration, video.duration)
            
            clip = video.subclip(start, end)
            output_path = self.output_dir / f"clip_{clip_num:03d}.mp4"
            
            clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                fps=30
            )
            
            clips.append(str(output_path))
            clip_num += 1
            
            start += (clip_duration - overlap)
        
        return clips
    
    def add_subtitles(
        self,
        video_path: str,
        subtitle_data: List[Dict],
        style: str = "default"
    ) -> str:
        """
        Add subtitles to video
        
        Args:
            video_path: Path to video
            subtitle_data: List of dicts with 'text', 'start', 'end'
            style: Subtitle style (default, bold, outline)
        
        Returns:
            Path to output video
        """
        video = VideoFileClip(video_path)
        
        subtitle_clips = []
        
        for sub in subtitle_data:
            txt_clip = TextClip(
                sub['text'],
                fontsize=50,
                color='white' if style == "default" else 'yellow',
                font='Arial-Bold' if style == "bold" else 'Arial',
                stroke_color='black' if style == "outline" else None,
                stroke_width=2 if style == "outline" else 0,
                size=(video.w - 100, None),
                method='caption',
                align='center'
            )
            
            txt_clip = txt_clip.set_position(('center', 'bottom'))
            txt_clip = txt_clip.set_start(sub['start'])
            txt_clip = txt_clip.set_duration(sub['end'] - sub['start'])
            
            subtitle_clips.append(txt_clip)
        
        final_video = CompositeVideoClip([video] + subtitle_clips)
        
        output_path = str(Path(video_path).parent / f"{Path(video_path).stem}_subtitled.mp4")
        final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')
        
        return output_path


# Example usage
if __name__ == "__main__":
    compositor = VideoCompositor()
    
    # Example script data
    script_data = {
        'title': 'Test Video',
        'scenes': [
            {'text': 'Scene 1 text', 'duration': 4},
            {'text': 'Scene 2 text', 'duration': 4},
        ],
        'cta': 'Like and Subscribe!',
        'add_intro': True,
        'add_outro': True
    }
    
    print("Video compositor ready!")
    print("Use compose_final_video() to create your final video")
