#!/usr/bin/env python3
import os
import sys
import json
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO_FILE = "output.mp4"
THUMB_FILE = "thumbnail.jpg"
SCRIPT_FILE = "script.txt"

def fail(msg):
    print(f"[YT] ❌ {msg}")
    sys.exit(1)

def load_script():
    if not os.path.exists(SCRIPT_FILE):
        fail("script.txt not found")
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def build_metadata(script):
    lines = script.split(".")
    hook = lines[0][:90]

    title = hook.strip()
    if not title.lower().endswith("#shorts"):
        title += " #Shorts"

    description = (
        script[:900] +
        "\n\n#truecrime #unsolved #mystery #darkhistory #shorts"
    )

    tags = [
        "true crime", "unsolved mystery", "crime documentary",
        "dark history", "missing persons", "cold case", "mystery shorts"
    ]

    return title, description, tags

def youtube_client():
    creds = google.oauth2.credentials.Credentials(
        None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)

def upload_video(youtube, title, description, tags):
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "24",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True),
    )
    response = request.execute()
    return response["id"]

def upload_thumbnail(youtube, video_id):
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(THUMB_FILE)
    ).execute()

def main():
    for f in [VIDEO_FILE, THUMB_FILE, SCRIPT_FILE]:
        if not os.path.exists(f):
            fail(f"{f} missing")

    script = load_script()
    title, desc, tags = build_metadata(script)

    yt = youtube_client()
    video_id = upload_video(yt, title, desc, tags)
    upload_thumbnail(yt, video_id)

    print(f"[YT] ✅ Uploaded successfully: https://youtu.be/{video_id}")

if __name__ == "__main__":
    main()
