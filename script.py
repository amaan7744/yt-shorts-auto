#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (FINAL, ASSET-LOCKED)

CORE GUARANTEES:
- assets.py is the ONLY source of asset truth
- Script drives visuals, NOT the other way around
- Every 5s segment maps to a REAL asset keyword
- Hook ALWAYS shows a real human asset
- NO fake tags (like 'human')
- NO random scenery
- CTA rotates + names victim + loops
"""

import os
import json
import random
import re
from pathlib import Path
from groq import Groq

from assets import ASSET_KEYWORDS, validate_assets

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

# ==================================================
# CASE INPUT (EDIT ONLY THIS)
# ==================================================

CURRENT_CASE = {
    "victim_name": "Joe",
    "victim_gender": "male",          # male / female / unknown
    "victim_age": "elderly",           # child / adult / elderly / unknown
    "victim_desc": "an elderly man",
    "incident_type": "accident",       # accident / murder / suicide / mystery
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
# GROQ CLIENT (STREAMING, EXACT API)
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

# ==================================================
# SCRIPT GENERATION (RETENTION FORMULA)
# ==================================================

def generate_script(client: Groq) -> str:
    """
    Generates a 35–40s script following:
    Hook → What happened → Who → Where/When → Clue → Contradiction → CTA
    """

    prompt = f"""
Write a true crime YouTube Shorts script.

STRICT STRUCTURE (DO NOT BREAK):
1. HOOK: A sharp QUESTION implying {CURRENT_CASE['incident_type']}
2. WHAT HAPPENED
3. WHO IT HAPPENED TO
4. WHERE + WHEN
5. STRANGE CLUE
6. OFFICIAL STORY + DOUBT
7. CTA-style QUESTION (no subscribe words)

RULES:
- Short sentences
- Calm investigative tone
- No conclusions
- No names except the victim
- Each line must describe a VISUAL moment

CASE DETAILS:
Victim: {CURRENT_CASE['victim_desc']}
Location: {CURRENT_CASE['location']}
Time: {CURRENT_CASE['time']}
Clue: {CURRENT_CASE['key_clue']}
Official story: {CURRENT_CASE['official_story']}

Return EXACTLY 7 lines, one per line.
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        max_completion_tokens=512,
        stream=True,
    )

    script = ""
    for chunk in completion:
        script += chunk.choices[0].delta.content or ""

    lines = [l.strip() for l in script.split("\n") if l.strip()]
    if len(lines) != 7:
        raise RuntimeError("❌ Script must be exactly 7 lines")

    return lines

# ==================================================
# KEYWORD DERIVATION (NO FAKE TAGS)
# ==================================================

def derive_keywords(text: str, index: int):
    t = text.lower()

    # -------- PERSON (HOOK + WHO) --------
    if index in (0, 2):
        if CURRENT_CASE["victim_age"] == "elderly" and CURRENT_CASE["victim_gender"] == "male":
            return ["elderly man"]
        if CURRENT_CASE["victim_age"] == "elderly" and CURRENT_CASE["victim_gender"] == "female":
            return ["elderly woman"]
        if CURRENT_CASE["victim_gender"] == "female":
            return ["woman"]
        if CURRENT_CASE["victim_gender"] == "male":
            return ["man"]
        return ["human figure"]

    # -------- LOCATION --------
    if "hospital" in t:
        return ["hospital"]
    if "parking" in t or "car" in t:
        return ["parked car"]
    if "street" in t:
        return ["street"]

    # -------- CLUE --------
    if "key" in t or "keys" in t:
        return ["trunk", "car pov"]
    if "phone" in t or "text" in t:
        return ["phone", "text"]

    # -------- INVESTIGATION --------
    if "official" in t or "ruled" in t:
        return ["interrogation", "evidence"]

    # -------- CTA --------
    if index == 6:
        return ["shadow", "human figure"]

    # -------- SAFE FALLBACK --------
    return ["human figure"]

# ==================================================
# ASSET MATCHING (STRICT)
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

    # Replace last line with controlled CTA
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
    print("🎯 Visuals are 1:1 aligned with narrative")

# ==================================================
if __name__ == "__main__":
    main()
