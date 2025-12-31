#!/usr/bin/env python3
import json
import os
import re
import requests
import time
import sys

CASE_FILE = "case.json"
OUT_SCRIPT = "script.txt"
OUT_IMAGES = "image_prompts.json"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

MAX_RETRIES = 4

def clean(text: str) -> str:
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def fail(msg):
    print(f"❌ {msg}", file=sys.stderr)

def main():
    if not os.path.exists(CASE_FILE):
        fail("case.json missing")
        sys.exit(1)

    facts = json.load(open(CASE_FILE, encoding="utf-8"))

    prompt = f"""
Rewrite these REAL FACTS into a high-retention YouTube Shorts script.

GOAL:
Keep the viewer watching until the final line.

RULES:
- First line MUST include Date and Location
- Do NOT invent facts
- Short sentences
- Calm, serious tone
- No questions
- No dramatic words
- Each sentence must remove a normal assumption
- 20–30 seconds spoken

STRUCTURE:
1. Authority + time
2. What it looked like at first
3. Why that assumption fails
4. New detail that raises tension
5. Consequence of that detail
6. Final contradiction

FACTS:
Date: {facts['Date']}
Location: {facts['Location']}
Object: {facts['Object']}
State: {facts['State']}
Detail: {facts['Detail']}
Extra: {facts['Extra']}

Write ONLY the script.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You rewrite factual crime cases to maximize viewer retention."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.45,
        "max_tokens": 300,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(
                OPENROUTER_URL,
                headers=HEADERS,
                json=payload,
                timeout=60,
            )

            if r.status_code != 200:
                fail(f"API HTTP {r.status_code}: {r.text}")
                time.sleep(3)
                continue

            data = r.json()

            # 🔒 CRITICAL FIX
            if "choices" not in data or not data["choices"]:
                fail(f"Invalid API response (no choices): {data}")
                time.sleep(3)
                continue

            content = data["choices"][0]["message"]["content"]
            script = clean(content)

            if len(script.split()) < 40:
                fail("Generated script too short, retrying")
                time.sleep(2)
                continue

            # ✅ SUCCESS
            with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
                f.write(script)

            image_prompts = [
                "abandoned car night headlights on",
                "locked car door interior night",
                "police tape residential street night",
                "phone recording empty seat night",
                "empty road fog night"
            ]

            with open(OUT_IMAGES, "w", encoding="utf-8") as f:
                json.dump(image_prompts, f, indent=2)

            print("✅ Script generated successfully")
            return

        except Exception as e:
            fail(f"Exception: {e}")
            time.sleep(3)

    # ❌ Only after ALL retries
    fail("Unable to generate valid script after retries")
    sys.exit(1)

if __name__ == "__main__":
    main()
