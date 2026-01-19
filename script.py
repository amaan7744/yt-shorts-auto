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
# CONFIG — SHORTS ONLY (HARD LOCK)
# --------------------------------------------------

ENDPOINT = "https://models.github.ai/inference"
PRIMARY_MODEL = "openai/gpt-4o-mini"
FALLBACK_MODEL = "openai/gpt-4.1-mini"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

MAX_RETRIES = 3
RETRY_DELAY = 2

# 25–30 seconds spoken (male voice)
TARGET_WORDS_MIN = 55
TARGET_WORDS_MAX = 65

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
# PROMPT — GATE 1 + GATE 2 OPTIMIZED
# --------------------------------------------------

def build_script_prompt(case: dict) -> str:
    return f"""
You write HIGH-PERFORMANCE YouTube Shorts narration
for TRUE CRIME content combined with fast gameplay visuals.

This script MUST pass:
- Gate 1: STOP the scroll instantly
- Gate 2: HOLD attention until the end

CRITICAL RULES (STRICT):
- MAX 30 seconds spoken
- 55–65 words total
- No filler
- No repetition
- Calm, serious, investigative tone
- Every sentence must add NEW information

HOOK RULE (MOST IMPORTANT):
- First sentence MUST:
  • State a specific official conclusion
  • Immediately contradict it with a concrete issue
- It must work as on-screen text with NO AUDIO

FACTS (DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}

STRUCTURE (MANDATORY):
1. Hook: official claim + why it doesn’t fully work (1 sentence)
2. Facts: who / where / what happened (2 short sentences)
3. Failure: what authorities could not explain (2 sentences)
4. CTA: invite viewers to subscribe to keep cases like this alive (1 sentence)
5. Loop: unresolved final line that restates the contradiction (1 sentence)

CTA TONE:
- Documentary, not salesy
- Example style (do NOT copy):
  “If you want cases like this to stay alive, consider subscribing.”

OUTPUT:
- One continuous narration
- No labels
- No emojis
- No commentary
"""

# --------------------------------------------------
# GPT CALL
# --------------------------------------------------

def call_gpt(model: str, prompt: str) -> str:
    response = client.complete(
        model=model,
        messages=[
            {"role": "system", "content": "You write sharp, investigative true crime Shorts narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.25,
        max_tokens=350,
    )

    text = clean(response.choices[0].message.content)
    if not text:
        raise ValueError("Empty response")

    return text

# --------------------------------------------------
# VISUAL BEATS (FOR IMAGE + GAMEPLAY)
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
