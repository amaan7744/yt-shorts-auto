#!/usr/bin/env python3

import os
import json
import time
import cv2
import numpy as np
from PIL import Image, ImageEnhance
from huggingface_hub import InferenceClient

# --------------------------------------------------
# CONFIG (FREE SAFE)
# --------------------------------------------------

BEATS_FILE = "beats.json"
OUTPUT_DIR = "frames"

TARGET_W, TARGET_H = 1080, 1920

IMAGES_PER_BEAT = 1      # ONLY ONE IMAGE
MAX_ATTEMPTS = 2         # MAX 2 TRIES PER BEAT
RETRY_DELAY = 2

# FREE HF MODEL (DO NOT CHANGE)
HF_MODEL = "runwayml/stable-diffusion-v1-5"

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise SystemExit("❌ HF_TOKEN missing")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------
# HF CLIENT (FREE ENDPOINT)
# --------------------------------------------------

client = InferenceClient(api_key=HF_TOKEN)

# --------------------------------------------------
# SCENE → PROMPTS (SD 1.5 FRIENDLY)
# --------------------------------------------------

SCENE_PROMPTS = {
    "HOOK": "cinematic noir city at night, blurred lights, suspenseful mood, dramatic shadows, film grain, no people",
    "CONFLICT": "dark interior room, shadows, tense atmosphere, low key lighting, cinematic, no people",
    "CRIME": "police lights reflecting on wet road, empty alley at night, rain, cinematic noir, no people",
    "INVESTIGATION": "detective desk with papers, rain on window, moody lighting, cinematic, no people",
    "AFTERMATH": "empty room at dawn, soft light, melancholic mood, cinematic stillness, no people",
    "NEUTRAL": "dark abstract background, subtle texture, cinematic lighting, minimal"
}

NEGATIVE_PROMPT = (
    "people, faces, blood, gore, violence, text, watermark, logo, "
    "low quality, blurry, distorted, cartoon, illustration"
)

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
    img = ImageEnhance.Sharpness(img).enhance(1.04)
    return img

# --------------------------------------------------
# QUALITY METRICS (METADATA)
# --------------------------------------------------

def score_image(img: Image.Image) -> dict:
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = gray.mean()
    contrast = gray.std()

    return {
        "score": float(sharpness + contrast),
        "sharpness": float(sharpness),
        "brightness": float(brightness),
        "contrast": float(contrast),
    }

# --------------------------------------------------
# IMAGE GENERATION (FREE SAFE)
# --------------------------------------------------

def generate_image(prompt: str):
    try:
        img = client.text_to_image(
            prompt=prompt,
            model=HF_MODEL,
            negative_prompt=NEGATIVE_PROMPT,
        )
        return img.convert("RGB")

    except Exception as e:
        msg = str(e)
        log(f"⚠️ HF error: {msg[:100]}")

        # STOP immediately if paid limit is hit
        if "402" in msg or "Payment Required" in msg:
            raise RuntimeError("HF paid limit reached")

        return None

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    beats = load_beats()
    frame_index = 1

    for idx, beat in enumerate(beats, 1):
        scene = beat.get("scene", "NEUTRAL").upper()
        prompt = SCENE_PROMPTS.get(scene, SCENE_PROMPTS["NEUTRAL"])

        log(f"Scene {idx}: {scene}")

        img = None
        attempts = 0

        while img is None and attempts < MAX_ATTEMPTS:
            attempts += 1
            try:
                img = generate_image(prompt)
            except RuntimeError:
                log("❌ Paid HF limit hit — switching to fallback")
                break

            if img is None:
                time.sleep(RETRY_DELAY)

        # ----------------------------
        # FALLBACK (NEVER FAIL)
        # ----------------------------
        if img is None:
            log("⚠️ Using fallback neutral image")
            img = Image.new("RGB", (TARGET_W, TARGET_H), color=(12, 12, 12))

        img = enhance(make_vertical(img))
        metrics = score_image(img)

        img_name = f"img_{frame_index:04d}.jpg"
        meta_name = f"img_{frame_index:04d}.json"

        img.save(os.path.join(OUTPUT_DIR, img_name), quality=95, subsampling=0)

        with open(os.path.join(OUTPUT_DIR, meta_name), "w", encoding="utf-8") as f:
            json.dump({
                "frame": img_name,
                "scene": scene,
                "prompt": prompt,
                "quality": metrics,
                "model": HF_MODEL,
            }, f, indent=2)

        log(f"Selected {img_name} | score={metrics['score']:.2f}")
        frame_index += 1

    log("✅ Image generation completed safely")

if __name__ == "__main__":
    main()
