from pydub import AudioSegment

audio = AudioSegment.from_wav("final_audio.wav")
script = open("script.txt", encoding="utf-8").read()

lines = [l.strip() for l in script.split(". ") if l.strip()]
per = audio.duration_seconds / len(lines)

def fmt(t):
    s = int(t)
    ms = int((t - s) * 1000)
    return f"00:00:{s:02d},{ms:03d}"

with open("subs.srt", "w", encoding="utf-8") as f:
    t = 0.0
    for i, line in enumerate(lines, 1):
        f.write(f"{i}\n")
        f.write(f"{fmt(t)} --> {fmt(t+per)}\n")
        f.write(line + "\n\n")
        t += per

print("[OK] Subtitles generated")
