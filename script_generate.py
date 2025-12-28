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
    "police found abandoned vehicle",
    "missing person last seen night police",
    "police investigation unexplained scene",
    "unidentified incident police report",
]

# ---------------- SAFE FALLBACK (SHORT + UNEASY) ----------------
FALLBACK_SCRIPT = """A car was running in a driveway with nobody inside.
The headlights were still on.
Police later found it this way outside a quiet home.
The doors were locked.
No one nearby reported seeing anyone leave.
Inside the car, a backpack sat on the seat.
Nothing else was disturbed.
Police still cannot explain why the scene does not add up."""

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

def enforce_structure(text: str) -> str:
    """
    Retention enforcement:
    - Remove questions
    - Remove explanation language
    - Force contradiction ending
    """
    banned_phrases = [
        "normally",
        "usually",
        "this means",
        "would only happen",
        "remains open",
        "unsolved",
        "tragic",
        "mysterious",
    ]

    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if any(bad in line.lower() for bad in banned_phrases):
            continue
        line = line.replace("?", "")
        lines.append(line)

    if lines:
        lines[-1] = "Police still cannot explain why the scene does not add up."

    return "\n".join(lines)

def generate_script(context: str):
    prompt = f"""
Write a SHORT, HIGH-RETENTION true crime script for a YouTube Short.

STRICT RULES:
- 60–75 words ONLY
- No explanations of what normally happens
- No filler words (unsolved, mysterious, tragic, usually, means)
- Short sentences only (max 10 words)
- Calm, factual tone
- Do not explain logic — only state contradictions
- Introduce the strangest detail early
- End with a contradiction, not a question

STRUCTURE:
1. Abnormal scene (object-focused)
2. Something present that should not be
3. Authority confirmation (police)
4. Another conflicting detail
5. Contradiction ending

Context (facts only, adapt carefully):
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write minimalist, unease-driven true crime scripts "
                    "for YouTube Shorts. You avoid explanations."
                )
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        "temperature": 0.4,
        "max_tokens": 300,
    }

    for _ in range(3):
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
                if 60 <= wc <= 75:
                    return enforce_structure(text)
        except Exception:
            time.sleep(2)

    return None

# ---------------- MAIN ----------------
def main():
    used = load_used()

    for _ in range(5):
        raw = fetch_news()
        if not raw or len(raw) < 80:
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
            print("✅ Short unease-driven script generated.")
            return

    # Guaranteed fallback
    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(FALLBACK_SCRIPT + "\n")

    used.add(hash_text(FALLBACK_SCRIPT))
    save_used(used)
    print("⚠️ Used safe fallback.")

if __name__ == "__main__":
    main()
