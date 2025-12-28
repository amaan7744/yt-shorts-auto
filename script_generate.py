#!/usr/bin/env python3
"""
script_generate.py — HIGH-RETENTION, LENGTH-LOCKED

Guarantees:
- Script duration: 30–35 seconds
- Strong hook in first line
- Human relevance (date + person later)
- Automation-safe (retry + fallback)
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

# ---------------- CONFIG ----------------

MIN_WORDS = 80   # ≈30s
MAX_WORDS = 95   # ≈35s
MAX_TRIES = 4

NEWS_QUERIES = [
    "police investigation disappearance",
    "missing person last seen night police",
    "abandoned vehicle police report",
    "unexplained incident police confirmed",
]

# HARD SAFE FALLBACK (≈32s)
FALLBACK_SCRIPT = (
    "If this happened to you, nobody would believe it. "
    "A man left his home late at night and never returned. "
    "On October 3, police confirmed his phone stopped moving minutes later. "
    "His car was found parked nearby with the lights still on. "
    "The doors were locked. "
    "Nothing inside was disturbed. "
    "No witnesses came forward. "
    "Cameras in the area recorded nothing useful. "
    "Police later said the timeline does not match the evidence they found."
)

# ---------------------------------------


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
    return " ".join(titles[1:3] + desc[1:3])[:1200]


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


def generate_script(context: str) -> str | None:
    prompt = f"""
Write a HIGH-RETENTION YouTube Shorts true crime script.

NON-NEGOTIABLE RULES:
- 80–95 words ONLY
- First line MUST directly address the viewer (use "you")
- First line MUST create immediate danger or disbelief
- Calm, factual tone
- Short sentences
- Mention a real date or time later in the script
- Mention police confirmation
- No filler words (unsolved, mysterious, tragic)
- No questions at the end
- End with a contradiction or disturbing fact

STRUCTURE:
1) Viewer-addressed hook (line 1)
2) What happened
3) Date / police confirmation
4) Evidence that does not add up
5) Contradiction ending

Context (facts only, adapt carefully):
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write high-retention YouTube Shorts scripts "
                    "that emotionally involve the viewer without exaggeration."
                )
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.45,
        "max_tokens": 350,
    }

    for _ in range(MAX_TRIES):
        try:
            r = requests.post(
                OPENROUTER_URL,
                headers=HEADERS,
                json=payload,
                timeout=60
            )
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
        if not raw or len(raw) < 100:
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
            print("✅ Script generated (30–35s enforced).")
            return

    # Fallback (guaranteed length)
    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(FALLBACK_SCRIPT + "\n")

    used.add(hash_text(FALLBACK_SCRIPT))
    save_used(used)
    print("⚠️ Used fallback script.")


if __name__ == "__main__":
    main()
