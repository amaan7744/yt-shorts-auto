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

MIN_CASE_LEN = 200          # aligned with normalized summaries
TARGET_WORDS_MIN = 85       # ~30s
TARGET_WORDS_MAX = 105      # ~35s

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
     if len(summary) < MIN_CASE_LEN:
    print("⚠️ Case summary short but usable — continuing")

    return case

# --------------------------------------------------
# PROMPT (RETENTION-FIRST + AZURE-SAFE)
# --------------------------------------------------

def build_prompt(case: dict) -> str:
    return f"""
You write HIGH-RETENTION YouTube Shorts scripts.

The content must feel intense and mysterious,
but MUST remain factual and non-graphic.

FACTS (DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}

STRICT REQUIREMENTS:
- 30–35 seconds spoken length
- {TARGET_WORDS_MIN}–{TARGET_WORDS_MAX} words total
- Short spoken sentences
- No questions
- No opinions
- No violent or graphic wording

MANDATORY STRUCTURE:

1) HOOK (first 1 second)
- ONE short sentence (max 7 words)
- Describes a strange outcome or contradiction
- No date, no location, no names

2) CONTEXT
- Calm explanation of how this situation began
- Introduce date and location here

3) ESCALATION
- 2–3 factual details that deepen the mystery
- Focus on unexplained observations

4) LOOP ENDING (CRITICAL)
- Final line must reinterpret the hook
- Ending should make the viewer rewatch the first line

AFTER SCRIPT, OUTPUT IMAGE PROMPTS.

IMAGE RULES:
- NO people
- NO faces
- Empty locations, objects, night scenes
- Cinematic realism
- EXACTLY 4 prompts matching story flow

OUTPUT FORMAT (EXACT):

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
            {"role": "system", "content": "You write investigative short-form narration."},
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
    prompt = build_prompt(case)

    try:
        text = call_gpt(PRIMARY_MODEL, prompt)
    except Exception:
        text = call_gpt(FALLBACK_MODEL, prompt)

    if "SCRIPT:" not in text or "IMAGES_JSON:" not in text:
        raise ValueError("Invalid GPT format")

    script_part, images_part = text.split("IMAGES_JSON:", 1)
    script = script_part.replace("SCRIPT:", "").strip()

    words = script.split()
    if not (TARGET_WORDS_MIN <= len(words) <= TARGET_WORDS_MAX):
        raise ValueError("Script length outside target range")

    images = json.loads(images_part.strip())
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

            print("✅ High-retention script generated")
            return

        except Exception as e:
            print(f"⚠️ Retry {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Failed to generate valid script")

if __name__ == "__main__":
    main()
