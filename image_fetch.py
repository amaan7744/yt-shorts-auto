#!/usr/bin/env python3

import os
import json
import time
import requests
from io import BytesIO
from PIL import Image, ImageEnhance

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise SystemExit("❌ HF_TOKEN missing")

BEATS_FILE = "beats.json"
FRAMES_DIR = "frames"

TARGET_W, TARGET_H = 1080, 1920
MAX_RETRIES = 2
RETRY_DELAY = 5

HF_ENDPOINT = "https://router.huggingface.co/hf-inference/models"

# VERIFIED WORKING MODELS (FREE)
MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",
    "runwayml/stable-diffusion-v1-5",
]

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Accept": "image/png",
    "Content-Type": "application/json",
}

STYLE_PROMPT = (
    "dark cinematic crime documentary style, "
    "symbolic, realistic, low light, night atmosphere, "
    "no people, no humans, no faces, no bodies, "
    "no violence, no blood, no text, no logos, "
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

def generate_image(prompt, filename):
    full_prompt = f"{prompt}, {STYLE_PROMPT}"

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "steps": 30,
            "guidance_scale": 7.5
        }
    }

    for model in MODELS:
        url = f"{HF_ENDPOINT}/{model}"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.post(
                    url,
                    headers=HEADERS,
                    json=payload,
                    timeout=180
                )

                if r.status_code != 200:
                    raise RuntimeError(f"{r.status_code}: {r.text}")

                img = Image.open(BytesIO(r.content)).convert("RGB")
                img = make_vertical(img)
                img = enhance(img)

                out = os.path.join(FRAMES_DIR, filename)
                img.save(out, quality=95, subsampling=0)

                print(f"[IMG] Saved {filename} via {model}", flush=True)
                return

            except Exception as e:
                print(f"[WARN] {model} attempt {attempt} failed: {e}", flush=True)
                time.sleep(RETRY_DELAY)

    raise SystemExit(f"❌ Image generation failed for: {filename}")

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")

    beats = json.load(open(BEATS_FILE, "r", encoding="utf-8"))

    for i, beat in enumerate(beats, 1):
        prompt = beat.get("image_prompt")
        if not prompt:
            raise SystemExit(f"❌ Missing image_prompt in beat {i}")

        generate_image(prompt, f"img_{i:03d}.jpg")

    print("✅ All images generated successfully", flush=True)

if __name__ == "__main__":
    main()
