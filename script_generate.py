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
            "The truth was never documented."
        ]
        i = 0
        while len(words) < TARGET_WORDS_MIN:
            words.extend(filler[i % len(filler)].split())
            i += 1
        return " ".join(words[:TARGET_WORDS_MIN])

    return script

# --------------------------------------------------
# PROMPT (SCRIPT + IMAGE PROMPTS)
# --------------------------------------------------

def build_prompt(case: dict, neutral: bool = False) -> str:
    tone = "calm, investigative, high-stakes" if not neutral else "neutral factual"

    return f"""
You create HIGH-RETENTION YouTube Shorts narration
for a True Crime / Unresolved Mystery channel.

Your task has TWO outputs:
1) A spoken script
2) Image prompts aligned with each story beat

TONE:
- {tone}
- Serious, credible, restrained
- No exaggeration
- No speculation
- Adult US audience

FACTS (DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}
Narrative Flags: {case.get("flags")}

MANDATORY STRUCTURE (DO NOT BREAK):

1) HOOK
- ONE sentence
- Suggest failure or unresolved outcome
- No names, dates, or locations

2) CONTEXT
- ONE sentence
- Calmly introduce date and location

3) ESCALATION
- 4 short sentences
- Each adds a NEW failure, gap, or inconsistency

4) CTA
- ONE sentence
- Must include the word "subscribing"
- Must feel moral, not promotional
- Example: "Subscribing helps keep cases like this from disappearing."

5) LOOP ENDING
- ONE sentence
- Reframe the hook
- No questions
- Feels incomplete but factual

IMAGE PROMPT RULES:
- No people
- No faces
- No bodies
- No violence
- Symbolic, documentary style
- Night, low light, or neutral interiors
- Each prompt must visually represent the beat

LENGTH:
- {TARGET_WORDS_MIN}–{TARGET_WORDS_MAX} words
- Spoken-friendly rhythm

OUTPUT FORMAT (EXACT — NO EXTRA TEXT):

SCRIPT:
<full script>

BEATS_JSON:
[
  {{
    "beat": "hook",
    "image_prompt": "<visual that represents unresolved failure>"
  }},
  {{
    "beat": "context",
    "image_prompt": "<visual that represents time and place>"
  }},
  {{
    "beat": "escalation",
    "image_prompt": "<visual that represents investigation mistake>"
  }},
  {{
    "beat": "cta",
    "image_prompt": "<visual that represents case being forgotten>"
  }},
  {{
    "beat": "loop",
    "image_prompt": "<visual that represents unresolved ending>"
  }}
]
"""

# --------------------------------------------------
# GPT CALL
# --------------------------------------------------

def call_gpt(model: str, prompt: str) -> str:
    response = client.complete(
        model=model,
        messages=[
            {"role": "system", "content": "You write retention-optimized crime scripts with image prompts."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.45,
        max_tokens=900,
    )

    text = clean(getattr(response.choices[0].message, "content", None))
    if not text:
        raise ValueError("Empty response from model")

    return text

# --------------------------------------------------
# GENERATION
# --------------------------------------------------

def generate(case: dict) -> Tuple[str, list]:
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
        raise ValueError("Invalid output format")

    script_part, beats_part = text.split("BEATS_JSON:", 1)

    script = script_part.replace("SCRIPT:", "").strip()
    script = normalize_length(script)

    beats = json.loads(beats_part.strip())

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
            print(f"🧠 Generating script + image prompts (attempt {attempt})")

            script, beats = generate(case)

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(BEATS_FILE, "w", encoding="utf-8") as f:
                json.dump(beats, f, indent=2)

            print("✅ Script and image prompts generated")
            return

        except (ValueError, HttpResponseError, json.JSONDecodeError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Failed after retries")

if __name__ == "__main__":
    main()
