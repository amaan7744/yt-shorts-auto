#!/usr/bin/env python
"""
image_fetch.py

Usage:
    python image_fetch.py

Behavior:
- Reads script_meta.json (if present) to get:
    - wiki_title (for Wikipedia PD images)
    - pexels_keywords (for Pexels search)
- If script_meta.json is missing or incomplete, falls back to generic
  crime/mystery keywords.
- Downloads:
    1) Public-domain images from Wikipedia/Wikimedia for the case (if possible)
    2) Portrait crime/night ambience from Pexels
- Saves all images into ./frames/ as:
    frames/img_001.jpg, frames/img_002.jpg, ...

These are then used by video_build.py to create the final vertical video.
"""

import json
import os
import pathlib
import random
from typing import List, Optional

import requests

FRAMES_DIR = pathlib.Path("frames")
SCRIPT_META_PATH = pathlib.Path("script_meta.json")

# How many images we aim for in total
TARGET_MIN_IMAGES = 6
TARGET_MAX_IMAGES = 12


def log(msg: str) -> None:
    print(f"[IMG] {msg}", flush=True)


def safe_get(d: dict, key: str, default=None):
    v = d.get(key)
    return v if v is not None else default


# ------------------------- Wikipedia helpers ------------------------- #

def wiki_get_pageid(title: str) -> Optional[int]:
    if not title:
        return None

    log(f"Wikipedia page lookup: {title}")
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "titles": title,
            },
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as e:
        log(f"Wikipedia title lookup error: {e}")
        return None

    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    for pid, page in pages.items():
        try:
            pid_int = int(pid)
        except ValueError:
            continue
        if pid_int < 0:
            continue
        return pid_int
    return None


def wiki_fetch_pd_images(title: str, max_images: int = 4) -> List[pathlib.Path]:
    """
    Fetch a few public-domain images from Wikimedia via Wikipedia.
    Saves them as JPEG files in FRAMES_DIR.

    Only uses images whose metadata clearly shows 'Public domain'.
    """
    saved: List[pathlib.Path] = []
    if not title:
        log("No wiki_title provided; skipping Wikipedia PD images.")
        return saved

    pageid = wiki_get_pageid(title)
    if not pageid:
        log("Could not resolve Wikipedia page ID; skipping Wikipedia images.")
        return saved

    # Get images attached to the page
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "pageids": pageid,
                "prop": "images",
                "imlimit": "20",
            },
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
