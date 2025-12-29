#!/usr/bin/env python3
import os
import json
import random
import hashlib
import requests
from io import BytesIO
from PIL import Image

PEXELS_KEY = os.getenv("PEXELS_KEY")
OUT_DIR = "frames"
USED_IMAGES_FILE = "used_images.json"

os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {"Authorization": PEXELS_KEY}

BEATS = [
    ("01_hook.jpg", "car headlights night empty"),
    ("02_detail.jpg", "abandoned object night ground"),
    ("03_context.jpg", "quiet residential street night"),
    ("04_contradiction.jpg", "empty road night high contrast"),
]

BANNED_TERMS = [
    "woman", "women", "girl", "female",
    "man", "men", "person", "people",
    "couple", "romance", "portrait",
    "model", "face", "hands"
]

def load_used():
    if os.path.exists(USED_IMAGES_FILE):
        try:
            return set(json.load(open(USED_IMAGES_FILE, "r", encoding="utf-8")))
        except:
            return set()
    return set()

def save_used(used):
    with open(USED_IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)

def img_hash(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

def halal(photo):
    text = " ".join([
        photo.get("alt", ""),
        photo.get("url", ""),
        photo.get("photographer", "")
    ]).lower()
    return not any(b in text for b in BANNED_TERMS)

def fetch(query, filename, used):
    url = (
        "https://api.pexels.com/v1/search"
        f"?query={query}&orientation=portrait&size=large&per_page=40"
    )

    r = requests.get(url, headers=HEADERS, timeout=20)
    photos = r.json().get("photos", [])
    random.shuffle(photos)

    for p in photos:
        if not halal(p):
            continue

        src = p["src"]["original"]  # <-- IMPORTANT
        h = img_hash(src)

        if h in used:
            continue

        try:
            img_data = requests.get(src, timeout=20).content
            img = Image.open(BytesIO(img_data)).convert("RGB")

            # DO NOT RESIZE HERE
            img.save(os.path.join(OUT_DIR, filename), quality=95)

            used.add(h)
            print(f"[IMG] Saved high-res {filename}")
            return
        except:
            continue

    raise RuntimeError(f"No new halal image for {query}")

def main():
    used = load_used()
    for name, query in BEATS:
        fetch(query, name, used)
    save_used(used)

if __name__ == "__main__":
    main()
