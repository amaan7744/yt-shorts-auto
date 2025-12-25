#!/usr/bin/env python3
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

NEWS_QUERIES = [
    "unsolved cold case investigation",
    "missing person last seen night",
    "unidentified body police case",
    "cold case evidence police appeal"
]

# ---------------- FALLBACK (GUARANTEED) ----------------
FALLBACK_SCRIPT = """It was just after midnight on a quiet road in Ohio.
Thirty-four-year-old Mark Jensen was walking home from work.
He never arrived.
His phone last connected to a nearby cell tower.
No calls were made after that moment.
Police found no witnesses and no usable camera footage.
There were no signs of a struggle.
The case remains unsolved.
What happened during that short walk home?"""

# ---------------- HELPERS ----------------
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
    return " ".join(titles[1:4] + desc[1:4])[:2000]

def fetch_news():
    q = random.choice(NEWS_QUERIES)
    url = f"https://news.google.com/rss/search?q={q}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and r.text:
            return clean_rss_text(r.text)
    except Exception:
        pass
    return None

def generate_script(context):
    prompt = f"""
Write a calm, factual true-crime narration for a 40-second YouTube Short.

Rules:
- Mention a real person, place, and time
- Neutral investigative tone
- No drama, no exaggeration
- 110–140 words
- End with one unresolved question

Context:
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You write factual true-crime documentaries."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }

    for _ in range(3):
        try:
            r = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=60)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            time.sleep(2)

    return None

# ---------------- MAIN ----------------
def main():
    used = load_used()

    for _ in range(5):
        raw = fetch_news()
        if not raw or len(raw) < 100:
            continue

        h = hash_text(raw[:200])
        if h in used:
            continue

        script = generate_script(raw)
        if script:
            with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
                f.write(script.strip() + "\n")
            used.add(h)
            save_used(used)
            print("✅ Script generated from news.")
            return

    # 🚨 GUARANTEED FALLBACK
    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(FALLBACK_SCRIPT + "\n")

    used.add(hash_text(FALLBACK_SCRIPT))
    save_used(used)
    print("⚠️ Used fallback script (safe).")

if __name__ == "__main__":
    main()
