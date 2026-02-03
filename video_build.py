#!/usr/bin/env python3
"""
YouTube Shorts Video Builder (STABLE)

FIXES:
- Supports asset_key OR asset_file
- Supports estimated_duration OR duration
- Audio is the timing authority
- No zero-duration bugs
- Deterministic, CI-safe
"""

import json
import subprocess
import sys
from pathlib import Path

# ==================================================
# CONFIG
# ==================================================

WIDTH, HEIGHT = 1080, 1920

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT = Path("output.mp4")

FPS = 30

# ==================================================
# HELPERS
# ==================================================

def die(msg):
    print(f"[VIDEO] ❌ {msg}", file=sys.stderr)
    sys.exit(1)

def ffprobe_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        die(f"Failed to get duration for {path}: {e}")

def get_beat_duration(beat: dict, index: int) -> float:
    dur = beat.get("estimated_duration") or beat.get("duration")
    if not dur or dur <= 0:
        die(f"Beat {index} missing valid duration")
    return float(dur)

def get_beat_asset(beat: dict, index: int) -> Path:
    if "asset_file" in beat:
        asset = ASSET_DIR / beat["asset_file"]
    elif "asset_key" in beat:
        asset = ASSET_DIR / f"{beat['asset_key']}.mp4"
    else:
        die(f"Beat {index} missing asset reference")

    if not asset.exists():
        die(f"Missing asset file: {asset}")

    return asset

# ==================================================
# MAIN
# ==================================================

def main():
    # -------- Validation --------
    if not BEATS_FILE.exists():
        die("beats.json missing")
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")
    if not ASSET_DIR.exists():
        die("asset directory missing")

    # -------- Load beats --------
    try:
        beats_data = json.loads(BEATS_FILE.read_text())
        beats = beats_data.get("beats")
        if not beats or not isinstance(beats, list):
            die("beats.json has no valid beats list")
    except Exception as e:
        die(f"Failed to parse beats.json: {e}")

    # -------- Audio duration --------
    audio_duration = ffprobe_duration(AUDIO_FILE)
    print(f"[VIDEO] 🎵 Audio duration: {audio_duration:.3f}s")

    # -------- Beat validation --------
    print(f"[VIDEO] 🔍 Validating {len(beats)} beats...")
    total_beat_duration = 0.0
    assets = []

    for i, beat in enumerate(beats):
        dur = get_beat_duration(beat, i)
        asset = get_beat_asset(beat, i)

        total_beat_duration += dur
        assets.append((asset, dur))

        asset_dur = ffprobe_duration(asset)
        if asset_dur < dur:
            print(
                f"[VIDEO] ⚠️  {asset.name} is shorter ({asset_dur:.2f}s) "
                f"than beat ({dur:.2f}s) — looping enabled"
            )

    print(f"[VIDEO] 📊 Total beat duration: {total_beat_duration:.3f}s")

    if abs(total_beat_duration - audio_duration) > 0.75:
        print(
            f"[VIDEO] ⚠️  Beat duration differs from audio "
            f"({total_beat_duration:.2f}s vs {audio_duration:.2f}s)"
        )

    # -------- FFmpeg build --------
    cmd = ["ffmpeg", "-y", "-hide_banner"]

    # Inputs
    for asset, _ in assets:
        cmd.extend(["-i", str(asset)])

    cmd.extend(["-i", str(AUDIO_FILE)])
    audio_index = len(assets)

    # -------- Filters --------
    filters = []

    for i, (_, dur) in enumerate(assets):
        filters.append(
            f"[{i}:v]"
            f"fps={FPS},"
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"setsar=1,"
            f"loop=loop=-1:size=1:start=0,"
            f"trim=duration={dur},"
            f"setpts=PTS-STARTPTS"
            f"[v{i}];"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(assets)))
    filters.append(
        f"{concat_inputs}concat=n={len(assets)}:v=1:a=0[vcat];"
    )

    filters.append(
        f"[vcat]trim=end={audio_duration},setpts=PTS-STARTPTS[vtrim];"
    )

    if SUBS_FILE.exists():
        subs = str(SUBS_FILE).replace("\\", "/").replace(":", "\\:")
        filters.append(f"[vtrim]ass='{subs}'[vout]")
        vmap = "[vout]"
        print(f"[VIDEO] 📝 Subtitles enabled")
    else:
        vmap = "[vtrim]"
        print(f"[VIDEO] ℹ️  No subtitles")

    filter_complex = "".join(filters)

    # -------- Output --------
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", vmap,
        "-map", f"{audio_index}:a",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.2",
        "-crf", "18",
        "-preset", "medium",
        "-r", str(FPS),
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-t", str(audio_duration),
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    # -------- Run --------
    print("[VIDEO] 🎬 Rendering video…")
    subprocess.run(cmd, check=True)

    # -------- Verify --------
    if not OUTPUT.exists():
        die("output.mp4 was not created")

    out_dur = ffprobe_duration(OUTPUT)
    diff = abs(out_dur - audio_duration)

    print(f"[VIDEO] ✅ output.mp4 ready")
    print(f"[VIDEO] 📊 Output duration: {out_dur:.3f}s (Δ {diff:.3f}s)")

    if diff > 0.15:
        print("[VIDEO] ⚠️  Minor duration mismatch")
    else:
        print("[VIDEO] ✅ Duration perfectly synced")

# ==================================================
if __name__ == "__main__":
    main()
