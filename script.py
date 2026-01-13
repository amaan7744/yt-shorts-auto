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
            "The official records never explained why.",
            "Several details were left unresolved.",
            "The final report did not address the gaps."
        ]
        i = 0
        while len(words) < TARGET_WORDS_MIN:
            words.extend(filler[i % len(filler)].split())
            i += 1
        return " ".join(words[:TARGET_WORDS_MIN])

    return script

# --------------------------------------------------
# PROMPT (RETENTION + CRIME-REALISTIC + LOOP)
# --------------------------------------------------

def build_prompt(case: dict, neutral: bool = False) -> str:
    tone = "calm, investigative, high-stakes" if not neutral else "neutral factual"

    return f"""
You write HIGH-RETENTION YouTube Shorts narration
for a TRUE CRIME / UNRESOLVED MYSTERY channel.

Your output must maximize:
- Scroll-stop
- Watch time
- Replay (loop)

You MUST avoid generic storytelling.

TONE:
- {tone}
- Serious, restrained, documentary
- No exaggeration
- No speculation
- Adult US audience

FACTS (DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}
Narrative Flags: {case.get("flags")}

MANDATORY STRUCTURE (DO NOT BREAK):

1) HOOK (1 sentence)
- Immediate failure or unresolved outcome
- Feels disturbing or incomplete
- No names, no dates, no locations
- Must feel like the END of a case, not the start

2) CONTEXT (1 sentence)
- Calmly introduce date and location
- Neutral, factual grounding

3) ESCALATION (4 short sentences)
- Each sentence introduces a NEW procedural failure
- Focus on:
  • evidence handling
  • timeline gaps
  • ignored records
  • unanswered inconsistencies
- No emotional language, only factual tension

4) CTA (1 sentence)
- Must include the word "subscribing"
- Moral / archival framing
- Not promotional
- Example tone:
  "Subscribing helps keep cases like this from disappearing."

5) LOOP ENDING (1 sentence)
- Reframes the hook
- Mirrors the first sentence thematically
- No questions
- Must feel unfinished so replay feels natural

IMAGE PROMPT RULES (CRITICAL):
- Describe PHYSICAL LOCATIONS and OBJECTS only
- NO abstract words like cinematic, symbolic, mysterious
- Allowed: men, investigators, police environments
- BLOCK:
  • women
  • girls
  • nudity
  • romance
  • couples
- No gore
- No explicit violence
- Documentary / investigative photography style
- Night or institutional lighting preferred

IMAGE PROMPTS MUST INCLUDE:
- Location (room / building / exterior)
- Crime-related objects (files, evidence, documents, markers)
- Lighting type (fluorescent, office, night streetlight)
- Realistic materials (metal, paper, concrete)

LENGTH:
- {TARGET_WORDS_MIN}–{TARGET_WORDS_MAX} words
- Spoken-friendly rhythm
- Short sentences

OUTPUT FORMAT (EXACT — NO EXTRA TEXT):

SCRIPT:
<full narration>

BEATS_JSON:
[
  {{
    "beat": "hook",
    "image_prompt": "<forensic or institutional scene that visually implies failure>"
  }},
  {{
    "beat": "context",
    "image_prompt": "<realistic location establishing time and place>"
  }},
  {{
    "beat": "escalation",
    "image_prompt": "<evidence, documents, or procedural failure scene>"
  }},
  {{
    "beat": "cta",
    "image_prompt": "<archival or forgotten case imagery>"
  }},
  {{
    "beat": "loop",
    "image_prompt": "<visual that closely echoes the hook image>"
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
            {"role": "system", "content": "You write retention-optimized true crime Shorts with realistic image prompts."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
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
            print(f"🧠 Generating high-retention script + forensic image prompts (attempt {attempt})")

            script, beats = generate(case)

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(BEATS_FILE, "w", encoding="utf-8") as f:
                json.dump(beats, f, indent=2)

            print("✅ Script and beats generated successfully")
            return

        except (ValueError, HttpResponseError, json.JSONDecodeError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Failed after retries")

if __name__ == "__main__":
    main()
