#!/usr/bin/env python3

import os, json, random, hashlib, requests
from io import BytesIO
from PIL import Image

PEXELS_KEY = os.getenv("PEXELS_KEY")
if not PEXELS_KEY:
    raise SystemExit("❌ PEXELS_KEY missing")

HEADERS = {"Authorization": PEXELS_KEY}

FRAMES_DIR = "frames"
BEATS_FILE = "beats.json"
USED_IMAGES_FILE = "used_images.json"

TARGET_W, TARGET_H = 1080, 1920
MIN_WIDTH = 2000
MAX_TRIES = 40

os.makedirs(FRAMES_DIR, exist_ok=True)

# ---------------- HALAL FILTER ----------------
BANNED_TERMS = {
    "woman","women","girl","female","man","men","person",
    "people","face","portrait","selfie","model","hands",
    "child","couple"
}

# ---------------- INTENT MAP ----------------
INTENT_PROMPTS = {
    "failure": [
        "empty road at night",
        "abandoned street dark",
    ],
    "time_place": [
        "city skyline night",
        "old map texture dark",
    ],
    "mistake": [
        "case files on desk",
        "documents under desk lamp",
    ],
    "attention": [
        "case file stamped unresolved",
        "evidence board dark room",
        "cold case folder under light",
    ],
    "reframe": [
        "dark hallway fading",
        "empty room single light",
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

def hash_url(u): return hashlib.sha256(u.encode()).hexdigest()

def is_halal(p):
    text = " ".join([
        p.get("alt",""),
        p.get("url",""),
        p.get("photographer","")
    ]).lower()
    if any(b in text for b in BANNED_TERMS): return False
    if p.get("type") == "portrait": return False
    return True

def make_vertical(img):
    w,h = img.size
    s = max(TARGET_W/w, TARGET_H/h)
    img = img.resize((int(w*s), int(h*s)), Image.Resampling.LANCZOS)
    x = (img.width - TARGET_W)//2
    y = (img.height - TARGET_H)//2
    return img.crop((x,y,x+TARGET_W,y+TARGET_H))

# ---------------- FETCH ----------------
def fetch(intent, filename, used):
    prompts = INTENT_PROMPTS.get(intent)
    if not prompts:
        raise SystemExit(f"❌ Unknown intent: {intent}")

    random.shuffle(prompts)

    for prompt in prompts:
        url = f"https://api.pexels.com/v1/search?query={prompt}&orientation=portrait&per_page=80"
        try:
            photos = requests.get(url, headers=HEADERS, timeout=25).json().get("photos",[])
        except:
            continue

        random.shuffle(photos)

        for p in photos[:MAX_TRIES]:
            if not is_halal(p): continue
            src = p["src"].get("original") or p["src"].get("large2x")
            if not src: continue
            if p.get("width",0) < MIN_WIDTH: continue

            h = hash_url(src)
            if h in used: continue

            try:
                img = Image.open(BytesIO(requests.get(src,timeout=20).content)).convert("RGB")
                img = make_vertical(img)
                img.save(os.path.join(FRAMES_DIR, filename), quality=95, subsampling=0)
                used.add(h)
                log(f"Saved {filename} ({intent})")
                return
            except:
                continue

    raise SystemExit(f"❌ No image for intent {intent}")

# ---------------- MAIN ----------------
def main():
    beats = json.load(open(BEATS_FILE))
    used = load_used()

    for i, beat in enumerate(beats, 1):
        intent = beat.get("intent")
        fetch(intent, f"img_{i:03d}.jpg", used)

    save_used(used)
    log("✅ Beat-aligned images generated")

if __name__ == "__main__":
    main()
