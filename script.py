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

- 7 sentences
- ~35–40 seconds total
- Visuals mapped dynamically from text
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

MODEL = "llama-3.1-70b-versatile"

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
# PROMPT (CONTENT-ENGINEERED)
# ==================================================

def build_prompt(case: Dict) -> str:
    return f"""
Write a true crime YouTube Short narration using EXACTLY 7 sentences.

STRICT RULES:
• Sentence 1 MUST be a cliffhanger question
  - No names
  - No locations
  - No dates
  - Examples: "Was it murder or suicide?" / "What really happened that night?"

• Sentence 2 reveals:
  - What happened
  - To whom
  - Where

• Sentence 3 shows evidence or a POV moment
• Sentence 4 describes police or investigation action
• Sentence 5 introduces a MINI-HOOK doubt or contradiction
• Sentence 6 adds context or unexplained detail
• Sentence 7 MUST end with a QUESTION (loop)

STYLE:
• Calm investigative tone
• No accusations
• No conclusions
• Every sentence must describe ONE clear visual moment
• No emojis, no hashtags

CASE DETAILS:
Location: {case['location']}
Background: {case['summary']}

Output ONLY the 7 sentences as ONE paragraph.
"""

# ==================================================
# AI CALL
# ==================================================

def call_ai(client: Groq, prompt: str) -> str:
    res = client.chat.completions.create(
        model=MODEL,
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

# ==================================================
# VISUAL / ASSET MAPPING (CONTENT-DRIVEN)
# ==================================================

def sentence_to_asset(sentence: str) -> str:
    s = sentence.lower()

    if any(k in s for k in ["car", "vehicle", "highway", "road"]):
        return "car_pov"
    if any(k in s for k in ["window", "shadow", "seen"]):
        return "window_pov"
    if any(k in s for k in ["police", "questioned", "interrogation", "detective"]):
        return "interrogation"
    if any(k in s for k in ["phone", "message", "ping", "call"]):
        return "mobile_message"
    if any(k in s for k in ["evidence", "found", "reported"]):
        return "evidence"
    if any(k in s for k in ["home", "room", "apartment"]):
        return "dark_room"
    if any(k in s for k in ["night", "late", "evening"]):
        return "road_night"

    return "shadow"

# ==================================================
# BEATS
# ==================================================

def build_beats(sentences: List[str]) -> List[Dict]:
    beats = []
    for i, sentence in enumerate(sentences):
        beats.append({
            "beat_id": i + 1,
            "text": sentence.strip(),
            "estimated_duration": BLOCK_DURATION,
            "asset_key": sentence_to_asset(sentence)
        })
    return beats

# ==================================================
# MAIN
# ==================================================

def main():
    case = load_case()
    client = init_client()

    script_body = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            candidate = call_ai(client, build_prompt(case))
            sentences = re.findall(r"[^.!?]+[.!?]?", candidate)

            if len(sentences) == 7:
                script_body = candidate
                break

            print(f"[SCRIPT] ⚠️ Attempt {attempt}: got {len(sentences)} sentences")
            time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"[SCRIPT] ⚠️ Attempt {attempt} failed: {e}")
            time.sleep(RETRY_DELAY)

    if not script_body:
        sys.exit("[SCRIPT] ❌ Failed to generate valid 7-sentence script")

    engagement = random.choice(ENGAGEMENT_QUESTIONS)

    final_script = (
        script_body.rstrip(". ")
        + f" {CTA_LINE} {engagement}"
    )

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
