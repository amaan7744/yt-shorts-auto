#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (FINAL, LOCKED)

GUARANTEES:
- CTA is GENERATED, not injected
- Script explicitly describes visuals
- Assets FOLLOW script, never random
- Hook uses STATIC IMAGES word-by-word
- Videos play ONLY after hook
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
    CRIME_SCENE_DOUBT,
    HUMAN_FOCUSED_HOOKS,
    DARK_CURIOSITY,
)

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

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
    "official_story": "it was ruled an accident"
}

# ==================================================
# CASE MEMORY (NEVER REPEAT)
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
    if LAST_HOOK_FILE.exists():
        return LAST_HOOK_FILE.read_text().strip()
    return None

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
# SCRIPT GENERATION
# ==================================================

def generate_script(client: Groq, hook_category: str):
    """
    AI WRITES ALL 7 LINES INCLUDING CTA
    Line 1 = HOOK QUESTION (words only)
    Lines 2–7 = MUST include [VISUAL: ...]
    """

    prompt = f"""
Write a true crime YouTube Shorts script.

ABSOLUTE RULES:
- EXACTLY 7 lines
- Line 1 is a HOOK QUESTION (no visuals, no brackets)
- Lines 2–7 MUST include [VISUAL: ...]
- Every visual must be concrete and filmable
- NO abstract language
- NO conclusions
- Calm investigative tone

STRUCTURE:
1. Hook question about the case
2. What physically happened [VISUAL]
3. Who the victim is [VISUAL]
4. Where and when [VISUAL]
5. A strange physical clue [VISUAL]
6. The official explanation that feels wrong [VISUAL]
7. CTA that:
   - Mentions {CURRENT_CASE['victim_name']}
   - Includes Subscribe or Follow
   - Ends with a QUESTION

HOOK CATEGORY:
{hook_category}

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
        temperature=0.35,
        max_completion_tokens=600
    )

    lines = [l.strip() for l in res.choices[0].message.content.split("\n") if l.strip()]

    if len(lines) != 7:
        raise RuntimeError(f"❌ Script must be exactly 7 lines, got {len(lines)}")

    return lines

# ==================================================
# ASSET MATCHING (STRICT)
# ==================================================

def video_asset_for_visual(visual: str, used: set):
    visual_l = visual.lower()

    for asset, tags in VIDEO_ASSET_KEYWORDS.items():
        if asset in used:
            continue
        if all(tag in visual_l for tag in tags):
            return asset

    raise RuntimeError(f"❌ No video asset matches visual: {visual}")

# ==================================================
# MAIN
# ==================================================

def main():
    print("🧪 Validating assets…")
    validate_video_assets()
    validate_hook_images()

    cid = case_id(CURRENT_CASE)
    if cid in load_used_cases():
        raise RuntimeError("❌ This case has already been used. Aborting.")

    last_hook = load_last_hook()
    hook_category = CORE_MURDER_SUICIDE_MYSTERY if last_hook != CORE_MURDER_SUICIDE_MYSTERY else PSYCHOLOGICAL_HOOKS
    save_last_hook(hook_category)

    client = init_client()
    lines = generate_script(client, hook_category)

    beats = []

    # --------------------
    # HOOK (STATIC IMAGES)
    # --------------------
    hook_words = [w.strip("?,.") for w in lines[0].split() if len(w) > 4]

    hook_images = [
        img for img, cat in HOOK_IMAGE_CATEGORIES.items()
        if cat == hook_category
    ][:len(hook_words)]

    for i, img in enumerate(hook_images):
        beats.append({
            "beat_id": len(beats) + 1,
            "text": hook_words[i],
            "asset_file": img,
            "duration": None  # driven by word timing
        })

    # --------------------
    # STORY (VIDEO ASSETS)
    # --------------------
    used_assets = set()

    for line in lines[1:]:
        if "[VISUAL:" not in line:
            raise RuntimeError("❌ Missing [VISUAL] in story line")

        text, visual = line.split("[VISUAL:")
        visual = visual.replace("]", "").strip()

        asset = video_asset_for_visual(visual, used_assets)
        used_assets.add(asset)

        beats.append({
            "beat_id": len(beats) + 1,
            "text": text.strip(),
            "asset_file": asset,
            "duration": 5.0
        })

    Path(SCRIPT_FILE).write_text(" ".join(lines), encoding="utf-8")
    Path(BEATS_FILE).write_text(json.dumps({"beats": beats}, indent=2), encoding="utf-8")

    save_used_case(cid)

    print("✅ Script written")
    print("🎞️ Hook images synced to hook words")
    print("🔒 Case permanently locked")

# ==================================================
if __name__ == "__main__":
    main()
