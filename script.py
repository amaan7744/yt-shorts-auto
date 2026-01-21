#!/usr/bin/env python3

import os
import sys
import json
import time
import re
from typing import Tuple, List

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# ==================================================
# CONFIG — SHORTS ATTENTION ENGINE
# ==================================================

ENDPOINT = "https://models.github.ai/inference"
MODEL = "openai/gpt-4o-mini"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

# 18–22 seconds at ~155 WPM
TARGET_WORDS_MIN = 44
TARGET_WORDS_MAX = 52

MAX_RETRIES = 3
RETRY_DELAY = 2

# ==================================================
# CLIENT
# ==================================================

TOKEN = os.getenv("GH_MODELS_TOKEN")
if not TOKEN:
    sys.exit("❌ GH_MODELS_TOKEN missing")

client = ChatCompletionsClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(TOKEN),
)

# ==================================================
# UTIL
# ==================================================

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()

def load_case() -> dict:
    if not os.path.isfile(CASE_FILE):
        sys.exit("❌ case.json missing")

    with open(CASE_FILE, "r", encoding="utf-8") as f:
        case = json.load(f)

    if not case.get("summary"):
        sys.exit("❌ case.json missing summary")

    return case

def enforce_length(text: str) -> str:
    words = text.split()
    return " ".join(words[:TARGET_WORDS_MAX])

# ==================================================
# PROMPT — PROVEN ENGAGEMENT MODEL
# ==================================================

def build_script_prompt(case: dict) -> str:
    return f"""
Write a 20-second YouTube Shorts narration about a real unresolved case.

You are optimizing for:
- Scroll-stopping first frame
- Rising tension every sentence
- Calm authority (not hype)
- Rewatchability

ABSOLUTE RULES:
- 44–52 words total
- One paragraph only
- Short sentences
- No speculation language
- No graphic detail
- Must work muted as text

STRUCTURE (DO NOT LABEL):

1. Start with a specific fact that feels impossible or wrong.
2. Immediately anchor the viewer with time and place.
3. Add a verified detail that contradicts the first.
4. Add a second detail that makes the situation harder to explain.
5. State what official records fail to reconcile.
6. Frame the case as something that could disappear without attention.
7. End with an unresolved line that loops naturally.

FACTS YOU MUST USE (DO NOT ALTER):
Location: {case.get("location")}
Summary: {case.get("summary")}

CTA GUIDANCE:
- Do NOT say like or comment.
- Acceptable style:
  “Subscribing helps preserve cases like this.”

OUTPUT:
Only the narration text.
"""

# ==================================================
# GPT CALL
# ==================================================

def call_gpt(prompt: str) -> str:
    response = client.complete(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You write concise, high-retention documentary narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=220,
    )

    text = clean(response.choices[0].message.content)
    if not text:
        raise ValueError("Empty model response")

    return text

# ==================================================
# VISUAL BEATS — ATTENTION SYNCED
# ==================================================

def derive_visual_beats(script: str) -> List[dict]:
    sentences = [s.strip() for s in re.split(r"[.!?]", script) if len(s.strip()) > 4]

    beats = []
    for i, s in enumerate(sentences):
        if i == 0:
            scene = "HOOK"
        elif i == 1:
            scene = "ANCHOR"
        elif i in (2, 3):
            scene = "ESCALATION"
        elif i == len(sentences) - 2:
            scene = "IMPLICATION"
        else:
            scene = "LOOP"

        beats.append({
            "beat": f"scene_{i+1}",
            "scene": scene,
            "text": s,
        })

    return beats

# ==================================================
# GENERATION
# ==================================================

def generate(case: dict) -> Tuple[str, list]:
    prompt = build_script_prompt(case)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            script = call_gpt(prompt)
            script = enforce_length(script)
            beats = derive_visual_beats(script)
            return script, beats
        except (ValueError, HttpResponseError) as e:
            print(f"⚠️ Attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    sys.exit("❌ Script generation failed")

# ==================================================
# MAIN
# ==================================================

def main():
    case = load_case()
    print("🧠 Generating engagement-optimized Shorts script…")

    script, beats = generate(case)

    with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(script)

    with open(BEATS_FILE, "w", encoding="utf-8") as f:
        json.dump(beats, f, indent=2)

    print("✅ Script generated (engineered for scroll-stop + hold)")

if __name__ == "__main__":
    main()
