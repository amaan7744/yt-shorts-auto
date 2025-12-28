#!/usr/bin/env python3
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from pydub import AudioSegment
import os

FRAMES = [
    ("frames/01_hook.jpg", 1.3),
    ("frames/02_odd.jpg", 2.2),
    ("frames/03_conflict.jpg", 2.8),
    ("frames/04_contradiction.jpg", None),
]

AUDIO = "final_audio.wav"
OUT = "video_raw.mp4"
FPS = 30

def main():
    audio = AudioSegment.from_file(AUDIO)
    total = len(audio)/1000

    used = sum(d for _,d in FRAMES if d)
    last = max(1.5, total-used)

    clips = []
    for path, dur in FRAMES:
        d = dur if dur else last
        clips.append(ImageClip(path).set_duration(d))

    video = concatenate_videoclips(clips, method="compose")
    video = video.set_audio(AudioFileClip(AUDIO))

    video.write_videofile(
        OUT,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="veryfast",
        verbose=False,
        logger=None
    )

if __name__ == "__main__":
    main()
