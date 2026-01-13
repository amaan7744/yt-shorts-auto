#!/usr/bin/env python3

import os
import json
import time
from PIL import Image, ImageEnhance
from huggingface_hub import InferenceClient

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
RETRY_DELAY = 3

MODEL_ID = "Tongyi-MAI/Z-Image-Turbo"

os.makedirs(FRAMES_DIR, exist_ok=True)

# --------------------------------------------------
# CLIENT (FAL-AI PROVIDER)
# --------------------------------------------------

client = InferenceClient(
    provider="fal-ai",
    api_key=HF_TOKEN,
)

# --------------------------------------------------
# STYLE LOCK (CRIME-REALISTIC, NOT STOCK)
# --------------------------------------------------

STYLE_PROMPT = (
    "realistic investigative crime scene photography, "
    "documentary style, gritty, cold fluorescent lighting, "
    "abandoned police station or evidence room, "
    "case files, evidence bags, forensic markers, "
    "metal desks, concrete walls, night time, "
    "high detail, sharp focus, "
    "no people, no faces, no bodies, no blood, "
    "no text, no logos, no stock photography"
)

NEGATIVE_PROMPT = (
    "stock photo, wallpaper, travel photography, "
    "sunset, sunrise, cinematic lens flare, "
    "beautiful lighting, aesthetic photo, "
    "illustration, cartoon, unreal engine"
)

# --------------------------------------------------
# IMAGE OPS
# --------------------------------------------------

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

    # final pass to guarantee sharp 1080x1920
    return img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)

# --------------------------------------------------
# GENERATION
# --------------------------------------------------

def generate_image(prompt: str, filename: str):
    full_prompt = f"{prompt}, {STYLE_PROMPT}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            img = client.text_to_image(
                full_prompt,
                model=MODEL_ID,
                negative_prompt=NEGATIVE_PROMPT,
                guidance_scale=7.5,
                num_inference_steps=30,
            )

            if not isinstance(img, Image.Image):
                raise RuntimeError("Model did not return an image")

            img = make_vertical(img)
            img = enhance(img)

            out_path = os.path.join(FRAMES_DIR, filename)
            img.save(out_path, quality=95, subsampling=0)

            print(f"[IMG] Saved {filename} via {MODEL_ID}", flush=True)
            return

        except Exception as e:
            print(f"[WARN] Attempt {attempt} failed: {e}", flush=True)
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

    if not isinstance(beats, list) or not beats:
        raise SystemExit("❌ Invalid beats.json")

    for i, beat in enumerate(beats, 1):
        prompt = beat.get("image_prompt")
        if not prompt:
            raise SystemExit(f"❌ Missing image_prompt in beat {i}")

        filename = f"img_{i:03d}.jpg"
        generate_image(prompt, filename)

    print("✅ All images generated successfully", flush=True)

if __name__ == "__main__":
    main()
