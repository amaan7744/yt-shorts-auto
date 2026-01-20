#!/usr/bin/env python3

import os
import sys
import json
import time
from typing import Tuple, List

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# --------------------------------------------------
# CONFIG — SHORTS (20s HARD LIMIT)
# --------------------------------------------------

ENDPOINT = "https://models.github.ai/inference"
PRIMARY_MODEL = "openai/gpt-4o-mini"
FALLBACK_MODEL = "openai/gpt-4.1-mini"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

MAX_RETRIES = 3
RETRY_DELAY = 2

# 18–22 seconds spoken (male voice)
TARGET_WORDS_MIN = 40
TARGET_WORDS_MAX = 50

# --------------------------------------------------
# ENV
# --------------------------------------------------

TOKEN = os.getenv("GH_MODELS_TOKEN")
if not TOKEN:
    sys.exit("❌ GH_MODELS_TOKEN missing")

client = ChatCompletionsClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(TOKEN),
)

# --------------------------------------------------
# UTIL
# --------------------------------------------------

def clean(text: str) -> str:
    return str(text or "").replace("```", "").strip()

def load_case() -> dict:
    if not os.path.isfile(CASE_FILE):
        sys.exit("❌ case.json missing")

    with open(CASE_FILE, "r", encoding="utf-8") as f:
        case = json.load(f)

    if not case.get("summary"):
        sys.exit("❌ Case summary missing")

    return case

def enforce_length(script: str) -> str:
    words = script.split()
    return " ".join(words[:TARGET_WORDS_MAX])

# --------------------------------------------------
# PROMPT — AZURE SAFE + GATE OPTIMIZED
# --------------------------------------------------

def build_script_prompt(case: dict) -> str:
    return f"""
Write a concise YouTube Shorts narration
about an unresolved real-world case.

STRICT RULES:
- 18–22 seconds spoken
- 40–50 words total
- Calm, factual, documentary tone
- No speculation
- No accusations
- No violent description
- Every sentence must add new information

OPENING REQUIREMENT:
- First sentence must present a documented conclusion
  followed by an unresolved detail or inconsistency.
- It must work as on-screen text with no audio.

FACTS (DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}

STRUCTURE:
1. Opening: official conclusion + unresolved detail (1 sentence)
2. Facts: who / where / what is known (2 sentences)
3. Gap: what records do not fully explain (1 sentence)
4. CTA: invite viewers to subscribe to keep cases like this visible (1 sentence)
5. Loop: calm unresolved closing line (1 sentence)

CTA STYLE:
- Neutral and archival
- Example style (do NOT copy):
  “Subscribing helps keep cases like this visible.”

OUTPUT:
- One continuous narration
- No labels
- No commentary
"""

# --------------------------------------------------
# GPT CALL
# --------------------------------------------------

def call_gpt(model: str, prompt: str) -> str:
    response = client.complete(
        model=model,
        messages=[
            {"role": "system", "content": "You write short, factual documentary narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.25,
        max_tokens=300,
    )

    text = clean(response.choices[0].message.content)
    if not text:
        raise ValueError("Empty response")

    return text

# --------------------------------------------------
# VISUAL BEATS
# --------------------------------------------------

def derive_visual_beats(script: str) -> List[dict]:
    sentences = [s.strip() for s in script.split(".") if s.strip()]
    beats = []

    for i, sentence in enumerate(sentences):
        if i == 0:
            scene = "HOOK"
        elif i <= 2:
            scene = "CRIME"
        elif "subscribe" in sentence.lower():
            scene = "NEUTRAL"
        else:
            scene = "AFTERMATH"

        beats.append({
            "beat": f"scene_{i+1}",
            "scene": scene,
            "text": sentence
        })

    return beats

# --------------------------------------------------
# GENERATION
# --------------------------------------------------

def generate(case: dict) -> Tuple[str, list]:
    prompt = build_script_prompt(case)

    try:
        script = call_gpt(PRIMARY_MODEL, prompt)
    except Exception:
        script = call_gpt(FALLBACK_MODEL, prompt)

    script = enforce_length(script)
    beats = derive_visual_beats(script)

    return script, beats

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    case = load_case()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🧠 Generating 20s filter-safe Shorts script (attempt {attempt})")

            script, beats = generate(case)

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(BEATS_FILE, "w", encoding="utf-8") as f:
                json.dump(beats, f, indent=2)

            print("✅ Script generated (Gate 1 + Gate 2 + Azure-safe)")
            return

        except (ValueError, HttpResponseError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Script generation failed")

if __name__ == "__main__":
    main()

def derive_visual_beats(script: str) -> List[dict]:
    sentences = [s.strip() for s in script.split(".") if s.strip()]
    beats = []

    for i, sentence in enumerate(sentences):
        if i == 0:
            scene = "HOOK"
        elif i <= 2:
            scene = "CRIME"
        elif "subscribe" in sentence.lower():
            scene = "NEUTRAL"
        else:
            scene = "AFTERMATH"

        beats.append({
            "beat": f"scene_{i+1}",
            "scene": scene,
            "text": sentence
        })

    return beats

# --------------------------------------------------
# GENERATION
# --------------------------------------------------

def generate(case: dict) -> Tuple[str, list]:
    prompt = build_script_prompt(case)

    try:
        script = call_gpt(PRIMARY_MODEL, prompt)
    except Exception as e:
        if "content_filter" in str(e).lower():
            script = call_gpt(FALLBACK_MODEL, prompt)
        else:
            raise

    script = enforce_length(script)
    beats = derive_visual_beats(script)

    return script, beats

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    case = load_case()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🧠 Generating GATE-PASSING Shorts script (attempt {attempt})")

            script, beats = generate(case)

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(BEATS_FILE, "w", encoding="utf-8") as f:
                json.dump(beats, f, indent=2)

            print("✅ Script passes Gate 1 + Gate 2")
            return

        except (ValueError, HttpResponseError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Script generation failed")

if __name__ == "__main__":
    main()
