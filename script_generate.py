#!/usr/bin/env python3
import os
import sys
import requests
import json
import re
import time

OUT_SCRIPT = "script.txt"
API_KEY = os.getenv("GITHUB_TOKEN")

ENDPOINT = "https://models.inference.ai.azure.com/chat/completions"
MODEL = "gpt-5"

MIN_WORDS = 55
MAX_WORDS = 75

if not API_KEY:
    print("❌ GITHUB_TOKEN missing")
    sys.exit(1)

def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def generate_script():
    prompt = (
        "Write a true crime YouTube Shorts script.\n"
        "Start with a DATE and LOCATION.\n"
        "Mention a specific object or scene detail.\n"
        "Keep it factual, tense, and disturbing.\n"
        "End with an unresolved question.\n"
        "Length: 60–70 words.\n"
        "No emojis. No filler.\n"
    )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert true crime storyteller."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 220
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=60)

    if r.status_code != 200:
        raise RuntimeError(f"API HTTP {r.status_code}: {r.text}")

    data = r.json()

    if "choices" not in data:
        raise RuntimeError(f"Invalid response: {data}")

    text = clean(data["choices"][0]["message"]["content"])
    wc = len(text.split())

    if wc < MIN_WORDS or wc > MAX_WORDS:
        raise RuntimeError(f"Bad length: {wc}")

    return text

def main():
    for attempt in range(3):
        try:
            script = generate_script()
            with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
                f.write(script)
            print("✅ Script generated successfully")
            return
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2)

    print("❌ Unable to generate valid script")
    sys.exit(1)

if __name__ == "__main__":
    main()
