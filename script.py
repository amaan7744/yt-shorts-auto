#!/usr/bin/env python3
"""
YouTube Shorts True Crime Script Generator
- 35–40 words
- Question hook
- Asset-locked beats
- Looping CTA
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import List, Dict

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

# ===============================
# CONFIG
# ===============================

ENDPOINT = "https://models.github.ai/inference"
MODEL = "openai/gpt-4o-mini"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

WORDS_MIN = 35
WORDS_MAX = 40

TEMPERATURE = 0.35

# ===============================
# CLIENT
# ===============================

def init_client():
    token = os.getenv("GH_MODELS_TOKEN")
    if not token:
        sys.exit("❌ GH_MODELS_TOKEN missing")
    return ChatCompletionsClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(token),
    )

# ===============================
# UTIL
# ===============================

def wc(text: str) -> int:
    return len(text.split())

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def load_case() -> Dict:
    if not Path(CASE_FILE).exists():
        sys.exit("❌ case.json missing")
    return json.loads(Path(CASE_FILE).read_text())

# ===============================
# PROMPT
# ===============================

def build_prompt(case: Dict) -> str:
    return f"""
Write a true crime YouTube Short narration (35–40 words).

Rules:
• FIRST sentence must be a QUESTION hook
• Mention WHAT happened
• Mention WHEN (date or year)
• Calm investigative tone
• No accusations
• No conclusions
• Every sentence must clearly describe a visual moment
• End with a LOOPING QUESTION CTA

Structure:
1. Question hook
2. What happened + date
3. Context detail
4. Unsettling detail
5. Looping question CTA

Location: {case['location']}
Background: {case['summary']}

Output ONLY the narration text.
"""

# ===============================
# AI CALL
# ===============================

def call_ai(client, prompt: str) -> str:
    res = client.complete(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You write visual-first true crime narrations."},
            {"role": "user", "content": prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=200,
    )
    return clean(res.choices[0].message.content)

# ===============================
# ASSET MAPPING
# ===============================

def sentence_to_asset(sentence: str) -> str:
    s = sentence.lower()

    if "car" in s:
        return "car_pov"
    if "camera" in s or "cctv" in s:
        return "cctv"
    if "police" in s or "interrogation" in s:
        return "interrogation"
    if "door" in s:
        return "closing_door"
    if "message" in s or "phone" in s:
        return "mobile_message"
    if "evidence" in s or "found" in s:
        return "evidence"
    if "shadow" in s:
        return "shadow"
    if "window" in s:
        return "window_pov"
    if "tape" in s:
        return "yellow_tape"
    if "room" in s or "home" in s:
        return "dark_room"

    return "dynamics"

# ===============================
# BEATS
# ===============================

def derive_beats(script: str) -> List[Dict]:
    sentences = re.findall(r"[^.!?]+[.!?]?", script)
    beats = []

    for i, s in enumerate(sentences):
        duration = round(max(2.5, wc(s) / 2.2), 2)
        beats.append({
            "beat_id": i + 1,
            "text": s.strip(),
            "estimated_duration": duration,
            "asset_key": sentence_to_asset(s)
        })

    return beats

# ===============================
# MAIN
# ===============================

def main():
    case = load_case()
    client = init_client()

    script = call_ai(client, build_prompt(case))
    if not (WORDS_MIN <= wc(script) <= WORDS_MAX):
        sys.exit("❌ Script length out of bounds")

    beats = derive_beats(script)

    Path(SCRIPT_FILE).write_text(script, encoding="utf-8")
    Path(BEATS_FILE).write_text(
        json.dumps({"beats": beats}, indent=2),
        encoding="utf-8"
    )

    print("✅ Script & beats generated")
    print(script)

if __name__ == "__main__":
    main()
