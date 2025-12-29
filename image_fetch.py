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

# Visual beats (same structure, different assets)
BEATS = [
    ("01_hook.jpg", "car headlights night empty"),
    ("02_detail.jpg", "abandoned object night ground"),
    ("03_context.jpg", "quiet residential street night"),
    ("04_contradiction.jpg", "empty road fog night"),
]

# Strict halal filter
BANNED_TERMS = [
    "woman", "women", "girl", "female",
    "man", "men", "person", "people",
    "couple", "romance", "portrait",
    "model", "face", "hands"
]

def load_used_images():
    if os.path.exists(USED_IMAGES_FILE):
        try:
            return set(json.load(open(USED_IMAGES_FILE, "r", encoding="utf-8")))
        except Exception:
            return set()
    return set()

def save_used_images(used):
    with open(USED_IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)

def image_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

def make_vertical(img):
    img.thumbnail((1080, 1920), Image.Resampling.LANCZOS)
    bg = Image.new("RGB", (1080, 1920), (0, 0, 0))
    bg.paste(img, ((1080 - img.width)//2, (1920 - img.height)//2))
    return bg

def halal(photo):
    text = " ".join([
        photo.get("alt", ""),
        photo.get("url", ""),
        photo.get("photographer", "")
    ]).lower()
    return not any(bad in text for bad in BANNED_TERMS)

def fetch_image(query, filename, used_hashes):
    url = f"https://api.pexels.com/v1/search?query={query}&orientation=portrait&per_page=40"
    r = requests.get(url, headers=HEADERS, timeout=20)
    photos = r.json().get("photos", [])

    random.shuffle(photos)  # IMPORTANT

    for p in photos:
        if not halal(p):
            continue

        img_url = p["src"]["large2x"]
        h = image_hash(img_url)

        if h in used_hashes:
            continue  # Skip previously used images

        try:
            img_data = requests.get(img_url, timeout=15).content
            img = Image.open(BytesIO(img_data)).convert("RGB")
            img = make_vertical(img)
            img.save(os.path.join(OUT_DIR, filename), quality=90)

            used_hashes.add(h)
            print(f"[IMG] Saved {filename}")
            return

        except Exception:
            continue

    raise RuntimeError(f"No NEW halal-safe image found for: {query}")

def main():
    used_hashes = load_used_images()

    for fname, query in BEATS:
        fetch_image(query, fname, used_hashes)

    save_used_images(used_hashes)

if __name__ == "__main__":
    main()
