#!/usr/bin/env python3
"""
Scene Composer - 100% FREE SERVERLESS EDITION
Forces 'hf-inference' provider to bypass 402 Payment Required errors.
"""
import json
import os
import time
import random
import sys
from pathlib import Path
from io import BytesIO

try:
    from huggingface_hub import InferenceClient
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    print("❌ Missing libraries. Run: pip install huggingface_hub pillow requests")
    sys.exit(1)

OUT = Path("frames")
OUT.mkdir(exist_ok=True)
W, H = 1080, 1920

# 🔑 SDXL-Lightning is the best 2026 choice for high-quality FREE serverless calls.
# Models like FLUX often force a 402 error because they require paid providers.
HF_MODEL = "ByteDance/SDXL-Lightning-4step"

def get_cinematic_prompt(beat: dict) -> str:
    text = beat.get("text", "").lower()
    base_style = "cinematic, hyper-realistic, dark mystery, 8k, photorealistic, vertical 9:16"
    
    if any(k in text for k in ["train", "track", "rail"]):
        scene = "empty dark train tracks at night, cinematic fog"
    elif any(k in text for k in ["car", "drive", "road"]):
        scene = "POV dashboard inside a moving car, dark night road"
    else:
        scene = text[:60]
    return f"{scene}, {base_style}"

def try_ai_generate(prompt: str) -> Image.Image:
    token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
    if not token:
        return None

    # 🚀 CRITICAL FIX: Explicitly set provider="hf-inference"
    # This forces the Hub to use its own free hardware and ignore paid partners.
    client = InferenceClient(api_key=token)
    
    for attempt in range(3):
        try:
            # We use text_to_image with the specific free provider flag
            # Note: num_inference_steps=4 is required for '4step' lightning models
            response = client.text_to_image(
                prompt,
                model=HF_MODEL,
                provider="hf-inference" 
            )
            return response.resize((W, H), Image.Resampling.LANCZOS)

        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "loading" in error_str.lower():
                wait = 20 + (attempt * 20)
                print(f"  ⏳ Model Loading... Waiting {wait}s")
                time.sleep(wait)
            else:
                print(f"  ⚠ AI Failed: {error_str[:100]}")
                break
    return None

def create_cinematic_fallback(out_path):
    img = Image.new("RGB", (W, H), (15, 15, 20))
    draw = ImageDraw.Draw(img)
    # Moody textured background
    for y in range(H):
        s = 15 + int((y / H) * 20)
        draw.line([(0, y), (W, y)], fill=(s, s, s + 5))
    img.save(out_path, quality=95)

def main():
    if not Path("beats.json").exists(): return
    beats = json.loads(Path("beats.json").read_text())["beats"]

    print(f"🚀 Composing {len(beats)} Scenes (Free Tier Only)...")

    for beat in beats:
        b_id = beat["beat_id"]
        out_file = OUT / f"scene_{b_id:02d}.png"
        
        img = try_ai_generate(get_cinematic_prompt(beat))
        
        if img:
            img.save(out_file, quality=95)
            print(f"  ✅ [Scene {b_id}] AI Success")
        else:
            create_cinematic_fallback(out_file)
            print(f"  ⚠️ [Scene {b_id}] Fallback used")
        
        # 5s sleep to stay under free rate limits
        time.sleep(5)

if __name__ == "__main__":
    main()
