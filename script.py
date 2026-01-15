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
# PROMPT — EDITORIAL SCRIPT
# --------------------------------------------------

def build_script_prompt(case: dict, neutral: bool = False) -> str:
    tone = "calm, investigative, restrained" if not neutral else "neutral factual"

    return f"""
You write HIGH-RETENTION YouTube Shorts narration
for a TRUE CRIME / UNRESOLVED MYSTERY channel.

TONE:
- {tone}
- Documentary style
- No exaggeration
- No speculation
- Adult audience

FACTS (DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}
Narrative Flags: {case.get("flags")}

STRUCTURE:
- Strong unresolved opening
- Clear factual grounding
- Procedural failures and gaps
- Moral archival CTA
- Unresolved looping ending

LENGTH:
- {TARGET_WORDS_MIN}–{TARGET_WORDS_MAX} words

OUTPUT (NO LABELS, NO EXPLANATIONS):
<full narration>
"""

# --------------------------------------------------
# GPT CALL
# --------------------------------------------------

def call_gpt(model: str, prompt: str) -> str:
    response = client.complete(
        model=model,
        messages=[
            {"role": "system", "content": "You write high-retention true crime narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=800,
    )

    text = clean(response.choices[0].message.content)
    if not text:
        raise ValueError("Empty response from model")

    return text

# --------------------------------------------------
# VISUAL BEAT DERIVATION (THIS IS THE KEY FIX)
# --------------------------------------------------

def derive_visual_beats(script: str) -> List[dict]:
    sentences = [s.strip() for s in script.split(".") if s.strip()]

    beats = []

    for i, sentence in enumerate(sentences):
        if i == 0:
            scene = "HOOK"
        elif i == 1:
           scene = "CRIME"
        elif i < len(sentences) - 2:
            scene = "CRIME"
        elif "subscrib" in sentence.lower():
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
    prompt = build_script_prompt(case, neutral=False)

    try:
        script = call_gpt(PRIMARY_MODEL, prompt)
    except Exception as e:
        if "content_filter" in str(e).lower():
            script = call_gpt(FALLBACK_MODEL, build_script_prompt(case, neutral=True))
        else:
            raise

    script = normalize_length(script)
    beats = derive_visual_beats(script)

    return script, beats

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    case = load_case()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🧠 Generating script + visual beats (attempt {attempt})")

            script, beats = generate(case)

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(BEATS_FILE, "w", encoding="utf-8") as f:
                json.dump(beats, f, indent=2)

            print("✅ Script and visual beats generated")
            return

        except (ValueError, HttpResponseError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Failed after retries")

if __name__ == "__main__":
    main()
