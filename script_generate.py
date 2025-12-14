#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import hashlib
import requests

# ---------------- CONFIG ---------------- #

USED_TOPICS_FILE = "used_topics.json"
SCRIPT_OUT = "script.txt"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    print("[FATAL] DEEPSEEK_API_KEY missing", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Wikipedia public-domain style list pages (safe)
WIKI_SOURCES = [
    "List_of_unsolved_murder_cases_in_the_United_States",
    "List_of_missing_persons_cases",
    "List_of_people_who_disappeared_mysteriously",
]

REDDIT_SOURCES = [
    "truecrime",
    "UnresolvedMysteries",
    "ColdCases",
]

# ---------------- UTIL ---------------- #

def load_used_topics():
    if not os.path.exists(USED_TOPICS_FILE):
        return set()
    try:
        with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_used_topics(used):
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)

def topic_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# ---------------- FETCH CONTENT ---------------- #

def fetch_content(source: str) -> str:
    """
    Always returns text.
    Never throws.
    """

    try:
        # -------- Wikipedia -------- #
        if source.startswith("wiki:"):
            title = source.split(":", 1)[1]
            url = (
                "https://en.wikipedia.org/w/api.php"
                "?action=query&prop=extracts&format=json"
                f"&titles={title}&explaintext=1"
            )

            r = requests.get(url, timeout=15)
            if r.status_code != 200 or not r.text.strip():
                raise RuntimeError("Wikipedia empty response")

            j = r.json()
            pages = j.get("query", {}).get("pages", {})
            page = next(iter(pages.values()), {})
            text = page.get("extract", "").strip()

            if not text:
                raise RuntimeError("Wikipedia extract empty")

            return text[:5000]

        # -------- Reddit -------- #
        if source.startswith("reddit:"):
            sub = source.split(":", 1)[1]
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=25"

            r = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )

            if r.status_code != 200 or not r.text.strip():
                raise RuntimeError("Reddit empty response")

            j = r.json()
            posts = j.get("data", {}).get("children", [])

            bodies = [
                p["data"].get("selftext", "").strip()
                for p in posts
                if p.get("data", {}).get("selftext")
                and len(p["data"]["selftext"].split()) > 80
            ]

            if not bodies:
                raise RuntimeError("No usable Reddit posts")

            return random.choice(bodies)[:5000]

        # -------- Google News RSS -------- #
        if source == "news":
            import feedparser

            feed = feedparser.parse(
                "https://news.google.com/rss/search"
                "?q=unsolved+crime&hl=en-US&gl=US&ceid=US:en"
            )

            if not feed.entries:
                raise RuntimeError("News feed empty")

            entry = random.choice(feed.entries)
            text = f"{entry.title}. {entry.get('summary', '')}".strip()

            if not text:
                raise RuntimeError("News entry empty")

            return text[:3000]

    except Exception as e:
        print(f"[WARN] fetch_content failed ({source}): {e}", file=sys.stderr)

    # -------- HARD FALLBACK -------- #
    return (
        "Investigators documented a routine evening that ended without explanation. "
        "Limited evidence was recovered, timelines remained incomplete, and no clear "
        "suspect was identified. The case remains open."
    )

# ---------------- SOURCE PICKER ---------------- #

def pick_source(used_hashes):
    candidates = []

    for w in WIKI_SOURCES:
        candidates.append(f"wiki:{w}")

    for r in REDDIT_SOURCES:
        candidates.append(f"reddit:{r}")

    candidates.append("news")

    random.shuffle(candidates)

    for src in candidates:
        if topic_hash(src) not in used_hashes:
            return src

    # If all sources used, still rotate content (never block)
    return random.choice(candidates)

# ---------------- SCRIPT GENERATION ---------------- #

def generate_script(raw_text: str) -> str:
    prompt = f"""
Write a 30–40 second true-crime short script.

Style:
- Calm
- Neutral
- Investigative
- Professional documentary tone

Rules:
- Begin with a simple, quiet real-world moment.
- Describe a disappearance or crime factually.
- Mention only realistic clues (time, place, missing evidence).
- No drama, no sensational language.
- No emotional manipulation.
- End with one concise unresolved question.
- Do NOT reference Wikipedia, Reddit, news, or sources.
- Do NOT repeat earlier examples.

Source material:
{raw_text[:2000]}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 320,
    }

    for attempt in range(3):
        try:
            r = requests.post(
                OPENROUTER_URL,
                headers=HEADERS,
                json=payload,
                timeout=60,
            )

            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")

            j = r.json()
            text = j["choices"][0]["message"]["content"].strip()

            words = len(text.split())
            if 95 <= words <= 130:
                return text

            print(f"[WARN] Word count {words} out of range, retrying…", file=sys.stderr)
            time.sleep(2)

        except Exception as e:
            print(f"[WARN] LLM attempt failed: {e}", file=sys.stderr)
            time.sleep(2)

    # FINAL fallback (never fail)
    return (
        "It began as a routine walk along a quiet road. "
        "Witnesses later reported nothing unusual at the time. "
        "A phone was recovered, but no clear timeline could be established. "
        "No surveillance footage explained what happened next. "
        "The investigation remains unresolved. "
        "What was missed that night?"
    )

# ---------------- MAIN ---------------- #

def main():
    used = load_used_topics()

    source = pick_source(used)
    raw = fetch_content(source)
    script = generate_script(raw)

    with open(SCRIPT_OUT, "w", encoding="utf-8") as f:
        f.write(script)

    used.add(topic_hash(source))
    save_used_topics(used)

    print("[OK] Script generated successfully.")
    print(f"[INFO] Source used: {source}")

if __name__ == "__main__":
    main()

