#!/usr/bin/env python3

import os
import json
import time
import requests
from io import BytesIO
from typing import List
from PIL import Image, ImageEnhance

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BEATS_FILE = "beats.json"
OUTPUT_DIR = "frames"

TARGET_W, TARGET_H = 1080, 1920
IMAGES_PER_BEAT = 3          # critical for motion + retention
HF_TIMEOUT = 90

HF_MODEL = "stabilityai/stable-diffusion-2-1"
HF_API = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise SystemExit("❌ HF_TOKEN missing")

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------
# SCENE → PROMPT MAP (DO NOT RANDOMIZE THIS)
# --------------------------------------------------

SCENE_PROMPTS = {
    "HOOK": [
        "cinematic noir atmosphere, blurred city lights at night, suspenseful mood, film grain, dramatic shadows, no people"
    ],
    "CONFLICT": [
        "dimly lit interior, shadowy environment, tense atmosphere, low key lighting, cinematic noir, no people"
    ],
    "CRIME": [
        "police lights reflecting on wet asphalt, empty alley at night, rain, cinematic noir style, symbolic, no people"
    ],
    "INVESTIGATION": [
        "detective desk, scattered papers, evidence board, rain on window, moody lighting, cinematic style, no people"
    ],
    "AFTERMATH": [
        "empty room at dawn, soft light through window, melancholic mood, cinematic stillness, no people"
    ],
    "NEUTRAL": [
        "dark abstract background, subtle texture, cinematic lighting, minimal, no people"
    ],
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

def enhance(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(1.10)
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
# AI IMAGE GENERATION (HF FREE)
# --------------------------------------------------

def generate_image(prompt: str) -> Image.Image | None:
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": NEGATIVE_PROMPT,
            "guidance_scale": 7.5,
            "num_inference_steps": 25,
        },
    }

    try:
        r = requests.post(
            HF_API,
            headers=HEADERS,
            json=payload,
            timeout=HF_TIMEOUT,
        )
    except requests.RequestException:
        return None

    if r.status_code != 200:
        return None

    try:
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception:
        return None

# --------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------

def main():
    beats = load_beats()
    frame_index = 1

    for beat_idx, beat in enumerate(beats, 1):
        scene = beat.get("scene", "NEUTRAL").upper()

        if scene not in SCENE_PROMPTS:
            raise SystemExit(f"❌ Unknown scene type: {scene}")

        prompt = SCENE_PROMPTS[scene][0]
        log(f"Scene {beat_idx}: {scene}")

        generated = 0
        attempts = 0

        while generated < IMAGES_PER_BEAT and attempts < IMAGES_PER_BEAT * 3:
            attempts += 1
            img = generate_image(prompt)

            if img is None:
                log("⚠️ HF generation failed, retrying")
                time.sleep(2)
                continue

            img = make_vertical(img)
            img = enhance(img)

            out = os.path.join(OUTPUT_DIR, f"img_{frame_index:04d}.jpg")
            img.save(out, quality=95, subsampling=0)

            log(f"Saved {out}")
            frame_index += 1
            generated += 1

        if generated < IMAGES_PER_BEAT:
            raise SystemExit(
                f"❌ Failed to generate enough images for scene {beat_idx} ({scene})"
            )

    log("✅ Scene-aware AI images prepared successfully")

if __name__ == "__main__":
    main()
