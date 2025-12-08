#!/usr/bin/env python
import os
import sys
import json
import random
import pathlib
import time
from typing import List

import requests
from pydub import AudioSegment
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.editor import CompositeAudioClip


META_PATH = pathlib.Path("script_meta.json")
FRAMES_DIR = pathlib.Path("frames")
AMBIENCE_DIR = pathlib.Path("ambience")
OUTPUT_MP4 = "output.mp4"
VOICE_WAV = "tts-audio.wav"


def load_meta():
    if not META_PATH.exists():
        print("[video] script_meta.json not found.", file=sys.stderr)
        sys.exit(1)
    return json.loads(META_PATH.read_text(encoding="utf-8"))


def fetch_pexels_images(pexels_key: str, keywords: List[str], max_images: int = 10) -> List[str]:
    if not pexels_key:
        print("[video] No PEXELS_API_KEY, skipping Pexels.", flush=True)
        return []

    out_files = []
    FRAMES_DIR.mkdir(exist_ok=True, parents=True)

    base_url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": pexels_key}

    random.shuffle(keywords)
    for kw in keywords:
        if len(out_files) >= max_images:
            break
        print(f"[video] Pexels search: {kw}")
        try:
            resp = requests.get(
                base_url,
                headers=headers,
                params={"query": kw, "per_page": 4, "orientation": "portrait"},
                timeout=30,
            )
            if resp.status_code != 200:
                print(f"[video] Pexels status: {resp.status_code}")
                continue
            data = resp.json()
            photos = data.get("photos", [])
            random.shuffle(photos)
            for ph in photos:
                src = ph.get("src", {})
                url = src.get("large") or src.get("original")
                if not url:
                    continue
                fname = f"pexels_{len(out_files)+1}.jpg"
                dest = FRAMES_DIR / fname
                print(f"[video] Downloading Pexels image: {url}")
                try:
                    r = requests.get(url, timeout=60)
                    r.raise_for_status()
                    dest.write_bytes(r.content)
                    out_files.append(str(dest))
                    if len(out_files) >= max_images:
                        break
                except Exception as e:
                    print(f"[video] Error downloading Pexels image: {e}")
                    continue
        except Exception as e:
            print(f"[video] Pexels request error: {e}")
            continue

    return out_files


def fetch_wikipedia_images(wiki_title: str, max_images: int = 4) -> List[str]:
    """
    Basic Wikipedia image fetch:
    - Finds images on the page.
    - Prefers ones whose license metadata mentions 'public domain' or 'CC0'.
    THIS IS BEST-EFFORT, not a legal guarantee.
    """
    if not wiki_title:
        return []

    print(f"[video] Fetching Wikipedia images for: {wiki_title}")
    FRAMES_DIR.mkdir(exist_ok=True, parents=True)

    api_base = "https://en.wikipedia.org/w/api.php"
    try:
        # Get all images on the page
        params = {
            "action": "query",
            "titles": wiki_title,
            "prop": "images",
            "format": "json",
            "imlimit": "max",
        }
        resp = requests.get(api_base, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        img_list = page.get("images", [])
        img_titles = [img["title"] for img in img_list if "title" in img]

        if not img_titles:
            print("[video] No images listed on Wikipedia page.")
            return []

        # Query imageinfo for license + url
        titles_chunked = []
        chunk = []
        for t in img_titles:
            chunk.append(t)
            if len(chunk) == 40:
                titles_chunked.append("|".join(chunk))
                chunk = []
        if chunk:
            titles_chunked.append("|".join(chunk))

        pd_imgs = []
        for chunk_titles in titles_chunked:
            params = {
                "action": "query",
                "titles": chunk_titles,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "format": "json",
            }
            r2 = requests.get(api_base, params=params, timeout=30)
            r2.raise_for_status()
            d2 = r2.json()
            pages2 = d2.get("query", {}).get("pages", {})
            for p in pages2.values():
                infos = p.get("imageinfo", [])
                for info in infos:
                    url = info.get("url")
                    meta = info.get("extmetadata", {})
                    lic = (meta.get("LicenseShortName", {}).get("value", "") or "").lower()
                    desc = (meta.get("ImageDescription", {}).get("value", "") or "").lower()
                    # crude public domain filter
                    if "public domain" in lic or "public domain" in desc or "cc0" in lic:
                        if url:
                            pd_imgs.append(url)
        if not pd_imgs:
            print("[video] No clearly PD images found on Wikipedia.")
            return []

        random.shuffle(pd_imgs)
        out_files = []
        for url in pd_imgs[:max_images]:
            fname = f"wiki_{len(out_files)+1}.jpg"
            dest = FRAMES_DIR / fname
            print(f"[video] Downloading PD-like Wikipedia image: {url}")
            try:
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                dest.write_bytes(r.content)
                out_files.append(str(dest))
            except Exception as e:
                print(f"[video] Error downloading Wikipedia image: {e}")
                continue

        return out_files
    except Exception as e:
        print(f"[video] Wikipedia fetch error: {e}")
        return []


def pick_ambience_files() -> List[str]:
    if not AMBIENCE_DIR.exists():
        print("[video] ambience/ folder not found, skipping ambience mix.")
        return []
    candidates = []
    for root, dirs, files in os.walk(AMBIENCE_DIR):
        for f in files:
            lower = f.lower()
            if lower.endswith((".wav", ".mp3", ".flac", ".ogg")):
                if any(k in lower for k in ("rain", "wind", "thunder")):
                    candidates.append(os.path.join(root, f))
    if not candidates:
        print("[video] No ambience files (rain/wind/thunder) found, skipping ambience.")
        return []
    return candidates


def mix_voice_and_ambience(voice_path: str, out_path: str) -> float:
    """
    Returns final duration in seconds.
    """
    voice = AudioSegment.from_file(voice_path)
    duration_ms = len(voice)

    ambience_files = pick_ambience_files()
    if not ambience_files:
        print("[video] No ambience mixed, using pure voice.")
        voice.export(out_path, format="wav")
        return duration_ms / 1000.0

    chosen = random.choice(ambience_files)
    print(f"[video] Using ambience: {chosen}")
    amb = AudioSegment.from_file(chosen)

    if len(amb) < duration_ms:
        loops = duration_ms // len(amb) + 1
        amb = (amb * loops)[:duration_ms]
    else:
        amb = amb[:duration_ms]

    # ambience low volume
    amb = amb - 20  # quieter

    mixed = voice.overlay(amb)
    mixed.export(out_path, format="wav")
    return duration_ms / 1000.0


def build_ken_burns_video(image_paths: List[str], audio_path: str, output_path: str):
    if not image_paths:
        raise SystemExit("[video] No images to build video.")

    audio_seg = AudioSegment.from_file(audio_path)
    audio_duration = len(audio_seg) / 1000.0

    print(f"[video] Final audio duration ~{audio_duration:.2f}s")
    min_total = max(40.0, audio_duration + 1.0)
    target_total = min(45.0, min_total)

    # divide time roughly over images
    per_image = target_total / len(image_paths)
    per_image = max(3.0, min(7.0, per_image))

    print(f"[video] Using {len(image_paths)} images, ~{per_image:.1f}s each")

    clips = []
    w_target, h_target = 1080, 1920

    for idx, img_path in enumerate(image_paths, start=1):
        print(f"[video] Building clip from {img_path}")
        img_clip = ImageClip(img_path)

        # scale to fill height, then center crop width
        img_clip = img_clip.resize(height=h_target)
        w, h = img_clip.size
        if w < w_target:
            img_clip = img_clip.resize(width=w_target)
            w, h = img_clip.size
        x1 = (w - w_target) // 2
        img_clip = img_clip.crop(x1=x1, y1=0, x2=x1 + w_target, y2=h_target)

        # subtle zoom-in/out
        direction = 1 if idx % 2 == 0 else -1
        def zoom(t):
            # t from 0..per_image
            factor = 1.0 + direction * 0.04 * (t / per_image)
            return factor

        kb = img_clip.resize(lambda t: zoom(t)).set_duration(per_image)
        clips.append(kb)

    video = concatenate_videoclips(clips, method="compose")

    # Attach audio
    narration = AudioFileClip(audio_path)
    final_audio = CompositeAudioClip([narration])
    video = video.set_audio(final_audio)

    # cut exactly to audio length (no freeze)
    video = video.set_duration(audio_duration)

    print(f"[video] Writing final video: {output_path}")
    video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        threads=4,
        preset="veryfast",
        verbose=False,
        logger=None,
    )
    print("[video] Done.")


def main():
    if not os.path.exists(VOICE_WAV):
        print("[video] Voice file not found: tts-audio.wav", file=sys.stderr)
        sys.exit(1)

    meta = load_meta()
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    pexels_keywords = meta.get("pexels_keywords") or []
    wiki_title = meta.get("wiki_title", "")

    FRAMES_DIR.mkdir(exist_ok=True, parents=True)

    # 1) Wikipedia images (PD-ish)
    wiki_imgs = fetch_wikipedia_images(wiki_title, max_images=3)

    # 2) Pexels images
    pexels_imgs = fetch_pexels_images(pexels_key, pexels_keywords, max_images=8)

    image_paths = wiki_imgs + pexels_imgs
    image_paths = [p for p in image_paths if os.path.exists(p)]

    if not image_paths:
        print("[video] No images from Wikipedia/Pexels, cannot build video.", file=sys.stderr)
        sys.exit(1)

    # 3) Mix ambience + voice into final audio
    final_audio = "tts-audio-mixed.wav"
    final_duration = mix_voice_and_ambience(VOICE_WAV, final_audio)

    # 4) Build Ken Burns vertical video synced to final audio
    build_ken_burns_video(image_paths, final_audio, OUTPUT_MP4)


if __name__ == "__main__":
    main()
