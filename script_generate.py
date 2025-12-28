#!/usr/bin/env python3
"""
script_generate.py — MRBEAST-STYLE SHORTS SCRIPT

Targets:
- 22–28 seconds
- 55–65 words
- Strong hook
- Simple, watchable flow
"""

import os
import json
import hashlib
import random
import time
import requests
import re

OUT_SCRIPT = "script.txt"
USED_TOPICS_FILE = "used_topics.json"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

MIN_WORDS = 55
MAX_WORDS = 65

NEWS_QUERIES = [
    "police investigation disappearance",
    "abandoned car police night",
    "missing person last seen evening",
]

FALLBACK_SCRIPT = (
    "If this happened to you, nobody would believe it. "
    "A man stepped outside his home late one night. "
    "He never came back. "
    "Police later found his car parked nearby with the lights on. "
    "The doors were locked. "
    "Nothing inside was touched. "
    "No one saw him leave. "
    "Police say the timeline does not make sense."
)

def load_used():
    if os.path.exists(USED_TOPICS_FILE):
        try:
            return set(json.load(open(USED_TOPICS_FILE, "r", encoding="utf-8")))
        except Exception:
            return set()
    return set()

def save_used(used):
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)

def hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def clean_rss_text(xml):
    titles = re.findall(r"<title>(.*?)</title>", xml)
    desc = re.findall(r"<description>(.*?)</description>", xml)
    return " ".join(titles[1:3] + desc[1:3])[:900]

def fetch_news():
    q = random.choice(NEWS_QUERIES)
    url = f"https://news.google.com/rss/search?q={q}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return clean_rss_text(r.text)
    except Exception:
        pass
    return None

def generate_script(context):
    prompt = f"""
Write a SHORT YouTube Shorts true crime script.

STRICT RULES:
- 55–65 words ONLY
- First line must hook the viewer directly
- Simple sentences
- No filler or explanations
- Calm, clear narration
- End with something unsettling (not a question)

STYLE:
MrBeast Shorts pacing.
Easy to listen.
Not heavy.

Context:
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You write short, high-retention YouTube Shorts scripts."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 220,
    }

    for _ in range(4):
        try:
            r = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=60)
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"].strip()
                wc = len(text.split())
                if MIN_WORDS <= wc <= MAX_WORDS:
                    return text
        except Exception:
            time.sleep(2)

    return None

def main():
    used = load_used()

    for _ in range(5):
        raw = fetch_news()
        if not raw:
            continue

        h = hash_text(raw[:200])
        if h in used:
            continue

        script = generate_script(raw)
        if script:
            with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
                f.write(script + "\n")
            used.add(h)
            save_used(used)
            print("✅ Short MRBeast-style script generated.")
            return

    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(FALLBACK_SCRIPT + "\n")

    used.add(hash_text(FALLBACK_SCRIPT))
    save_used(used)
    print("⚠️ Used fallback script.")

if __name__ == "__main__":
    main()
