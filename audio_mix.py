import os
import glob
from pydub import AudioSegment

VOICE_PATH = "narration.wav"
AMBIENCE_DIR = "ambience"
OUTPUT = "final_audio.wav"

def find_ambience():
    if not os.path.isdir(AMBIENCE_DIR):
        print("[AUDIO] ambience/ folder not found, skipping ambience")
        return []

    files = []
    for ext in ("*.mp3", "*.wav"):
        files.extend(glob.glob(os.path.join(AMBIENCE_DIR, ext)))

    if not files:
        print("[AUDIO] No ambience audio files found")
    return files


def main():
    if not os.path.isfile(VOICE_PATH):
        raise SystemExit(f"[AUDIO] Voice file not found: {VOICE_PATH}")

    voice = AudioSegment.from_file(VOICE_PATH)

    ambience_files = find_ambience()

    if ambience_files:
        layers = []
        for f in ambience_files:
            try:
                a = AudioSegment.from_file(f) - 18  # keep ambience subtle
                layers.append(a)
                print(f"[AUDIO] Loaded ambience: {f}")
            except Exception:
                continue

        if layers:
            ambience = layers[0]
            for l in layers[1:]:
                ambience = ambience.overlay(l)

            loops = int(len(voice) / len(ambience)) + 1
            ambience = (ambience * loops)[:len(voice)]

            final = voice.overlay(ambience)
        else:
            final = voice
    else:
        final = voice

    final.export(OUTPUT, format="wav")
    print("[AUDIO] Final audio written:", OUTPUT)


if __name__ == "__main__":
    main()
