#!/usr/bin/env python3
"""
YouTube Shorts True Crime Script Generator (Groq)

STRUCTURE:
1. Cliffhanger hook (NO names / places)
2. What happened + who + where
3. Evidence or POV
4. Investigation
5. Mini-hook doubt
6. Context / unresolved detail
7. CTA + looping engagement question
"""

import os
import sys
import json
import time
import re
import random
from pathlib import Path
from typing import Dict, List

from groq import Groq

# ==================================================
# CONFIG
# ==================================================

PRIMARY_MODEL = "llama-3.3-70b-instruct"
FALLBACK_MODEL = "llama-3.1-8b-instant"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

BLOCK_DURATION = 5.0
MAX_ATTEMPTS = 4
RETRY_DELAY = 1.5
TEMPERATURE = 0.35

CTA_LINE = "To keep these cases alive, subscribe."

ENGAGEMENT_QUESTIONS = [
    "What do you think really happened?",
    "Why is this still a mystery?",
    "What would you have done?",
    "Do you think this was all?"
]

# ==================================================
# CLIENT
# ==================================================

def init_client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        sys.exit("[SCRIPT] ❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

# ==================================================
# UTIL
# ==================================================

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def load_case() -> Dict:
    if not Path(CASE_FILE).exists():
        sys.exit("[SCRIPT] ❌ case.json missing")
    return json.loads(Path(CASE_FILE).read_text())

# ==================================================
# PROMPT
# ==================================================

def build_prompt(case: Dict) -> str:
    return f"""
Write a true crime YouTube Short narration using EXACTLY 7 sentences.

STRICT RULES:
• Sentence 1 MUST be a cliffhanger question
  - No names
  - No locations
  - No dates

• Sentence 2 reveals what happened, to whom, and where
• Sentence 3 shows evidence or POV
• Sentence 4 describes investigation or police action
• Sentence 5 introduces doubt or contradiction
• Sentence 6 adds unresolved context
• Sentence 7 MUST end with a question (loop)

STYLE:
• Calm investigative tone
• No accusations
• No conclusions
• Every sentence must describe ONE clear visual moment

CASE DETAILS:
Location: {case['location']}
Background: {case['summary']}

Output ONLY the 7 sentences as one paragraph.
"""

# ==================================================
# AI CALL (WITH FALLBACK)
# ==================================================

def call_ai(client: Groq, prompt: str, model: str) -> str:
    res = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior true-crime scriptwriter specializing in "
                    "short-form video retention and visual storytelling."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=TEMPERATURE,
        max_tokens=240,
    )
    return clean(res.choices[0].message.content)

def sentence_to_asset(sentence: str) -> str:
    s = sentence.lower()

    # ─────────────────────────────
    # VEHICLES / TRAVEL
    # ─────────────────────────────
    if any(k in s for k in [
        "car", "vehicle", "driving", "driver",
        "highway", "road", "freeway", "route"
    ]):
        return "car_pov"

    if any(k in s for k in [
        "parked car", "abandoned car", "left the car"
    ]):
        return "parked_car"

    if any(k in s for k in [
        "bridge", "overpass"
    ]):
        return "bridge"

    # ─────────────────────────────
    # NIGHT / LOCATION ATMOSPHERE
    # ─────────────────────────────
    if any(k in s for k in [
        "alley", "back alley", "narrow street"
    ]):
        return "night_alley"

    if any(k in s for k in [
        "night", "late night", "after midnight", "evening"
    ]):
        return "blurred_alley"

    if any(k in s for k in [
        "rooftop", "roof"
    ]):
        return "rooftop"

    # ─────────────────────────────
    # SURVEILLANCE / POV
    # ─────────────────────────────
    if any(k in s for k in [
        "cctv", "camera", "surveillance", "footage"
    ]):
        return "cctv"

    if any(k in s for k in [
        "window", "seen through a window", "curtain", "inside looking out"
    ]):
        return "window_pov"

    # ─────────────────────────────
    # BUILDINGS / INTERIORS
    # ─────────────────────────────
    if any(k in s for k in [
        "room", "bedroom", "apartment", "inside the house"
    ]):
        return "dark_room"

    if any(k in s for k in [
        "hallway", "corridor"
    ]):
        return "hallway"

    if any(k in s for k in [
        "door", "closing door", "last seen entering"
    ]):
        return "closing_door"

    # ─────────────────────────────
    # POLICE / INVESTIGATION
    # ─────────────────────────────
    if any(k in s for k in [
        "interrogation", "questioned", "questioning"
    ]):
        return "interogationroom"

    if any(k in s for k in [
        "police", "detectives", "investigators"
    ]):
        return "dynamics"

    if any(k in s for k in [
        "evidence", "found evidence", "crime scene"
    ]):
        return "evidence"

    if any(k in s for k in [
        "yellow tape", "crime tape", "restricted area"
    ]):
        return "yellow_tape"

    # ─────────────────────────────
    # DIGITAL / COMMUNICATION
    # ─────────────────────────────
    if any(k in s for k in [
        "phone", "message", "text", "ping", "last call"
    ]):
        return "mobilemessage"

    # ─────────────────────────────
    # HUMAN PRESENCE / MYSTERY
    # ─────────────────────────────
    if any(k in s for k in [
        "shadow", "figure", "someone watching"
    ]):
        return "shadow"

    if any(k in s for k in [
        "left behind", "belongings", "personal items"
    ]):
        return "leftover"

    # ─────────────────────────────
    # FALLBACK (SAFE, NON-LAME)
    # ─────────────────────────────
    return "dynamics"


# ==================================================
# BEATS
# ==================================================

def build_beats(sentences: List[str]) -> List[Dict]:
    return [
        {
            "beat_id": i + 1,
            "text": s.strip(),
            "estimated_duration": BLOCK_DURATION,
            "asset_key": sentence_to_asset(s),
        }
        for i, s in enumerate(sentences)
    ]

# ==================================================
# MAIN
# ==================================================

def main():
    case = load_case()
    client = init_client()

    script_body = None
    models = [PRIMARY_MODEL, FALLBACK_MODEL]

    for model in models:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                candidate = call_ai(client, build_prompt(case), model)
                sentences = re.findall(r"[^.!?]+[.!?]?", candidate)

                if len(sentences) == 7:
                    script_body = candidate
                    break

                print(f"[SCRIPT] ⚠️ {model} attempt {attempt}: {len(sentences)} sentences")
                time.sleep(RETRY_DELAY)

            except Exception as e:
                print(f"[SCRIPT] ⚠️ {model} attempt {attempt} failed: {e}")
                time.sleep(RETRY_DELAY)

        if script_body:
            break

    if not script_body:
        sys.exit("[SCRIPT] ❌ Failed to generate valid 7-sentence script")

    engagement = random.choice(ENGAGEMENT_QUESTIONS)

    final_script = f"{script_body} {CTA_LINE} {engagement}"

    sentences = re.findall(r"[^.!?]+[.!?]?", script_body)
    beats = build_beats(sentences)

    Path(SCRIPT_FILE).write_text(final_script, encoding="utf-8")
    Path(BEATS_FILE).write_text(
        json.dumps({"beats": beats}, indent=2),
        encoding="utf-8"
    )

    print("✅ Script & beats generated\n")
    print(final_script)

# ==================================================
if __name__ == "__main__":
    main()
