#!/usr/bin/env python3
"""
Scene Composer - RESILIENT FREE EDITION
Specifically handles 503 (Loading) and 402 (Payment) errors.
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

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
OUT = Path("frames")
OUT.mkdir(exist_ok=True)

W, H = 1080, 1920

# We use FLUX.1-schnell because it is the most robust free model in 2026.
# If this model is busy, the script will wait for it.
HF_MODEL = "black-forest-labs/FLUX.1-schnell"

def get_cinematic_prompt(beat: dict) -> str:
    text = beat.get("text", "").lower()
    # High-quality technical cues to force "Real" looks over "Drawings"
    base_style = "cinematic film still, 35mm lens, moody lighting, hyper-realistic, 8k, vertical 9:16"
    
    if any(k in text for k in ["train", "track", "rail"]):
        scene = "dark moody train tracks at night, misty atmosphere"
    elif any(k in text for k in ["car", "drive", "road"]):
        scene = "POV shot from car interior, dashboard glow, dark road"
    elif any(k in text for k in ["police", "cop", "siren"]):
        scene = "police sirens flashing blue and red, wet pavement"
    else:
        scene = text[:60]

    return f"{scene}, {base_style}"

# --------------------------------------------------
# AI GENERATION WITH WAITING LOGIC
# --------------------------------------------------

def try_ai_generate(prompt: str) -> Image.Image:
    token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
    if not token:
        print("  ❌ No API Key found in Environment Variables!")
        return None

    # Force the free serverless endpoint
    client = InferenceClient(api_key=token)
    
    # We try up to 4 times to give the "Cold" model time to wake up
    max_attempts = 4
    for attempt in range(max_attempts):
        try:
            print(f"  🎨 Requesting AI (Attempt {attempt+1}/{max_attempts})...")
            
            # num_inference_steps=4 is the sweet spot for FLUX-schnell
            response = client.text_to_image(
                prompt,
                model=HF_MODEL,
                num_inference_steps=4
            )
            return response.resize((W, H), Image.Resampling.LANCZOS)

        except Exception as e:
            error_msg = str(e)
            
            # Check if the error is "Payment Required" (402)
            if "402" in error_msg:
                print("  ⚠ 402 Error: API is trying to use a paid provider. Switching tactics...")
                # We can't fix this without a Pro account, so we move to fallback
                return None
                
            # Check if the error is "Model Loading" (503)
            if "503" in error_msg or "loading" in error_msg.lower():
                wait_time = 25 + (attempt * 15)
                print(f"  ⏳ Model is waking up. Waiting {wait_time}s for GPU...")
                time.sleep(wait_time)
            else:
                print(f"  ⚠ AI Error: {error_msg}")
                return None
                
    return None

# --------------------------------------------------
# HIGH-QUALITY PROGRAMMATIC FALLBACK
# --------------------------------------------------

def create_cinematic_fallback(out_path):
    """Creates a grainy, atmospheric background so the video isn't 'shitty'."""
    img = Image.new("RGB", (W, H), (15, 15, 22))
    draw = ImageDraw.Draw(img)

    # Add a moody spotlight
    overlay = Image.new("RGB", (W, H), (40, 40, 60))
    mask = Image.new("L", (W, H), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.ellipse([W//4, H//4, 3*W//4, H//2], fill=120)
    mask = mask.filter(ImageFilter.GaussianBlur(250))
    img.paste(overlay, (0,0), mask)

    # Add Film Grain
    noise = Image.new("RGB", (W, H))
    n_draw = ImageDraw.Draw(noise)
    for _ in range(10000):
        nx, ny = random.randint(0, W-1), random.randint(0, H-1)
        v = random.randint(0, 35)
        n_draw.point((nx, ny), fill=(v, v, v))
    
    img = Image.blend(img, noise, 0.1)
    img.save(out_path, quality=95)

# --------------------------------------------------
# MAIN PROCESS
# --------------------------------------------------

def main():
    if not Path("beats.json").exists():
        print("❌ beats.json missing!")
        return

    with open("beats.json", "r") as f:
        beats = json.load(f)["beats"]

    print(f"🚀 Processing {len(beats)} scenes for YouTube Shorts...")

    for beat in beats:
        b_id = beat["beat_id"]
        out_file = OUT / f"scene_{b_id:02d}.png"
        
        prompt = get_cinematic_prompt(beat)
        
        # 1. Try AI with retry logic
        img = try_ai_generate(prompt)
        
        if img:
            img.save(out_file, quality=95)
            print(f"  ✅ [Scene {b_id}] AI Visual Generated.")
        else:
            # 2. Resilient Fallback
            create_cinematic_fallback(out_file)
            print(f"  ⚠️ [Scene {b_id}] AI Unavailable. Using Cinematic Fallback.")
        
        # Respect Rate Limits (Free tier is strict!)
        time.sleep(5)

    print("\n✅ All scenes processed.")

if __name__ == "__main__":
    main()
