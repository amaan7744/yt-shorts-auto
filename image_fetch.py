#!/usr/bin/env python3
import os, json, random, hashlib, requests
from io import BytesIO
from PIL import Image, ImageEnhance

PEXELS_KEY = os.getenv("PEXELS_KEY")
if not PEXELS_KEY:
    raise SystemExit("❌ PEXELS_KEY missing")

HEADERS = {"Authorization": PEXELS_KEY}

FRAMES_DIR = "frames"
BEATS_FILE = "beats.json"
USED_IMAGES_FILE = "used_images.json"

TARGET_W, TARGET_H = 1080, 1920
MIN_WIDTH = 2200
MAX_TRIES = 50

os.makedirs(FRAMES_DIR, exist_ok=True)

# ---------------- HALAL FILTER ----------------
BANNED_TERMS = {
    "woman","women","girl","female","man","men","person","people",
    "face","portrait","selfie","model","hands","child","couple",
    "body","human"
}

# ---------------- INTENT MAP (CLARITY-FIRST) ----------------
INTENT_PROMPTS = {
    "failure": [
        "empty road at night",
        "abandoned street night",
        "deserted parking lot night"
    ],
    "time_place": [
        "city skyline night",
        "town street night exterior",
        "urban neighborhood night"
    ],
    "mistake": [
        "case files on desk",
        "documents under desk lamp",
        "evidence folder on table"
    ],
    "attention": [
        "evidence board with notes",
        "cold case file folder",
        "unsolved case documents"
    ],
    "reframe": [
        "dark hallway with light",
        "empty room single light",
        "open door dark corridor"
    ],
}

# ---------------- UTIL ----------------
def log(m): print(f"[IMG] {m}", flush=True)

def load_used():
    if os.path.isfile(USED_IMAGES_FILE):
        try:
            return set(json.load(open(USED_IMAGES_FILE)))
        except:
            return set()
    return set()

def save_used(u):
    json.dump(sorted(u), open(USED_IMAGES_FILE, "w"), indent=2)

def hash_url(u):
    return hashlib.sha256(u.encode()).hexdigest()

def is_halal(p):
    text = " ".join([
        p.get("alt",""),
        p.get("url",""),
        p.get("photographer","")
    ]).lower()
    if any(b in text for b in BANNED_TERMS):
        return False
    if p.get("type") == "portrait":
        return False
    return True

def enhance_image(img):
    """
    VERY subtle enhancement.
    Designed for trust + clarity, not drama.
    """
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Sharpness(img).enhance(1.08)
    return img

def make_vertical(img):
    w, h = img.size
    scale = max(TARGET_W / w, TARGET_H / h)
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    x = (img.width - TARGET_W) // 2
    y = max(0, (img.height - TARGET_H) // 2 - int(TARGET_H * 0.08))
    return img.crop((x, y, x + TARGET_W, y + TARGET_H))

# ---------------- FETCH ----------------
def fetch(intent, filename, used):
    prompts = INTENT_PROMPTS.get(intent)
    if not prompts:
        raise SystemExit(f"❌ Unknown intent: {intent}")

    random.shuffle(prompts)

    for prompt in prompts:
        url = f"https://api.pexels.com/v1/search?query={prompt}&orientation=portrait&per_page=80"
        try:
            photos = requests.get(url, headers=HEADERS, timeout=25).json().get("photos", [])
        except:
            continue

        candidates = [p for p in photos if is_halal(p) and p.get("width",0) >= MIN_WIDTH]
        random.shuffle(candidates)

        for p in candidates[:MAX_TRIES]:
            src = p["src"].get("original") or p["src"].get("large2x")
            if not src:
                continue

            h = hash_url(src)
            if h in used:
                continue

            try:
                img = Image.open(BytesIO(requests.get(src, timeout=20).content)).convert("RGB")
                img = make_vertical(img)
                img = enhance_image(img)
                img.save(os.path.join(FRAMES_DIR, filename), quality=95, subsampling=0)
                used.add(h)
                log(f"Saved {filename} ({intent})")
                return
            except:
                continue

    raise SystemExit(f"❌ No image found for intent {intent}")

# ---------------- MAIN ----------------
def main():
    if not os.path.isfile(BEATS_FILE):
        raise SystemExit("❌ beats.json missing")

    beats = json.load(open(BEATS_FILE))
    used = load_used()

    for i, beat in enumerate(beats, 1):
        intent = beat.get("intent")
        fetch(intent, f"img_{i:03d}.jpg", used)

    save_used(used)
    log("✅ Retention-safe images generated")

if __name__ == "__main__":
    main()
