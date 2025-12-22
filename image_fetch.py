import os
import random
import requests
from io import BytesIO
from PIL import Image

PEXELS_KEY = os.getenv("PEXELS_KEY")
OUT_DIR = "frames"

KEYWORDS = [
    "dark alley night",
    "empty street rain night",
    "abandoned road night",
    "police tape night",
    "silhouette man night",
    "urban fog night",
]

os.makedirs(OUT_DIR, exist_ok=True)

def make_vertical(img):
    img.thumbnail((1080, 1920), Image.Resampling.LANCZOS)
    bg = Image.new("RGB", (1080, 1920), (0, 0, 0))
    bg.paste(img, ((1080 - img.width)//2, (1920 - img.height)//2))
    return bg

headers = {"Authorization": PEXELS_KEY}
query = random.choice(KEYWORDS)

url = f"https://api.pexels.com/v1/search?query={query}&orientation=portrait&per_page=15"
r = requests.get(url, headers=headers, timeout=20)

photos = r.json().get("photos", []) if r.status_code == 200 else []

for i, p in enumerate(photos[:12], 1):
    img_data = requests.get(p["src"]["large2x"], timeout=20).content
    img = Image.open(BytesIO(img_data))
    img = make_vertical(img)
    img.save(f"{OUT_DIR}/img_{i:03d}.jpg", quality=90)

print("[OK] Images fetched")
