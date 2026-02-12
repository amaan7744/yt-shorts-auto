#!/usr/bin/env python3
"""
YouTube Shorts Upload — Production Edition

FIXES
✔ Auto-detect output video (no hardcoded filename)
✔ Supports output/shorts_4k.mp4
✔ Strong Shorts validation
✔ Smart metadata generation
✔ Keyword extraction from script
✔ Better title generation
✔ Stable upload handling
✔ Production-safe logging
"""

import os
import sys
import json
import subprocess
import warnings
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


warnings.filterwarnings("ignore", category=FutureWarning)

# ==========================================================
# CONFIG
# ==========================================================

VIDEO_CANDIDATES = [
    "output/shorts_4k.mp4",
    "output.mp4",
    "shorts.mp4"
]

SCRIPT_FILE = "script.txt"
META_FILE = "memory/upload_meta.jsonl"

CATEGORY_ID = "22"
UPLOAD_COOLDOWN_MINUTES = 90


# ==========================================================
# ENV
# ==========================================================

def require_env(name):
    val = os.getenv(name)
    if not val:
        sys.exit(f"[YT] ❌ Missing env var: {name}")
    return val


# ==========================================================
# AUTO VIDEO DETECTION (FIXED)
# ==========================================================

def find_video_file():
    for path in VIDEO_CANDIDATES:
        if os.path.isfile(path):
            print(f"[YT] 🎬 Using video: {path}")
            return path

    sys.exit("[YT] ❌ No output video found")


VIDEO_FILE = find_video_file()


# ==========================================================
# AUTH
# ==========================================================

def build_youtube():
    creds = Credentials(
        token=None,
        refresh_token=require_env("YT_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=require_env("YT_CLIENT_ID"),
        client_secret=require_env("YT_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)


# ==========================================================
# COOLDOWN
# ==========================================================

def should_pause():
    if not os.path.isfile(META_FILE):
        return False

    try:
        with open(META_FILE) as f:
            lines = f.readlines()
            if not lines:
                return False

            last = json.loads(lines[-1])

        last_time = datetime.fromisoformat(last["uploaded_at"])
        return datetime.utcnow() - last_time < timedelta(minutes=UPLOAD_COOLDOWN_MINUTES)

    except Exception:
        return False


# ==========================================================
# TITLE + METADATA (UPGRADED)
# ==========================================================

def extract_keywords(script):
    words = [
        w.lower().strip(".,!?")
        for w in script.split()
        if len(w) > 4
    ]

    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    return sorted(freq, key=freq.get, reverse=True)[:5]


def extract_title(script):
    """
    Use first question line or create curiosity hook
    """
    for line in script.splitlines():
        if "?" in line:
            base = line.strip()
            break
    else:
        base = script.splitlines()[0]

    base = base.rstrip(".?!")[:55]
    return f"{base}? #Shorts"


def build_metadata(script):
    keywords = extract_keywords(script)

    description = (
        "🔎 True Crime Short\n\n"
        "A disturbing mystery. One detail changes everything.\n\n"
        "What really happened?\n\n"
        "#Shorts #TrueCrime #Mystery\n"
    )

    tags = list(set([
        "shorts",
        "youtube shorts",
        "true crime",
        "unsolved mystery",
        "crime story",
        "mystery",
        "vertical video",
        *keywords
    ]))

    return description, tags


# ==========================================================
# SHORTS VALIDATION
# ==========================================================

def validate_shorts_format():
    try:
        cmd = [
            "ffprobe",
            "-v","error",
            "-show_entries","stream=width,height:format=duration",
            "-of","json",
            VIDEO_FILE
        ]

        data = json.loads(subprocess.check_output(cmd).decode())

        stream = data["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
        duration = float(data["format"]["duration"])

        print(f"[YT] 📊 {width}x{height} | {duration:.2f}s")

        if height <= width:
            sys.exit("[YT] ❌ Video not vertical")

        if duration > 60:
            sys.exit("[YT] ❌ Video longer than 60s")

    except Exception as e:
        sys.exit(f"[YT] ❌ Validation failed: {e}")


# ==========================================================
# QUALITY REPORT
# ==========================================================

def print_quality_report():
    try:
        cmd = [
            "ffprobe",
            "-v","error",
            "-select_streams","v:0",
            "-show_entries",
            "stream=codec_name,width,height,avg_frame_rate,bit_rate",
            "-of","default=noprint_wrappers=1",
            VIDEO_FILE
        ]
        print("[YT] 📈 Upload Quality Report")
        print(subprocess.check_output(cmd).decode())
    except:
        pass


# ==========================================================
# UPLOAD
# ==========================================================

def upload_video(youtube, title, description, tags):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": CATEGORY_ID,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        VIDEO_FILE,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,
    )

    print(f"[YT] 🚀 Uploading → {title}")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[YT] ⏳ {int(status.progress() * 100)}%")

    return response["id"]


# ==========================================================
# LOG
# ==========================================================

def log_upload(video_id, title):
    os.makedirs("memory", exist_ok=True)

    entry = {
        "video_id": video_id,
        "title": title,
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    with open(META_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ==========================================================
# MAIN
# ==========================================================

def main():
    if not os.path.isfile(SCRIPT_FILE):
        sys.exit("[YT] ❌ script.txt missing")

    if should_pause():
        print("[YT] ⏸ Upload paused (cooldown active)")
        sys.exit(0)

    validate_shorts_format()
    print_quality_report()

    script = open(SCRIPT_FILE).read().strip()

    title = extract_title(script)
    description, tags = build_metadata(script)

    youtube = build_youtube()

    try:
        video_id = upload_video(youtube, title, description, tags)
        print(f"[YT] ✅ LIVE → https://youtu.be/{video_id}")
        log_upload(video_id, title)

    except HttpError as e:
        sys.exit(f"[YT] ❌ API error: {e}")

    except Exception as e:
        sys.exit(f"[YT] ❌ Upload failed: {e}")


if __name__ == "__main__":
    main()
