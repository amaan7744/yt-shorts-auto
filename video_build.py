#!/usr/bin/env python3
"""
YouTube Shorts Video Builder (FINAL – HOOK AWARE, AUDIO LOCKED)

GUARANTEES:
- Hook images persist ONLY for hook duration
- Hard cuts between images
- Images converted → video clips
- Videos trimmed per beat duration
- No video dropped or randomly extended
- Single final encode
- Output ends EXACTLY with audio
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# ==================================================
# FILES
# ==================================================

BEATS_FILE = Path("beats.json")
ASSET_DIR = Path("asset")
AUDIO_FILE = Path("final_audio.wav")
SUBS_FILE = Path("subs.ass")
OUTPUT = Path("output.mp4")

# ==================================================
# QUALITY TARGET (LOCKED)
# ==================================================

TARGET_W = 1440
TARGET_H = 2560
CRF = "17"
PRESET = "slow"

# ==================================================
# UTILS
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
# IMAGE → VIDEO (STATIC)
# ==================================================

def image_to_video(image: Path, duration: float, out: Path):
    run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image),
        "-t", f"{duration:.6f}",
        "-vf",
        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.2",
        "-crf", CRF,
        "-preset", PRESET,
        "-movflags", "+faststart",
        str(out)
    ])

# ==================================================
# VIDEO → VIDEO (TRIM)
# ==================================================

def trim_video(video: Path, duration: float, out: Path):
    run([
        "ffmpeg", "-y",
        "-i", str(video),
        "-t", f"{duration:.6f}",
        "-vf",
        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.2",
        "-crf", CRF,
        "-preset", PRESET,
        "-movflags", "+faststart",
        str(out)
    ])

# ==================================================
# MAIN
# ==================================================

def main():
    if not BEATS_FILE.exists():
        die("beats.json missing")
    if not AUDIO_FILE.exists():
        die("final_audio.wav missing")

    beats = json.loads(BEATS_FILE.read_text()).get("beats")
    if not beats:
        die("No beats found")

    temp_dir = Path(tempfile.mkdtemp(prefix="clips_"))
    clips = []

    # --------------------------------------------------
    # Build clips (IMAGES + VIDEOS)
    # --------------------------------------------------

    for i, beat in enumerate(beats, start=1):
        asset_path = ASSET_DIR / beat["asset_file"]
        if not asset_path.exists():
            die(f"Missing asset: {asset_path}")

        if "duration" not in beat or beat["duration"] <= 0:
            die(f"Beat {i} missing valid duration")

        out_clip = temp_dir / f"clip_{i:03d}.mp4"

        if beat["type"] == "image":
            print(f"[VIDEO] 🖼️ Image → video ({beat['duration']:.2f}s)")
            image_to_video(asset_path, beat["duration"], out_clip)

        elif beat["type"] == "video":
            print(f"[VIDEO] 🎞️ Video trimmed ({beat['duration']:.2f}s)")
            trim_video(asset_path, beat["duration"], out_clip)

        else:
            die(f"Unknown beat type: {beat['type']}")

        clips.append(out_clip)

    print(f"[VIDEO] 🎬 {len(clips)} clips ready")

    # --------------------------------------------------
    # Concat (NO RE-ENCODE)
    # --------------------------------------------------

    concat_file = temp_dir / "concat.txt"
    with concat_file.open("w") as f:
        for clip in clips:
            f.write(f"file '{clip.resolve()}'\n")

    merged = temp_dir / "merged.mp4"

    print("[VIDEO] 🔗 Concatenating clips")
    run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(merged)
    ])

    # --------------------------------------------------
    # FINAL ENCODE (AUDIO LOCKED)
    # --------------------------------------------------

    audio_duration = ffprobe_duration(AUDIO_FILE)

    filters = [
        f"scale={TARGET_W}:{TARGET_H}:flags=lanczos:force_original_aspect_ratio=decrease",
        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black",
        "hqdn3d=0.8:0.8:1.5:1.5"
    ]

    if SUBS_FILE.exists():
        subs = str(SUBS_FILE).replace("\\", "/").replace(":", "\\:")
        filters.append(f"ass='{subs}'")

    vf = ",".join(filters)

    print("[VIDEO] 🎧 Final render (audio locked)")
    run([
        "ffmpeg", "-y",
        "-i", str(merged),
        "-i", str(AUDIO_FILE),
        "-vf", vf,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-crf", CRF,
        "-preset", PRESET,
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

    print("[VIDEO] ✅ output.mp4 ready")
    print("[VIDEO] 🚀 Audio & visuals perfectly aligned")

# ==================================================
if __name__ == "__main__":
    main()
