#!/usr/bin/env python3

import os
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

VIDEO_FILE = "output.mp4"
THUMBNAIL_FILE = "thumbnail.jpg"


def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"[YT] ❌ Missing env var: {name}", file=sys.stderr)
        sys.exit(1)
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


def upload_video(youtube, title, description, tags):
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": "24",
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
        status, response = request.next_chunk()

    return response["id"]


def try_set_thumbnail(youtube, video_id):
    if not os.path.isfile(THUMBNAIL_FILE):
        print("[YT] ⚠ thumbnail.jpg not found — skipping")
        return

    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(THUMBNAIL_FILE),
        ).execute()
        print("[YT] ✅ Thumbnail uploaded")

    except HttpError as e:
        if e.resp.status == 403:
            print("[YT] ⚠ Thumbnail forbidden — skipping.")
        else:
            print(f"[YT] ⚠ Thumbnail upload failed: {e}")


def main():
    if not os.path.isfile(VIDEO_FILE):
        sys.exit("[YT] ❌ output.mp4 missing")

    if not os.path.isfile("script.txt"):
        sys.exit("[YT] ❌ script.txt missing")

    # -------- TITLE (from script, first sentence only) --------
    with open("script.txt", "r", encoding="utf-8") as f:
        script = f.read().strip()

    title = script.split("\n")[0][:90]

    # -------- DESCRIPTION (TAGS ONLY) --------
    description = (
        "#truecrime\n"
        "#mystery\n"
        "#crimeshorts\n"
        "#darkstories\n"
        "#police\n"
        "#shorts"
    )

    tags = [
        "true crime",
        "crime shorts",
        "police investigation",
        "dark stories",
        "mystery short",
    ]

    youtube = build_youtube()

    video_id = upload_video(youtube, title, description, tags)
    print(f"[YT] ✅ Video uploaded: https://youtu.be/{video_id}")

    try_set_thumbnail(youtube, video_id)


if __name__ == "__main__":
    main()
