from pydub import AudioSegment

voice = AudioSegment.from_wav("tts.wav")

rain = AudioSegment.from_mp3("ambience/night-street-rain-263233.mp3") - 12
wind = AudioSegment.from_mp3("ambience/soft-wind-318856.mp3") - 18

ambience = rain.overlay(wind)

loops = int(len(voice) / len(ambience)) + 1
ambience = (ambience * loops)[:len(voice)]

final = voice.overlay(ambience)
final.export("final_audio.wav", format="wav")

print("[OK] Audio mixed")
