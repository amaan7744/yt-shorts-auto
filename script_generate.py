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
    "missing person last seen night",
    "unsolved disappearance police investigation",
    "cold case police appeal last seen",
    "unidentified person found case"
]

# ---------------- VIRAL-SAFE FALLBACK ----------------
FALLBACK_SCRIPT = """At 1:42 AM, a 29-year-old man left his apartment in Ohio.
His security camera recorded him locking the door.
He never returned.
His phone stopped moving seven minutes later.
No calls. No messages. No activity.
Police traced his last location to a residential street.
There were no witnesses.
No nearby cameras showed anything unusual.
Friends said he had no reason to disappear.
Investigators still don’t know why he stepped outside that night.
What happened in those seven minutes?"""

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
    return " ".join(titles[1:4] + desc[1:4])[:1800]

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
Write a HIGH-RETENTION true crime script for a 30–40 second YouTube Short.

ABSOLUTE RULES:
- First sentence MUST start with a specific time (e.g., "At 2:14 AM")
- Mention one real person (or age if name unknown), one place, and one night
- Short sentences only (max 12 words per sentence)
- No introductions, no filler, no scene setting
- Every 2–3 sentences must add NEW information
- Tone: investigative, unsettling, controlled
- End with ONE unanswered question
- 90–120 words total

STRUCTURE YOU MUST FOLLOW:
1) Time-based hook (first line)
2) Who + where (immediately)
3) Escalation: disappearance / abnormal event
4) One detail that breaks logic
5) Cliff question

Context (facts to adapt, not copy):
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You write high-retention true crime scripts optimized for YouTube Shorts."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        "temperature": 0.6,
        "max_tokens": 450,
    }

    for _ in range(3):
        try:
            r = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=60)
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"].strip()
                # basic sanity check
                if len(text.split()) >= 80:
                    return text
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

        h = hash_text(raw[:250])
        if h in used:
            continue

        script = generate_script(raw)
        if script:
            with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
                f.write(script.strip() + "\n")
            used.add(h)
            save_used(used)
            print("✅ High-retention script generated.")
            return

    # 🚨 VIRAL-SAFE FALLBACK
    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(FALLBACK_SCRIPT + "\n")

    used.add(hash_text(FALLBACK_SCRIPT))
    save_used(used)
    print("⚠️ Used viral-safe fallback.")

if __name__ == "__main__":
    main()
