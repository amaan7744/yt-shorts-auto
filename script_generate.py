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

# Length control (spoken Shorts)
TARGET_MIN_WORDS = 85     # ~30s
TARGET_MAX_WORDS = 105    # ~35s

MIN_CASE_LEN = 500

# --------------------------------------------------
# ENV
# --------------------------------------------------

TOKEN = os.getenv("GH_MODELS_TOKEN")
if not TOKEN:
    print("❌ GH_MODELS_TOKEN missing", file=sys.stderr)
    sys.exit(1)

client = ChatCompletionsClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(TOKEN),
)

# --------------------------------------------------
# UTIL
# --------------------------------------------------

def clean(text) -> str:
    if not text:
        return ""
    return str(text).replace("```", "").strip()


def word_count(text: str) -> int:
    return len(text.split())


def load_case() -> dict:
    if not os.path.exists(CASE_FILE):
        sys.exit("❌ case.json missing")

    with open(CASE_FILE, "r", encoding="utf-8") as f:
        case = json.load(f)

    summary = case.get("summary", "")
    if len(summary) < MIN_CASE_LEN:
        raise ValueError("Case summary too weak")

    return case

# --------------------------------------------------
# PROMPT (RETENTION-FIRST)
# --------------------------------------------------

def build_prompt(case: dict) -> str:
    return f"""
You are writing a HIGH-RETENTION YouTube Shorts true-crime script.
Your only goal is to force viewers to WATCH UNTIL THE END and REPLAY.

FACTS (REAL — DO NOT CHANGE FACTS):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}

STRICT TARGET:
- Spoken length: 30–35 seconds
- 85–105 words total
- Short, punchy spoken sentences
- No filler
- No opinions
- No speculation
- No questions

MANDATORY STRUCTURE:

1) SHOCK HOOK (first 1–2 seconds)
- Start with the OUTCOME or DISTURBING FACT
- No dates
- No locations
- No names
- Must instantly create unease

2) CONTEXT (next 4–6 seconds)
- Explain how this situation happened
- Introduce date and location ONLY here

3) ESCALATION
- Reveal 2–3 unsettling factual details
- Each sentence must raise tension

4) LOOP ENDING (CRITICAL)
- End with a factual contradiction or unresolved detail
- The final line MUST naturally connect back to the first line
- Viewer should feel compelled to rewatch

LANGUAGE RULES:
- Calm but intense
- Spoken, not documentary
- Every sentence must move the story forward

AFTER THE SCRIPT, OUTPUT IMAGE PROMPTS.

IMAGE PROMPTS RULES:
- NO people
- NO faces
- Empty places, objects, night scenes
- Cinematic realism
- EXACTLY 4 prompts matching:
  hook → context → escalation → contradiction

OUTPUT FORMAT (EXACT — NO EXTRA TEXT):

SCRIPT:
<30–35 second script>

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
            {"role": "system", "content": "You write high-retention factual crime Shorts."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=700,
    )

    msg = response.choices[0].message
    text = clean(getattr(msg, "content", None))

    if not text:
        raise ValueError("GPT returned empty output")

    return text

# --------------------------------------------------
# GENERATION
# --------------------------------------------------

def generate_script(case: dict) -> Tuple[str, list]:
    prompt = build_prompt(case)

    try:
        text = call_gpt(PRIMARY_MODEL, prompt)
    except Exception as e:
        print(f"⚠️ Primary model failed: {e}", file=sys.stderr)
        text = call_gpt(FALLBACK_MODEL, prompt)

    if "SCRIPT:" not in text or "IMAGES_JSON:" not in text:
        raise ValueError("Missing SCRIPT or IMAGES_JSON")

    script_part, images_part = text.split("IMAGES_JSON:", 1)
    script = script_part.replace("SCRIPT:", "").strip()

    wc = word_count(script)
    if wc < TARGET_MIN_WORDS or wc > TARGET_MAX_WORDS:
        raise ValueError(f"Script word count out of range: {wc}")

    try:
        images = json.loads(images_part.strip())
    except json.JSONDecodeError:
        raise ValueError("Invalid IMAGES_JSON")

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

        except (ValueError, HttpResponseError, json.JSONDecodeError) as e:
            print(f"⚠️ Retry {attempt} failed: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    sys.exit("❌ Failed to generate a valid high-retention script")

# --------------------------------------------------

if __name__ == "__main__":
    main()
