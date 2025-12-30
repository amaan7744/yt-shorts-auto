#!/usr/bin/env python3
import os
import random
import time
import requests
import re

OUT_SCRIPT = "script.txt"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

NEWS_QUERIES = [
    "police responded late night call strange scene",
    "missing person case investigation night",
    "abandoned vehicle found police report",
    "last seen leaving home night police",
]

FALLBACK_SCRIPT = (
    "On October 14, 2019, police in Ohio responded to a late-night call. "
    "A man had left his house just minutes earlier. "
    "His car was found running with the lights on. "
    "The doors were locked. "
    "His phone was still inside. "
    "He was never seen again."
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
    return "police investigating a late night disappearance"


def generate_script(context):
    prompt = f"""
Write a TRUE CRIME YouTube Short script (22–30 seconds).

STRICT REQUIREMENTS:
- Start with a real date and location
- Mention one real person or “a man / woman”
- Short sentences
- Calm, serious tone
- Make the viewer imagine it happening to them
- No hype words
- End unresolved

STRUCTURE:
1. Date + place (first line)
2. Who and what happened
3. Escalation
4. Evidence that doesn't fit
5. Open ending

Context:
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You write realistic, credible true crime narrations for YouTube Shorts."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        "temperature": 0.6,
        "max_tokens": 220,
    }

    try:
        r = requests.post(
            OPENROUTER_URL,
            headers=HEADERS,
            json=payload,
            timeout=60
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
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(FALLBACK_SCRIPT)
        return

    context = fetch_context()
    script = generate_script(context)

    # Sanity check ONLY (no strict word gates)
    if script and len(script.split()) >= 55:
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(script)
        print("✅ Script generated.")
    else:
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(FALLBACK_SCRIPT)
        print("⚠️ Used fallback.")


if __name__ == "__main__":
    main()
