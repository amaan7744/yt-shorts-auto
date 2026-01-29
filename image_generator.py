#!/usr/bin/env python3
"""
Image Generator
- Uses Hugging Face Inference API
- One image per beat
- CI safe
"""

import os
import time
import requests
from pathlib import Path


# ==================================================
# CONFIG
# ==================================================

HF_API_TOKEN = os.getenv("HF_API_TOKEN")  # REQUIRED
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

OUT_DIR = Path("frames")
OUT_DIR.mkdir(exist_ok=True)

TIMEOUT = 120


# ==================================================
# CORE
# ==================================================

def generate_image(prompt: str, out_path: Path) -> None:
    if not HF_API_TOKEN:
        raise RuntimeError("HF_API_TOKEN not set")

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
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

    response = requests.post(
        f"https://api-inference.huggingface.co/models/{HF_MODEL}",
        headers=headers,
        json=payload,
        timeout=TIMEOUT
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"HF API error {response.status_code}: {response.text}"
        )

    out_path.write_bytes(response.content)

    # Tiny delay to avoid rate-limit
    time.sleep(1.2)
