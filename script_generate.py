#!/usr/bin/env python3
import json
import os
import re
import requests

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

def clean(text):
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def main():
    if not os.path.exists(CASE_FILE):
        raise SystemExit("❌ case.json missing")

    facts = json.load(open(CASE_FILE))

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

    r = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=60)
    text = clean(r.json()["choices"][0]["message"]["content"])

    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(text)

    # Visuals tied to escalation
    image_prompts = [
        "abandoned car night headlights on",
        "locked car door interior night",
        "police tape residential street night",
        "phone recording empty seat night",
        "empty road fog night"
    ]

    with open(OUT_IMAGES, "w", encoding="utf-8") as f:
        json.dump(image_prompts, f, indent=2)

    print("✅ Retention-optimized script generated")

if __name__ == "__main__":
    main()
