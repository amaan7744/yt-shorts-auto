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
    "police investigating unexplained disappearance",
    "missing person case last seen at night",
    "unsolved police investigation remains open",
    "unidentified person found police appeal"
]

# ---------------- HARD VIRAL FALLBACK ----------------
FALLBACK_SCRIPT = """In October 2023, police in Ohio reported a disappearance that made no sense.
A 29-year-old man left his apartment just after midnight.
His door was locked behind him.
Seven minutes later, his phone stopped moving.
No calls were made.
No messages were sent.
Cameras nearby recorded nothing unusual.
Friends said he had no plans to leave.
There was no sign of a struggle.
Police still do not know why his phone activity ended before he vanished."""

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
    return " ".join(titles[1:4] + desc[1:4])[:1600]

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

def enforce_structure(script: str) -> str:
    lines = [l.strip() for l in script.split("\n") if l.strip()]

    # Remove any soft questions
    lines = [l.replace("?", "") for l in lines]

    # Force contradiction ending
    lines[-1] = "Police still do not know why the evidence contradicts itself."

    return "\n".join(lines)

def generate_script(context):
    prompt = f"""
Write a HIGH-RETENTION true crime script optimized for YouTube Shorts.

NON-NEGOTIABLE RULES:
- First sentence MUST start with a DATE or EXACT TIME
- First sentence must include authority or investigation
- First sentence must describe an abnormal fact
- First sentence: 8–12 words ONLY
- Short sentences throughout (max 11 words)
- No introductions, no atmosphere, no storytelling buildup
- Every 2–3 sentences must add NEW information
- End with a contradiction, NOT a question
- 90–105 words total

STRUCTURE:
1) Date/time + authority + abnormal event
2) Who and where
3) Escalation (disappearance or discovery)
4) One detail that breaks logic
5) Contradiction ending

Context (adapt facts, do not copy):
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You write high-retention true crime scripts that stop scrolling."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        "temperature": 0.55,
        "max_tokens": 420,
    }

    for _ in range(3):
        try:
            r = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=60)
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"].strip()
                if 85 <= len(text.split()) <= 115:
                    return enforce_structure(text)
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
                f.write(script + "\n")
            used.add(h)
            save_used(used)
            print("✅ High-retention Shorts script generated.")
            return

    # 🚨 GUARANTEED VIRAL-SAFE FALLBACK
    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(FALLBACK_SCRIPT + "\n")

    used.add(hash_text(FALLBACK_SCRIPT))
    save_used(used)
    print("⚠️ Used viral-safe fallback.")

if __name__ == "__main__":
    main()
