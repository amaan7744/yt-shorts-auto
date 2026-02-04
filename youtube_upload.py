#!/usr/bin/env python3
"""
YouTube Shorts Upload Script
Hardened + Honest Edition

- Strong Shorts classification
- Safe ffprobe parsing
- Honest quality reporting
- No fake compression hacks
"""

import os
import sys
import json
import warnings
import subprocess
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# --------------------------------------------------
warnings.filterwarnings("ignore", category=FutureWarning)

VIDEO_FILE = "output.mp4"
SCRIPT_FILE = "script.txt"
META_FILE = "memory/upload_meta.jsonl"

CATEGORY_ID = "22"  # People & Blogs
UPLOAD_COOLDOWN_MINUTES = 90

# --------------------------------------------------
# ENV
# --------------------------------------------------

def require_env(name):
    val = os.getenv(name)
    if not val:
        sys.exit(f"[YT] ❌ Missing env var: {name}")
    return val

# --------------------------------------------------
# AUTH
# --------------------------------------------------

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

# --------------------------------------------------
# COOLDOWN
# --------------------------------------------------

def should_pause():
    if not os.path.isfile(META_FILE):
        return False
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                return False
            last = json.loads(lines[-1])
        last_time = datetime.fromisoformat(last["uploaded_at"])
        return datetime.utcnow() - last_time < timedelta(minutes=UPLOAD_COOLDOWN_MINUTES)
    except Exception:
        return False

# --------------------------------------------------
# TITLE / META
# --------------------------------------------------

def extract_title(script: str) -> str:
    """
    Extract first full QUESTION sentence.
    """
    for line in script.splitlines():
        if "?" in line:
            title = line.strip()
            break
    else:
        title = script[:60]

    title = title.rstrip(".?!")
    title = title[:55]

    return f"{title}? #Shorts"

def build_metadata():
    description = (
        "#Shorts #TrueCrime\n"
        "An unresolved case. One detail didn’t make sense.\n\n"
        "What do YOU think really happened?"
    )

    tags = [
        "shorts",
        "youtube shorts",
        "true crime shorts",
        "unsolved mystery",
        "crime story",
        "mystery short",
        "vertical video",
    ]

    return description, tags

# --------------------------------------------------
# SHORTS VALIDATION (SAFE)
# --------------------------------------------------

def validate_shorts_format():
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json",
            VIDEO_FILE
        ]
        data = json.loads(subprocess.check_output(cmd).decode())

        stream = data["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
        duration = float(data["format"]["duration"])

        print(f"[YT] 📊 Video Stats → {width}x{height}, {duration:.2f}s")

        if height <= width:
            sys.exit("[YT] ❌ Video not vertical (Shorts rejected)")

        if duration > 60:
            sys.exit("[YT] ❌ Video longer than 60s (Shorts rejected)")

    except Exception as e:
        sys.exit(f"[YT] ❌ Shorts validation failed: {e}")

# --------------------------------------------------
# QUALITY REPORT
# --------------------------------------------------

def print_quality_report():
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=codec_name,profile,level,width,height,avg_frame_rate,"
            "format=duration,bit_rate",
            "-of", "default=noprint_wrappers=1"
        ]
        out = subprocess.check_output(cmd + [VIDEO_FILE]).decode()
        print("[YT] 📈 Upload Quality Report")
        print(out)
    except Exception as e:
        print(f"[YT] ⚠️ Could not generate quality report: {e}")

# --------------------------------------------------
# UPLOAD
# --------------------------------------------------

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

    print(f"[YT] 🚀 Uploading Short → {title}")

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

# --------------------------------------------------
# LOG
# --------------------------------------------------

def log_upload(video_id, title):
    os.makedirs("memory", exist_ok=True)
    entry = {
        "video_id": video_id,
        "title": title,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    with open(META_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if not os.path.isfile(VIDEO_FILE):
        sys.exit("[YT] ❌ output.mp4 missing")
    if not os.path.isfile(SCRIPT_FILE):
        sys.exit("[YT] ❌ script.txt missing")

    if should_pause():
        print("[YT] ⏸ Upload paused (cooldown active)")
        sys.exit(0)

    validate_shorts_format()
    print_quality_report()

    script = open(SCRIPT_FILE, "r", encoding="utf-8").read().strip()
    title = extract_title(script)
    description, tags = build_metadata()

    youtube = build_youtube()

    try:
        video_id = upload_video(youtube, title, description, tags)
        print(f"[YT] ✅ LIVE → https://youtu.be/{video_id}")
        log_upload(video_id, title)

    except HttpError as e:
        sys.exit(f"[YT] ❌ API error: {e}")
    except Exception as e:
        sys.exit(f"[YT] ❌ Upload failed: {e}")

# --------------------------------------------------
if __name__ == "__main__":
    main()
