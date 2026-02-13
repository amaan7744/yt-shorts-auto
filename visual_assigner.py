#!/usr/bin/env python3
"""
VISUAL ASSIGNER — PRODUCTION ENGINE
===================================

BEHAVIOR
✔ Script is source of truth
✔ No asset reuse (global)
✔ Exact audio match
✔ No duration extension
✔ Strong semantic matching
✔ Always picks best possible visual
✔ Deterministic selection
✔ Multiple visuals per segment
✔ Fail only when asset pool exhausted
✔ Debug scoring output

Requires:
pip install scikit-learn
"""

import json
import subprocess
import sys
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from assets import (
    VIDEO_ASSET_KEYWORDS,
    HOOK_IMAGE_CATEGORIES,
    validate_video_assets,
    validate_hook_images,
)


# ============================================================
# CONFIG
# ============================================================

SCRIPT_FILE = Path("script.txt")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT_FILE = Path("beats.json")

ASSET_DIR = Path("asset")
HOOK_DIR = ASSET_DIR / "hook_static"

TIMELINE_TOLERANCE = 0.01
MIN_SIM_THRESHOLD = 0.01  # very low → always choose best match


# ============================================================
# UTILS
# ============================================================

def die(msg):
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(1)


def tokenize(text):
    text = text.lower()
    words = re.findall(r"[a-zA-Z']+", text)
    return " ".join(words)


def get_media_duration(path: Path):
    if not path.exists():
        die(f"Missing media: {path}")

    r = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
    )

    try:
        return float(r.stdout.strip())
    except:
        die(f"Could not read duration for {path}")


# ============================================================
# VALIDATE ASSETS
# ============================================================

print("🔍 Validating assets...")
validate_video_assets()
validate_hook_images()


# ============================================================
# LOAD SCRIPT
# ============================================================

if not SCRIPT_FILE.exists():
    die("script.txt missing")

lines = [
    l.strip()
    for l in SCRIPT_FILE.read_text(encoding="utf-8").splitlines()
    if l.strip()
]

if len(lines) < 2:
    die("Script must contain hook + story")

HOOK_LINE = lines[0]
STORY_LINES = lines[1:]


# ============================================================
# AUDIO
# ============================================================

audio_duration = get_media_duration(AUDIO_FILE)

print("=" * 70)
print("🎬 VISUAL ASSIGNER — PRODUCTION ENGINE")
print("=" * 70)
print("🔊 Audio duration:", round(audio_duration, 2), "seconds")


# ============================================================
# TIMELINE WEIGHTING
# ============================================================

weights = [len(tokenize(l).split()) for l in lines]
total_weight = sum(weights)

segment_durations = [
    (w / total_weight) * audio_duration
    for w in weights
]

segment_durations[-1] += audio_duration - sum(segment_durations)


# ============================================================
# LOAD VIDEO ASSETS
# ============================================================

VIDEO_FILES = []
VIDEO_DURATIONS = {}
VIDEO_TEXT = []

for video, keywords in VIDEO_ASSET_KEYWORDS.items():
    path = ASSET_DIR / video
    if not path.exists():
        continue

    VIDEO_FILES.append(video)
    VIDEO_DURATIONS[video] = get_media_duration(path)

    # include filename + keywords for stronger matching
    corpus_text = video.replace("_", " ") + " " + " ".join(keywords)
    VIDEO_TEXT.append(tokenize(corpus_text))

if not VIDEO_FILES:
    die("No video assets found")


# ============================================================
# SEMANTIC MODEL
# ============================================================

vectorizer = TfidfVectorizer(stop_words="english")
video_vectors = vectorizer.fit_transform(VIDEO_TEXT)


def select_video(text, used_videos):
    """Pick best unused video by semantic similarity"""

    available = [
        i for i, v in enumerate(VIDEO_FILES)
        if v not in used_videos
    ]

    if not available:
        return None

    query = tokenize(text)
    query_vec = vectorizer.transform([query])

    sims = cosine_similarity(query_vec, video_vectors)[0]

    # sort by score descending then filename (deterministic)
    ranked = sorted(
        [(sims[i], VIDEO_FILES[i]) for i in available],
        key=lambda x: (-x[0], x[1])
    )

    best_score, best_video = ranked[0]

    print(f"   → match score {best_score:.3f} : {best_video}")

    if best_score < MIN_SIM_THRESHOLD:
        print("   ⚠ weak semantic match")

    return best_video


# ============================================================
# HOOK IMAGE SELECTION
# ============================================================

HOOK_FILES = list(HOOK_IMAGE_CATEGORIES.keys())
HOOK_TEXT = [
    tokenize(img.replace("_", " ") + " " + " ".join(HOOK_IMAGE_CATEGORIES[img]))
    for img in HOOK_FILES
]

hook_vectorizer = TfidfVectorizer(stop_words="english")
hook_vectors = hook_vectorizer.fit_transform(HOOK_TEXT)


def select_hook_images(text, count=2):
    query = tokenize(text)
    query_vec = hook_vectorizer.transform([query])
    sims = cosine_similarity(query_vec, hook_vectors)[0]

    ranked = sorted(
        zip(sims, HOOK_FILES),
        key=lambda x: (-x[0], x[1])
    )

    selected = []

    for score, img in ranked:
        if (HOOK_DIR / img).exists():
            selected.append(img)
        if len(selected) == count:
            break

    if len(selected) != count:
        die("Not enough hook images")

    return selected


# ============================================================
# BUILD TIMELINE
# ============================================================

beats = []
used_videos = set()
beat_id = 1

# ---------- HOOK ----------
hook_images = select_hook_images(HOOK_LINE)
hook_duration_each = segment_durations[0] / len(hook_images)

for img in hook_images:
    beats.append({
        "beat_id": beat_id,
        "type": "image",
        "asset_file": f"hook_static/{img}",
        "duration": hook_duration_each,
        "role": "hook"
    })
    beat_id += 1


# ---------- STORY ----------
print("\n📍 STORY TIMELINE")

for line, seg_duration in zip(STORY_LINES, segment_durations[1:]):

    remaining = seg_duration

    while remaining > 0.01:

        video = select_video(line, used_videos)

        if not video:
            die("Asset pool exhausted. Need more videos.")

        used_videos.add(video)

        asset_duration = VIDEO_DURATIONS[video]
        use_time = min(asset_duration, remaining)

        beats.append({
            "beat_id": beat_id,
            "type": "video",
            "asset_file": video,
            "duration": use_time,
            "text": line
        })

        print(f"[{beat_id:02d}] {video} ({use_time:.2f}s)")

        beat_id += 1
        remaining -= use_time


# ============================================================
# FINAL VALIDATION
# ============================================================

timeline_total = sum(b["duration"] for b in beats)

if abs(timeline_total - audio_duration) > TIMELINE_TOLERANCE:
    die("Timeline mismatch")

print("\n⏱️ Timeline:", round(timeline_total, 2))
print("Unique videos used:", len(used_videos))

OUTPUT_FILE.write_text(
    json.dumps({"beats": beats}, indent=2),
    encoding="utf-8"
)

print("\n✅ Timeline ready → beats.json")
