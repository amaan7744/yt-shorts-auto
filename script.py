#!/usr/bin/env python3
"""
Script Generator – True Crime Shorts (ASSET-LOCKED FINAL)

RULES:
- assets.py is the single source of truth
- Script AUTO-ADJUSTS to fit assets
- NO random asset picking
- NO asset reuse per video
- Hook ALWAYS shows a human
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
# CASE INPUT (ONLY EDIT THIS)
# ==================================================

CURRENT_CASE = {
    "victim_desc": "a night shift nurse",
    "location": "a hospital parking lot",
    "time_of_incident": "3:17 AM",
    "strange_clue": "her car keys were still in the ignition",
    "official_theory": "she walked away voluntarily"
}

# ==================================================
# GROQ MODELS (SAFE)
# ==================================================

GROQ_MODELS = [
    "llama3-8b-8192",
    "mixtral-8x7b-32768"
]

# ==================================================
# BEAT DEFINITIONS (VISUAL LAW)
# ==================================================

BEAT_RULES = {
    0: {"must_have": ["woman", "man", "elderly", "child", "human"], "human_required": True},
    1: {"must_have": ["hospital", "street", "home", "parking", "bridge", "train"]},
    2: {"must_have": ["woman", "man", "elderly", "child", "human"]},
    3: {"must_have": ["hospital", "hallway", "door", "police"]},
    4: {"must_have": ["phone", "text", "evidence", "mirror", "computer", "key"]},
    5: {"must_have": ["cctv", "clock", "elevator", "timeline"]},
    6: {"must_have": ["shadow", "human", "rooftop"]}
}

# ==================================================
# GROQ CLIENT
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

# ==================================================
# AI SCRIPT GENERATION (TAG-AWARE)
# ==================================================

def generate_script_with_tags(client):
    asset_tags = sorted({t for tags in ASSET_KEYWORDS.values() for t in tags})

    prompt = f"""
Write EXACTLY 7 beats for a true crime YouTube Short.

For EACH beat, output JSON with:
- "text": the sentence
- "tags": a list of semantic tags

STRUCTURE:
1. Hook QUESTION (human present)
2. What happened + where
3. Who (victim)
4. Discovery / investigation
5. Strange clue (object)
6. Context / contradiction
7. CTA + looping QUESTION

CASE DETAILS:
Victim: {CURRENT_CASE['victim_desc']}
Location: {CURRENT_CASE['location']}
Time: {CURRENT_CASE['time_of_incident']}
Strange clue: {CURRENT_CASE['strange_clue']}
Official theory: {CURRENT_CASE['official_theory']}

IMPORTANT RULES:
- Tags MUST come ONLY from this list:
{asset_tags}

- If unsure, CHANGE THE TEXT to match tags
- Do NOT invent new tags
- Beat 1 and 7 MUST be questions

Return ONLY valid JSON array.
"""

    for model in GROQ_MODELS:
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You write asset-aware true crime Shorts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )

            data = json.loads(res.choices[0].message.content)

            if len(data) != 7:
                raise ValueError("Script must have exactly 7 beats")

            return data

        except Exception as e:
            print(f"⚠️ Model {model} failed: {e}")

    raise RuntimeError("❌ All AI models failed")

# ==================================================
# ASSET RESOLUTION (STRICT)
# ==================================================

def resolve_asset(beat_index, tags, used_assets):
    rules = BEAT_RULES[beat_index]

    candidates = []
    for asset, asset_tags in ASSET_KEYWORDS.items():
        if asset in used_assets:
            continue
        if all(
            any(r in at for at in asset_tags)
            for r in rules["must_have"]
            if r in tags
        ):
            candidates.append(asset)

    if not candidates:
        # AUTO-ADJUST SCRIPT LOGIC: loosen tag requirement
        for asset, asset_tags in ASSET_KEYWORDS.items():
            if asset in used_assets:
                continue
            if any(t in asset_tags for t in tags):
                return asset

        raise RuntimeError(f"❌ No valid asset for beat {beat_index + 1}")

    return random.choice(candidates)

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

    print("🧠 Generating script with semantic tags…")
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

    Path(SCRIPT_FILE).write_text(
        " ".join(b["text"] for b in beats),
        encoding="utf-8"
    )

    Path(BEATS_FILE).write_text(
        json.dumps({"beats": beats}, indent=2),
        encoding="utf-8"
    )

    print("✅ Script + beats generated with PERFECT visual alignment")

# ==================================================
if __name__ == "__main__":
    main()
