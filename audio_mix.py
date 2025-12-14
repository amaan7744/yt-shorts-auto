#!/usr/bin/env python3
from pydub import AudioSegment
import os

AMBIENCE = [
    "ambience/rain.mp3",
    "ambience/wind.mp3",
    "ambience/thunder.mp3",
]

def main():
    narration = AudioSegment.from_wav("tts.wav")

    dur = len(narration)

    layers = []
    for a in AMBIENCE:
        if not os.path.exists(a):
            continue
        snd = AudioSegment.from_file(a)
        loops = (dur // len(snd)) + 2
        snd = (snd * loops)[:dur]

        # volumes
        if "rain" in a:
            snd -= 10
        elif "wind" in a:
            snd -= 14
        elif "thunder" in a:
            snd -= 18

        layers.append(snd)

    mixed = narration
    for l in layers:
        mixed = mixed.overlay(l)

    mixed.export("final_audio.wav", format="wav")
    print("[AUDIO] Final audio created.")

if __name__ == "__main__":
    main()

