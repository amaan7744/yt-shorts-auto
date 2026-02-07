#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (FINAL, LOCKED)

ABSOLUTE GUARANTEES:
- Filenames are NEVER invented
- Assets are chosen ONLY from disk
- Registry must exactly match disk
- Hook uses STATIC IMAGES word-by-word
- Videos play ONLY after hook
- CTA is GENERATED, not injected
- A case is NEVER reused
"""

import os
import json
from pathlib import Path
from groq import Groq

from assets import (
    VIDEO_ASSET_KEYWORDS,
    HOOK_IMAGE_CATEGORIES,
    validate_video_assets,
    validate_hook_images,
    CORE_MURDER_SUICIDE_MYSTERY,
    PSYCHOLOGICAL_HOOKS,
)

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

ASSET_DIR = Path("asset")
HOOK_DIR = ASSET_DIR / "hook_static"

MEMORY_DIR = Path("memory")
USED_CASES_FILE = MEMORY_DIR / "used_cases.json"
LAST_HOOK_FILE = MEMORY_DIR / "last_hook_category.txt"

# ==================================================
# CASE INPUT
# ==================================================

CURRENT_CASE = {
    "victim_name": "Joe",
    "victim_gender": "male",
    "victim_age": "elderly",
    "victim_desc": "an elderly man",
    "incident_type": "accident",
    "location": "a hospital parking lot",
    "time": "3:17 AM",
    "key_clue": "his car keys were still in the ignition",
    "official_story": "it was ruled an accident",
}

# ==================================================
# MEMORY (NEVER REPEAT)
# ==================================================

def case_id(case: dict) -> str:
    return f"{case['victim_name']}|{case['location']}|{case['time']}".lower()

def load_used_cases():
    MEMORY_DIR.mkdir(exist_ok=True)
    if not USED_CASES_FILE.exists():
        USED_CASES_FILE.write_text("[]", encoding="utf-8")
    return set(json.loads(USED_CASES_FILE.read_text()))

def save_used_case(cid: str):
    used = load_used_cases()
    used.add(cid)
    USED_CASES_FILE.write_text(json.dumps(sorted(used), indent=2))

# ==================================================
# HOOK CATEGORY MEMORY (NO REPEAT)
# ==================================================

def load_last_hook():
    return LAST_HOOK_FILE.read_text().strip() if LAST_HOOK_FILE.exists() else None

def save_last_hook(cat: str):
    LAST_HOOK_FILE.write_text(cat)

# ==================================================
# GROQ CLIENT
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

# ==================================================
# DISK-LOCKED HOOK IMAGE ACCESS
# ==================================================

def hook_images_on_disk(category: str):
    """
    Returns ONLY hook images that:
    - exist on disk
    - are declared in the registry
    - belong to the requested category
    """
    disk_files = {p.name for p in HOOK_DIR.glob("*.jpeg")}

    images = [
        name for name, cat in HOOK_IMAGE_CATEGORIES.items()
        if cat == category and name in disk_files
    ]

    if not images:
        raise RuntimeError(
            f"❌ No hook images on disk for category: {category}"
        )

    return images

# ==================================================
# SCRIPT GENERATION (VISUAL-LOCKED)
# ==================================================

ALLOWED_VISUALS = [
    "elderly man lying on stair landing",
    "elderly man seated indoors",
    "elderly man in hospital bed",
    "hospital corridor with gurney",
    "parked car at night",
    "driver slumped in driver seat",
    "phone lying on floor",
    "dimly lit human figure",
    "empty hospital hallway",
    "dark bedroom interior",
    "hallway interior",
    "motel room interior",
    "crime scene with blood",
    "interrogation room",
    "evidence on table",
]

def generate_script(client: Groq, hook_category: str):
    """
    Line 1: Hook question
    Lines 2–7: MUST use allowed visuals ONLY
    """

    prompt = f"""
Write a true crime YouTube Shorts script.

ABSOLUTE RULES:
- EXACTLY 7 lines
- Line 1 is a HOOK QUESTION (no visuals)
- Lines 2–7 MUST include [VISUAL: ...]
- Visuals MUST be chosen ONLY from the ALLOWED VISUALS list
- NO invented or abstract visuals
- Calm investigative tone
- NO conclusions

ALLOWED VISUALS (MUST MATCH EXACTLY):
{chr(10).join("- " + v for v in ALLOWED_VISUALS)}

STRUCTURE:
1. Hook question
2. What physically happened [VISUAL]
3. Who the victim is [VISUAL]
4. Where and when [VISUAL]
5. A strange physical clue [VISUAL]
6. The official explanation that feels wrong [VISUAL]
7. CTA mentioning {CURRENT_CASE['victim_name']} and Subscribe/Follow, ending with a QUESTION

CASE FACTS:
Victim: {CURRENT_CASE['victim_desc']}
Location: {CURRENT_CASE['location']}
Time: {CURRENT_CASE['time']}
Key clue: {CURRENT_CASE['key_clue']}
Official story: {CURRENT_CASE['official_story']}
Incident type: {CURRENT_CASE['incident_type']}

Return ONLY the 7 lines.
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_completion_tokens=600,
    )

    lines = [l.strip() for l in res.choices[0].message.content.split("\n") if l.strip()]

    if len(lines) != 7:
        raise RuntimeError(f"❌ Script must be exactly 7 lines, got {len(lines)}")

    return lines

# ==================================================
# VIDEO ASSET MATCHING (DISK-FIRST)
# ==================================================

def video_asset_for_visual(visual: str, used: set):
    visual_l = visual.lower()

    for asset, tags in VIDEO_ASSET_KEYWORDS.items():
        if asset in used:
            continue
        if any(tag in visual_l for tag in tags):
            path = ASSET_DIR / asset
            if not path.exists():
                raise RuntimeError(f"❌ Declared video missing on disk: {asset}")
            return asset

    raise RuntimeError(f"❌ No video asset matches visual: {visual}")

# ==================================================
# MAIN
# ==================================================

def main():
    print("🧪 Validating assets…")
    validate_video_assets()
    validate_hook_images()

    # HARD LOCK: registry must equal disk
    hook_disk = {p.name for p in HOOK_DIR.glob("*.jpeg")}
    hook_declared = set(HOOK_IMAGE_CATEGORIES.keys())
    if hook_disk != hook_declared:
        raise RuntimeError(
            f"❌ Hook registry mismatch\n"
            f"Missing: {hook_disk - hook_declared}\n"
            f"Extra: {hook_declared - hook_disk}"
        )

    cid = case_id(CURRENT_CASE)
    if cid in load_used_cases():
        raise RuntimeError("❌ This case has already been used. Aborting.")

    last_hook = load_last_hook()
    hook_category = (
        CORE_MURDER_SUICIDE_MYSTERY
        if last_hook != CORE_MURDER_SUICIDE_MYSTERY
        else PSYCHOLOGICAL_HOOKS
    )
    save_last_hook(hook_category)

    client = init_client()
    lines = generate_script(client, hook_category)

    beats = []

    # --------------------
    # HOOK (STATIC IMAGES)
    # --------------------
    hook_words = [w.strip("?,.") for w in lines[0].split() if len(w) > 4]
    hook_images = hook_images_on_disk(hook_category)

    per_word_duration = 0.6

    for i, word in enumerate(hook_words):
        beats.append({
            "beat_id": len(beats) + 1,
            "type": "image",
            "text": word,
            "asset_file": hook_images[i % len(hook_images)],
            "duration": per_word_duration,
        })

    # --------------------
    # STORY (VIDEO ASSETS)
    # --------------------
    used_assets = set()

    for line in lines[1:]:
        text, visual = line.split("[VISUAL:")
        visual = visual.replace("]", "").strip()

        asset = video_asset_for_visual(visual, used_assets)
        used_assets.add(asset)

        beats.append({
            "beat_id": len(beats) + 1,
            "type": "video",
            "text": text.strip(),
            "asset_file": asset,
        })

    Path(SCRIPT_FILE).write_text(" ".join(lines), encoding="utf-8")
    Path(BEATS_FILE).write_text(json.dumps({"beats": beats}, indent=2), encoding="utf-8")

    save_used_case(cid)

    print("✅ Script written")
    print("🎞️ Assets selected ONLY from disk")
    print("🔒 Case permanently locked")

# ==================================================
if __name__ == "__main__":
    main()
