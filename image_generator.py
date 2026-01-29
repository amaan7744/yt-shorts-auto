#!/usr/bin/env python3
"""
Image Generator (HF + Local Fallback)
- Tries Hugging Face first
- Falls back to local renderer if HF fails
- NEVER breaks pipeline
"""

import os
import time
import json
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

# ===============================
# CONFIG
# ===============================

HF_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
HF_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

OUT_DIR = Path("frames")
OUT_DIR.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1024, 1024
TIMEOUT = 120


# ===============================
# HF GENERATOR
# ===============================

def try_hf(prompt: str) -> Image.Image | None:
    if not HF_TOKEN:
        return None

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "width": WIDTH,
            "height": HEIGHT,
            "guidance_scale": 7.5,
            "num_inference_steps": 30
        }
    }

    try:
        r = requests.post(
            HF_URL,
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )

        if r.status_code != 200:
            print(f"[IMG] HF failed ({r.status_code}), falling back")
            return None

        return Image.open(BytesIO(r.content)).convert("RGB")

    except Exception as e:
        print(f"[IMG] HF error: {e}")
        return None


# ===============================
# LOCAL FALLBACK GENERATOR
# ===============================

def local_generate(prompt: str) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), (18, 18, 22))
    draw = ImageDraw.Draw(img)

    # Gradient lighting
    for y in range(HEIGHT):
        shade = int(20 + (y / HEIGHT) * 50)
        draw.line([(0, y), (WIDTH, y)], fill=(shade, shade, shade))

    p = prompt.lower()

    # Simple semantic shapes
    if "car" in p:
        draw.rectangle([200, 600, 820, 900], fill=(50, 50, 55))
        draw.rectangle([300, 520, 740, 600], fill=(70, 70, 75))
        draw.ellipse([480, 680, 560, 760], fill=(100, 100, 100))

    if "police" in p:
        draw.rectangle([0, 0, WIDTH, 120], fill=(180, 0, 0))
        draw.rectangle([0, 120, WIDTH, 240], fill=(0, 0, 180))

    if "room" in p or "bedroom" in p:
        draw.rectangle([260, 720, 760, 860], fill=(80, 80, 85))

    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    return img


# ===============================
# MAIN GENERATOR
# ===============================

def generate_image(prompt: str, out_path: Path):
    print(f"[IMG] Generating → {out_path.name}")

    img = try_hf(prompt)
    if img is None:
        img = local_generate(prompt)

    img.save(out_path)
    time.sleep(0.5)


def main():
    beats = json.loads(Path("beats.json").read_text())["beats"]

    for beat in beats:
        out = OUT_DIR / f"scene_{beat['beat_id']:02d}.png"
        if out.exists():
            print(f"[IMG] Exists → {out.name}")
            continue

        generate_image(beat["image_prompt"], out)


if __name__ == "__main__":
    main()
