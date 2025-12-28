import os
import requests
from io import BytesIO
from PIL import Image

PEXELS_KEY = os.getenv("PEXELS_KEY")
OUT_DIR = "frames"
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {"Authorization": PEXELS_KEY}

# Beat-based keywords (NOT random)
BEAT_KEYWORDS = {
    "01_hook.jpg": "empty driveway night car",
    "02_odd.jpg": "abandoned backpack night",
    "03_conflict.jpg": "locked door night exterior",
    "04_contradiction.jpg": "empty street fog night",
}

BANNED_TERMS = [
    "woman","women","girl","female","couple","romance",
    "portrait","model","people","person","man","men"
]

def make_vertical(img):
    img.thumbnail((1080,1920), Image.Resampling.LANCZOS)
    bg = Image.new("RGB",(1080,1920),(0,0,0))
    bg.paste(img,((1080-img.width)//2,(1920-img.height)//2))
    return bg

def halal(photo):
    text = " ".join([
        photo.get("alt",""),
        photo.get("url",""),
        photo.get("photographer","")
    ]).lower()
    return not any(b in text for b in BANNED_TERMS)

def fetch(query, out):
    url = f"https://api.pexels.com/v1/search?query={query}&orientation=portrait&per_page=15"
    r = requests.get(url, headers=HEADERS, timeout=20)
    for p in r.json().get("photos", []):
        if not halal(p):
            continue
        img = Image.open(BytesIO(
            requests.get(p["src"]["large2x"], timeout=15).content
        )).convert("RGB")
        make_vertical(img).save(os.path.join(OUT_DIR,out), quality=90)
        print(f"[IMG] Saved {out}")
        return
    raise RuntimeError(f"No safe image for {query}")

def main():
    for name, query in BEAT_KEYWORDS.items():
        fetch(query, name)

if __name__ == "__main__":
    main()
