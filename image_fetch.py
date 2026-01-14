#!/usr/bin/env python3

import os
import json
import time
from typing import List
from PIL import Image, ImageEnhance
from huggingface_hub import InferenceClient

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BEATS_FILE = "beats.json"
OUTPUT_DIR = "frames"

TARGET_W, TARGET_H = 1080, 1920
IMAGES_PER_BEAT = 3          # important for motion + retention
RETRY_DELAY = 3
MAX_ATTEMPTS_PER_IMAGE = 4

HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
HF_PROVIDER = "nscale"

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise SystemExit("❌ HF_TOKEN missing")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------
# HF CLIENT (CORRECT WAY)
# --------------------------------------------------

client = InferenceClient(
    provider=HF_PROVIDER,
    api_key=HF_TOKEN,
)

# --------------------------------------------------
# SCENE → PROMPT MAP
# --------------------------------------------------

SCENE_PROMPTS = {
    "HOOK": (
        "cinematic noir atmosphere, blurred city lights at night, "
        "suspenseful mood, dramatic shadows, film grain, no people"
    ),
    "CONFLICT": (
        "dimly lit interior, shadowy environment, tense atmosphere, "
        "low key lighting, cinematic noir, no people"
    ),
    "CRIME": (
        "police lights reflecting on wet asphalt, empty alley at night, "
        "rain, cinematic noir style, symbolic, no people"
    ),
    "INVESTIGATION": (
        "detective desk, scattered papers, evidence board, rain on window, "
        "moody lighting, cinematic style, no people"
    ),
    "AFTERMATH": (
        "empty room at dawn, soft light through window, melancholic mood, "
        "cinematic stillness, no people"
    ),
    "NEUTRAL": (
        "dark abstract background, subtle texture, cinematic lighting, minimal, no people"
    ),
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
# IMAGE GENERATION (HF SDK – RELIABLE)
# --------------------------------------------------

def generate_image(prompt: str) -> Image.Image | None:
    try:
        image = client.text_to_image(
            prompt=prompt,
            model=HF_MODEL,
            negative_prompt=NEGATIVE_PROMPT,
        )
        return image.convert("RGB")

    except Exception as e:
        log(f"⚠️ HF error: {str(e)[:120]}")
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

        prompt = SCENE_PROMPTS[scene]
        log(f"Scene {beat_idx}: {scene}")

        generated = 0
        attempts = 0

        while generated < IMAGES_PER_BEAT:
            if attempts >= MAX_ATTEMPTS_PER_IMAGE * IMAGES_PER_BEAT:
                raise SystemExit(
                    f"❌ Failed to generate images for scene {beat_idx} ({scene})"
                )

            attempts += 1
            img = generate_image(prompt)

            if img is None:
                time.sleep(RETRY_DELAY)
                continue

            img = make_vertical(img)
            img = enhance(img)

            out = os.path.join(OUTPUT_DIR, f"img_{frame_index:04d}.jpg")
            img.save(out, quality=95, subsampling=0)

            log(f"Saved {out}")
            frame_index += 1
            generated += 1

    log("✅ AI image generation completed successfully")

if __name__ == "__main__":
    main()
