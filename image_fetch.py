#!/usr/bin/env python3

import os
import json
import random
from PIL import Image, ImageEnhance

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BEATS_FILE = "beats.json"
ASSETS_DIR = "assets"
FRAMES_DIR = "frames"

TARGET_W, TARGET_H = 1080, 1920

os.makedirs(FRAMES_DIR, exist_ok=True)

# --------------------------------------------------
# UTIL
# --------------------------------------------------

def log(msg):
    print(f"[IMG] {msg}", flush=True)

def load_beats():
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")
    return json.load(open(BEATS_FILE, "r", encoding="utf-8"))

def get_asset_folder(beat_name: str) -> str:
    path = os.path.join(ASSETS_DIR, beat_name)
    if not os.path.isdir(path):
        raise SystemExit(f"❌ Missing asset folder: {path}")
    return path

def pick_image(folder: str) -> str:
    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not files:
        raise SystemExit(f"❌ No images in {folder}")
    return random.choice(files)

def enhance(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Sharpness(img).enhance(1.05)
    return img

def make_vertical(img: Image.Image) -> Image.Image:
    w, h = img.size
    scale = max(TARGET_W / w, TARGET_H / h)
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    x = (img.width - TARGET_W) // 2
    y = (img.height - TARGET_H) // 2
    img = img.crop((x, y, x + TARGET_W, y + TARGET_H))

    return img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    beats = load_beats()

    for i, beat in enumerate(beats, 1):
        beat_name = beat.get("beat")
        if not beat_name:
            raise SystemExit(f"❌ Beat missing name at index {i}")

        folder = get_asset_folder(beat_name)
        src_img = pick_image(folder)

        img = Image.open(src_img).convert("RGB")
        img = make_vertical(img)
        img = enhance(img)

        out = os.path.join(FRAMES_DIR, f"img_{i:03d}.jpg")
        img.save(out, quality=95, subsampling=0)

        log(f"Selected {os.path.basename(src_img)} → img_{i:03d}.jpg")

    log("✅ Public-domain images prepared successfully")

if __name__ == "__main__":
    main()
