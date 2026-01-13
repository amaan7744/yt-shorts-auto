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

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise SystemExit("❌ HF_TOKEN missing")

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

BEATS_FILE = "beats.json"
FRAMES_DIR = "frames"

TARGET_W, TARGET_H = 1080, 1920
MAX_RETRIES = 2
RETRY_DELAY = 3

# Primary + fallback (Chinese open-source)
MODELS = [
    "Qwen/Qwen-Image",
    "IDEA-CCNL/Taiyi-Stable-Diffusion-XL"
]

# --------------------------------------------------
# GLOBAL STYLE LOCK (RETENTION + HALAL)
# --------------------------------------------------

STYLE_PROMPT = (
    "dark cinematic crime documentary style, "
    "symbolic, realistic, low light, night atmosphere, "
    "no people, no humans, no faces, no bodies, "
    "no violence, no text, no logos, "
    "vertical composition, high detail"
)

os.makedirs(FRAMES_DIR, exist_ok=True)

# --------------------------------------------------
# IMAGE OPS
# --------------------------------------------------

def enhance(img):
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Sharpness(img).enhance(1.08)
    return img

def make_vertical(img):
    w, h = img.size
    scale = max(TARGET_W / w, TARGET_H / h)
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    x = (img.width - TARGET_W) // 2
    y = (img.height - TARGET_H) // 2
    return img.crop((x, y, x + TARGET_W, y + TARGET_H))

# --------------------------------------------------
# GENERATION
# --------------------------------------------------

def generate_image(prompt: str, filename: str):
    full_prompt = f"{prompt}, {STYLE_PROMPT}"

    for model in MODELS:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers=HEADERS,
                    json={"inputs": full_prompt},
                    timeout=120
                )

                if r.status_code != 200:
                    raise RuntimeError(r.text)

                img = Image.open(BytesIO(r.content)).convert("RGB")
                img = make_vertical(img)
                img = enhance(img)

                img.save(
                    os.path.join(FRAMES_DIR, filename),
                    quality=95,
                    subsampling=0
                )

                print(f"[IMG] Saved {filename} via {model}")
                return

            except Exception as e:
                print(f"[WARN] {model} attempt {attempt} failed: {e}")
                time.sleep(RETRY_DELAY)

    raise SystemExit(f"❌ Image generation failed for: {filename}")

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")

    with open(BEATS_FILE, "r", encoding="utf-8") as f:
        beats = json.load(f)

    if not isinstance(beats, list):
        raise SystemExit("❌ Invalid beats.json format")

    for i, beat in enumerate(beats, 1):
        image_prompt = beat.get("image_prompt")
        if not image_prompt:
            raise SystemExit(f"❌ Missing image_prompt in beat {i}")

        filename = f"img_{i:03d}.jpg"
        generate_image(image_prompt, filename)

    print("✅ All story-aligned images generated")

if __name__ == "__main__":
    main()
