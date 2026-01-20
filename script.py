#!/usr/bin/env python3

import os
import sys
import json
import time
import re
from typing import Tuple, List

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# ==================================================
# CONFIG — 20s SHORTS (RETENTION SAFE)
# ==================================================

ENDPOINT = "https://models.github.ai/inference"
MODEL = "openai/gpt-4o-mini"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

TARGET_WORDS_MIN = 40
TARGET_WORDS_MAX = 52

MAX_RETRIES = 3
RETRY_DELAY = 2

# ==================================================
# CLIENT
# ==================================================

TOKEN = os.getenv("GH_MODELS_TOKEN")
if not TOKEN:
    sys.exit("❌ GH_MODELS_TOKEN missing")

client = ChatCompletionsClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(TOKEN),
)

# ==================================================
# UTIL
# ==================================================

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()

def load_case() -> dict:
    if not os.path.isfile(CASE_FILE):
        sys.exit("❌ case.json missing")

    with open(CASE_FILE, "r", encoding="utf-8") as f:
        case = json.load(f)

    if not case.get("summary"):
        sys.exit("❌ case.json missing summary")

    return case

def enforce_length(text: str) -> str:
    words = text.split()
    return " ".join(words[:TARGET_WORDS_MAX])

# ==================================================
# PROMPT — ANOMALY FIRST (NO VIOLENCE FLAGS)
# ==================================================

def build_script_prompt(case: dict) -> str:
    return f"""
Write a 20-second true crime mystery narration.

STRICT RULES:
- 40–52 words total
- Calm, factual, documentary tone
- No graphic violence
- No accusations
- No speculation language
- Short sentences

HOOK:
- Start with an unexplained anomaly.
- Do NOT mention conclusions or officials.
- First line must feel incomplete without context.

FACTS:
Location: {case.get("location")}
Summary: {case.get("summary")}

STRUCTURE:
1. Anomaly hook
2. What is known
3. What does not align
4. Unresolved close
5. Neutral archival CTA (1 sentence)

CTA STYLE:
“Subscribing helps keep cases like this visible.”

OUTPUT:
One paragraph only.
"""

# ==================================================
# GPT CALL
# ==================================================

def call_gpt(prompt: str) -> str:
    response = client.complete(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You write short, factual documentary narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=250,
    )

    text = clean(response.choices[0].message.content)
    if not text:
        raise ValueError("Empty model response")

    return text

# ==================================================
# VISUAL BEATS — FAST CUTS (2–3s)
# ==================================================

def derive_visual_beats(script: str) -> List[dict]:
    parts = re.split(r"[,.]| and ", script)
    parts = [p.strip() for p in parts if len(p.strip()) > 5]

    beats = []
    for i, text in enumerate(parts):
        if i == 0:
            scene = "HOOK"
        elif i == len(parts) - 1:
            scene = "LOOP"
        else:
            scene = "DETAIL" if i % 2 == 0 else "LOCATION"

        beats.append({
            "beat": f"scene_{i+1}",
            "scene": scene,
            "text": text,
        })

    return beats

# ==================================================
# GENERATION
# ==================================================

def generate(case: dict) -> Tuple[str, list]:
    prompt = build_script_prompt(case)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            script = call_gpt(prompt)
            script = enforce_length(script)
            beats = derive_visual_beats(script)
            return script, beats
        except (ValueError, HttpResponseError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Script generation failed")

# ==================================================
# MAIN
# ==================================================

def main():
    case = load_case()
    print("🧠 Generating high-retention Shorts script…")

    script, beats = generate(case)

    with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(script)

    with open(BEATS_FILE, "w", encoding="utf-8") as f:
        json.dump(beats, f, indent=2)

    print("✅ Script + beats generated successfully")

if __name__ == "__main__":
    main()
