#!/usr/bin/env python3

import os
import json
import hashlib
import random
import requests
from io import BytesIO
from PIL import Image

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

PEXELS_KEY = os.getenv("PEXELS_KEY")
if not PEXELS_KEY:
    raise SystemExit("❌ PEXELS_KEY missing")

HEADERS = {"Authorization": PEXELS_KEY}

FRAMES_DIR = "frames"
BEATS_FILE = "beats.json"
USED_IMAGES_FILE = "used_images.json"

TARGET_W, TARGET_H = 1080, 1920
MIN_WIDTH = 2000
MAX_TRIES_PER_INTENT = 40

os.makedirs(FRAMES_DIR, exist_ok=True)

# --------------------------------------------------
# HALAL FILTER
# --------------------------------------------------

BANNED_TERMS = {
    "woman", "women", "girl", "female",
    "man", "men", "person", "people",
    "face", "portrait", "selfie",
    "model", "hands", "child", "couple"
}

# --------------------------------------------------
# INTENT → VISUAL ROLE MAP (CRITICAL)
# --------------------------------------------------

INTENT_PROMPTS = {
    "failure": [
        "empty road at night",
        "abandoned street dark",
        "deserted location night",
    ],
    "time_place": [
        "city skyline at night",
        "old map texture dark",
        "quiet town night exterior",
    ],
    "mistake": [
        "case files on desk",
        "documents under desk lamp",
        "evidence folder dark room",
    ],
    "reframe": [
        "dark hallway fading",
        "empty room single light",
        "shadowed corridor night",
    ],
}

# --------------------------------------------------
# UTIL
# --------------------------------------------------

def log(msg: str):
    print(f"[IMG] {msg}", flush=True)

def load_used():
    if os.path.isfile(USED_IMAGES_FILE):
        try:
            return set(json.load(open(USED_IMAGES_FILE, "r")))
        except Exception:
            return set()
    return set()

def save_used(used):
    with open(USED_IMAGES_FILE, "w") as f:
        json.dump(sorted(used), f, indent=2)

def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()

def is_halal(photo: dict) -> bool:
    text = " ".join([
        photo.get("alt", ""),
        photo.get("url", ""),
        photo.get("photographer", "")
    ]).lower()

    if any(term in text for term in BANNED_TERMS):
        return False

    if photo.get("type") == "portrait":
        return False

    return True

def make_vertical(img: Image.Image) -> Image.Image:
    w, h = img.size
    scale = max(TARGET_W / w, TARGET_H / h)
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    left = (img.width - TARGET_W) // 2
    top = (img.height - TARGET_H) // 2
    return img.crop((left, top, left + TARGET_W, top + TARGET_H))

# --------------------------------------------------
# FETCH LOGIC (INTENT-DRIVEN)
# --------------------------------------------------

def fetch_image_for_intent(intent: str, filename: str, used_hashes: set) -> bool:
    prompts = INTENT_PROMPTS.get(intent, [])
    random.shuffle(prompts)

    for prompt in prompts:
        url = (
            "https://api.pexels.com/v1/search"
            f"?query={prompt}"
            "&orientation=portrait"
            "&per_page=80"
        )

        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            photos = r.json().get("photos", [])
        except Exception:
            continue

        random.shuffle(photos)
        tries = 0

        for p in photos:
            if tries >= MAX_TRIES_PER_INTENT:
                break
            tries += 1

            if not is_halal(p):
                continue

            src = p["src"].get("original") or p["src"].get("large2x")
            if not src:
                continue

            h = hash_url(src)
            if h in used_hashes:
                continue

            if p.get("width", 0) < MIN_WIDTH:
                continue

            try:
                img_data = requests.get(src, timeout=20).content
                img = Image.open(BytesIO(img_data)).convert("RGB")
                img = make_vertical(img)

                out_path = os.path.join(FRAMES_DIR, filename)
                img.save(out_path, quality=95, subsampling=0)

                used_hashes.add(h)
                log(f"Saved {filename} ← {intent} ({prompt})")
                return True

            except Exception:
                continue

    return False

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")

    beats = json.load(open(BEATS_FILE, "r"))
    if not isinstance(beats, list) or len(beats) == 0:
        raise SystemExit("❌ Invalid beats.json")

    used = load_used()

    for idx, beat in enumerate(beats, 1):
        intent = beat.get("intent")
        if not intent:
            raise SystemExit("❌ Beat missing intent")

        fname = f"img_{idx:03d}.jpg"
        ok = fetch_image_for_intent(intent, fname, used)

        if not ok:
            raise SystemExit(f"❌ Failed to fetch image for intent: {intent}")

    save_used(used)
    log("✅ Beat-aligned image generation complete")

if __name__ == "__main__":
    main()
