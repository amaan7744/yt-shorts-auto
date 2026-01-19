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
# CONFIG — SHORTS ONLY
# --------------------------------------------------

ENDPOINT = "https://models.github.ai/inference"
PRIMARY_MODEL = "openai/gpt-4o-mini"
FALLBACK_MODEL = "openai/gpt-4.1-mini"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

MAX_RETRIES = 3
RETRY_DELAY = 2

# HARD LIMITS (≈30s spoken)
TARGET_WORDS_MIN = 55
TARGET_WORDS_MAX = 70

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

    if len(words) > TARGET_WORDS_MAX:
        return " ".join(words[:TARGET_WORDS_MAX])

    if len(words) < TARGET_WORDS_MIN:
        closer = (
            "No official explanation has ever fully accounted for what went wrong."
        )
        words.extend(closer.split())

    return " ".join(words)

# --------------------------------------------------
# PROMPT — STRONG HOOK LOGIC
# --------------------------------------------------

def build_script_prompt(case: dict) -> str:
    return f"""
Write a HIGH-RETENTION YouTube Shorts narration
for a TRUE CRIME or UNRESOLVED case.

CRITICAL RULES:
- MAX 30 seconds spoken
- 55–70 words total
- No repetition
- No filler
- Written to be spoken naturally
- Calm, serious, investigative tone

HOOK REQUIREMENTS (MANDATORY):
- The opening sentence MUST include:
  • A specific fact
  • A contradiction, failure, or inconsistency
- The hook must clearly imply:
  “The official explanation does not fully make sense.”

FACTS (DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}

STRUCTURE (STRICT):
1. Hook: specific fact + what doesn’t add up (1 sentence)
2. Core facts: who / where / what happened (2 sentences)
3. Investigative failure or contradiction (1–2 sentences)
4. CTA: invite viewers to subscribe to keep cases like this alive (1 sentence)
5. Loop ending: unresolved final line that echoes the contradiction (1 sentence)

CTA STYLE:
- Documentary tone
- Example phrasing (do NOT copy):
  "If you want cases like this to stay alive, consider subscribing."

OUTPUT:
- One continuous narration
- No labels
- No explanations
"""

# --------------------------------------------------
# GPT CALL
# --------------------------------------------------

def call_gpt(model: str, prompt: str) -> str:
    response = client.complete(
        model=model,
        messages=[
            {"role": "system", "content": "You write concise, investigative true crime narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=400,
    )

    text = clean(response.choices[0].message.content)
    if not text:
        raise ValueError("Empty response from model")

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
    except Exception as e:
        if "content_filter" in str(e).lower():
            script = call_gpt(FALLBACK_MODEL, build_script_prompt(case))
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
            print(f"🧠 Generating STRONG-HOOK Shorts script (attempt {attempt})")

            script, beats = generate(case)

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(BEATS_FILE, "w", encoding="utf-8") as f:
                json.dump(beats, f, indent=2)

            print("✅ 30s script with strong hook generated")
            return

        except (ValueError, HttpResponseError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Failed after retries")

if __name__ == "__main__":
    main()
