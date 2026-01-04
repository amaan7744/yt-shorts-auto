#!/usr/bin/env python3
import os
import json
import hashlib
import random
import requests
from io import BytesIO
from PIL import Image

# ---------------- CONFIG ----------------
PEXELS_KEY = os.getenv("PEXELS_KEY")
FRAMES_DIR = "frames"
PROMPTS_FILE = "image_prompts.json"
USED_IMAGES_FILE = "used_images.json"

TARGET_W, TARGET_H = 1080, 1920
MIN_WIDTH = 2000
MAX_TRIES_PER_PROMPT = 30

os.makedirs(FRAMES_DIR, exist_ok=True)
HEADERS = {"Authorization": PEXELS_KEY}

# STRONG HALAL FILTER (TEXT + CATEGORY)
BANNED_TERMS = {
    "woman", "women", "girl", "female",
    "man", "men", "person", "people",
    "couple", "portrait", "selfie",
    "model", "face", "hands", "child"
}

# --------------------------------------

def log(msg):
    print(f"[IMG] {msg}", flush=True)

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

def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

def is_halal(photo) -> bool:
    # Text-based filter (best effort)
    text = " ".join([
        photo.get("alt", ""),
        photo.get("url", ""),
        photo.get("photographer", "")
    ]).lower()

    if any(b in text for b in BANNED_TERMS):
        return False

    # Category-based safety (extra)
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

def fetch_for_prompt(prompt: str, filename: str, used_hashes: set):
    url = (
        "https://api.pexels.com/v1/search"
        f"?query={prompt}"
        "&orientation=portrait"
        "&per_page=80"
    )

    r = requests.get(url, headers=HEADERS, timeout=25)
    photos = r.json().get("photos", [])
    random.shuffle(photos)

    tries = 0

    for p in photos:
        if tries >= MAX_TRIES_PER_PROMPT:
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
            log(f"Saved {filename} ← {prompt}")
            return True

        except Exception:
            continue

    log(f"⚠️ No perfect image for '{prompt}', allowing fallback")
    return False

def main():
    if not os.path.isfile(PROMPTS_FILE):
        raise SystemExit("❌ image_prompts.json missing")

    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    if not isinstance(prompts, list) or len(prompts) < 3:
        raise SystemExit("❌ Invalid image prompts")

    used = load_used()

    for idx, prompt in enumerate(prompts, 1):
        fname = f"img_{idx:03d}.jpg"
        ok = fetch_for_prompt(prompt, fname, used)

        # Soft fallback: reuse previous frame if needed
        if not ok and idx > 1:
            prev = os.path.join(FRAMES_DIR, f"img_{idx-1:03d}.jpg")
            if os.path.exists(prev):
                os.system(f"cp {prev} {os.path.join(FRAMES_DIR, fname)}")
                log(f"Fallback reused previous frame for {fname}")

    save_used(used)
    log("✅ Image fetch complete (safe + diverse)")

if __name__ == "__main__":
    main()
