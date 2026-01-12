#!/usr/bin/env python3

import os
import sys
import json
import time
from typing import Tuple

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

ENDPOINT = "https://models.github.ai/inference"
PRIMARY_MODEL = "openai/gpt-4o-mini"
FALLBACK_MODEL = "openai/gpt-4.1-mini"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

MAX_RETRIES = 3
RETRY_DELAY = 2

# Shorts timing (~30–35 sec)
TARGET_WORDS_MIN = 90
TARGET_WORDS_MAX = 110

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

def normalize_length(script: str) -> str:
    words = script.split()

    if len(words) > TARGET_WORDS_MAX:
        return " ".join(words[:TARGET_WORDS_MAX])

    if len(words) < TARGET_WORDS_MIN:
        filler = [
            "The records never explained why.",
            "Some details were never resolved.",
            "The truth was never made clear."
        ]
        i = 0
        while len(words) < TARGET_WORDS_MIN:
            words.extend(filler[i % len(filler)].split())
            i += 1
        return " ".join(words[:TARGET_WORDS_MIN])

    return script

# --------------------------------------------------
# PROMPT (AGGRESSIVE HOOK + RETENTION ENGINEERING)
# --------------------------------------------------

def build_prompt(case: dict, neutral: bool = False) -> str:
    tone = "calm but high-stakes investigative" if not neutral else "neutral factual"

    return f"""
You write HIGH-RETENTION YouTube Shorts narration
for a True Crime / Unresolved Mystery channel.

This script MUST reduce swipe-away and increase replay.

TONE:
- {tone}
- Serious, credible, non-graphic
- No exaggeration, no opinions
- Speak to an adult audience (US-focused)

FACTS (DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}
Narrative Flags: {case.get("flags")}

MANDATORY STRUCTURE (DO NOT BREAK):

1) SCROLL-STOPPING HOOK (0–3 seconds)
- ONE sentence only
- High stakes, emotional, or disturbing implication
- MUST suggest failure, disappearance, or unanswered outcome
- NO dates, NO locations, NO names
- Example style:
  “She vanished in seconds, and no one saw it happen.”

2) CONTEXT DROP
- Introduce date and location calmly
- ONE sentence
- Factual and grounded

3) ESCALATION (CORE RETENTION)
- 3–4 short sentences
- Focus on what went wrong, what was missed, or what never made sense
- Each sentence must ADD new information
- No repetition

4) CONTEXTUAL CTA (SUBTLE, NOT SALESY)
- ONE short sentence
- Tie subscribing to the mystery itself
- Example:
  “Following this channel helps keep cases like this alive.”

5) LOOP ENDING (REPLAY ENGINE)
- Reframe the opening hook
- No questions
- Must feel incomplete but factual

LENGTH RULES:
- {TARGET_WORDS_MIN}–{TARGET_WORDS_MAX} words
- Short sentences
- Spoken-friendly rhythm

OUTPUT FORMAT (EXACT — NO EXTRA TEXT):

SCRIPT:
<full narration>

BEATS_JSON:
[
  {{ "beat": "hook",     "intent": "failure" }},
  {{ "beat": "context",  "intent": "time_place" }},
  {{ "beat": "detail",   "intent": "mistake" }},
  {{ "beat": "cta",      "intent": "attention" }},
  {{ "beat": "loop",     "intent": "reframe" }}
]
"""

# --------------------------------------------------
# GPT CALL
# --------------------------------------------------

def call_gpt(model: str, prompt: str) -> str:
    response = client.complete(
        model=model,
        messages=[
            {"role": "system", "content": "You write high-retention Shorts narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.48,
        max_tokens=750,
    )

    text = clean(getattr(response.choices[0].message, "content", None))
    if not text:
        raise ValueError("Empty response from model")

    return text

# --------------------------------------------------
# GENERATION
# --------------------------------------------------

def generate_script(case: dict) -> Tuple[str, list]:
    prompt = build_prompt(case, neutral=False)

    try:
        text = call_gpt(PRIMARY_MODEL, prompt)
    except Exception as e:
        if "content_filter" in str(e).lower():
            prompt = build_prompt(case, neutral=True)
            text = call_gpt(FALLBACK_MODEL, prompt)
        else:
            raise

    if "SCRIPT:" not in text or "BEATS_JSON:" not in text:
        raise ValueError("Invalid GPT output format")

    script_part, beats_part = text.split("BEATS_JSON:", 1)
    script = script_part.replace("SCRIPT:", "").strip()
    script = normalize_length(script)

    try:
        beats = json.loads(beats_part.strip())
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in BEATS_JSON")

    if not isinstance(beats, list) or len(beats) != 5:
        raise ValueError("Exactly 5 beats required")

    return script, beats

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    case = load_case()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🧠 Generating high-retention script (attempt {attempt})")

            script, beats = generate_script(case)

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(BEATS_FILE, "w", encoding="utf-8") as f:
                json.dump(beats, f, indent=2)

            print("✅ Script + beats generated (retention-optimized)")
            return

        except (ValueError, HttpResponseError, json.JSONDecodeError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Failed to generate script after retries")

if __name__ == "__main__":
    main()
