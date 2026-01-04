#!/usr/bin/env python3
import os
import sys
import json
import time

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# intelligence layers
from intelligence.idea_scorer import score_idea
from intelligence.hook_enforcer import enforce_hook
from intelligence.loop_engine import apply_loop

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
MODEL_NAME = "openai/gpt-4o-mini"
ENDPOINT = "https://models.github.ai/inference"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
IMAGE_PROMPTS_FILE = "image_prompts.json"

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
# PROMPT (STRICT, SHORTS-FIRST)
# --------------------------------------------------
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
- Night, objects, empty places
- 4 beats: hook, detail, context, contradiction

OUTPUT FORMAT (EXACT):

SCRIPT:
<each sentence on new line>

IMAGES_JSON:
[
  "prompt 1",
  "prompt 2",
  "prompt 3",
  "prompt 4"
]
"""

# --------------------------------------------------
# PHASE 1 — GPT DRAFT (ONLY PLACE GPT IS USED)
# --------------------------------------------------
def gpt_generate_draft(case: dict) -> tuple[str, list]:
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
        raise ValueError("Missing SCRIPT or IMAGES_JSON")

    script_part, images_part = text.split("IMAGES_JSON:")
    script = script_part.replace("SCRIPT:", "").strip()
    images = json.loads(images_part.strip())

    return script, images

# --------------------------------------------------
# PHASE 2 — INTELLIGENCE & CONTROL (NO GPT)
# --------------------------------------------------
def post_process_script(script: str, case: dict) -> str:
    # 1. Enforce hook quality
    script = enforce_hook(script)

    # 2. Score idea (kill weak scripts)
    score = score_idea(case.get("summary", ""), script)
    if score["kill"]:
        raise ValueError(f"Script killed: {score['reasons']}")

    # 3. Force loop ending
    looped = apply_loop(script)
    script = looped["script"]

    return script

# --------------------------------------------------
# MAIN ORCHESTRATOR
# --------------------------------------------------
def main():
    case = load_json(CASE_FILE)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🧠 Generating script (attempt {attempt})")

            # GPT draft (new every run)
            raw_script, images = gpt_generate_draft(case)

            # Intelligence processing
            final_script = post_process_script(raw_script, case)

            # Save outputs
            with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(final_script)

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
