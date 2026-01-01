#!/usr/bin/env python3
import os
import sys
import json
import time
import random

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
MODEL_NAME = "openai/gpt-4o-mini"
ENDPOINT = "https://models.github.ai/inference"

SCRIPT_FILE = "script.txt"
IMAGE_PROMPTS_FILE = "image_prompts.json"
USED_TOPICS_FILE = "used_topics.json"

MAX_RETRIES = 3

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
def load_used():
    if os.path.exists(USED_TOPICS_FILE):
        try:
            return set(json.load(open(USED_TOPICS_FILE)))
        except Exception:
            return set()
    return set()

def save_used(used):
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)

def clean(text: str) -> str:
    return text.replace("```", "").strip()

# --------------------------------------------------
# CASE SEEDS (REAL + NON-GENERIC)
# --------------------------------------------------
CASE_SEEDS = [
    "October 13, 2019 — Springfield, Ohio — abandoned car with engine running",
    "March 22, 2016 — Delphi, Indiana — disappearance near hiking trail",
    "September 11, 2006 — Napa Valley, California — early morning jogger vanishes",
    "July 8, 2004 — Moscow, Idaho — late-night home crime with no forced entry",
]

# --------------------------------------------------
# PROMPT
# --------------------------------------------------
def build_prompt(case: str) -> str:
    return f"""
You are a YouTube Shorts true-crime writer.

Write a 30–40 second script.

STRICT RULES:
- Start with DATE and LOCATION in first sentence
- Calm, factual, unsettling tone
- No filler phrases
- No questions
- Spoken, short sentences
- End on contradiction

After the script, output IMAGE PROMPTS as JSON.

IMAGE RULES:
- NO PEOPLE
- Night, objects, empty places only
- Cinematic, realistic
- 4 beats: hook, detail, context, contradiction

OUTPUT FORMAT (VERY IMPORTANT):

SCRIPT:
<text>

IMAGES_JSON:
[
  "prompt 1",
  "prompt 2",
  "prompt 3",
  "prompt 4"
]

CASE:
{case}
"""

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    used = load_used()
    available = [c for c in CASE_SEEDS if c not in used]

    if not available:
        print("❌ No unused cases left", file=sys.stderr)
        sys.exit(1)

    case = random.choice(available)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🧠 Generating script (attempt {attempt})")

            response = client.complete(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You write factual crime narration."},
                    {"role": "user", "content": build_prompt(case)},
                ],
                temperature=0.5,
                max_tokens=700,
            )

            text = clean(response.choices[0].message.content)

            if "SCRIPT:" not in text or "IMAGES_JSON:" not in text:
                raise ValueError("Missing required sections")

            script_part, images_part = text.split("IMAGES_JSON:")
            script = script_part.replace("SCRIPT:", "").strip()

            images = json.loads(images_part.strip())

            if len(images) < 4 or len(script) < 200:
                raise ValueError("Script or images too weak")

            # Write outputs
            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(IMAGE_PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(images, f, indent=2)

            used.add(case)
            save_used(used)

            print("✅ Script + image prompts generated")
            return

        except (HttpResponseError, ValueError, json.JSONDecodeError) as e:
            print(f"⚠️ Retry {attempt}: {e}", file=sys.stderr)
            time.sleep(2)

    print("❌ Failed to generate valid script", file=sys.stderr)
    sys.exit(1)

# --------------------------------------------------
if __name__ == "__main__":
    main()
