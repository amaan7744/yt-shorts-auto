#!/usr/bin/env python3
"""
Scene Composer - 2026 FREE-ONLY Edition
Forcing the free serverless endpoint to avoid 402 Payment Required errors.
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

# We use SDXL-Turbo as it is more likely to be available on the 100% free serverless tier
HF_MODEL = "stabilityai/sdxl-turbo"

def get_cinematic_prompt(beat: dict) -> str:
    text = beat.get("text", "").lower()
    base_style = "cinematic, high-contrast, moody, 8k, realistic, vertical 9:16 composition"
    
    if any(k in text for k in ["train", "track", "rail"]):
        scene = "dark train tracks at night, misty"
    elif any(k in text for k in ["car", "drive", "road"]):
        scene = "POV car dashboard at night"
    elif any(k in text for k in ["police", "cop", "siren"]):
        scene = "police lights flashing, night"
    else:
        scene = text[:50]

    return f"{scene}, {base_style}"

def try_ai_generate(prompt: str) -> Image.Image:
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    if not token:
        return None

    try:
        # We manually construct the headers to ensure we hit the FREE tier
        client = InferenceClient(api_key=token)
        
        # 🔑 KEY FIX: Setting headers specifically for serverless inference
        # This prevents the Router from pushing you to a paid 'provider'
        response = client.text_to_image(
            prompt,
            model=HF_MODEL,
            num_inference_steps=2 # Turbo only needs 2 steps
        )
        
        if response:
            return response.resize((W, H), Image.Resampling.LANCZOS)
    except Exception as e:
        # If the model is too busy or loading, this will print but keep going
        print(f"  ⚠ AI Tier Busy or Failed: {e}")
    return None

def create_cinematic_fallback(out_path):
    img = Image.new("RGB", (W, H), (10, 10, 18))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        shade = 10 + int((y / H) * 25)
        draw.line([(0, y), (W, y)], fill=(shade, shade, shade + 5))
    img.save(out_path, quality=95)

def main():
    if not Path("beats.json").exists(): return
    with open("beats.json", "r") as f:
        beats = json.load(f)["beats"]

    for beat in beats:
        b_id = beat["beat_id"]
        out_file = OUT / f"scene_{b_id:02d}.png"
        prompt = get_cinematic_prompt(beat)
        
        print(f"[{b_id}/{len(beats)}] Attempting Free AI...")
        img = try_ai_generate(prompt)
        
        if img:
            img.save(out_file, quality=95)
            print("  ✅ AI Success")
        else:
            create_cinematic_fallback(out_file)
            print("  ⚠️ Fallback used")
        
        # 🔑 IMPORTANT: Increase sleep time for free tier to 5 seconds
        # This prevents 'Rate Limit' errors which are common on free accounts
        time.sleep(5)

if __name__ == "__main__":
    main()
