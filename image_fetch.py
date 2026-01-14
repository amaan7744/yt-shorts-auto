#!/usr/bin/env python3

import os
import json
import time
import cv2
import numpy as np
from typing import List
from PIL import Image, ImageEnhance
from huggingface_hub import InferenceClient

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BEATS_FILE = "beats.json"
OUTPUT_DIR = "frames"

TARGET_W, TARGET_H = 1080, 1920

IMAGES_PER_BEAT = 3        # generate
BEST_IMAGES_PER_BEAT = 1  # keep

RETRY_DELAY = 3
MAX_ATTEMPTS = IMAGES_PER_BEAT * 4

HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
HF_PROVIDER = "nscale"

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise SystemExit("❌ HF_TOKEN missing")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------
# HF CLIENT
# --------------------------------------------------

client = InferenceClient(
    provider=HF_PROVIDER,
    api_key=HF_TOKEN,
)

# --------------------------------------------------
# SCENE → PROMPTS
# --------------------------------------------------

SCENE_PROMPTS = {
    "HOOK": "cinematic noir atmosphere, blurred city lights at night, suspenseful, dramatic shadows, film grain, no people",
    "CONFLICT": "dimly lit interior, shadowy environment, tense atmosphere, low key lighting, cinematic noir, no people",
    "CRIME": "police lights reflecting on wet asphalt, empty alley at night, rain, cinematic noir, symbolic, no people",
    "INVESTIGATION": "detective desk, scattered papers, evidence board, rain on window, moody lighting, cinematic, no people",
    "AFTERMATH": "empty room at dawn, soft light through window, melancholic mood, cinematic stillness, no people",
    "NEUTRAL": "dark abstract background, subtle texture, cinematic lighting, minimal, no people",
}

NEGATIVE_PROMPT = (
    "people, faces, blood, gore, violence, text, watermark, logo, "
    "low quality, blurry, distorted, cartoon, illustration"
)

# --------------------------------------------------
# UTIL
# --------------------------------------------------

def log(msg: str):
    print(f"[IMG] {msg}", flush=True)

def load_beats() -> List[dict]:
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")
    with open(BEATS_FILE, "r", encoding="utf-8") as f:
        beats = json.load(f)
    if not beats:
        raise SystemExit("❌ beats.json empty")
    return beats

def make_vertical(img: Image.Image) -> Image.Image:
    w, h = img.size
    scale = max(TARGET_W / w, TARGET_H / h)
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    x = (img.width - TARGET_W) // 2
    y = (img.height - TARGET_H) // 2
    img = img.crop((x, y, x + TARGET_W, y + TARGET_H))
    return img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)

def enhance(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(1.10)
    img = ImageEnhance.Sharpness(img).enhance(1.05)
    return img

# --------------------------------------------------
# QUALITY SCORING (METADATA CORE)
# --------------------------------------------------

def score_image(img: Image.Image) -> dict:
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = gray.mean()
    contrast = gray.std()

    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist / (hist.sum() + 1e-7)
    entropy = -np.sum(hist * np.log2(hist + 1e-7))

    score = (
        sharpness * 0.4 +
        contrast * 0.3 +
        entropy * 0.2 -
        abs(brightness - 110) * 0.1
    )

    return {
        "score": float(score),
        "sharpness": float(sharpness),
        "contrast": float(contrast),
        "entropy": float(entropy),
        "brightness": float(brightness),
    }

# --------------------------------------------------
# IMAGE GENERATION
# --------------------------------------------------

def generate_image(prompt: str) -> Image.Image | None:
    try:
        img = client.text_to_image(
            prompt=prompt,
            model=HF_MODEL,
            negative_prompt=NEGATIVE_PROMPT,
        )
        return img.convert("RGB")
    except Exception as e:
        log(f"⚠️ HF error: {str(e)[:120]}")
        return None

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    beats = load_beats()
    frame_index = 1

    for beat_idx, beat in enumerate(beats, 1):
        scene = beat.get("scene", "NEUTRAL").upper()
        prompt = SCENE_PROMPTS.get(scene)

        if not prompt:
            raise SystemExit(f"❌ Unknown scene: {scene}")

        log(f"Scene {beat_idx}: {scene}")

        candidates = []
        attempts = 0

        while len(candidates) < IMAGES_PER_BEAT and attempts < MAX_ATTEMPTS:
            attempts += 1
            img = generate_image(prompt)
            if img is None:
                time.sleep(RETRY_DELAY)
                continue

            img = enhance(make_vertical(img))
            metrics = score_image(img)
            candidates.append({"img": img, "metrics": metrics})

        if not candidates:
            raise SystemExit(f"❌ No images generated for scene {scene}")

        candidates.sort(key=lambda x: x["metrics"]["score"], reverse=True)
        selected = candidates[:BEST_IMAGES_PER_BEAT]

        for item in selected:
            img = item["img"]
            metrics = item["metrics"]

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
                    "provider": HF_PROVIDER,
                }, f, indent=2)

            log(f"Selected {img_name} | score={metrics['score']:.2f}")
            frame_index += 1

    log("✅ Image generation + metadata completed")

if __name__ == "__main__":
    main()
