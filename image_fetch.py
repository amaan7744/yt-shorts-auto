#!/usr/bin/env python3

import os
import json
import time
import random
import requests
from io import BytesIO
from PIL import Image, ImageEnhance

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BEATS_FILE = "beats.json"
OUTPUT_DIR = "frames"

TARGET_W, TARGET_H = 1080, 1920

MAX_ATTEMPTS = 4
RETRY_DELAY = 1.5

HALAL_MODE = True   # 🔒 ENFORCED

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    raise SystemExit("❌ PEXELS_API_KEY missing")

PEXELS_ENDPOINT = "https://api.pexels.com/v1/search"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------
# HALAL-SAFE SCENE → SEARCH QUERIES
# --------------------------------------------------

SCENE_PROMPTS = {
    "HOOK": "dark city night empty street neon rain cinematic no people",
    "CRIME": "empty alley night police lights wet road cinematic no people",
    "INVESTIGATION": "empty detective desk papers moody lighting cinematic no people",
    "CONFLICT": "dark empty room shadows dramatic lighting cinematic no people",
    "AFTERMATH": "empty room dawn soft light cinematic no people",
    "NEUTRAL": "dark abstract texture cinematic background no people",
}

# --------------------------------------------------
# HARD FORBIDDEN WORDS (HALAL FILTER)
# --------------------------------------------------

FORBIDDEN_WORDS = {
    "woman", "women", "girl", "girls",
    "female", "lady",
    "couple", "romantic", "dating",
    "model", "fashion", "portrait",
    "wedding", "kiss", "love"
}

# --------------------------------------------------
# UTILS
# --------------------------------------------------

def log(msg: str):
    print(f"[IMG] {msg}", flush=True)

def load_beats():
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")
    with open(BEATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def make_vertical(img: Image.Image) -> Image.Image:
    w, h = img.size
    scale = max(TARGET_W / w, TARGET_H / h)
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    x = (img.width - TARGET_W) // 2
    y = (img.height - TARGET_H) // 2
    img = img.crop((x, y, x + TARGET_W, y + TARGET_H))
    return img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)

def enhance(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Sharpness(img).enhance(1.05)
    return img

# --------------------------------------------------
# HALAL FILTER
# --------------------------------------------------

def is_halal_safe(photo: dict) -> bool:
    alt = (photo.get("alt") or "").lower()
    for word in FORBIDDEN_WORDS:
        if word in alt:
            return False
    return True

# --------------------------------------------------
# PEXELS API
# --------------------------------------------------

def search_pexels(query: str):
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": f"{query} -woman -girl -couple -portrait -fashion",
        "orientation": "portrait",
        "size": "large",
        "per_page": 15,
    }

    r = requests.get(PEXELS_ENDPOINT, headers=headers, params=params, timeout=10)
    if r.status_code != 200:
        log(f"⚠️ Pexels error {r.status_code}")
        return []

    return r.json().get("photos", [])

def download_image(url: str):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        log(f"⚠️ Download failed: {e}")
        return None

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    beats = load_beats()
    frame_index = 1

    for idx, beat in enumerate(beats, 1):
        scene = beat.get("scene", "NEUTRAL").upper()
        query = SCENE_PROMPTS.get(scene, SCENE_PROMPTS["NEUTRAL"])

        log(f"Scene {idx}: {scene}")

        img = None
        attempts = 0

        while img is None and attempts < MAX_ATTEMPTS:
            attempts += 1

            photos = search_pexels(query)
            if HALAL_MODE:
                photos = [p for p in photos if is_halal_safe(p)]

            if not photos:
                time.sleep(RETRY_DELAY)
                continue

            photo = random.choice(photos)
            img = download_image(photo["src"]["large"])

            if img is None:
                time.sleep(RETRY_DELAY)

        # ----------------------------
        # SAFE FALLBACK (ALWAYS HALAL)
        # ----------------------------
        if img is None:
            log("⚠️ Using fallback abstract image")
            img = Image.new("RGB", (TARGET_W, TARGET_H), (10, 10, 10))

        img = enhance(make_vertical(img))

        img_name = f"img_{frame_index:04d}.jpg"
        meta_name = f"img_{frame_index:04d}.json"

        img.save(
            os.path.join(OUTPUT_DIR, img_name),
            quality=95,
            subsampling=0
        )

        with open(os.path.join(OUTPUT_DIR, meta_name), "w", encoding="utf-8") as f:
            json.dump({
                "frame": img_name,
                "scene": scene,
                "query": query,
                "source": "pexels",
                "halal_mode": HALAL_MODE
            }, f, indent=2)

        log(f"Saved {img_name}")
        frame_index += 1

    log("✅ Image fetch completed (HALAL MODE ON)")

if __name__ == "__main__":
    main()
