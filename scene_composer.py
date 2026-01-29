#!/usr/bin/env python3
"""
Scene Composer - 2026 FLUX.1 Edition
Uses the high-speed FLUX.1-schnell model for cinematic 9:16 visuals.
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
# CONFIG & MODEL SELECTION
# --------------------------------------------------
OUT = Path("frames")
OUT.mkdir(exist_ok=True)

W, H = 1080, 1920
# FLUX.1-schnell is the best 2026 choice for free, fast, high-quality API calls
HF_MODEL = "black-forest-labs/FLUX.1-schnell"

# --------------------------------------------------
# CINEMATIC PROMPT ENGINE
# --------------------------------------------------

def get_cinematic_prompt(beat: dict) -> str:
    """Creates detailed, active prompts that avoid common AI safety triggers."""
    text = beat.get("text", "").lower()
    
    # 2026 Prompting Tip: Use natural language and technical camera cues
    # for better cinematic results with FLUX models.
    base_style = (
        "cinematic film still, high-contrast lighting, moody atmosphere, "
        "shot on 35mm lens, realistic textures, 8k, professional cinematography, "
        "dark mystery aesthetic, vertical 9:16 composition"
    )

    # Scene Detection Logic
    if any(k in text for k in ["train", "track", "rail", "station"]):
        scene = "mysterious train tracks at night, heavy fog, distant station lights glowing"
    elif any(k in text for k in ["car", "drive", "road", "dashboard"]):
        scene = "POV from a car interior, glowing dashboard, headlights hitting a dark lonely road"
    elif any(k in text for k in ["police", "cop", "siren", "officer"]):
        scene = "flashing blue and red emergency lights reflecting on wet pavement, cinematic bokeh"
    elif any(k in text for k in ["room", "house", "inside", "bedroom"]):
        scene = "dark interior room, single warm lamp light, long dramatic shadows, investigative vibe"
    elif any(k in text for k in ["city", "street", "alley", "downtown"]):
        scene = "dark urban alleyway, neon sign reflections in puddles, atmospheric mist"
    else:
        scene = f"atmospheric cinematic shot of {text[:50]}"

    return f"{scene}, {base_style}"

# --------------------------------------------------
# AI GENERATION (FLUX ROUTING)
# --------------------------------------------------

def try_ai_generate(prompt: str) -> Image.Image:
    """Attempts generation using HF Inference Client with FLUX-optimized params."""
    # Check for common secret names
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    if not token:
        return None

    try:
        # 2026 Best Practice: Let the Hub route to the fastest available provider
        client = InferenceClient(api_key=token)
        
        # FLUX.1-schnell excels at speed (1-4 steps) and complex detail
        img = client.text_to_image(
            prompt,
            model=HF_MODEL,
            # 'schnell' is distilled; more steps aren't needed
            num_inference_steps=4 
        )
        
        if img:
            return img.resize((W, H), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"  ⚠ AI Request failed: {e}")
    return None

# --------------------------------------------------
# IMPROVED CINEMATIC FALLBACK (NO CIRCLES)
# --------------------------------------------------

def create_cinematic_fallback(out_path):
    """Generates a moody, textured gradient fallback if the AI is offline."""
    # Deep 'Investigative' Blue/Black Gradient
    img = Image.new("RGB", (W, H), (10, 10, 18))
    draw = ImageDraw.Draw(img)

    for y in range(H):
        # Subtle vertical gradient
        shade = 10 + int((y / H) * 25)
        draw.line([(0, y), (W, y)], fill=(shade, shade, shade + 5))

    # Add 'Film Grain' noise
    noise = Image.new("RGB", (W, H))
    n_draw = ImageDraw.Draw(noise)
    for _ in range(8000):
        nx, ny = random.randint(0, W-1), random.randint(0, H-1)
        val = random.randint(0, 40)
        n_draw.point((nx, ny), fill=(val, val, val))
    
    img = Image.blend(img, noise, 0.1)
    img = img.filter(ImageFilter.GaussianBlur(1.5))
    img.save(out_path, quality=95)

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

def main():
    if not Path("beats.json").exists():
        print("❌ Error: beats.json not found")
        return

    with open("beats.json", "r") as f:
        beats = json.load(f)["beats"]

    print(f"🎬 Composing {len(beats)} Cinematic Scenes...")

    for beat in beats:
        b_id = beat["beat_id"]
        out_file = OUT / f"scene_{b_id:02d}.png"
        
        prompt = get_cinematic_prompt(beat)
        print(f"[{b_id}/{len(beats)}] Generating visual...")

        # 1. Attempt High-Quality AI
        img = try_ai_generate(prompt)
        
        if img:
            img.save(out_file, quality=95)
            print(f"  ✅ AI Visual Saved")
        else:
            # 2. Resilient Fallback (Guarantees no black screen)
            create_cinematic_fallback(out_file)
            print(f"  ⚠️ Used Cinematic Fallback")
        
        # Small delay to respect free tier rate limits
        time.sleep(2)

    print(f"✅ Finished! Check {OUT} folder.")

if __name__ == "__main__":
    main()
