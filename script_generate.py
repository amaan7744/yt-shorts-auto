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
    "police investigating disappearance",
    "missing person last seen late night",
    "police report unexplained event",
    "unidentified person police investigation",
]

# ---------------- SAFE FALLBACK (STAKES-FIRST) ----------------
FALLBACK_SCRIPT = """This person vanished in less than seven minutes.
That means whatever happened started immediately.
Their phone stopped moving while they were still outside.
That only happens when a device is shut off or taken.
Police later confirmed this occurred late at night.
Nearby cameras showed no one approaching or leaving.
No witnesses reported anything unusual.
Investigators found no signs of a struggle.
Police still do not know why the evidence contradicts itself."""

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
    return " ".join(titles[1:4] + desc[1:4])[:1400]

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
    Final retention enforcement:
    - No questions
    - Guaranteed early stakes
    - Hard contradiction ending
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Remove all questions
    lines = [l.replace("?", "") for l in lines]

    # Force contradiction ending
    if lines:
        lines[-1] = "Police still do not know why the evidence contradicts itself."

    return "\n".join(lines)

def generate_script(context: str):
    prompt = f"""
Write a HIGH-RETENTION true crime script for a YouTube Short (28–35 seconds).

NON-NEGOTIABLE RULES:
1. Line 1 MUST describe a visual impossibility or abnormal event.
   - No dates, no names, no locations.
2. Line 2 MUST introduce an irreversible consequence or immediate risk.
   - Example logic: loss of time, loss of control, evidence compromised.
3. Line 3 MUST explain why this should not normally happen.
4. Dates, locations, or police confirmation may appear ONLY after line 3.
5. Every 2–3 lines must remove a normal explanation.
6. Introduce ONE detail early (within first 8–10 seconds) that does not belong.
7. No filler words (unsolved, mysterious, tragic).
8. Short sentences only (max 11 words).
9. Calm, factual tone. No dramatic language.
10. End with a contradiction, NOT a question.
11. 85–100 words total.

STRUCTURE (STRICT):
- Abnormal event
- Immediate stakes
- Implication
- Authority/context
- Escalation
- Contradiction ending

Context (facts only, adapt carefully):
{context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write high-retention true crime scripts for YouTube Shorts. "
                    "You prioritize early stakes over explanation."
                )
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        "temperature": 0.45,
        "max_tokens": 400,
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
                if 85 <= wc <= 100:
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
            print("✅ High-retention script generated.")
            return

    # Guaranteed fallback
    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(FALLBACK_SCRIPT + "\n")

    used.add(hash_text(FALLBACK_SCRIPT))
    save_used(used)
    print("⚠️ Used safe fallback.")

if __name__ == "__main__":
    main()
