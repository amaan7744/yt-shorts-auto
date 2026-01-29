#!/usr/bin/env python3
"""
YouTube Shorts Upload Script
STRONG Shorts classification signals
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

warnings.filterwarnings("ignore", category=FutureWarning)

VIDEO_FILE = "output.mp4"
SCRIPT_FILE = "script.txt"
META_FILE = "memory/upload_meta.jsonl"

CATEGORY_ID = "22"  # People & Blogs (Shorts-friendly)
UPLOAD_COOLDOWN_MINUTES = 90


# --------------------------------------------------

def require_env(name):
    val = os.getenv(name)
    if not val:
        sys.exit(f"[YT] ❌ Missing env var: {name}")
    return val


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

def should_pause():
    if not os.path.isfile(META_FILE):
        return False
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            last = json.loads(list(f)[-1])
        last_time = datetime.fromisoformat(last["uploaded_at"])
        return datetime.utcnow() - last_time < timedelta(minutes=UPLOAD_COOLDOWN_MINUTES)
    except Exception:
        return False


# --------------------------------------------------
# 🔑 TITLE: SHORTS HOOK, NOT SUMMARY
# --------------------------------------------------

def extract_title(script: str) -> str:
    first = script.split(".")[0].strip()
    words = first.split()

    # 6–8 words max (Shorts hook)
    title = " ".join(words[:7])

    # Remove punctuation that signals long-form
    title = title.rstrip(".?!")

    return title[:60]


# --------------------------------------------------
# 🔑 METADATA
# --------------------------------------------------

def build_metadata():
    description = (
        "#Shorts #TrueCrime\n"
        "Unresolved case. Verified records. No conclusions."
    )

    tags = [
        "shorts",
        "youtube shorts",
        "true crime shorts",
        "unsolved mystery",
        "crime short",
        "vertical video",
    ]

    return description, tags


# --------------------------------------------------
# 🔑 HARD VIDEO VALIDATION
# --------------------------------------------------

def validate_video():
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            VIDEO_FILE
        ]).decode().strip()

        if not out:
            sys.exit("[YT] ❌ No video stream detected")

    except Exception:
        sys.exit("[YT] ❌ Video validation failed")


# --------------------------------------------------

def upload_video(youtube, title, description, tags):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": CATEGORY_ID,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
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

    print(f"[YT] 🚀 Uploading SHORT → {title}")

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

def main():
    if not os.path.isfile(VIDEO_FILE):
        sys.exit("[YT] ❌ output.mp4 missing")
    if not os.path.isfile(SCRIPT_FILE):
        sys.exit("[YT] ❌ script.txt missing")

    if should_pause():
        print("[YT] ⏸ Upload paused (cooldown)")
        sys.exit(0)

    validate_video()

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


if __name__ == "__main__":
    main()
