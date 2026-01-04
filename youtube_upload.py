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

VIDEO_FILE = "output.mp4"
SCRIPT_FILE = "script.txt"
META_FILE = "memory/upload_meta.json"


# ---------------- UTIL ----------------
def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"[YT] ❌ Missing env var: {name}", file=sys.stderr)
        sys.exit(1)
    return val


# ---------------- AUTH ----------------
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


# ---------------- UPLOAD ----------------
def upload_video(youtube, title, description, tags):
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": "24",  # Entertainment
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

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    return response["id"]


# ---------------- THUMBNAIL ----------------
def try_set_thumbnail(youtube, video_id):
    thumb = "thumbnail.jpg"
    if not os.path.isfile(thumb):
        return

    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumb),
        ).execute()
        print("[YT] ✅ Thumbnail uploaded")

    except HttpError as e:
        print(f"[YT] ⚠ Thumbnail skipped: {e}")


# ---------------- META LOG ----------------
def log_upload_meta(video_id, title, hook):
    os.makedirs("memory", exist_ok=True)

    meta = {
        "video_id": video_id,
        "title": title,
        "hook_text": hook,
        "uploaded_at": datetime.utcnow().isoformat()
    }

    with open(META_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(meta) + "\n")


# ---------------- MAIN ----------------
def main():
    if not os.path.isfile(VIDEO_FILE):
        sys.exit("[YT] ❌ output.mp4 missing")

    if not os.path.isfile(SCRIPT_FILE):
        sys.exit("[YT] ❌ script.txt missing")

    # ---- Upload guard (CRITICAL) ----
    if should_pause_uploads():
        print("[YT] ⏸ Upload paused due to channel fatigue")
        sys.exit(0)

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        script = f.read().strip()

    seo = build_seo(script)

    title = seo["title"]
    description = seo["description"] + "\n\n" + " ".join(seo["hashtags"])
    tags = seo["tags"]

    youtube = build_youtube()
    video_id = upload_video(youtube, title, description, tags)

    print(f"[YT] ✅ Uploaded: https://youtu.be/{video_id}")

    try_set_thumbnail(youtube, video_id)

    # Log metadata for analytics & hook learning
    hook_line = script.split("\n")[0]
    log_upload_meta(video_id, title, hook_line)


if __name__ == "__main__":
    main()
