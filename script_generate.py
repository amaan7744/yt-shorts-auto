#!/usr/bin/env python3
import os
import json
import random
import hashlib
import requests
import re
import time
from datetime import datetime

# ---------------- FILES ----------------
OUT_SCRIPT = "script.txt"
OUT_IMAGE_PROMPTS = "image_prompts.json"
USED_TOPICS_FILE = "used_topics.json"

# ---------------- API ----------------
API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ---------------- SOURCES ----------------
NEWS_QUERIES = [
    "police found abandoned vehicle",
    "missing person last seen night",
    "unidentified body police investigation",
]

LOCATIONS = [
    "Ohio", "Texas", "Florida", "California", "Pennsylvania",
    "Illinois", "New York", "Michigan", "Georgia"
]

# ---------------- HELPERS ----------------
def clean(text: str) -> str:
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("*", "").replace("#", "")
    return text.strip()

def load_used():
    if os.path.exists(USED_TOPICS_FILE):
        try:
            return set(json.load(open(USED_TOPICS_FILE)))
        except:
            return set()
    return set()

def save_used(used):
    with open(USED_TOPICS_FILE, "w") as f:
        json.dump(sorted(list(used)), f, indent=2)

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

# ---------------- CONTEXT ----------------
def fetch_news_context():
    q = random.choice(NEWS_QUERIES)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.text[:1200]
    except:
        pass
    return "police investigation at night involving an unexplained disappearance"

# ---------------- SCRIPT ----------------
def generate_raw_script(context: str):
    prompt = f"""
Write a short true crime narration for YouTube Shorts.
Tone: calm, factual, serious.
No questions.
No fluff.
Short sentences.

Context:
{context}
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You write realistic true crime narrations."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    try:
        r = requests.post(
            OPENROUTER_URL,
            headers=HEADERS,
            json=payload,
            timeout=60
        )
        if r.status_code == 200:
            return clean(r.json()["choices"][0]["message"]["content"])
    except:
        pass

    return None

# ---------------- ENFORCE HOOK ----------------
def enforce_hook(script: str):
    date = datetime.now().strftime("%B %d, %Y")
    location = random.choice(LOCATIONS)

    first_line = f"On {date}, police in {location} reported something unusual."
    lines = script.split(". ")
    body = ". ".join(lines[:6])

    final = f"{first_line} {body} Police say the timeline still does not make sense."
    return final

# ---------------- IMAGE PROMPTS ----------------
def build_image_prompts():
    return [
        "abandoned car night headlights on",
        "empty residential street night",
        "police tape evidence scene night",
        "object left behind ground night",
        "foggy road night no people"
    ]

# ---------------- MAIN ----------------
def main():
    used = load_used()
    context = fetch_news_context()

    raw = generate_raw_script(context)
    if not raw:
        raw = "Police responded to a nighttime incident involving a missing person."

    script = enforce_hook(raw)
    h = hash_text(script)

    # Prevent exact repetition
    if h in used:
        script += " Investigators later confirmed no clear explanation was found."

    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(script)

    with open(OUT_IMAGE_PROMPTS, "w", encoding="utf-8") as f:
        json.dump(build_image_prompts(), f, indent=2)

    used.add(h)
    save_used(used)

    print("✅ Script and image prompts written successfully")

if __name__ == "__main__":
    main()

