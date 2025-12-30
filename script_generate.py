#!/usr/bin/env python3
import os
import json
import random
import time
import hashlib
import requests
import re
from datetime import datetime, timedelta

OUT_SCRIPT = "script.txt"
USED_FILE = "used_scripts.json"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

HOOKS = [
    "If this happened outside your house, you would panic.",
    "Imagine stepping outside at night and never coming back.",
    "This started like a normal night, and ended without answers.",
    "Police say this case could happen to anyone.",
    "Nothing about this night seemed unusual at first.",
]

US_LOCATIONS = [
    "Ohio", "Texas", "Florida", "California",
    "Pennsylvania", "Illinois", "Georgia",
    "Arizona", "Michigan", "New York"
]

NEWS_QUERIES = [
    "police responded late night call",
    "missing person last seen night",
    "abandoned vehicle police report",
    "unusual police investigation night",
]

# ---------------- UTILS ----------------

def load_used():
    if os.path.exists(USED_FILE):
        try:
            return set(json.load(open(USED_FILE, "r")))
        except:
            return set()
    return set()

def save_used(used):
    with open(USED_FILE, "w") as f:
        json.dump(sorted(list(used)), f, indent=2)

def hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def random_date():
    days_ago = random.randint(365, 3650)
    d = datetime.now() - timedelta(days=days_ago)
    return d.strftime("%B %d, %Y")

def fetch_context():
    q = random.choice(NEWS_QUERIES)
    try:
        r = requests.get(
            f"https://news.google.com/rss/search?q={q}",
            timeout=15
        )
        if r.status_code == 200:
            titles = re.findall(r"<title>(.*?)</title>", r.text)
            return " ".join(titles[1:4])
    except:
        pass
    return "police investigating a late night disappearance"

# ---------------- GENERATION ----------------

def generate_ai_script(context, hook, date, place):
    prompt = f"""
Write a TRUE CRIME YouTube Short narration (22–30 seconds).

MANDATORY:
- First line EXACTLY this hook:
"{hook}"
- Second line MUST include this date and location:
"On {date}, police in {place} responded to a late-night call."
- Mention a man or woman
- Short sentences
- Calm, serious tone
- End unresolved
- Make the viewer imagine it happening to them

Context:
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You write high-retention true crime Shorts."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.65,
        "max_tokens": 240,
    }

    r = requests.post(
        OPENROUTER_URL,
        headers=HEADERS,
        json=payload,
        timeout=60,
    )

    if r.status_code == 200:
        text = r.json()["choices"][0]["message"]["content"].strip()
        return re.sub(r"\s+", " ", text)

    return None

def procedural_fallback(hook, date, place):
    subject = random.choice(["a man", "a woman"])
    return (
        f"{hook} "
        f"On {date}, police in {place} responded to a late-night call. "
        f"{subject.capitalize()} had stepped outside minutes earlier. "
        f"Their car was found running with the lights on. "
        f"The doors were locked. "
        f"Their phone was still inside. "
        f"No one nearby saw anything. "
        f"The case has never been explained."
    )

# ---------------- MAIN ----------------

def main():
    used = load_used()

    hook = random.choice(HOOKS)
    date = random_date()
    place = random.choice(US_LOCATIONS)
    context = fetch_context()

    for _ in range(3):
        script = generate_ai_script(context, hook, date, place)
        if not script or len(script.split()) < 55:
            continue

        h = hash_text(script)
        if h in used:
            continue

        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(script)

        used.add(h)
        save_used(used)
        print("✅ Hook-optimized script generated.")
        return

    fallback = procedural_fallback(hook, date, place)
    h = hash_text(fallback)

    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(fallback)

    used.add(h)
    save_used(used)
    print("⚠️ Used hook-optimized fallback.")

if __name__ == "__main__":
    main()
