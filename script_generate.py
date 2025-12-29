#!/usr/bin/env python3
import os
import json
import random
import time
import requests
import re

OUT_SCRIPT = "script.txt"
USED_TOPICS_FILE = "used_topics.json"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

NEWS_QUERIES = [
    "police investigating strange discovery",
    "missing person last seen at night",
    "abandoned vehicle police report",
    "unexplained incident local police",
]

FALLBACK_SCRIPT = (
    "A car was found running with no one inside. "
    "The doors were locked. The lights were on. "
    "Police said the owner never came back. "
    "No one nearby saw anything unusual. "
    "The scene still does not make sense."
)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def fetch_context():
    q = random.choice(NEWS_QUERIES)
    try:
        r = requests.get(
            f"https://news.google.com/rss/search?q={q}",
            timeout=15
        )
        if r.status_code == 200 and r.text:
            titles = re.findall(r"<title>(.*?)</title>", r.text)
            return " ".join(titles[1:4])
    except:
        pass
    return "police investigating an unexplained incident"


def generate_script(context):
    prompt = f"""
Write a short true-crime narration for a YouTube Short.

Rules:
- Calm, factual tone
- Visual language
- No hype words
- No questions at the end
- Keep it concise and unsettling

Context:
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You write concise, high-retention crime narrations."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 200,
    }

    try:
        r = requests.post(
            OPENROUTER_URL,
            headers=HEADERS,
            json=payload,
            timeout=60,
        )
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"].strip()
            text = re.sub(r"\s+", " ", text)
            return text
    except:
        pass

    return None


def main():
    if not API_KEY:
        print("❌ Missing API key. Using fallback.")
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(FALLBACK_SCRIPT)
        return

    context = fetch_context()
    script = generate_script(context)

    if script and len(script.split()) >= 40:
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(script)
        print("✅ Script generated successfully.")
    else:
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(FALLBACK_SCRIPT)
        print("⚠️ Fallback used (generation failed).")


if __name__ == "__main__":
    main()

