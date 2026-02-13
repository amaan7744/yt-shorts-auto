#!/usr/bin/env python3
"""
VISUAL ASSIGNER — STRICT SEMANTIC ENGINE (FULL REWRITE)
=======================================================

CORE GUARANTEES
✔ Script = source of truth
✔ No visual duration extension
✔ No frame freezing
✔ No zoom/stretch
✔ No asset reuse inside same video
✔ Exact audio timeline match
✔ Semantic visual selection
✔ Deterministic output
✔ Multiple visuals per narration segment if needed
✔ Hard fail if asset pool insufficient
✔ Hard fail if no relevant asset exists
"""

import json
import subprocess
import sys
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from assets import VIDEO_ASSET_KEYWORDS, HOOK_IMAGE_CATEGORIES


# ============================================================
# CONFIG
# ============================================================

SCRIPT_FILE = Path("script.txt")
AUDIO_FILE = Path("final_audio.wav")
OUTPUT_FILE = Path("beats.json")

ASSET_DIR = Path("asset")
HOOK_DIR = ASSET_DIR / "hook_static"

SEMANTIC_THRESHOLD = 0.05
TIMELINE_TOLERANCE = 0.01


# ============================================================
# UTILS
# ============================================================

def die(msg: str):
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(1)


def tokenize(text: str):
    """Clean word extraction"""
    text = text.lower()
    words = re.findall(r"[a-zA-Z']+", text)
    return {w for w in words if len(w) > 2}


def get_media_duration(path: Path):
    """Read media duration using ffprobe"""
    if not path.exists():
        die(f"Missing media file: {path}")

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
    except Exception:
        die(f"Could not read duration for {path}")


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
    die("Script must contain hook + story lines")

HOOK_LINE = lines[0]
STORY_LINES = lines[1:]


# ============================================================
# AUDIO
# ============================================================

audio_duration = get_media_duration(AUDIO_FILE)

print("=" * 70)
print("🎬 VISUAL ASSIGNER — STRICT SEMANTIC ENGINE")
print("=" * 70)
print("🔊 Audio duration:", round(audio_duration, 2), "seconds")


# ============================================================
# TIMELINE ALLOCATION FROM SCRIPT WEIGHT
# ============================================================

weights = [len(tokenize(l)) for l in lines]
total_weight = sum(weights)

if total_weight == 0:
    die("Script contains no usable words")

segment_durations = [
    (w / total_weight) * audio_duration
    for w in weights
]

# rounding correction
segment_durations[-1] += audio_duration - sum(segment_durations)


# ============================================================
# LOAD VIDEO ASSETS
# ============================================================

VIDEO_FILES = []
VIDEO_DURATIONS = {}
VIDEO_KEYWORD_TEXT = []

for video_name, keywords in VIDEO_ASSET_KEYWORDS.items():
    path = ASSET_DIR / video_name

    if not path.exists():
        continue

    VIDEO_FILES.append(video_name)
    VIDEO_DURATIONS[video_name] = get_media_duration(path)
    VIDEO_KEYWORD_TEXT.append(" ".join(keywords))

if not VIDEO_FILES:
    die("No video assets found in asset directory")

if len(VIDEO_FILES) < len(STORY_LINES):
    die("Not enough video assets for strict non-reuse")


# ============================================================
# BUILD SEMANTIC MODEL (TF-IDF)
# ============================================================

vectorizer = TfidfVectorizer()
video_vectors = vectorizer.fit_transform(VIDEO_KEYWORD_TEXT)


def select_video(text, used_videos):
    """
    Select best unused video based on semantic similarity.
    Hard fail if no meaningful match exists.
    """

    available_indices = [
        i for i, v in enumerate(VIDEO_FILES)
        if v not in used_videos
    ]

    if not available_indices:
        return None

    query_vec = vectorizer.transform([text])
    similarities = cosine_similarity(query_vec, video_vectors)[0]

    best_score = 0
    best_video = None

    for idx in available_indices:
        if similarities[idx] > best_score:
            best_score = similarities[idx]
            best_video = VIDEO_FILES[idx]

    if best_score < SEMANTIC_THRESHOLD:
        return None

    return best_video


# ============================================================
# HOOK IMAGE SELECTION
# ============================================================

def select_hook_images(text, count=2):
    """Select most relevant hook images"""

    words = tokenize(text)
    scored = []

    for img, keywords in HOOK_IMAGE_CATEGORIES.items():
        score = sum(1 for k in keywords if k in words)
        if score > 0 and (HOOK_DIR / img).exists():
            scored.append((score, img))

    scored.sort(reverse=True)

    selected = [img for _, img in scored[:count]]

    if len(selected) != count:
        die("Not enough relevant hook images")

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
            die(
                "No unused video semantically matches script.\n"
                "Add more assets or improve asset keywords."
            )

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
    die("Timeline does not match audio duration")

print("\n⏱️ Timeline:", round(timeline_total, 2), "seconds")
print("Unique videos used:", len(used_videos))

OUTPUT_FILE.write_text(
    json.dumps({"beats": beats}, indent=2),
    encoding="utf-8"
)

print("\n✅ Timeline ready → beats.json")
