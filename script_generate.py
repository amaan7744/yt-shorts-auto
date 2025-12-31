#!/usr/bin/env python3
import os
import sys
import json
import requests
import time

OUT_SCRIPT = "script.txt"
API_KEY = os.getenv("GH_MODELS_TOKEN")

API_URL = "https://models.inference.ai.azure.com/chat/completions"

MODEL = "gpt-5"

PROMPT = """
Write a 30–35 second YouTube Shorts true crime script.

Rules:
- Start with a DATE and LOCATION in the first line
- Use clear, real-world details
- No filler
- No repeating phrases
- End with an unresolved hook

Structure:
1) Date + place hook
2) Strange discovery
3) Unexplained contradiction
4) Chilling unanswered question
"""

def main():
    if not API_KEY:
        print("❌ GH_MODELS_TOKEN missing")
        sys.exit(1)

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You write viral true crime Shorts."},
            {"role": "user", "content": PROMPT}
        ],
        "temperature": 0.7,
        "max_tokens": 220
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    for attempt in range(3):
        r = requests.post(API_URL, headers=headers, json=payload, timeout=60)

        if r.status_code == 200:
            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()

            if len(text.split()) >= 70:
                with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
                    f.write(text)
                print("✅ Script generated")
                return

        print(f"⚠️ Retry {attempt+1}")
        time.sleep(2)

    print("❌ Failed to generate script")
    sys.exit(1)

if __name__ == "__main__":
    main()
