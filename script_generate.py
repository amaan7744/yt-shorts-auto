#!/usr/bin/env python3
import os
import sys
import json
import time

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
MODEL_NAME = "openai/gpt-4o-mini"
ENDPOINT = "https://models.github.ai/inference"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
IMAGE_PROMPTS_FILE = "image_prompts.json"
USED_CASES_FILE = "used_cases.json"

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
def load_json(path):
    if not os.path.exists(path):
        print(f"❌ Required file missing: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def clean(text: str) -> str:
    return text.replace("```", "").strip()

# --------------------------------------------------
# PROMPT
# --------------------------------------------------
def build_prompt(case: dict) -> str:
    return f"""
You are a professional YouTube Shorts true-crime writer.

CASE FACTS (REAL — DO NOT CHANGE):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}

TASK:
Write a 30–40 second narration.

STRICT RULES:
- First sentence MUST include the date and location
- Calm, factual, unsettling tone
- Short spoken sentences
- No questions
- No filler words
- No supernatural claims
- End on a factual contradiction or unresolved detail

After the script, output IMAGE PROMPTS as JSON.

IMAGE RULES:
- NO people
- Night scenes, objects, empty places
- Cinematic, realistic
- 4 beats: hook, detail, context, contradiction

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
# MAIN
# --------------------------------------------------
def main():
    case = load_json(CASE_FILE)

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

            if len(script) < 200:
                raise ValueError("Script too short")

            if len(images) < 4:
                raise ValueError("Not enough image prompts")

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(script)

            with open(IMAGE_PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(images, f, indent=2)

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
