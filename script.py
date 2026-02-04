#!/usr/bin/env python3
"""
Script Generator – True Crime Shorts (FINAL, TIMELINE-FIRST)

ARCHITECTURE:
1. AI generates ONE continuous 35–40s script
2. Script is split into ~5s segments (CTA may be shorter)
3. Each segment gets a narrative ROLE
4. Keywords are derived from (role + text)
5. Assets are matched STRICTLY from assets.py
6. Script adapts to assets — not the other way around

RULES:
- assets.py is the ONLY source of truth
- NO random asset picking
- NO asset reuse in the same video
- Hook ALWAYS shows a human
- CTA always mentions the victim by name
- Uses Groq streaming API ONLY
- No fallback script — AI failure = pipeline failure
"""

import json
import os
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
# TIMING CONFIG
# ==================================================

WORDS_PER_SECOND = 2.5        # ~150 WPM narration
TARGET_SEGMENT_SEC = 5.0     # Shorts pacing

# ==================================================
# CASE INPUT (EDIT THIS ONLY)
# ==================================================

CURRENT_CASE = {
    "victim_name": "Joe",
    "victim_desc": "a night shift nurse",
    "location": "a hospital parking lot",
    "time_of_incident": "3:17 AM",
    "strange_clue": "her car keys were still in the ignition",
    "official_theory": "she walked away voluntarily"
}

# ==================================================
# GROQ CONFIG (LOCKED, STREAMING)
# ==================================================

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY missing")

# ==================================================
# CTA CONFIG (ROTATING, CONTROLLED)
# ==================================================

CTA_ACTIONS = [
    "Subscribe",
    "Follow",
    "Stay with us"
]

def build_cta(victim_name: str) -> str:
    action = random.choice(CTA_ACTIONS)
    return (
        f"{action} to help keep cases like {victim_name}'s alive — "
        f"was this really the truth?"
    )

# ==================================================
# 1. FULL SCRIPT GENERATION (AI ONLY)
# ==================================================

def generate_full_script(client: Groq) -> str:
    """
    Generates ONE continuous true-crime script (~35–40s).
    No beats, no tags, no structure labels.
    """

    prompt = f"""
Write a continuous true-crime narration for a YouTube Short.
Target length: 35–40 seconds when spoken.

STYLE:
- Calm, investigative
- High retention
- Short sentences
- No filler
- No section labels
- End with a strong looping question

STRUCTURE (IMPLICIT, DO NOT LABEL):
- Hook question
- What happened + where + when
- Who the victim was
- Discovery / investigation
- Strange detail that doesn’t add up
- Context that challenges the official story
- Looping ending question

CASE DETAILS:
Victim name: {CURRENT_CASE['victim_name']}
Victim description: {CURRENT_CASE['victim_desc']}
Location: {CURRENT_CASE['location']}
Time: {CURRENT_CASE['time_of_incident']}
Strange clue: {CURRENT_CASE['strange_clue']}
Official theory: {CURRENT_CASE['official_theory']}
"""

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_completion_tokens=900,
        top_p=1,
        stream=True
    )

    script = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            script += chunk.choices[0].delta.content

    if not script.strip():
        raise RuntimeError("❌ Groq returned empty script")

    return script.strip()

# ==================================================
# 2. SEGMENTATION (TIME-BASED)
# ==================================================

def segment_script(text: str):
    """
    Splits script into ~5s segments based on speaking rate.
    """
    words = text.split()
    segments, current, acc_time = [], [], 0.0

    for w in words:
        current.append(w)
        acc_time += 1 / WORDS_PER_SECOND

        if acc_time >= TARGET_SEGMENT_SEC:
            segments.append(" ".join(current))
            current, acc_time = [], 0.0

    if current:
        segments.append(" ".join(current))

    return segments

# ==================================================
# 3. ROLE ASSIGNMENT (DETERMINISTIC)
# ==================================================

ROLES = [
    "hook",
    "event",
    "victim",
    "discovery",
    "clue",
    "context",
    "cta"
]

def assign_roles(segments):
    """
    Assigns roles by position.
    Extra segments default to context.
    """
    out = []
    for i, seg in enumerate(segments):
        role = ROLES[i] if i < len(ROLES) else "context"
        out.append((seg, role))
    return out

# ==================================================
# 4. KEYWORD DERIVATION (CONTROLLED, ASSET-AWARE)
# ==================================================

def derive_keywords(text: str, role: str):
    t = text.lower()

    # Hook must always show a human
    if role == "hook":
        return ["human"]

    # Location-aware
    if "hospital" in t:
        return ["hospital"]

    if "car" in t or "keys" in t:
        return ["car pov"]

    if "door" in t:
        return ["door locked", "closing door"]

    if role == "clue":
        return ["evidence", "phone", "text"]

    if role == "cta":
        return ["human", "shadow"]

    return ["human"]

# ==================================================
# 5. ASSET MATCHING (STRICT, NO RANDOM SHIT)
# ==================================================

def match_asset(keywords, used_assets):
    # First pass: all keywords must match
    for asset, tags in ASSET_KEYWORDS.items():
        if asset in used_assets:
            continue
        if all(k in tags for k in keywords):
            return asset

    # Second pass: partial match (script auto-adjust)
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

    client = Groq(api_key=GROQ_API_KEY)

    print("🧠 Generating full script via Groq streaming API…")
    full_script = generate_full_script(client)

    print("✂️ Segmenting script into 5s blocks…")
    segments = segment_script(full_script)

    # Inject controlled CTA (overwrites last segment text)
    segments[-1] = build_cta(CURRENT_CASE["victim_name"])

    beats = []
    used_assets = set()

    print("🎞️ Matching segments to assets…")
    for i, (text, role) in enumerate(assign_roles(segments)):
        keywords = derive_keywords(text, role)
        asset = match_asset(keywords, used_assets)
        used_assets.add(asset)

        beats.append({
            "beat_id": i + 1,
            "text": text,
            "role": role,
            "asset_file": asset,
            "duration": round(len(text.split()) / WORDS_PER_SECOND, 2),
            "keywords": keywords
        })

    Path(SCRIPT_FILE).write_text(full_script, encoding="utf-8")
    Path(BEATS_FILE).write_text(json.dumps({"beats": beats}, indent=2), encoding="utf-8")

    print("✅ Script generated, segmented, and asset-matched perfectly")

# ==================================================
if __name__ == "__main__":
    main()
