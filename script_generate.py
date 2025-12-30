#!/usr/bin/env python3
import os
import json
import hashlib
import random
import requests
import re
import time

# ---------------- FILES ----------------
OUT_SCRIPT = "script.txt"
OUT_IMAGE_PROMPTS = "image_prompts.json"
USED_TOPICS_FILE = "used_topics.json"

# ---------------- API ----------------
API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat"  # stable with OpenRouter

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ---------------- LIMITS ----------------
MIN_WORDS = 65   # ~22 sec
MAX_WORDS = 95   # ~30 sec

# ---------------- SOURCES ----------------
WIKI_PAGES = [
    "List_of_people_who_disappeared",
    "Unsolved_deaths",
    "Unidentified_decedents"
]

REDDIT_URL = "https://www.reddit.com/r/UnresolvedMysteries/top.json?t=year&limit=50"

NEWS_QUERIES = [
    "police found abandoned vehicle",
    "missing person last seen night police",
    "unidentified person police investigation",
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

# ---------------- FETCH CONTEXT ----------------
def fetch_wikipedia():
    page = random.choice(WIKI_PAGES)
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page}"
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        return r.json().get("extract")
    return None

def fetch_reddit():
    r = requests.get(
        REDDIT_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15
    )
    if r.status_code != 200:
        return None
    posts = r.json()["data"]["children"]
    post = random.choice(posts)["data"]
    return f"{post['title']} {post.get('selftext','')}"

def fetch_news():
    q = random.choice(NEWS_QUERIES)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        return r.text[:1500]
    return None

def fetch_context():
    sources = [fetch_wikipedia, fetch_reddit, fetch_news]
    random.shuffle(sources)
    for src in sources:
        text = src()
        if text and len(text) > 250:
            return clean(text)
    return None

# ---------------- SCRIPT GENERATION ----------------
def generate_script(context: str):
    prompt = f"""
Write a YouTube Shorts TRUE CRIME script.

NON-NEGOTIABLE RULES:
- First sentence MUST begin with:
  • a DATE or
  • an EXACT TIME or
  • a LOCATION + police confirmation
- No imagination prompts
- No greetings
- Calm documentary tone
- Short sentences
- Must feel real and specific
- 22–30 seconds spoken
- End with an unresolved contradiction
- NO questions

STRUCTURE:
1. Date/time/location hook (line 1)
2. What police found
3. Why this is abnormal
4. One detail that does not belong
5. Another detail that removes explanation
6. Contradiction ending

Context (real case reference):
{context}

Return ONLY the script text.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You write high-retention YouTube Shorts scripts."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.55,
        "max_tokens": 380,
    }

    r = requests.post(
        OPENROUTER_URL,
        headers=HEADERS,
        json=payload,
        timeout=60
    )

    if r.status_code != 200:
        return None

    text = clean(r.json()["choices"][0]["message"]["content"])
    wc = len(text.split())

    if MIN_WORDS <= wc <= MAX_WORDS:
        return text

    return None

# ---------------- IMAGE PROMPTS ----------------
def build_image_prompts(script: str):
    return [
        "abandoned car night headlights on",
        "empty residential street night",
        "police evidence scene night",
        "object left behind ground night",
        "foggy road night no people"
    ]

# ---------------- MAIN ----------------
def main():
    used = load_used()

    for _ in range(8):
        context = fetch_context()
        if not context:
            continue

        h = hash_text(context[:300])
        if h in used:
            continue

        script = generate_script(context)
        if not script:
            continue

        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(script)

        prompts = build_image_prompts(script)
        with open(OUT_IMAGE_PROMPTS, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=2)

        used.add(h)
        save_used(used)

        print("✅ Script + image prompts generated")
        return

    raise SystemExit("❌ Unable to generate valid script after multiple real sources")

if __name__ == "__main__":
    main()

