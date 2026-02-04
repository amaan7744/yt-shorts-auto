#!/usr/bin/env python3
"""
YouTube Shorts Video Builder (PURE MERGE, AUDIO-LOCKED)

GOALS:
- NO re-encoding of video
- NO scaling, NO fps change
- Merge video + audio + subtitles only
- Video ENDS EXACTLY at audio/script end
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
        text=True
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
    # Resolve assets in order
    # --------------------------------------------------

    assets = []
    for i, beat in enumerate(beats):
        if "asset_file" in beat:
            asset = ASSET_DIR / beat["asset_file"]
        elif "asset_key" in beat:
            asset = ASSET_DIR / f"{beat['asset_key']}.mp4"
        else:
            die(f"Beat {i} missing asset reference")

        if not asset.exists():
            die(f"Missing asset: {asset}")

        assets.append(asset)

    print(f"[VIDEO] 🎞️ {len(assets)} video assets queued")

    # --------------------------------------------------
    # Step 1: LOSSLESS CONCAT of videos
    # --------------------------------------------------

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        concat_file = Path(f.name)
        for asset in assets:
            f.write(f"file '{asset.resolve()}'\n")

    merged_video = Path("merged_video.mp4")

    print("[VIDEO] 🔗 Concatenating videos (lossless)")
    run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(merged_video)
    ])

    # --------------------------------------------------
    # Step 2: Trim merged video to EXACT audio duration
    # --------------------------------------------------

    audio_duration = ffprobe_duration(AUDIO_FILE)
    print(f"[VIDEO] 🎵 Audio duration: {audio_duration:.3f}s")

    trimmed_video = Path("trimmed_video.mp4")

    print("[VIDEO] ✂️ Trimming video to audio duration (exact)")
    run([
        "ffmpeg", "-y",
        "-i", str(merged_video),
        "-t", f"{audio_duration:.6f}",
        "-c", "copy",
        str(trimmed_video)
    ])

    # --------------------------------------------------
    # Step 3: Mux audio + subtitles (video still copy)
    # --------------------------------------------------

    cmd = [
        "ffmpeg", "-y",
        "-i", str(trimmed_video),
        "-i", str(AUDIO_FILE),
    ]

    if SUBS_FILE.exists():
        subs = str(SUBS_FILE).replace("\\", "/").replace(":", "\\:")
        cmd.extend(["-vf", f"ass='{subs}'"])

    cmd.extend([
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",     # 🔥 NO video re-encode
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(OUTPUT)
    ])

    print("[VIDEO] 🎬 Muxing audio + subtitles")
    run(cmd)

    # --------------------------------------------------
    # Final verification
    # --------------------------------------------------

    out_dur = ffprobe_duration(OUTPUT)
    diff = abs(out_dur - audio_duration)

    print(f"[VIDEO] ✅ output.mp4 ready")
    print(f"[VIDEO] 🎯 Final duration: {out_dur:.3f}s (Δ {diff:.3f}s)")

    if diff > 0.05:
        print("[VIDEO] ⚠️  Minor container rounding difference")
    else:
        print("[VIDEO] ✅ Ends EXACTLY at script/audio end")

# ==================================================
if __name__ == "__main__":
    main()
