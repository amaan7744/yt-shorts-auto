#!/usr/bin/env python3
import os, requests, random
from PIL import Image
from io import BytesIO

FRAME_DIR = "frames"
PEXELS_KEY = os.getenv("PEXELS_KEY")

DARK_KEYWORDS = [
    "dark alley at night",
    "empty street rain night",
    "silhouette walking night",
    "misty road night",
    "police lights wet asphalt",
    "foggy urban street night",
    "shadowy figure streetlamp"
]

os.makedirs(FRAME_DIR, exist_ok=True)

def download_image(url):
    try:
        r = requests.get(url, timeout=10)
        img = Image.open(BytesIO(r.content)).convert("RGB")
        return img
    except:
        return None

def pexels_search():
    if not PEXELS_KEY:
        return []

    kw = random.choice(DARK_KEYWORDS)
    url = f"https://api.pexels.com/v1/search?query={kw}&orientation=portrait&size=large&per_page=10"
    r = requests.get(url, headers={"Authorization":PEXELS_KEY})
    items = r.json().get("photos",[])
    urls = [p["src"]["large2x"] for p in items if "src" in p]
    return urls

def vertical(img):
    target = (1080,1920)
    img.thumbnail((1200,2200), Image.Resampling.LANCZOS)
    w,h = img.size
    bg = Image.new("RGB", target, (0,0,0))
    bg.paste(img, ((1080-w)//2, (1920-h)//2))
    return bg

def main():
    urls = []

    # Fetch from Pexels
    urls.extend(pexels_search())

    # Pick 10–15 images total
    urls = list(dict.fromkeys(urls))[:15]

    idx = 1
    for u in urls:
        img = download_image(u)
        if img:
            v = vertical(img)
            v.save(f"{FRAME_DIR}/img_{idx:03d}.jpg", quality=92)
            idx += 1

    print("[IMAGES] Done.")

if __name__ == "__main__":
    main()
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as e:
        log(f"Wikipedia images lookup error: {e}")
        return saved

    data = resp.json()
    images = (
        data.get("query", {})
        .get("pages", {})
        .get(str(pageid), {})
        .get("images", [])
    )

    if not images:
        log("No images attached to Wikipedia page.")
        return saved

    random.shuffle(images)

    for img in images:
        if len(saved) >= max_images:
            break

        title = img.get("title")
        if not title or not title.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        # Get license + direct URL from Wikimedia Commons
        try:
            info_resp = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "format": "json",
                    "titles": title,
                    "prop": "imageinfo",
                    "iiprop": "url|extmetadata",
                },
                timeout=20,
            )
            info_resp.raise_for_status()
        except Exception as e:
            log(f"Commons info error for {title}: {e}")
            continue

        info_data = info_resp.json()
        pages = info_data.get("query", {}).get("pages", {})
        if not pages:
            continue

        page = next(iter(pages.values()), {})
        iinfo = page.get("imageinfo", [])
        if not iinfo:
            continue

        meta = iinfo[0].get("extmetadata", {}) or {}
        license_short = (meta.get("LicenseShortName", {}) or {}).get("value", "")
        url = iinfo[0].get("url")

        # Only accept if clearly Public domain
        if "public domain" not in license_short.lower():
            continue
        if not url:
            continue

        idx = len(saved) + 1
        out_path = FRAMES_DIR / f"img_wiki_{idx:03d}.jpg"
        log(f"Downloading PD Wikipedia image {idx}: {url}")

        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            log(f"Error downloading Wikipedia image: {e}")
            continue

        out_path.write_bytes(r.content)
        saved.append(out_path)

    return saved


# ------------------------- Pexels helpers ------------------------- #

def normalize_keywords(raw) -> List[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    return []


def default_pexels_keywords() -> List[str]:
    return [
        "dark alley at night",
        "empty street night rain",
        "crime scene tape at night",
        "police lights in the dark",
        "lonely road streetlights",
        "mysterious silhouette street",
    ]


def fetch_pexels_images(keywords: List[str], api_key: str, max_images: int = 8) -> List[pathlib.Path]:
    saved: List[pathlib.Path] = []

    if not api_key:
        log("PEXELS_KEY not set; skipping Pexels images.")
        return saved

    if not keywords:
        keywords = default_pexels_keywords()

    random.shuffle(keywords)

    headers = {"Authorization": api_key}

    for kw in keywords:
        if len(saved) >= max_images:
            break

        q = kw.strip()
        if not q:
            continue

        log(f"Pexels search: {q}")
        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                params={
                    "query": q,
                    "orientation": "portrait",
                    "per_page": 5,
                },
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
        except Exception as e:
            log(f"Pexels request error for '{q}': {e}")
            continue

        data = resp.json()
        photos = data.get("photos", [])
        if not photos:
            log(f"No photos found for '{q}'")
            continue

        random.shuffle(photos)

        for photo in photos:
            if len(saved) >= max_images:
                break

            src = photo.get("src") or {}
            url = (
                src.get("portrait")
                or src.get("large")
                or src.get("large2x")
                or src.get("original")
            )
            if not url:
                continue

            idx = len(saved) + 1
            out_path = FRAMES_DIR / f"img_pexels_{idx:03d}.jpg"
            log(f"Downloading Pexels image {idx}: {url}")

            try:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
            except Exception as e:
                log(f"Error downloading Pexels image: {e}")
                continue

            out_path.write_bytes(r.content)
            saved.append(out_path)

    return saved


# ------------------------- MAIN ------------------------- #

def main() -> None:
    FRAMES_DIR.mkdir(exist_ok=True)

    meta = {}
    if SCRIPT_META_PATH.is_file():
        try:
            meta = json.loads(SCRIPT_META_PATH.read_text(encoding="utf-8"))
            log("Loaded script_meta.json")
        except Exception as e:
            log(f"Error reading script_meta.json: {e}")
            meta = {}
    else:
        log("script_meta.json not found; using fallback keywords only.")

    wiki_title = safe_get(meta, "wiki_title", "") or safe_get(meta, "title", "")
    raw_pexels_keywords = (
        safe_get(meta, "pexels_keywords", None)
        or safe_get(meta, "visual_keywords", None)
    )
    pexels_keywords = normalize_keywords(raw_pexels_keywords)

    log(f"wiki_title: {wiki_title!r}")
    log(f"pexels_keywords: {pexels_keywords}")

    pexels_key = os.environ.get("PEXELS_KEY", "")

    saved_paths: List[pathlib.Path] = []

    # 1) Wikipedia PD images first (case visuals)
    wiki_imgs = wiki_fetch_pd_images(wiki_title, max_images=4)
    saved_paths.extend(wiki_imgs)

    # 2) Fill the rest from Pexels
    remaining_needed = max(TARGET_MIN_IMAGES - len(saved_paths), 0)
    max_more = max(TARGET_MAX_IMAGES - len(saved_paths), 0)

    if max_more > 0:
        pexels_imgs = fetch_pexels_images(
            pexels_keywords,
            pexels_key,
            max_images=max_more,
        )
        saved_paths.extend(pexels_imgs)

    if not saved_paths:
        raise SystemExit("[IMG] No images were fetched from Wikipedia or Pexels.")

    # Sort & rename to stable, sequential names: img_001.jpg, img_002.jpg, ...
    saved_paths = sorted(saved_paths)
    final_paths: List[pathlib.Path] = []

    for idx, old_path in enumerate(saved_paths, start=1):
        new_path = FRAMES_DIR / f"img_{idx:03d}.jpg"
        if old_path == new_path:
            final_paths.append(new_path)
            continue

        try:
            old_path.replace(new_path)
        except Exception:
            # fallback copy
            new_path.write_bytes(old_path.read_bytes())
            try:
                old_path.unlink()
            except Exception:
                pass

        final_paths.append(new_path)

    log("Final image list:")
    for p in final_paths:
        log(f" - {p}")
    log(f"Total frames: {len(final_paths)}")


if __name__ == "__main__":
    main()
