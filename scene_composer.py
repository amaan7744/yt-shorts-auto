#!/usr/bin/env python3
"""
Scene Composer - 100% FREE Forever
Uses Hugging Face's FREE Inference API (no credit card, no limits for hobby use)
"""
import json
import os
import time
from pathlib import Path
from PIL import Image
from io import BytesIO
import base64

# NO PAID APIS - ALL FREE!
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠ requests library not found. Install with: pip install requests --break-system-packages")

OUT = Path("frames")
OUT.mkdir(exist_ok=True)
W, H = 1080, 1920

# --------------------------------------------------
# HUGGING FACE FREE API (No credit card needed!)
# --------------------------------------------------
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

# Free models available on Hugging Face (no payment required!)
FREE_MODELS = {
    "sd-turbo": "stabilityai/sd-turbo",  # FAST - 1 step generation!
    "sdxl-turbo": "stabilityai/sdxl-turbo",  # FAST SDXL - 1 step!
    "sd-1.5": "runwayml/stable-diffusion-v1-5",  # Classic SD
    "openjourney": "prompthero/openjourney",  # Midjourney-style
    "anything-v4": "andite/anything-v4.0",  # Anime style
    "realistic-vision": "SG161222/Realistic_Vision_V5.1_noVAE",  # Photorealistic
}

# Default to fastest free model
DEFAULT_MODEL = "stabilityai/sdxl-turbo"

def generate_prompt(beat: dict) -> dict:
    """Generate detailed prompt from beat text"""
    text = beat.get("text", "").lower()
    
    # Scene detection
    scene_keywords = {
        "car": ["car", "drive", "driving", "vehicle", "highway", "road", "dashboard"],
        "police": ["police", "cop", "officer", "arrest", "siren", "chase"],
        "room": ["room", "bedroom", "house", "home", "inside", "bed"],
        "city": ["city", "street", "urban", "downtown", "buildings"],
        "night": ["night", "dark", "evening", "midnight"],
        "club": ["club", "party", "dance", "music", "crowd"],
    }
    
    scene = "abstract"
    for scene_type, keywords in scene_keywords.items():
        if any(kw in text for kw in keywords):
            scene = scene_type
            break
    
    # Mood detection
    mood = "neutral"
    if any(w in text for w in ["chase", "fast", "escape", "urgent"]):
        mood = "tense"
    elif any(w in text for w in ["alone", "lonely", "sad", "empty"]):
        mood = "melancholic"
    elif any(w in text for w in ["party", "fun", "happy"]):
        mood = "energetic"
    
    # Build prompts
    prompts = {
        "car": f"cinematic POV from car interior, steering wheel visible, night driving, dashboard lights, windshield view, headlight beams on dark road, realistic, detailed, atmospheric",
        
        "police": f"POV from police car, emergency lights flashing red and blue, urgent atmosphere, night scene, dashboard radio equipment, dramatic lighting, realistic",
        
        "room": f"cozy bedroom interior POV, soft lighting through window blinds, bedside lamp glow, intimate atmosphere, warm colors, realistic, detailed",
        
        "city": f"urban cityscape at night, neon lights, tall buildings, street view, atmospheric fog, cinematic lighting, realistic, detailed",
        
        "night": f"dark atmospheric night scene, moody lighting, deep shadows, cinematic, mysterious atmosphere, realistic",
        
        "club": f"nightclub interior, colorful strobe lights, crowd silhouettes, DJ lights, party atmosphere, dynamic lighting, realistic",
        
        "abstract": f"abstract cinematic composition, dark atmospheric background, geometric shapes, gradient lighting, minimalist, artistic"
    }
    
    prompt = prompts.get(scene, prompts["abstract"])
    
    # Add mood modifier
    if mood == "tense":
        prompt += ", intense, dramatic, high contrast"
    elif mood == "melancholic":
        prompt += ", melancholic, somber, emotional"
    elif mood == "energetic":
        prompt += ", energetic, vibrant, dynamic"
    
    # Quality tags
    prompt += ", professional photography, 9:16 vertical composition"
    
    return {
        "scene": scene,
        "mood": mood,
        "prompt": prompt,
        "text": text
    }

def generate_with_huggingface(prompt: str, model: str = DEFAULT_MODEL) -> Image.Image:
    """
    Generate image using Hugging Face's FREE Inference API
    NO CREDIT CARD NEEDED! Just create free account at huggingface.co
    """
    if not HAS_REQUESTS:
        return None
    
    if not HUGGINGFACE_API_KEY:
        print("  ⚠ No Hugging Face API key found")
        print("  💡 Get FREE API key at: https://huggingface.co/settings/tokens")
        print("  Then: export HUGGINGFACE_API_KEY='your_key_here'")
        return None
    
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    
    # Payload for text-to-image
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": "ugly, blurry, low quality, distorted, deformed, text, watermark, bad anatomy",
            "num_inference_steps": 1 if "turbo" in model else 25,  # Turbo = 1 step!
            "guidance_scale": 0.0 if "turbo" in model else 7.5,  # Turbo doesn't use guidance
        }
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Resize to our target dimensions
            img = img.resize((W, H), Image.Resampling.LANCZOS)
            return img
        elif response.status_code == 503:
            print(f"  ⏳ Model loading... (this happens first time, wait 20s)")
            time.sleep(20)
            # Retry once
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img = img.resize((W, H), Image.Resampling.LANCZOS)
                return img
        
        print(f"  ⚠ API Error: {response.status_code}")
        if response.status_code == 401:
            print("  ❌ Invalid API key. Get one at: https://huggingface.co/settings/tokens")
        else:
            print(f"  Response: {response.text[:200]}")
        return None
        
    except Exception as e:
        print(f"  ⚠ Error: {e}")
        return None

# --------------------------------------------------
# ENHANCED FALLBACK (No API needed)
# --------------------------------------------------
def create_enhanced_scene(visual: dict) -> Image.Image:
    """Create high-quality programmatic scene as fallback"""
    from PIL import ImageDraw, ImageFilter
    import random
    
    scene = visual["scene"]
    
    # Base gradient
    img = Image.new("RGB", (W, H), (15, 15, 20))
    draw = ImageDraw.Draw(img)
    
    # Scene-specific rendering
    if scene == "car":
        # Gradient sky
        for y in range(int(H * 0.6)):
            shade = 15 + int((y / H) * 25)
            draw.line([(0, y), (W, y)], fill=(shade, shade, shade + 5))
        
        # Dashboard
        draw.rectangle([0, int(H * 0.6), W, H], fill=(25, 25, 30))
        
        # Steering wheel
        cx, cy = W // 2, int(H * 0.75)
        draw.ellipse([cx - 180, cy - 180, cx + 180, cy + 180], 
                     outline=(70, 70, 75), width=22)
        draw.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], 
                     fill=(85, 85, 90))
        
        # Spokes
        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            import math
            rad = math.radians(angle)
            x1 = cx + int(65 * math.cos(rad))
            y1 = cy + int(65 * math.sin(rad))
            x2 = cx + int(165 * math.cos(rad))
            y2 = cy + int(165 * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=(75, 75, 80), width=12)
        
        # Headlight glow
        glow = Image.new("RGB", (W, H), (255, 220, 150))
        glow = glow.filter(ImageFilter.GaussianBlur(200))
        img = Image.blend(img, glow, 0.15)
        
    elif scene == "police":
        # Alternating lights
        for i in range(8):
            y1 = i * (H // 8)
            y2 = (i + 1) * (H // 8)
            color = (180, 0, 0) if i % 2 == 0 else (0, 0, 180)
            overlay = Image.new("RGB", (W, H), color)
            overlay = overlay.filter(ImageFilter.GaussianBlur(60))
            mask = Image.new("L", (W, H), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rectangle([0, y1, W, y2], fill=150)
            img.paste(overlay, (0, 0), mask)
        
        # Dashboard
        draw.rectangle([0, int(H * 0.75), W, H], fill=(20, 20, 25))
        
    elif scene == "room":
        # Warm gradient
        for y in range(H):
            r = 20 + int((y / H) * 30)
            g = 18 + int((y / H) * 25)
            b = 15 + int((y / H) * 20)
            draw.line([(0, y), (W, y)], fill=(r, g, b))
        
        # Window with blinds
        wx, wy = 200, int(H * 0.2)
        ww, wh = 680, int(H * 0.4)
        draw.rectangle([wx, wy, wx + ww, wy + wh], 
                      fill=(40, 38, 35), outline=(55, 52, 48), width=6)
        
        # Blinds
        for y in range(wy, wy + wh, 40):
            draw.rectangle([wx, y, wx + ww, y + 32], fill=(35, 33, 30))
            draw.rectangle([wx, y + 32, wx + ww, y + 36], fill=(110, 95, 70))
        
        # Lamp glow
        lamp_x, lamp_y = 780, int(H * 0.65)
        glow = Image.new("RGB", (W, H), (255, 200, 120))
        mask = Image.new("L", (W, H), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([lamp_x - 250, lamp_y - 350, lamp_x + 250, lamp_y + 150], fill=180)
        glow = glow.filter(ImageFilter.GaussianBlur(180))
        img.paste(glow, (0, 0), mask)
        
    elif scene == "city":
        # Night sky gradient
        for y in range(H):
            r = 15 + int((y / H) * 20)
            g = 12 + int((y / H) * 25)
            b = 25 + int((y / H) * 40)
            draw.line([(0, y), (W, y)], fill=(r, g, b))
        
        # Buildings
        for i in range(9):
            bx = i * 130 + random.randint(-15, 15)
            bh = random.randint(int(H * 0.3), int(H * 0.75))
            bw = random.randint(90, 140)
            
            draw.rectangle([bx, H - bh, bx + bw, H], fill=(28, 28, 35))
            
            # Windows
            for wy in range(H - bh + 50, H - 50, 70):
                for wx in range(bx + 25, bx + bw - 25, 45):
                    if random.random() > 0.25:
                        draw.rectangle([wx, wy, wx + 25, wy + 40], 
                                     fill=(220, 200, 120))
        
        # Neon glow
        neon = Image.new("RGB", (W, H), (150, 50, 200))
        neon = neon.filter(ImageFilter.GaussianBlur(180))
        img = Image.blend(img, neon, 0.18)
        
    else:  # abstract/night
        # Artistic gradient
        colors = [(80, 50, 100), (50, 80, 120), (100, 60, 80)]
        base_color = random.choice(colors)
        
        for y in range(H):
            factor = y / H
            r = int(15 + base_color[0] * factor * 0.4)
            g = int(15 + base_color[1] * factor * 0.4)
            b = int(20 + base_color[2] * factor * 0.4)
            draw.line([(0, y), (W, y)], fill=(r, g, b))
        
        # Geometric shapes
        for _ in range(random.randint(2, 4)):
            x = random.randint(150, W - 150)
            y = random.randint(150, H - 150)
            size = random.randint(120, 280)
            alpha_val = random.randint(40, 80)
            
            overlay = Image.new("RGB", (W, H), (0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            shape_color = (random.randint(60, 140), 
                          random.randint(60, 140), 
                          random.randint(60, 140))
            
            if random.choice([True, False]):
                overlay_draw.ellipse([x - size//2, y - size//2, 
                                    x + size//2, y + size//2], 
                                   fill=shape_color)
            else:
                overlay_draw.rectangle([x - size//2, y - size//2, 
                                      x + size//2, y + size//2], 
                                     fill=shape_color)
            
            overlay = overlay.filter(ImageFilter.GaussianBlur(25))
            img = Image.blend(img, overlay, 0.15)
    
    # Add subtle blur
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    
    # Film grain
    noise = Image.new("L", (W, H))
    noise_pixels = noise.load()
    for x in range(0, W, 3):
        for y in range(0, H, 3):
            noise_pixels[x, y] = random.randint(0, 40)
    noise = noise.filter(ImageFilter.GaussianBlur(0.5))
    img = Image.blend(img.convert("RGB"), 
                     Image.new("RGB", (W, H), (0, 0, 0)).convert("RGB"), 
                     0.03)
    
    return img

def compose_scene(visual: dict, out: Path, use_ai: bool = True):
    """Generate scene - try AI first, fallback to programmatic"""
    
    img = None
    
    # Try AI generation if enabled
    if use_ai and HUGGINGFACE_API_KEY and HAS_REQUESTS:
        print(f"  🎨 Generating with AI...")
        img = generate_with_huggingface(visual["prompt"])
        if img:
            print(f"  ✓ AI generation successful!")
    
    # Fallback to programmatic
    if img is None:
        print(f"  🎨 Using enhanced programmatic rendering...")
        img = create_enhanced_scene(visual)
    
    # Save
    img.save(out, quality=95)
    print(f"  💾 Saved: {out.name}")

def main():
    print("=" * 70)
    print("🎬 SCENE COMPOSER - 100% FREE FOREVER")
    print("=" * 70)
    print()
    
    # Check API key
    if HUGGINGFACE_API_KEY:
        print("✅ Hugging Face API key found - AI generation enabled!")
        print(f"   Using model: {DEFAULT_MODEL}")
        print(f"   Rate limit: Generous free tier (perfect for hobby projects)")
    else:
        print("ℹ️  No API key - using enhanced programmatic generation")
        print()
        print("💡 Want FREE AI-generated images? (No credit card needed!)")
        print("   1. Create free account: https://huggingface.co/join")
        print("   2. Get API token: https://huggingface.co/settings/tokens")
        print("   3. Set environment variable:")
        print("      export HUGGINGFACE_API_KEY='hf_your_token_here'")
        print()
        print("   Models available:")
        for name, model_id in FREE_MODELS.items():
            print(f"   - {name}: {model_id}")
    
    print()
    print("-" * 70)
    print()
    
    # Load beats
    beats_file = Path("beats.json")
    if not beats_file.exists():
        print("📝 Creating sample beats.json...")
        sample = {
            "beats": [
                {"beat_id": 1, "text": "Driving through neon-lit city streets at night"},
                {"beat_id": 2, "text": "Police lights flashing in the rearview mirror"},
                {"beat_id": 3, "text": "Alone in my bedroom, thoughts racing"},
                {"beat_id": 4, "text": "Downtown skyline glowing against dark sky"},
                {"beat_id": 5, "text": "Lost in the club, bass shaking everything"}
            ]
        }
        beats_file.write_text(json.dumps(sample, indent=2))
        print("✓ Created sample beats.json")
        print()
    
    beats = json.loads(beats_file.read_text())["beats"]
    print(f"📋 Processing {len(beats)} beats...\n")
    
    # Generate scenes
    use_ai = bool(HUGGINGFACE_API_KEY and HAS_REQUESTS)
    
    for i, beat in enumerate(beats, 1):
        print(f"[{i}/{len(beats)}] Beat {beat['beat_id']}")
        print(f"  📝 Text: {beat.get('text', 'No text')[:65]}...")
        
        # Generate prompt
        visual = generate_prompt(beat)
        print(f"  🎬 Scene: {visual['scene']} | Mood: {visual['mood']}")
        
        if use_ai:
            print(f"  💬 Prompt: {visual['prompt'][:70]}...")
        
        # Output path
        out = OUT / f"scene_{beat['beat_id']:02d}.png"
        
        # Generate
        compose_scene(visual, out, use_ai=use_ai)
        print()
        
        # Small delay for API
        if use_ai:
            time.sleep(2)
    
    print("=" * 70)
    print(f"✅ COMPLETE! Generated {len(beats)} scenes")
    print(f"📁 Output: {OUT.absolute()}")
    print("=" * 70)
    print()
    
    if not use_ai:
        print("💡 TIP: Enable FREE AI generation for photorealistic images!")
        print("   No credit card required, generous free tier")
        print("   Instructions above ⬆️")

if __name__ == "__main__":
    main()
