#!/usr/bin/env python3
"""
YouTube Shorts Upload Script
ENHANCED Shorts classification signals
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

CATEGORY_ID = "22"  # People & Blogs
UPLOAD_COOLDOWN_MINUTES = 90

def require_env(name):
    val = os.getenv(name)
    if not val:
        sys.exit(f"[YT] ❌ Missing env var: {name}")
    return val

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

def should_pause():
    if not os.path.isfile(META_FILE):
        return False
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines: return False
            last = json.loads(lines[-1])
        last_time = datetime.fromisoformat(last["uploaded_at"])
        return datetime.utcnow() - last_time < timedelta(minutes=UPLOAD_COOLDOWN_MINUTES)
    except Exception:
        return False

def extract_title(script: str) -> str:
    first = script.split(".")[0].strip()
    words = first.split()
    # 🔑 CRITICAL: Title must contain #Shorts for the API to prioritize short-form processing
    title = " ".join(words[:7])
    title = title.rstrip(".?!")
    final_title = f"{title[:52]} #Shorts"
    return final_title

def build_metadata():
    # 🔑 CRITICAL: Description MUST contain #Shorts in the first two lines
    description = (
        "#Shorts #TrueCrime\n"
        "Unresolved case. Verified records. No conclusions.\n\n"
        "Subscribe for more daily shorts."
    )

    tags = ["shorts", "trending", "crime", "mystery"]
    return description, tags

def validate_shorts_format():
    """
    Checks if the video is actually Vertical and under 60 seconds.
    If it isn't, YouTube will NEVER put it in the Shorts shelf.
    """
    try:
        # Get dimensions and duration
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            VIDEO_FILE
        ]
        out = subprocess.check_output(cmd).decode().split()
        
        width = int(out[0])
        height = int(out[1])
        duration = float(out[2])

        print(f"[YT] 📊 Video Stats: {width}x{height}, {duration}s")

        if height < width:
            print("[YT] ⚠️ WARNING: Video is horizontal. It will NOT appear as a Short.")
        
        if duration > 60:
            print("[YT] ❌ ERROR: Video is longer than 60s. API will treat as long-form.")
            sys.exit(1)

    except Exception as e:
        print(f"[YT] ⚠️ Could not validate format: {e}")

def upload_video(youtube, title, description, tags):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": CATEGORY_ID,
            "defaultLanguage": "en",
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

def log_upload(video_id, title):
    os.makedirs("memory", exist_ok=True)
    entry = {
        "video_id": video_id,
        "title": title,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    with open(META_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def main():
    if not os.path.isfile(VIDEO_FILE):
        sys.exit("[YT] ❌ output.mp4 missing")
    if not os.path.isfile(SCRIPT_FILE):
        sys.exit("[YT] ❌ script.txt missing")

    if should_pause():
        print("[YT] ⏸ Upload paused (cooldown)")
        sys.exit(0)

    # 1. Check if the file is physically a Short
    validate_shorts_format()

    script = open(SCRIPT_FILE, "r", encoding="utf-8").read().strip()
    
    # 2. Add #Shorts to Title and Description
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
