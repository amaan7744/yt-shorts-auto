import os
import random
import requests
from io import BytesIO
from PIL import Image

PEXELS_KEY = os.getenv("PEXELS_KEY")
OUT_DIR = "frames"

# STRICTLY NON-HUMAN, DARK ENVIRONMENT KEYWORDS
KEYWORDS = [
    "empty dark alley night",
    "abandoned street night rain",
    "empty road fog night",
    "police tape crime scene night",
    "urban street lights fog night",
    "dark corridor abandoned building",
    "lonely highway night fog",
]

# WORDS THAT AUTOMATICALLY REJECT AN IMAGE
BANNED_TERMS = [
    "woman", "women", "girl", "female",
    "couple", "romance", "love",
    "portrait", "model",
    "people", "person", "man", "men",
    "walking", "standing"
]

os.makedirs(OUT_DIR, exist_ok=True)

def log(msg):
    print(f"[IMG] {msg}", flush=True)

def make_vertical(img):
    img.thumbnail((1080, 1920), Image.Resampling.LANCZOS)
    bg = Image.new("RGB", (1080, 1920), (0, 0, 0))
    bg.paste(img, ((1080 - img.width)//2, (1920 - img.height)//2))
    return bg

def is_halal_safe(photo):
    text = " ".join([
        str(photo.get("alt", "")),
        str(photo.get("url", "")),
        str(photo.get("photographer", "")),
    ]).lower()

    return not any(bad in text for bad in BANNED_TERMS)

headers = {"Authorization": PEXELS_KEY}
query = random.choice(KEYWORDS)

log(f"Searching Pexels for: {query}")

url = (
    f"https://api.pexels.com/v1/search"
    f"?query={query}"
    f"&orientation=portrait"
    f"&size=large"
    f"&per_page=30"
)

r = requests.get(url, headers=headers, timeout=20)
photos = r.json().get("photos", []) if r.status_code == 200 else []

saved = 0
max_images = 12

for p in photos:
    if saved >= max_images:
        break

    if not is_halal_safe(p):
        continue

    try:
        img_url = p["src"]["large2x"]
        img_data = requests.get(img_url, timeout=15).content
        img = Image.open(BytesIO(img_data)).convert("RGB")
        img = make_vertical(img)
        img.save(f"{OUT_DIR}/img_{saved+1:03d}.jpg", quality=90)
        saved += 1
        log(f"Saved image {saved}")
    except Exception:
        continue

if saved == 0:
    log("⚠️ No halal-safe images found — consider adjusting keywords.")
else:
    log(f"✅ {saved} halal-safe images fetched.")
