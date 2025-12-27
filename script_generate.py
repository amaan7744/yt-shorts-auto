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
    "missing person last seen at night",
    "unsolved police case remains open",
    "unidentified person investigation police",
]

# ---------------- SAFE FALLBACK (RETENTION-FIRST) ----------------
FALLBACK_SCRIPT = """This person vanished in less than seven minutes.
Their phone stopped moving while they were still outside.
That should not happen unless the phone was shut off or taken.
Police later confirmed this occurred late at night.
Nearby cameras recorded nothing useful.
No witnesses came forward.
Friends said there was no reason to leave.
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
    return " ".join(titles[1:4] + desc[1:4])[:1500]

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
    Hard safety + retention enforcement:
    - No questions
    - Hard contradiction ending
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Remove questions entirely
    lines = [l.replace("?", "") for l in lines]

    # Force contradiction ending
    if lines:
        lines[-1] = "Police still do not know why the evidence contradicts itself."

    return "\n".join(lines)

def generate_script(context: str) -> str | None:
    prompt = f"""
Write a HIGH-RETENTION true crime script for a YouTube Short (28–35 seconds).

NON-NEGOTIABLE RULES:
1. Line 1 MUST describe a visual impossibility or abnormal event.
   - No dates, no names, no locations in line 1.
2. Line 2 MUST explain why this violates logic or safety.
3. Dates, locations, or police confirmation may appear ONLY after line 2.
4. Every 2–3 lines must remove a normal explanation.
   - Use implication language like:
     "That would only happen if..."
     "Normally this means..., but..."
5. Introduce ONE detail early (within first 10 seconds) that clearly does not belong.
6. No filler words (unsolved, mysterious, tragic).
7. Short sentences only (max 11 words).
8. No dramatic language or exaggeration.
9. End with a contradiction, NOT a question.
10. 85–105 words total.

STRUCTURE:
- Abnormal event
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
                    "You write suspense-driven, implication-based true crime "
                    "scripts optimized for YouTube Shorts retention."
                )
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        "temperature": 0.5,
        "max_tokens": 420,
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
                if 85 <= wc <= 110:
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

    # Fallback (guaranteed safe)
    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(FALLBACK_SCRIPT + "\n")

    used.add(hash_text(FALLBACK_SCRIPT))
    save_used(used)
    print("⚠️ Used safe fallback.")

if __name__ == "__main__":
    main()
