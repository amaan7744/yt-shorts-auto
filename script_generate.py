#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import requests

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
MODEL_NAME = "meta-llama/llama-3.1-70b-instruct"
ENDPOINT = "https://models.github.ai/inference"
OUT_FILE = "script.txt"
USED_TOPICS_FILE = "used_topics.json"

MAX_RETRIES = 3
TIMEOUT = 30

# --------------------------------------------------
# ENV CHECK
# --------------------------------------------------
TOKEN = os.getenv("GH_MODELS_TOKEN")
if not TOKEN:
    print("❌ GH_MODELS_TOKEN not set", file=sys.stderr)
    sys.exit(1)

# --------------------------------------------------
# CLIENT
# --------------------------------------------------
client = ChatCompletionsClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(TOKEN),
)

# --------------------------------------------------
# UTILITIES
# --------------------------------------------------
def load_used_topics():
    if os.path.exists(USED_TOPICS_FILE):
        try:
            with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_used_topics(topics):
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(topics)), f, indent=2)

def clean(text: str) -> str:
    return (
        text.replace("```", "")
        .replace("—", "-")
        .strip()
    )

# --------------------------------------------------
# CASE SEED (REALISTIC, NON-REPEATING)
# --------------------------------------------------
CASE_SEEDS = [
    "October 13, 2019 – Springfield, Ohio – abandoned car found with engine running and doors locked",
    "March 22, 2016 – Delphi, Indiana – two teenagers vanish near a hiking trail",
    "July 8, 2004 – Moscow, Idaho – late-night house crime with no forced entry",
    "December 26, 1996 – Boulder, Colorado – child disappearance inside family home",
    "August 4, 2002 – Laci Peterson disappearance – Modesto, California",
    "April 19, 2013 – Boston Marathon bombing aftermath – unexplained suspect movement",
    "September 11, 2006 – Napa Valley, California – jogger disappearance at dawn",
]

# --------------------------------------------------
# SCRIPT PROMPT
# --------------------------------------------------
def build_prompt(case_seed: str) -> str:
    return f"""
You are a professional true-crime documentary writer.

Write a YouTube Shorts script (35–45 seconds max).

STRICT RULES:
- Start with DATE + LOCATION immediately
- No vague language
- No filler phrases
- No repetition
- No supernatural claims
- Calm, serious tone
- High retention hook in first 2 seconds

FORMAT:
Date:
Location:
Key Detail:
Script (short paragraphs, spoken style):

CASE:
{case_seed}
"""

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    used_topics = load_used_topics()

    available_cases = [c for c in CASE_SEEDS if c not in used_topics]
    if not available_cases:
        print("❌ No unused case seeds left", file=sys.stderr)
        sys.exit(1)

    case = random.choice(available_cases)
    prompt = build_prompt(case)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🧠 Generating script (attempt {attempt})")

            response = client.complete(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You write factual true crime narration."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
                max_tokens=500,
                timeout=TIMEOUT,
            )

            text = clean(response.choices[0].message.content)

            if len(text) < 200:
                raise ValueError("Script too short")

            with open(OUT_FILE, "w", encoding="utf-8") as f:
                f.write(text)

            used_topics.add(case)
            save_used_topics(used_topics)

            print("✅ Script generated successfully")
            return

        except HttpResponseError as e:
            print(f"❌ API error: {e.message}", file=sys.stderr)

        except Exception as e:
            print(f"⚠️ Retry {attempt}: {e}", file=sys.stderr)

        time.sleep(2)

    print("❌ Failed to generate script after retries", file=sys.stderr)
    sys.exit(1)

# --------------------------------------------------
if __name__ == "__main__":
    main()
