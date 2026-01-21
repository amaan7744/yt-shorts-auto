#!/usr/bin/env python3

import os
import sys
import json
import warnings
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# --------------------------------------------------
# SILENCE GOOGLE FUTUREWARNING
# --------------------------------------------------
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="google.api_core"
)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

VIDEO_FILE = "output.mp4"
SCRIPT_FILE = "script.txt"
META_FILE = "memory/upload_meta.json"

CATEGORY_ID = "25"  # News & Politics (crime-safe)
UPLOAD_COOLDOWN_MINUTES = 90

# --------------------------------------------------
# ENV
# --------------------------------------------------

def require_env(name: str) -> str:
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
# UPLOAD GUARD
# --------------------------------------------------

def should_pause_uploads() -> bool:
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
# METADATA AI (INLINE)
# --------------------------------------------------

def extract_hook(script: str) -> str:
    """
    Title = first sentence trimmed to curiosity length.
    """
    first = script.split(".")[0].strip()

    words = first.split()
    if len(words) > 9:
        first = " ".join(words[:9])

    return first

def build_metadata(script: str) -> dict:
    """
    Generates description, tags, hashtags.
    Title is handled separately as hook.
    """

    description = (
        "This short documents an unresolved case using public records and verified details.\n\n"
        "The facts are clear. The explanation is not.\n\n"
        "Subscribe to keep cases like this visible."
    )

    hashtags = [
        "#TrueCrime",
        "#Unsolved",
        "#CrimeShorts",
        "#Mystery",
        "#Investigation",
        "#Shorts",
    ]

    tags = [
        "true crime shorts",
        "unsolved mystery",
        "crime documentary",
        "real cases",
        "investigation",
        "shorts",
    ]

    return {
        "description": description,
        "hashtags": hashtags,
        "tags": tags,
    }

# --------------------------------------------------
# UPLOAD
# --------------------------------------------------

def upload_video(youtube, title, meta):
    body = {
        "snippet": {
            "title": title,
            "description": meta["description"] + "\n\n" + " ".join(meta["hashtags"]),
            "tags": meta["tags"],
            "categoryId": CATEGORY_ID,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
            "license": "youtube",
            "publicStatsViewable": True,
        },
        "recordingDetails": {
            "recordingDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        },
    }

    media = MediaFileUpload(
        VIDEO_FILE,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,
    )

    print(f"[YT] 🚀 Uploading Short: {title}")

    request = youtube.videos().insert(
        part="snippet,status,recordingDetails",
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
# META LOG
# --------------------------------------------------

def log_upload(video_id, title, hook):
    os.makedirs("memory", exist_ok=True)
    entry = {
        "video_id": video_id,
        "title": title,
        "hook": hook,
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

    if should_pause_uploads():
        print("[YT] ⏸ Upload paused (cooldown active)")
        sys.exit(0)

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        script = f.read().strip()

    title = extract_hook(script)
    meta = build_metadata(script)

    youtube = build_youtube()

    try:
        video_id = upload_video(youtube, title, meta)
        print(f"[YT] ✅ Live: https://youtu.be/{video_id}")

        log_upload(video_id, title, title)

    except HttpError as e:
        sys.exit(f"[YT] ❌ YouTube API error: {e}")
    except Exception as e:
        sys.exit(f"[YT] ❌ Upload failed: {e}")

if __name__ == "__main__":
    main()
