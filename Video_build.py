#!/usr/bin/env python
"""
video_build.py

Usage:
    python video_build.py final_audio.wav

Behavior:
- Reads the narration+ambience audio file (default: final_audio.wav).
- Measures audio duration.
- Reads all images from ./frames/ (img_*.jpg / .png) created by image_fetch.py.
- Builds a vertical 1080x1920 video:
    - Each image is shown for an equal slice of the audio duration.
    - Images are resized and center-cropped to 1080x1920 (no black bars).
    - Simple, stable cuts (no crazy effects) for maximum reliability.
- Writes result to video_raw.mp4 with no audio.
  main.yml will later mux final_audio.wav and video_raw.mp4 into output.mp4.

This is intentionally simple to avoid rendering bugs and freezing frames.
"""

import os
import sys
from typing import List

from moviepy.editor import ImageClip, concatenate_videoclips
from pydub import AudioSegment

FRAMES_DIR = "frames"
OUTPUT_VIDEO = "video_raw.mp4"
TARGET_RESOLUTION = (1080, 1920)  # width, height
DEFAULT_FPS = 30
MIN_CLIP_SEC = 3.0
MAX_CLIP_SEC = 7.0


def log(msg: str) -> None:
    print(f"[VID] {msg}", flush=True)


def get_audio_duration(audio_path: str) -> float:
    if not os.path.isfile(audio_path):
        raise SystemExit(f"[VID] Audio file not found: {audio_path}")
    audio = AudioSegment.from_file(audio_path)
    dur_sec = len(audio) / 1000.0
    log(f"Audio duration: {dur_sec:.2f} s")
    return max(dur_sec, MIN_CLIP_SEC)


def list_frames() -> List[str]:
    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit(f"[VID] Frames directory not found: {FRAMES_DIR}")

    files: List[str] = []
    for name in os.listdir(FRAMES_DIR):
        lower = name.lower()
        if lower.endswith((".jpg", ".jpeg", ".png")):
            files.append(os.path.join(FRAMES_DIR, name))

    if not files:
        raise SystemExit(f"[VID] No frame images found in {FRAMES_DIR}")

    files.sort()
    log(f"Using {len(files)} frame images.")
    return files


def make_vertical_clip(img_path: str, duration: float) -> ImageClip:
    """
    Create a vertical 1080x1920 ImageClip with center crop.
    """
    clip = ImageClip(img_path)

    target_w, target_h = TARGET_RESOLUTION
    w, h = clip.size

    # First, scale so that the image fully covers the 1080x1920 area.
    # We pick the scale factor so that both dimensions are >= target.
    scale_w = target_w / w
    scale_h = target_h / h
    scale = max(scale_w, scale_h)
    clip = clip.resize(scale)

    w, h = clip.size
    x_center = w / 2
    y_center = h / 2

    clip = clip.crop(
        x_center=x_center,
        y_center=y_center,
        width=target_w,
        height=target_h,
    )

    clip = clip.set_duration(duration)
    return clip


def main() -> None:
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "final_audio.wav"

    total_dur = get_audio_duration(audio_path)
    frame_paths = list_frames()
    n_frames = len(frame_paths)

    # Compute per-image duration
    per_clip = total_dur / n_frames
    per_clip = max(MIN_CLIP_SEC, min(MAX_CLIP_SEC, per_clip))

    # If clamped, total duration might differ slightly, but later ffmpeg
    # will trim to exact audio duration.
    log(f"Per-image duration: {per_clip:.2f} s")

    clips: List[ImageClip] = []
    for idx, path in enumerate(frame_paths, start=1):
        log(f"Creating clip {idx}/{n_frames} from {path}")
        clip = make_vertical_clip(path, per_clip)
        clips.append(clip)

    if not clips:
        raise SystemExit("[VID] No clips created, aborting.")

    log("Concatenating clips...")
    final = concatenate_videoclips(clips, method="compose")

    log(f"Writing {OUTPUT_VIDEO} at {DEFAULT_FPS} fps...")
    final.write_videofile(
        OUTPUT_VIDEO,
        fps=DEFAULT_FPS,
        codec="libx264",
        audio=False,
        preset="veryfast",
        threads=2,
        verbose=False,
        logger=None,
    )

    log("video_build.py finished successfully.")


if __name__ == "__main__":
    main()
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
