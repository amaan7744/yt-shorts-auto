#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (FINAL)

ABSOLUTE RULES:
- assets.py is the single source of truth
- Script defines intent → assets follow
- NO approximate keywords
- NO random visuals
- NO fake tags like "human"
- Hook ALWAYS shows a person
- CTA rotates + names victim + loops
"""

import os
import json
import random
from pathlib import Path
from groq import Groq

from assets import ASSET_KEYWORDS, validate_assets

# ==================================================
# OUTPUT FILES
# ==================================================

SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

# ==================================================
# CASE INPUT (ONLY EDIT THIS)
# ==================================================

CURRENT_CASE = {
    "victim_name": "Joe",
    "victim_gender": "male",      # male / female
    "victim_age": "elderly",      # child / adult / elderly
    "victim_desc": "an elderly man",
    "incident_type": "accident",  # accident / murder / suicide / mystery
    "location": "a hospital parking lot",
    "time": "3:17 AM",
    "key_clue": "his car keys were still in the ignition",
    "official_story": "it was ruled an accident"
}

# ==================================================
# CTA (CONTROLLED ROTATION)
# ==================================================

CTA_ACTIONS = ["Subscribe", "Follow", "Stay with us"]

def build_cta(victim_name: str) -> str:
    action = random.choice(CTA_ACTIONS)
    return (
        f"{action} to help keep cases like {victim_name}'s alive — "
        f"was this really the truth?"
    )

# ==================================================
# GROQ CLIENT (STREAMING – EXACT USAGE)
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

# ==================================================
# SCRIPT GENERATION (RETENTION FORMULA)
# ==================================================

def generate_script(client: Groq):
    """
    Returns EXACTLY 7 lines:
    1. Hook question
    2. What happened
    3. Who
    4. Where + when
    5. Strange clue
    6. Official story + doubt
    7. CTA question (will be replaced)
    """

    prompt = f"""
Write a true crime YouTube Shorts script.

STRICT FORMAT:
- EXACTLY 7 short lines
- Calm investigative tone
- No conclusions
- No filler

STRUCTURE:
1. Hook QUESTION implying {CURRENT_CASE['incident_type']}
2. What happened
3. Who it happened to
4. Where and when
5. Strange clue
6. Official explanation + doubt
7. Looping question

CASE DETAILS:
Victim: {CURRENT_CASE['victim_desc']}
Location: {CURRENT_CASE['location']}
Time: {CURRENT_CASE['time']}
Clue: {CURRENT_CASE['key_clue']}
Official story: {CURRENT_CASE['official_story']}

Return ONLY the 7 lines, one per line.
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        max_completion_tokens=512,
        stream=True
    )

    text = ""
    for chunk in completion:
        text += chunk.choices[0].delta.content or ""

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if len(lines) != 7:
        raise RuntimeError(f"❌ Script must be exactly 7 lines, got {len(lines)}")

    return lines

# ==================================================
# INTENT → ASSET TAG MAP (NO GUESSING)
# ==================================================

INTENT_TAG_MAP = {
    "victim_male_elderly": ["elderly man"],
    "victim_female_elderly": ["elderly woman"],
    "victim_male": ["human figure"],
    "victim_female": ["woman"],

    "hospital": ["hospital", "hospital hallway"],
    "parking": ["parked car", "highway", "trunk"],

    "phone_clue": ["phone", "text"],
    "investigation": ["evidence", "interrogation"],
    "cta": ["shadow", "human figure"]
}

# ==================================================
# KEYWORD DERIVATION (STRICT)
# ==================================================

def derive_keywords(line: str, index: int):
    t = line.lower()

    # ---- HOOK + WHO ----
    if index in (0, 2):
        if CURRENT_CASE["victim_age"] == "elderly" and CURRENT_CASE["victim_gender"] == "male":
            return INTENT_TAG_MAP["victim_male_elderly"]
        if CURRENT_CASE["victim_age"] == "elderly" and CURRENT_CASE["victim_gender"] == "female":
            return INTENT_TAG_MAP["victim_female_elderly"]
        if CURRENT_CASE["victim_gender"] == "female":
            return INTENT_TAG_MAP["victim_female"]
        return INTENT_TAG_MAP["victim_male"]

    # ---- LOCATION ----
    if "hospital" in t:
        return INTENT_TAG_MAP["hospital"]

    if "parking" in t or "car" in t:
        return INTENT_TAG_MAP["parking"]

    # ---- CLUE ----
    if "key" in t or "keys" in t or "phone" in t or "text" in t:
        return INTENT_TAG_MAP["phone_clue"]

    # ---- INVESTIGATION ----
    if "ruled" in t or "official" in t or "police" in t:
        return INTENT_TAG_MAP["investigation"]

    # ---- CTA ----
    if index == 6:
        return INTENT_TAG_MAP["cta"]

    raise RuntimeError(f"❌ Cannot derive asset intent from line: {line}")

# ==================================================
# ASSET MATCHING (STRICT, NON-RANDOM)
# ==================================================

def match_asset(keywords, used_assets):
    for asset, tags in ASSET_KEYWORDS.items():
        if asset in used_assets:
            continue
        if any(k in tags for k in keywords):
            return asset
    raise RuntimeError(f"❌ No asset matches keywords: {keywords}")

# ==================================================
# MAIN
# ==================================================

def main():
    print("🧪 Validating assets…")
    validate_assets()

    client = init_client()

    print("🧠 Generating full script via Groq streaming API…")
    lines = generate_script(client)

    # Replace final line with controlled CTA
    lines[-1] = build_cta(CURRENT_CASE["victim_name"])

    print("✂️ Segmenting script into 5s blocks…")
    beats = []
    used_assets = set()

    for i, line in enumerate(lines):
        keywords = derive_keywords(line, i)
        asset = match_asset(keywords, used_assets)
        used_assets.add(asset)

        beats.append({
            "beat_id": i + 1,
            "text": line,
            "asset_file": asset,
            "duration": 5.0,
            "keywords": keywords
        })

    Path(SCRIPT_FILE).write_text(" ".join(lines), encoding="utf-8")
    Path(BEATS_FILE).write_text(json.dumps({"beats": beats}, indent=2), encoding="utf-8")

    print("✅ Script + beats generated")
    print("🎯 Script and visuals are strictly aligned")

# ==================================================
if __name__ == "__main__":
    main()
