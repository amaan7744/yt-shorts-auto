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

PRIMARY_MODEL = "openai/gpt-4o-mini"
FALLBACK_MODEL = "openai/gpt-4.1-mini"
ENDPOINT = "https://models.github.ai/inference"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
IMAGE_PROMPTS_FILE = "image_prompts.json"

MAX_RETRIES = 3
RETRY_DELAY = 2

# Soft constraints (never block uploads)
MIN_CASE_LEN = 200

# Shorts timing control
TARGET_WORDS_MIN = 85   # ~30 sec
TARGET_WORDS_MAX = 105  # ~35 sec

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

def clean(text) -> str:
    return str(text or "").replace("```", "").strip()


def load_case() -> dict:
    if not os.path.exists(CASE_FILE):
        sys.exit("❌ case.json missing")

    with open(CASE_FILE, "r", encoding="utf-8") as f:
        case = json.load(f)

    summary = case.get("summary", "")

    # Never block the pipeline
    if len(summary) < MIN_CASE_LEN:
        print("⚠️ Case summary short but usable — continuing")

    return case

# --------------------------------------------------
# PROMPT (AZURE-SAFE + RETENTION-OPTIMIZED)
# --------------------------------------------------

def build_prompt(case: dict, neutral: bool = False) -> str:
    tone = (
        "informative and historical"
        if neutral
        else "mysterious and intriguing"
    )

    return f"""
You write HIGH-RETENTION YouTube Shorts narration
about REAL HISTORICAL ANOMALIES and UNRESOLVED EVENTS.

These are factual records where outcomes were never fully explained.
The tone must be {tone}, calm, and NON-GRAPHIC.

FACTUAL RECORD (DO NOT CHANGE FACTS):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}

STRICT REQUIREMENTS:
- Spoken length: 30–35 seconds
- {TARGET_WORDS_MIN}–{TARGET_WORDS_MAX} words total
- Short spoken sentences
- Neutral documentary narration
- No questions
- No opinions
- Avoid violent or graphic language entirely

MANDATORY STRUCTURE:

1) OPENING HOOK (first second)
- ONE short sentence (max 7 words)
- Describes a strange or unexplained outcome
- No names, dates, or locations

2) BACKGROUND
- Calm explanation of how this situation began
- Introduce date and location here

3) DETAILS
- 2–3 factual observations or unresolved elements
- Focus on what was unclear, missing, or unexplained

4) LOOP ENDING
- Final line must reframe the opening hook
- Ending should naturally encourage replay

AFTER THE SCRIPT, OUTPUT IMAGE PROMPTS.

IMAGE PROMPT RULES:
- NO people
- NO faces
- Empty places, objects, night environments
- Cinematic realism
- EXACTLY 4 prompts following story order

OUTPUT FORMAT (EXACT — NO EXTRA TEXT):

SCRIPT:
<text>

IMAGES_JSON:
[
  "prompt 1",
  "prompt 2",
  "prompt 3",
  "prompt 4"
]
"""

# --------------------------------------------------
# GPT CALL
# --------------------------------------------------

def call_gpt(model: str, prompt: str) -> str:
    response = client.complete(
        model=model,
        messages=[
            {"role": "system", "content": "You write short-form documentary narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=650,
    )

    text = clean(getattr(response.choices[0].message, "content", None))
    if not text:
        raise ValueError("GPT returned empty content")

    return text

# --------------------------------------------------
# GENERATION
# --------------------------------------------------

def generate_script(case: dict) -> Tuple[str, list]:
    # First attempt: normal mysterious framing
    prompt = build_prompt(case, neutral=False)

    try:
        text = call_gpt(PRIMARY_MODEL, prompt)
    except Exception as e:
        if "content_filter" in str(e).lower():
            print("⚠️ Content filter triggered — retrying with neutral framing")
            prompt = build_prompt(case, neutral=True)
            text = call_gpt(FALLBACK_MODEL, prompt)
        else:
            raise

    if "SCRIPT:" not in text or "IMAGES_JSON:" not in text:
        raise ValueError("Invalid GPT output format")

    script_part, images_part = text.split("IMAGES_JSON:", 1)
    script = script_part.replace("SCRIPT:", "").strip()

    words = script.split()
    if not (TARGET_WORDS_MIN <= len(words) <= TARGET_WORDS_MAX):
        raise ValueError("Script length outside target range")

    try:
        images = json.loads(images_part.strip())
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in IMAGES_JSON")

    if not isinstance(images, list) or len(images) != 4:
        raise ValueError("Exactly 4 image prompts required")

    return script, images

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    case = load_case()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🧠 Generating script (attempt {attempt})")

            script, images = generate_script(case)

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(IMAGE_PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(images, f, indent=2)

            print("✅ Script + image prompts generated")
            return

        except (ValueError, HttpResponseError, json.JSONDecodeError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Failed to generate valid script after retries")


if __name__ == "__main__":
    main()
    
