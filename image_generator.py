#!/usr/bin/env python3
"""
Scene Composer
Fully automated asset-based POV visuals
NO AI
NO API
NO MANUAL WORK
"""

import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path("frames")
OUT.mkdir(exist_ok=True)

W, H = 1080, 1920


# --------------------------------------------------
# BASE
# --------------------------------------------------

def base_scene(darkness=20):
    img = Image.new("RGB", (W, H), (darkness, darkness, darkness))
    draw = ImageDraw.Draw(img)

    # vertical gradient
    for y in range(H):
        shade = darkness + int((y / H) * 35)
        draw.line([(0, y), (W, y)], fill=(shade, shade, shade))

    return img


# --------------------------------------------------
# SCENES
# --------------------------------------------------

def car_pov():
    img = base_scene(random.randint(15, 25))
    draw = ImageDraw.Draw(img)

    # dashboard (foreground)
    draw.rectangle([0, int(H*0.7), W, H], fill=(30, 30, 35))

    # steering wheel
    offset = random.randint(-40, 40)
    draw.ellipse([360+offset, 1180, 720+offset, 1540], outline=(70,70,75), width=18)

    # body silhouette
    draw.ellipse([520+offset, 920, 620+offset, 1050], fill=(95,95,100))

    # street light glow
    glow = Image.new("RGB", (W, H), (255, 210, 140))
    glow = glow.filter(ImageFilter.GaussianBlur(300))
    img = Image.blend(img, glow, 0.08)

    return img.filter(ImageFilter.GaussianBlur(1))


def room_pov():
    img = base_scene(random.randint(18, 28))
    draw = ImageDraw.Draw(img)

    # bed edge
    draw.rectangle([200, int(H*0.68), 880, int(H*0.78)], fill=(65,65,70))

    # body
    draw.ellipse([520, 980, 640, 1100], fill=(100,100,105))

    return img.filter(ImageFilter.GaussianBlur(1))


def police_pov():
    img = base_scene(20)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, W, 260], fill=(180, 0, 0))
    draw.rectangle([0, 260, W, 520], fill=(0, 0, 180))

    return img.filter(ImageFilter.GaussianBlur(4))


# --------------------------------------------------
# ROUTER
# --------------------------------------------------

def compose_scene(prompt: str, out: Path):
    p = prompt.lower()

    if "car" in p:
        img = car_pov()
    elif "police" in p:
        img = police_pov()
    elif "room" in p or "bed" in p:
        img = room_pov()
    else:
        img = base_scene()

    img.save(out)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    beats = json.loads(Path("beats.json").read_text())["beats"]

    for beat in beats:
        out = OUT / f"scene_{beat['beat_id']:02d}.png"
        if out.exists():
            continue
        compose_scene(beat["image_prompt"], out)


if __name__ == "__main__":
    main()
