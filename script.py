#!/usr/bin/env python3
"""
YouTube Shorts True Crime Script Generator (BLOCK-LOCKED)

Structure:
- 7 blocks
- ~5 seconds per block
- Visual-first
- Asset-locked
- Strong hook + loop
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, List

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

# ==================================================
# CONFIG
# ==================================================

ENDPOINT = "https://models.github.ai/inference"
MODEL = "openai/gpt-4o-mini"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

BLOCK_DURATION = 5.0
MAX_ATTEMPTS = 4
RETRY_DELAY = 1.5
TEMPERATURE = 0.35

# Fixed CTA + engagement (DO NOT CHANGE)
CTA_LINE = "To keep these cases alive, subscribe."
ENGAGEMENT_QUESTION = "What do you think really happened?"

# ==================================================
# CLIENT
# ==================================================

def init_client():
    token = os.getenv("GH_MODELS_TOKEN")
    if not token:
        sys.exit("[SCRIPT] ❌ GH_MODELS_TOKEN missing")
    return ChatCompletionsClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(token),
    )

# ==================================================
# UTIL
# ==================================================

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def load_case() -> Dict:
    if not Path(CASE_FILE).exists():
        sys.exit("[SCRIPT] ❌ case.json missing")

    data = json.loads(Path(CASE_FILE).read_text())
    if not data.get("summary") or not data.get("location"):
        sys.exit("[SCRIPT] ❌ case.json incomplete")

    return data

# ==================================================
# PROMPT (STRICT STRUCTURE)
# ==================================================

def build_prompt(case: Dict) -> str:
    return f"""
Write a true crime YouTube Short narration using EXACTLY 7 short sentences.

RULES (MANDATORY):
• Sentence 1: QUESTION hook + what happened
• Sentence 2: WHAT happened + exact DATE or YEAR
• Sentence 3: Evidence or witness POV detail
• Sentence 4: Investigation action
• Sentence 5: Unsettling or disturbing detail
• Sentence 6: Context or unexplained doubt
• Sentence 7: Looping QUESTION (NOT a conclusion)

Tone:
• Calm
• Investigative
• No accusations
• No conclusions
• Each sentence must describe ONE clear visual moment

Location: {case['location']}
Background: {case['summary']}

Output ONLY the 7 sentences as one paragraph.
"""

# ==================================================
# AI CALL
# ==================================================

def call_ai(client, prompt: str) -> str:
    res = client.complete(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You write structured, visual-first true crime narrations."},
            {"role": "user", "content": prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=220,
    )
    return clean(res.choices[0].message.content)

# ==================================================
# ASSET MAPPING (LOCKED)
# ==================================================

def asset_for_block(index: int) -> str:
    return [
        "car_pov",        # Block 1 – hook
        "road_night",     # Block 2 – discovery
        "window_pov",     # Block 3 – evidence
        "interrogation",  # Block 4 – police
        "mobile_message", # Block 5 – unsettling detail
        "evidence",       # Block 6 – doubt
        "shadow",         # Block 7 – CTA + loop
    ][index]

# ==================================================
# BEATS
# ==================================================

def build_beats(sentences: List[str]) -> List[Dict]:
    beats = []

    for i, sentence in enumerate(sentences):
        beats.append({
            "beat_id": i + 1,
            "text": sentence,
            "estimated_duration": BLOCK_DURATION,
            "asset_key": asset_for_block(i)
        })

    return beats

# ==================================================
# MAIN
# ==================================================

def main():
    case = load_case()
    client = init_client()

    script_text = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            candidate = call_ai(client, build_prompt(case))
            sentences = re.findall(r"[^.!?]+[.!?]?", candidate)

            if len(sentences) == 7:
                script_text = candidate
                break

            print(f"[SCRIPT] ⚠️ Attempt {attempt}: got {len(sentences)} sentences, retrying…")
            time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"[SCRIPT] ⚠️ Attempt {attempt} failed: {e}")
            time.sleep(RETRY_DELAY)

    if not script_text:
        sys.exit("[SCRIPT] ❌ Failed to generate valid 7-sentence script")

    # Append CTA + engagement (spoken at end)
    final_script = (
        script_text.rstrip(". ")
        + f" {CTA_LINE} {ENGAGEMENT_QUESTION}"
    )

    sentences = re.findall(r"[^.!?]+[.!?]?", script_text)
    beats = build_beats(sentences)

    Path(SCRIPT_FILE).write_text(final_script, encoding="utf-8")
    Path(BEATS_FILE).write_text(
        json.dumps({"beats": beats}, indent=2),
        encoding="utf-8"
    )

    print("✅ Script & beats generated successfully\n")
    print(final_script)

if __name__ == "__main__":
    main()
