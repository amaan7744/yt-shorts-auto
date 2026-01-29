#!/usr/bin/env python3
"""
Image Generator (HF Router Compatible)
- One image per beat
- No video logic
- Safe to rerun
"""

import os
import time
import json
import requests
from pathlib import Path

HF_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

OUT_DIR = Path("frames")
OUT_DIR.mkdir(exist_ok=True)

TIMEOUT = 120


def generate_image(prompt: str, out_path: Path):
    if not HF_TOKEN:
        raise RuntimeError("HF_API_TOKEN missing")

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1024,
            "height": 1024,
            "guidance_scale": 7.5,
            "num_inference_steps": 30
        }
    }

    print(f"[IMG] Generating → {out_path.name}")

    r = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=TIMEOUT
    )

    if r.status_code != 200:
        raise RuntimeError(f"HF error {r.status_code}: {r.text}")

    out_path.write_bytes(r.content)
    time.sleep(1.2)  # rate-limit safety


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
