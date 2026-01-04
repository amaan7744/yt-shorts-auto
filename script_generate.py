#!/usr/bin/env python3

import os
import sys
import json
import time
from typing import Tuple

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# ---------------- INTELLIGENCE ----------------
from intelligence.idea_scorer import score_idea
from intelligence.hook_enforcer import enforce_hook
from intelligence.loop_engine import apply_loop

# ---------------- CONFIG ----------------
PRIMARY_MODEL = "openai/gpt-4o-mini"
FALLBACK_MODEL = "openai/gpt-4.1-mini"

ENDPOINT = "https://models.github.ai/inference"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
IMAGE_PROMPTS_FILE = "image_prompts.json"

MAX_RETRIES = 3
RETRY_DELAY = 2

# ---------------- ENV ----------------
TOKEN = os.getenv("GH_MODELS_TOKEN")
if not TOKEN:
    print("❌ GH_MODELS_TOKEN missing", file=sys.stderr)
    sys.exit(1)

client = ChatCompletionsClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(TOKEN),
)

# ---------------- UTIL ----------------
def load_json(path: str) -> dict:
    if not os.path.exists(path):
        print(f"❌ Required file missing: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean(text) -> str:
    if not text:
        return ""
    return str(text).replace("```", "").strip()


# ---------------- PROMPT ----------------
def build_prompt(case: dict) -> str:
    return f"""
You are a professional YouTube Shorts true-crime writer.

CASE FACTS (REAL — DO NOT CHANGE FACTS):
Date: {case.get("date")}
Location: {case.get("location")}
Summary: {case.get("summary")}

MANDATORY STRUCTURE:

LINE 1 (HOOK):
- Outcome or contradiction
- No date or location
- Max 12 words

LINE 2 (TENSION):
- One unsettling factual detail

LINE 3 (CONTEXT):
- Introduce date and location naturally

STYLE:
- Calm, factual, unsettling
- Short spoken sentences
- No opinions
- No supernatural claims

ENDING:
- End on an unresolved factual contradiction
- Do NOT explain it

AFTER SCRIPT OUTPUT IMAGE PROMPTS AS JSON.

IMAGE RULES:
- NO people
- Night scenes, empty places, objects
- 4 beats: hook, detail, context, contradiction

OUTPUT FORMAT (EXACT):

SCRIPT:
<each sentence on a new line>

IMAGES_JSON:
[
  "prompt 1",
  "prompt 2",
  "prompt 3",
  "prompt 4"
]
"""


# ---------------- GPT CALL (SAFE) ----------------
def call_gpt(model: str, prompt: str) -> str:
    response = client.complete(
        model=model,
        messages=[
            {"role": "system", "content": "You write factual crime narration."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=700,
    )

    # Defensive extraction (Azure can return None)
    message = response.choices[0].message
    text = message.content if getattr(message, "content", None) else ""
    text = clean(text)

    if not text:
        raise ValueError("GPT returned empty content")

    return text


# ---------------- DRAFT GENERATION ----------------
def gpt_generate_draft(case: dict) -> Tuple[str, list]:
    prompt = build_prompt(case)

    # Try primary model first
    try:
        text = call_gpt(PRIMARY_MODEL, prompt)
    except Exception as e:
        print(f"⚠️ Primary model failed ({PRIMARY_MODEL}): {e}", file=sys.stderr)
        print("↪ Falling back to secondary model", file=sys.stderr)
        text = call_gpt(FALLBACK_MODEL, prompt)

    if "SCRIPT:" not in text or "IMAGES_JSON:" not in text:
        raise ValueError("Missing SCRIPT or IMAGES_JSON sections")

    script_part, images_part = text.split("IMAGES_JSON:", 1)
    script = script_part.replace("SCRIPT:", "").strip()

    try:
        images = json.loads(images_part.strip())
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in IMAGES_JSON")

    if len(script) < 200:
        raise ValueError("Script too short")

    if not isinstance(images, list) or len(images) < 4:
        raise ValueError("Not enough image prompts")

    return script, images


# ---------------- POST PROCESS ----------------
def post_process_script(script: str, case: dict) -> str:
    # Enforce hook strength
    script = enforce_hook(script)

    # Kill weak ideas early
    score = score_idea(case.get("summary", ""), script)
    if score.get("kill"):
        raise ValueError(f"Script killed by idea scorer: {score.get('reasons')}")

    # Force loop ending
    looped = apply_loop(script)
    return looped["script"]


# ---------------- MAIN ----------------
def main():
    case = load_json(CASE_FILE)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🧠 Generating script (attempt {attempt})")

            raw_script, images = gpt_generate_draft(case)
            final_script = post_process_script(raw_script, case)

            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(final_script)

            with open(IMAGE_PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(images, f, indent=2)

            print("✅ Script + image prompts generated")
            return

        except (HttpResponseError, ValueError, json.JSONDecodeError) as e:
            print(f"⚠️ Retry {attempt} failed: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    print("❌ Failed to generate valid script after retries", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
