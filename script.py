#!/usr/bin/env python3
"""
Script Generator – True Crime Shorts (ASSET-LOCKED FINAL)

RULES:
- assets.py is the single source of truth
- Script AUTO-ADJUSTS to fit assets
- NO random asset picking
- NO asset reuse per video
- Hook ALWAYS shows a human
- NO fallback scripts
- AI failure = pipeline failure
"""

import json
import os
import random
from pathlib import Path
from groq import Groq

from assets import ASSET_KEYWORDS, validate_assets

SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

# ==================================================
# CASE INPUT
# ==================================================

CURRENT_CASE = {
    "victim_desc": "a night shift nurse",
    "location": "a hospital parking lot",
    "time_of_incident": "3:17 AM",
    "strange_clue": "her car keys were still in the ignition",
    "official_theory": "she walked away voluntarily"
}

# ==================================================
# GROQ CONFIG (LOCKED)
# ==================================================

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY missing")

# ==================================================
# BEAT DEFINITIONS (VISUAL LAW)
# ==================================================

BEAT_RULES = {
    0: {"must_have": ["woman", "man", "elderly", "human"]},     # Hook (human only)
    1: {"must_have": ["hospital", "street", "bridge", "train"]},
    2: {"must_have": ["woman", "man", "elderly", "human"]},
    3: {"must_have": ["hospital", "hallway", "door"]},
    4: {"must_have": ["phone", "text", "evidence", "computer", "mirror"]},
    5: {"must_have": ["cctv", "elevator"]},
    6: {"must_have": ["human", "shadow", "rooftop"]}
}

# ==================================================
# GROQ CLIENT
# ==================================================

def init_client():
    return Groq(api_key=GROQ_API_KEY)

# ==================================================
# AI SCRIPT GENERATION (STREAMING – CORRECT)
# ==================================================

def generate_script_with_tags(client):
    allowed_tags = sorted({t for tags in ASSET_KEYWORDS.values() for t in tags})

    prompt = f"""
Write EXACTLY 7 beats for a true crime YouTube Short.

For EACH beat return JSON with:
- "text"
- "tags" (ONLY from the allowed list)

STRUCTURE:
1. Hook QUESTION (human present)
2. What happened + where
3. Who (victim)
4. Discovery / investigation
5. Strange clue (object)
6. Context / contradiction
7. CTA + looping QUESTION

CASE:
Victim: {CURRENT_CASE['victim_desc']}
Location: {CURRENT_CASE['location']}
Time: {CURRENT_CASE['time_of_incident']}
Clue: {CURRENT_CASE['strange_clue']}
Theory: {CURRENT_CASE['official_theory']}

ALLOWED TAGS:
{allowed_tags}

RULES:
- Adjust wording to match tags
- Do NOT invent tags
- Beat 1 and 7 MUST be questions
- Output ONLY raw JSON array
"""

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        max_completion_tokens=1024,
        top_p=1,
        stream=True
    )

    raw = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            raw += chunk.choices[0].delta.content

    if not raw.strip():
        raise RuntimeError("❌ Groq returned empty response")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"❌ Invalid JSON from Groq:\n{raw}")

    if not isinstance(data, list) or len(data) != 7:
        raise RuntimeError("❌ Script must contain exactly 7 beats")

    return data

# ==================================================
# ASSET RESOLUTION (STRICT, NO RANDOM SHIT)
# ==================================================

def resolve_asset(beat_index, tags, used_assets):
    rules = BEAT_RULES[beat_index]

    for asset, asset_tags in ASSET_KEYWORDS.items():
        if asset in used_assets:
            continue
        if any(r in asset_tags for r in rules["must_have"]) and any(t in asset_tags for t in tags):
            return asset

    # Auto-adjust: relax to beat rules only
    for asset, asset_tags in ASSET_KEYWORDS.items():
        if asset in used_assets:
            continue
        if any(r in asset_tags for r in rules["must_have"]):
            return asset

    raise RuntimeError(f"❌ No valid asset for beat {beat_index + 1}")

# ==================================================
# DURATION
# ==================================================

def estimate_duration(text, idx):
    base = len(text.split()) * 0.42
    if idx == 4:
        return round(base + 2.5, 2)
    if idx == 6:
        return round(base + 1.5, 2)
    return round(base + 0.8, 2)

# ==================================================
# MAIN
# ==================================================

def main():
    print("🧪 Validating assets…")
    validate_assets()

    client = init_client()

    print("🧠 Generating script via Groq streaming API…")
    beats_ai = generate_script_with_tags(client)

    beats = []
    used_assets = set()

    for i, beat in enumerate(beats_ai):
        asset = resolve_asset(i, beat["tags"], used_assets)
        used_assets.add(asset)

        beats.append({
            "beat_id": i + 1,
            "text": beat["text"],
            "asset_file": asset,
            "duration": estimate_duration(beat["text"], i),
            "tags": beat["tags"]
        })

    Path(SCRIPT_FILE).write_text(" ".join(b["text"] for b in beats), encoding="utf-8")
    Path(BEATS_FILE).write_text(json.dumps({"beats": beats}, indent=2), encoding="utf-8")

    print("✅ Script + beats generated (Groq streaming, asset-locked)")

# ==================================================
if __name__ == "__main__":
    main()
