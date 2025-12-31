#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
import random

OUT_SCRIPT = "script.txt"
USED_TOPICS_FILE = "used_topics.json"

API_KEY = os.getenv("GH_MODELS_TOKEN")
if not API_KEY:
    print("❌ GH_MODELS_TOKEN missing")
    sys.exit(1)

API_URL = "https://models.inference.ai.azure.com/chat/completions"
MODEL = "openai/gpt-5"

MIN_WORDS = 55
MAX_WORDS = 75

# ----------------------------------------

def load_used():
    if os.path.exists(USED_TOPICS_FILE):
        return set(json.load(open(USED_TOPICS_FILE, "r", encoding="utf-8")))
    return set()

def save_used(used):
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)

REAL_CASE_SEEDS = [
    "October 2019 car found engine running doors locked",
    "January 2016 disappearance late night security footage",
    "March 2020 missing person last phone ping",
    "August 2018 abandoned vehicle highway shoulder",
    "November 2021 CCTV footage unexplained event",
]

def generate_case_seed(used):
    random.shuffle(REAL_CASE_SEEDS)
    for seed in REAL_CASE_SEEDS:
        if seed not in used:
            return seed
    return None

def call_model(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a YouTube Shorts true-crime writer.\n"
                    "Rules:\n"
                    "- Start with a DATE and LOCATION\n"
                    "- Write in clear spoken English\n"
                    "- No filler, no vague timelines\n"
                    "- End with an unsettling unanswered detail\n"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }

    r = requests.post(API_URL, headers=headers, json=payload, timeout=60)

    if r.status_code != 200:
        print(f"❌ API HTTP {r.status_code}: {r.text}")
        return None

    data = r.json()
    if "choices" not in data:
        print("❌ Invalid API response:", data)
        return None

    return data["choices"][0]["message"]["content"].strip()

def main():
    used = load_used()
    seed = generate_case_seed(used)

    if not seed:
        print("❌ No new topics left")
        sys.exit(1)

    prompt = f"""
Write a 60–70 word YouTube Short true-crime script.

Structure:
1. Start with exact DATE and LOCATION
2. Describe the discovery
3. Introduce a contradiction
4. End with an unanswered question

Case hint: {seed}
"""

    text = call_model(prompt)
    if not text:
        print("❌ Failed to generate script")
        sys.exit(1)

    wc = len(text.split())
    if wc < MIN_WORDS or wc > MAX_WORDS:
        print(f"❌ Bad length: {wc} words")
        sys.exit(1)

    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(text)

    used.add(seed)
    save_used(used)

    print("✅ Script generated successfully")

if __name__ == "__main__":
    main()
