#!/usr/bin/env python3
import os
import json
import hashlib
import random
import time
import requests
import re

# ---------------- CONFIG ----------------
OUT_SCRIPT = "script.txt"
USED_TOPICS_FILE = "used_topics.json"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# DEEPSEEK-SAFE LENGTH
MIN_WORDS = 42
MAX_WORDS = 52

NEWS_QUERIES = [
    "police found abandoned car night",
    "missing person last seen evening police",
    "unexplained police incident residential area",
]

FALLBACK_SCRIPT = (
    "If this happened outside your house, you would panic. "
    "A car was found running late at night with nobody inside. "
    "The doors were locked and the lights were still on. "
    "Police confirmed the driver was reported missing that night. "
    "No witnesses saw anyone leave the area. "
    "Investigators later said the timeline could not be explained."
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
    return " ".join(titles[1:3] + desc[1:3])[:700]


def fetch_news():
    q = random.choice(NEWS_QUERIES)
    try:
        r = requests.get(
            f"https://news.google.com/rss/search?q={q}",
            timeout=15
        )
        if r.status_code == 200:
            return clean_rss_text(r.text)
    except Exception:
        pass
    return None


def generate_script(context):
    prompt = f"""
Write a YouTube Shorts true crime script using EXACTLY 6 lines.

RULES (DO NOT BREAK):
- Total words: 42–52
- Each line: 7–12 words
- Short, direct sentences
- No metaphors
- No explanations
- No emotional adjectives
- No questions
- No filler phrases

STRUCTURE:
Line 1: Directly address the viewer with danger
Line 2: One concrete event
Line 3: One disturbing detail
Line 4: Police confirmation or date
Line 5: Another contradiction
Line 6: Unresolved ending statement

Context (facts only, adapt carefully):
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write extremely concise YouTube Shorts scripts. "
                    "You follow structure exactly."
                )
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.35,
        "max_tokens": 180,
    }

    for _ in range(4):
        try:
            r = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60
            )
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"].strip()
                text = re.sub(r"[{}\[\]*_]", "", text)
                wc = len(text.split())
                if MIN_WORDS <= wc <= MAX_WORDS:
                    return text
        except Exception:
            time.sleep(2)

    return None


def main():
    if not API_KEY:
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(FALLBACK_SCRIPT)
        return

    used = load_used()
    context = fetch_news() or "police reported an unexplained incident"

    script = generate_script(context)

    if script:
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(script)
        print("✅ Script generated (DeepSeek-optimized).")
    else:
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(FALLBACK_SCRIPT)
        print("⚠️ Used fallback script.")

if __name__ == "__main__":
    main()
