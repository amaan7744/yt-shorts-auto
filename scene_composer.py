#!/usr/bin/env python3
"""
Scene Composer (CI-Safe, Shorts-Ready)

• Uses Hugging Face InferenceClient (modern API)
• AI generation is BEST-EFFORT only
• Programmatic POV visuals are the PRIMARY path
• NEVER produces empty / black frames
"""

import json
import os
import time
import random
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter

# Optional HF (will safely fail)
try:
    from huggingface_hub import InferenceClient
    HAS_HF = True
except Exception:
    HAS_HF = False

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

OUT = Path("frames")
OUT.mkdir(exist_ok=True)

W, H = 1080, 1920
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

# --------------------------------------------------
# VISUAL MAPPING
# --------------------------------------------------

def map_visual(beat: dict) -> dict:
    text = beat.get("text", "").lower()

    if any(k in text for k in ["car", "drive", "vehicle", "road", "dashboard"]):
        scene = "car"
    elif any(k in text for k in ["police", "cop", "siren"]):
        scene = "police"
    elif any(k in text for k in ["room", "bed", "house"]):
        scene = "room"
    elif any(k in text for k in ["street", "city", "downtown"]):
        scene = "city"
    else:
        scene = "abstract"

    return {"scene": scene, "text": text}


# --------------------------------------------------
# HF AI GENERATION (BEST-EFFORT)
# --------------------------------------------------

def try_hf_generate(prompt: str) -> Optional[Image.Image]:
    """
    Attempts HF image generation.
    Returns None on ANY failure.
    """
    hf_token = os.getenv("HF_TOKEN")
    if not (HAS_HF and hf_token):
        return None

    try:
        client = InferenceClient(
            provider="nscale",  # paid provider; may fail in CI
            api_key=hf_token,
        )

        img = client.text_to_image(
            prompt,
            model=HF_MODEL,
        )

        if img:
            return img.resize((W, H), Image.Resampling.LANCZOS)

    except Exception as e:
        print(f"  ⚠ HF AI failed → {e}")

    return None


# --------------------------------------------------
# PROGRAMMATIC POV VISUALS (PRIMARY)
# --------------------------------------------------

def base_gradient(top=(15, 15, 20), bottom=(35, 35, 40)):
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    for y in range(H):
        t = y / H
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    return img


def render_car():
    img = base_gradient()
    d = ImageDraw.Draw(img)

    d.rectangle([0, int(H * 0.65), W, H], fill=(28, 28, 32))

    cx, cy = W // 2, int(H * 0.78)
    d.ellipse([cx - 180, cy - 180, cx + 180, cy + 180],
              outline=(80, 80, 85), width=22)

    glow = Image.new("RGB", (W, H), (255, 210, 140))
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    img = Image.blend(img, glow, 0.12)

    return img.filter(ImageFilter.GaussianBlur(1))


def render_police():
    img = base_gradient()
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, int(H * 0.25)], fill=(160, 0, 0))
    d.rectangle([0, int(H * 0.25), W, int(H * 0.5)], fill=(0, 0, 160))
    d.rectangle([0, int(H * 0.75), W, H], fill=(20, 20, 25))

    return img.filter(ImageFilter.GaussianBlur(2))


def render_room():
    img = base_gradient((25, 22, 20), (45, 40, 35))
    d = ImageDraw.Draw(img)

    d.rectangle([180, int(H * 0.22), 900, int(H * 0.55)],
                fill=(50, 45, 40), outline=(70, 65, 55), width=6)

    glow = Image.new("RGB", (W, H), (255, 190, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    img = Image.blend(img, glow, 0.1)

    return img.filter(ImageFilter.GaussianBlur(1))


def render_city():
    img = base_gradient((10, 12, 25), (25, 28, 45))
    d = ImageDraw.Draw(img)

    for i in range(8):
        bx = i * 140 + random.randint(-10, 10)
        bh = random.randint(int(H * 0.35), int(H * 0.75))
        d.rectangle([bx, H - bh, bx + 120, H], fill=(30, 30, 38))

    return img.filter(ImageFilter.GaussianBlur(1))


def render_abstract():
    img = base_gradient()
    d = ImageDraw.Draw(img)

    for _ in range(3):
        x = random.randint(200, W - 200)
        y = random.randint(200, H - 200)
        s = random.randint(120, 260)
        d.ellipse([x - s, y - s, x + s, y + s],
                  fill=(random.randint(60, 120),
                        random.randint(60, 120),
                        random.randint(60, 120)))

    return img.filter(ImageFilter.GaussianBlur(2))


def render_programmatic(visual: dict) -> Image.Image:
    scene = visual["scene"]

    if scene == "car":
        return render_car()
    if scene == "police":
        return render_police()
    if scene == "room":
        return render_room()
    if scene == "city":
        return render_city()

    return render_abstract()


# --------------------------------------------------
# MAIN COMPOSE
# --------------------------------------------------

def main():
    beats_path = Path("beats.json")
    if not beats_path.exists():
        raise SystemExit("❌ beats.json missing")

    beats = json.loads(beats_path.read_text())["beats"]

    print("=" * 68)
    print("🎬 SCENE COMPOSER (STABLE)")
    print("• HF AI: best-effort")
    print("• Programmatic visuals: guaranteed")
    print("=" * 68)

    for beat in beats:
        visual = map_visual(beat)
        out = OUT / f"scene_{beat['beat_id']:02d}.png"

        print(f"[Scene {beat['beat_id']}] {visual['scene']}")

        img = None

        # Try AI first (optional)
        if HAS_HF:
            prompt = f"{visual['scene']} cinematic POV, dark, atmospheric, 9:16"
            img = try_hf_generate(prompt)

        # Guaranteed fallback
        if img is None:
            img = render_programmatic(visual)

        img.save(out, quality=95)
        print(f"  ✓ saved {out.name}")

        time.sleep(0.3)

    print("=" * 68)
    print(f"✅ Generated {len(beats)} scenes → {OUT.absolute()}")
    print("=" * 68)


if __name__ == "__main__":
    main()
