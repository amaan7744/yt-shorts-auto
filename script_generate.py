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

MIN_CASE_LEN = 600
MIN_SCRIPT_LEN = 220

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


def load_case() -> dict:
    if not os.path.exists(CASE_FILE):
        sys.exit("❌ case.json missing")

    with open(CASE_FILE, "r", encoding="utf-8") as f:
        case = json.load(f)

    summary = case.get("summary", "")
    if len(summary) < MIN_CASE_LEN:
        raise ValueError("Case summary too weak for narration")

    return case


# --------------------------------------------------
# PROMPT
# --------------------------------------------------
def build_prompt(case: dict) -> str:
    return f"""
You are a professional true-crime narrator writing for YouTube Shorts.

FACTS (REAL — DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}

TASK:
Write a 30–40 second narration.

RULES (STRICT):
- Calm, factual, unsettling tone
- Short spoken sentences
- No opinions
- No questions
- No supernatural or speculative claims
- First line MUST state an outcome or contradiction
- End with an unresolved factual detail

AFTER THE SCRIPT, OUTPUT IMAGE PROMPTS.

IMAGE RULES:
- No people
- Night scenes, objects, empty locations
- Cinematic realism
- Exactly 4 prompts

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
# GPT CALL (SAFE)
# --------------------------------------------------
def call_gpt(model: str, prompt: str) -> str:
    response = client.complete(
        model=model,
        messages=[
            {"role": "system", "content": "You write factual crime narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=750,
    )

    msg = response.choices[0].message
    text = clean(getattr(msg, "content", None))

    if not text:
        raise ValueError("GPT returned empty content")

    return text


# --------------------------------------------------
# GENERATION LOGIC
# --------------------------------------------------
def generate_script(case: dict) -> Tuple[str, list]:
    prompt = build_prompt(case)

    try:
        text = call_gpt(PRIMARY_MODEL, prompt)
    except Exception as e:
        print(f"⚠️ Primary model failed: {e}", file=sys.stderr)
        text = call_gpt(FALLBACK_MODEL, prompt)

    if "SCRIPT:" not in text or "IMAGES_JSON:" not in text:
        raise ValueError("GPT output missing required sections")

    script_part, images_part = text.split("IMAGES_JSON:", 1)

    script = script_part.replace("SCRIPT:", "").strip()
    if len(script) < MIN_SCRIPT_LEN:
        raise ValueError("Script too short")

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

            print("✅ Script + image prompts generated successfully")
            return

        except (ValueError, HttpResponseError, json.JSONDecodeError) as e:
            print(f"⚠️ Retry {attempt} failed: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    sys.exit("❌ Failed to generate a valid script after retries")


if __name__ == "__main__":
    main()
