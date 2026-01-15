#!/usr/bin/env python3

import os
import sys
import json
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from intelligence.seo_builder import build_seo
from intelligence.upload_guard import should_pause_uploads

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

VIDEO_FILE = "output.mp4"
SCRIPT_FILE = "script.txt"
META_FILE = "memory/upload_meta.json"

SHORTS_HASHTAG = "#Shorts"
CATEGORY_ID = "25"  # News & Politics (better for crime / investigation Shorts)

# --------------------------------------------------
# UTILS
# --------------------------------------------------

def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"[YT] ❌ Missing env var: {name}", file=sys.stderr)
        sys.exit(1)
    return val

def clamp_title(title: str) -> str:
    """
    Shorts titles perform best at 40–70 chars.
    Hard cap at 70 without cutting words.
    """
    title = title.strip()
    if len(title) <= 70:
        return title
    return title[:67].rsplit(" ", 1)[0] + "…"

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
# UPLOAD
# --------------------------------------------------

def upload_video(youtube, seo_data):
    """
    Shorts-optimized upload.
    """

    title = clamp_title(seo_data["title"])

    hashtags = seo_data.get("hashtags", [])
    if SHORTS_HASHTAG.lower() not in " ".join(hashtags).lower():
        hashtags.append(SHORTS_HASHTAG)

    description = f"{seo_data['description']}\n\n" + " ".join(hashtags)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": seo_data.get("tags", []),
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

    return response["id"], title

# --------------------------------------------------
# THUMBNAIL (NON-BLOCKING)
# --------------------------------------------------

def try_set_thumbnail(youtube, video_id):
    thumb = "thumbnail.jpg"
    if not os.path.isfile(thumb):
        return
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumb),
        ).execute()
    except Exception:
        pass  # Never block Shorts uploads

# --------------------------------------------------
# META LOGGING
# --------------------------------------------------

def log_upload_meta(video_id, title, hook):
    os.makedirs("memory", exist_ok=True)
    meta = {
        "video_id": video_id,
        "title": title,
        "hook_text": hook,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    with open(META_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(meta) + "\n")

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if not os.path.isfile(VIDEO_FILE):
        sys.exit("[YT] ❌ output.mp4 missing")
    if not os.path.isfile(SCRIPT_FILE):
        sys.exit("[YT] ❌ script.txt missing")

    # Channel safety guard
    if should_pause_uploads():
        print("[YT] ⏸ Upload paused to protect channel authority")
        sys.exit(0)

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        script = f.read().strip()

    seo = build_seo(script)

    youtube = build_youtube()

    try:
        video_id, final_title = upload_video(youtube, seo)
        print(f"[YT] ✅ Live: https://youtu.be/{video_id}")

        try_set_thumbnail(youtube, video_id)

        hook_line = script.split(".")[0]
        log_upload_meta(video_id, final_title, hook_line)

    except HttpError as e:
        print(f"[YT] ❌ YouTube API error: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"[YT] ❌ Upload failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
