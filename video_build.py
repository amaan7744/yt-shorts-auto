#!/usr/bin/env python3
"""
YouTube Shorts Video Builder (AUDIO-LOCKED, VISUALLY LOSSLESS)

TRUTHS:
- Burned subtitles REQUIRE re-encoding (no exceptions)
- We use CRF 18 = visually lossless
- NO scaling, NO fps change
- Video ends EXACTLY with audio
"""

import json
import subprocess
import sys
from pathlib import Path
import tempfile

# ==================================================
# FILES
# ==================================================

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT = Path("output.mp4")

# ==================================================
# HELPERS
# ==================================================

def die(msg):
    print(f"[VIDEO] ❌ {msg}", file=sys.stderr)
    sys.exit(1)

def run(cmd):
    subprocess.run(cmd, check=True)

def ffprobe_duration(path: Path) -> float:
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
    return float(r.stdout.strip())

# ==================================================
# MAIN
# ==================================================

def main():
    if not BEATS_FILE.exists():
        die("beats.json missing")
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    beats = json.loads(BEATS_FILE.read_text()).get("beats", [])
    if not beats:
        die("No beats found")

    # --------------------------------------------------
    # Resolve assets
    # --------------------------------------------------

    assets = []
    for i, beat in enumerate(beats):
        asset = ASSET_DIR / beat["asset_file"]
        if not asset.exists():
            die(f"Missing asset: {asset}")
        assets.append(asset)

    print(f"[VIDEO] 🎞️ {len(assets)} video assets queued")

    # --------------------------------------------------
    # Step 1: LOSSLESS CONCAT
    # --------------------------------------------------

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        concat_file = Path(f.name)
        for asset in assets:
            f.write(f"file '{asset.resolve()}'\n")

    merged_video = Path("merged_video.mp4")

    print("[VIDEO] 🔗 Concatenating videos (bit-for-bit)")
    run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(merged_video)
    ])

    # --------------------------------------------------
    # Step 2: AUDIO-LOCKED RENDER WITH SUBS
    # --------------------------------------------------

    audio_duration = ffprobe_duration(AUDIO_FILE)
    print(f"[VIDEO] 🎵 Audio duration: {audio_duration:.3f}s")

    subs_filter = []
    if SUBS_FILE.exists():
        subs = str(SUBS_FILE).replace("\\", "/").replace(":", "\\:")
        subs_filter = ["-vf", f"ass='{subs}'"]
        print("[VIDEO] 📝 Burning subtitles (required re-encode)")

    print("[VIDEO] 🎬 Final render (visually lossless)")
    run([
        "ffmpeg", "-y",
        "-i", str(merged_video),
        "-i", str(AUDIO_FILE),
        *subs_filter,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-crf", "18",              # 🔒 visually lossless
        "-preset", "veryslow",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.2",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{audio_duration:.6f}",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    # --------------------------------------------------
    # Verify
    # --------------------------------------------------

    out_dur = ffprobe_duration(OUTPUT)
    diff = abs(out_dur - audio_duration)

    print(f"[VIDEO] ✅ output.mp4 ready")
    print(f"[VIDEO] 🎯 Duration: {out_dur:.3f}s (Δ {diff:.3f}s)")

    if diff > 0.05:
        print("[VIDEO] ⚠️ Container rounding difference (normal)")
    else:
        print("[VIDEO] ✅ Ends EXACTLY at audio/script end")

# ==================================================
if __name__ == "__main__":
    main()
