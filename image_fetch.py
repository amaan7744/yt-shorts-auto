#!/usr/bin/env python3
import os
import random
import requests
from io import BytesIO
from PIL import Image

PEXELS_KEY = os.getenv("PEXELS_KEY")
OUT_DIR = "frames"

DARK_KEYWORDS = [
    "dark alley night",
    "empty street rain night",
    "lonely road night",
    "silhouette walking night",
    "foggy street night",
    "police lights night",
    "misty urban night",
]

def ensure_dir():
    os.makedirs(OUT_DIR, exist_ok=True)

def fetch_from_pexels():
    if not PEXELS_KEY:
        print("[WARN] PEXELS_KEY missing, skipping image fetch")
        return []

    keyword = random.choice(DARK_KEYWORDS)
    url = (
        "https://api.pexels.com/v1/search"
        f"?query={keyword}&orientation=portrait&per_page=15"
    )

    headers = {"Authorization": PEXELS_KEY}

    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print("[WARN] Pexels request failed")
            return []

        data = r.json()
        photos = data.get("photos", [])
        return [p["src"]["large2x"] for p in photos if "src" in p]

    except Exception as e:
        print(f"[WARN] Pexels error: {e}")
        return []

def make_vertical(img: Image.Image) -> Image.Image:
    target_w, target_h = 1080, 1920
    img = img.convert("RGB")

    img.thumbnail((target_w, target_h * 2), Image.Resampling.LANCZOS)

    bg = Image.new("RGB", (target_w, target_h), (0, 0, 0))
    w, h = img.size

    bg.paste(img, ((target_w - w) // 2, (target_h - h) // 2))
    return bg

def download_and_save(urls):
    count = 0

    for idx, url in enumerate(urls, start=1):
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                continue

            img = Image.open(BytesIO(r.content))
            img = make_vertical(img)

            out_path = os.path.join(OUT_DIR, f"img_{idx:03d}.jpg")
            img.save(out_path, "JPEG", quality=92)
            count += 1

        except Exception:
            continue

        if count >= 12:
            break

    print(f"[IMAGES] Saved {count} images")

def main():
    ensure_dir()
    urls = fetch_from_pexels()

    if not urls:
        print("[WARN] No images downloaded")
        return

    download_and_save(urls)

if __name__ == "__main__":
    main()

