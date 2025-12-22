import os
import json
import hashlib
import random
import time
import requests

OUT_SCRIPT = "script.txt"
USED_TOPICS_FILE = "used_topics.json"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

NEWS_QUERIES = [
    "unsolved crime investigation",
    "missing person case",
    "cold case reopened",
    "unidentified body found",
]

def load_used():
    if os.path.exists(USED_TOPICS_FILE):
        return set(json.load(open(USED_TOPICS_FILE, "r")))
    return set()

def save_used(used):
    json.dump(sorted(list(used)), open(USED_TOPICS_FILE, "w"), indent=2)

def hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def fetch_news_text():
    q = random.choice(NEWS_QUERIES)
    url = f"https://news.google.com/rss/search?q={q}"
    r = requests.get(url, timeout=15)
    if r.status_code != 200 or not r.text:
        return None
    return r.text[:3000]

def generate_script(raw):
    prompt = f"""
Write a 40-second true-crime documentary script.

Rules:
- Mention a person, year, and location
- Calm, investigative tone
- No sensational language
- No supernatural elements
- End with unresolved facts
- One short hook at the start

Source material:
{raw}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 350,
    }

    for _ in range(3):
        r = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=60)
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"].strip()
            wc = len(text.split())
            if 95 <= wc <= 130:
                return text
        time.sleep(2)

    return (
        "In 2015, investigators examined the disappearance of a man last seen "
        "near an industrial road outside the city. Records were incomplete, "
        "and surveillance footage was missing. The timeline remains unclear. "
        "What detail was never accounted for?"
    )

def main():
    used = load_used()

    for _ in range(5):
        raw = fetch_news_text()
        if not raw:
            continue

        h = hash_text(raw)
        if h in used:
            continue

        script = generate_script(raw)
        open(OUT_SCRIPT, "w", encoding="utf-8").write(script)

        used.add(h)
        save_used(used)

        print("[OK] Script generated")
        return

    raise RuntimeError("No new topics available")

if __name__ == "__main__":
    main()
