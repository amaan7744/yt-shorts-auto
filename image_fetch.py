#!/usr/bin/env python
"""
image_fetch.py

Usage:
    python image_fetch.py

Behavior:
- Reads script_meta.json produced by script_generate.py.
  Expected keys: title, visual_keywords, pexels_keywords, wiki_title.
- Uses Pexels API (if PEXELS_KEY is set) to download crime/mystery photos.
- Tries to fetch a few public-domain images from Wikipedia/Commons for wiki_title.
- Saves all images under ./frames/ as:
    frames/img_001.jpg, img_002.jpg, ...

These images are then used by video_build.py to create Ken Burns / pan-zoom
style vertical video.
"""

import json
import os
import pathlib
import random
import sys
from typing import List, Optional

import requests

FRAMES_DIR = pathlib.Path("frames")
SCRIPT_META_PATH = pathlib.Path("script_meta.json")


def log(msg: str) -> None:
    print(f"[IMG] {msg}", flush=True)


# ------------------------- helpers ------------------------- #

def safe_get(d: dict, key: str, default):
    v = d.get(key)
    return v if v is not None else default


# ------------------------- PEXELS ------------------------- #

def fetch_pexels_images(keywords: List[str], api_key: str, max_images: int = 8) -> List[pathlib.Path]:
    if not api_key:
        log("PEXELS_KEY not set, skipping Pexels.")
        return []

    headers = {"Authorization": api_key}
    saved: List[pathlib.Path] = []

    random.shuffle(keywords)
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
                params={"query": q, "orientation": "portrait", "per_page": 5},
                headers=headers,
                timeout=20,
            )
            resp.raise_for_status()
        except Exception as e:
            log(f"Pexels request error for '{q}': {e}")
            continue

        data = resp.json()
        photos = data.get("photos", [])
        if not photos:
            log(f"No photos for '{q}'")
            continue

        random.shuffle(photos)

        for photo in photos:
            src = photo.get("src") or {}
            # Prefer portrait / large sizes
            url = src.get("portrait") or src.get("large") or src.get("large2x") or src.get("original")
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

            if len(saved) >= max_images:
                break

    return saved


# ------------------------- WIKIPEDIA / COMMONS ------------------------- #

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
        if int(pid) < 0:
            continue
        return int(pid)
    return None


def wiki_fetch_pd_images(title: str, max_images: int = 4) -> List[pathlib.Path]:
    """
    Try to fetch a few public-domain images from Wikimedia via Wikipedia.
    This is best-effort: if license info is missing or non-PD, we skip it.
    """
    saved: List[pathlib.Path] = []
    if not title:
        return saved

    pageid = wiki_get_pageid(title)
    if not pageid:
        return saved

    # First get images on the page
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
        return saved

    random.shuffle(images)

    for img in images:
        if len(saved) >= max_images:
            break

        title = img.get("title")
        if not title or not title.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        # Get imageinfo + license
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

        page = next(iter(pages.values()))
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


# ------------------------- MAIN ------------------------- #

def main() -> None:
    if not SCRIPT_META_PATH.is_file():
        raise SystemExit(f"[IMG] script_meta.json not found at {SCRIPT_META_PATH}")

    FRAMES_DIR.mkdir(exist_ok=True)

    meta = json.loads(SCRIPT_META_PATH.read_text(encoding="utf-8"))
    pexels_keywords = safe_get(meta, "pexels_keywords", [])
    wiki_title = safe_get(meta, "wiki_title", "")

    log(f"Meta wiki_title: {wiki_title}")
    log(f"Pexels keywords: {pexels_keywords}")

    pexels_key = os.environ.get("PEXELS_KEY", "")

    saved_paths: List[pathlib.Path] = []

    # 1) Wikipedia PD images first (real case visuals if possible)
    wiki_imgs = wiki_fetch_pd_images(wiki_title, max_images=4)
    saved_paths.extend(wiki_imgs)

    # 2) Then fill with Pexels photos
    remaining_needed = max(10 - len(saved_paths), 0)
    if remaining_needed > 0 and pexels_keywords:
        pexels_imgs = fetch_pexels_images(pexels_keywords, pexels_key, max_images=remaining_needed)
        saved_paths.extend(pexels_imgs)

    if not saved_paths:
        raise SystemExit("[IMG] No images were fetched from Wikipedia or Pexels.")

    # Sort & rename to a stable sequence (img_001.jpg, img_002.jpg, ...)
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
            old_path.unlink(missing_ok=True)
        final_paths.append(new_path)

    log("Final image list:")
    for p in final_paths:
        log(f" - {p}")

    log(f"Total frames: {len(final_paths)}")


if __name__ == "__main__":
    main()
  
