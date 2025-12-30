#!/usr/bin/env python3
import os
import json
import random
import requests
import time
import re
import hashlib

# ---------------- CONFIG ----------------
OUT_SCRIPT = "script.txt"
OUT_IMAGES = "image_prompts.json"
USED_FILE = "used_scripts.json"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL = "deepseek/deepseek-r2t1"  # IMPORTANT
MIN_WORDS, MAX_WORDS = 65, 85

NEWS_CONTEXTS = [
    "police incident night investigation",
    "missing person last seen evening police",
    "unexplained vehicle discovery police report",
]

# ---------------------------------------

def load_used():
    if os.path.exists(USED_FILE):
        try:
            return set(json.load(open(USED_FILE)))
        except:
            return set()
    return set()

def save_used(used):
    with open(USED_FILE, "w") as f:
        json.dump(sorted(list(used)), f, indent=2)

def hash_text(t):
    return hashlib.sha256(t.encode()).hexdigest()

def generate():
    context = random.choice(NEWS_CONTEXTS)

    prompt = f"""
Write a TRUE CRIME YouTube Shorts script.

ABSOLUTE RULES:
- 22–28 seconds ONLY
- First line MUST contain:
  • Date
  • City or state
  • Immediate abnormal event
- Calm, factual tone
- No metaphors
- No filler
- No questions
- End with a contradiction

STRUCTURE:
1. Date + location + incident
2. Why this is dangerous or wrong
3. Police confirmation
4. One detail that does NOT belong
5. Another detail that removes explanation
6. Final contradiction

AFTER THE SCRIPT:
Output IMAGE PROMPTS for each beat as JSON.
Images must be:
- Night
- Empty
- No people
- No faces
- Realistic
- Tense

Context:
{context}
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You write high-retention Shorts that stop scrolling."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.45,
        "max_tokens": 450,
    }

    r = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )

    if r.status_code != 200:
        return None, None

    text = r.json()["choices"][0]["message"]["content"]

    # Split script + image prompts
    parts = text.split("IMAGE PROMPTS")
    if len(parts) != 2:
        return None, None

    script = re.sub(r"\s+", " ", parts[0]).strip()
    wc = len(script.split())

    if wc < MIN_WORDS or wc > MAX_WORDS:
        return None, None

    try:
        images = json.loads(parts[1].strip())
    except:
        return None, None

    return script, images

def main():
    used = load_used()

    for _ in range(5):
        script, images = generate()
        if not script:
            time.sleep(2)
            continue

        h = hash_text(script)
        if h in used:
            continue

        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(script)

        with open(OUT_IMAGES, "w", encoding="utf-8") as f:
            json.dump(images, f, indent=2)

        used.add(h)
        save_used(used)

        print("✅ High-retention script + image prompts generated")
        return

    raise SystemExit("❌ Failed to generate valid script")

if __name__ == "__main__":
    main()

