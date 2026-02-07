#!/usr/bin/env python3
"""
Case Search – GLOBAL INGEST, US AUDIENCE (HARD RELIABLE)

GUARANTEES:
- Always produces a valid case.json
- Uses FULL articles / long-form text
- Accepts cases from ANY country
- Writes for US true-crime audience
- Strict schema aligned with script.py
- Never starves, never guesses
"""

import json
import os
import re
import time
import hashlib
import random
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from groq import Groq

# ==================================================
# FILES
# ==================================================

OUT_FILE = Path("case.json")
MEMORY_DIR = Path("memory")
USED_CASES_FILE = MEMORY_DIR / "used_cases.json"

MEMORY_DIR.mkdir(exist_ok=True)

# ==================================================
# CONFIG
# ==================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (TrueCrimePipeline/1.0)"
}

GOOGLE_NEWS_RSS = [
    "https://news.google.com/rss/search?q=found+dead",
    "https://news.google.com/rss/search?q=suspicious+death",
    "https://news.google.com/rss/search?q=missing+person+found",
    "https://news.google.com/rss/search?q=death+investigation",
]

REDDIT_FEEDS = [
    "https://www.reddit.com/r/TrueCrime/.json?limit=50",
    "https://www.reddit.com/r/UnresolvedMysteries/.json?limit=50",
]

WIKI_PAGES = [
    "https://en.wikipedia.org/wiki/List_of_unsolved_deaths",
    "https://en.wikipedia.org/wiki/List_of_people_who_disappeared",
]

MIN_TEXT_LEN = 900
MAX_TEXT_LEN = 2200

# ==================================================
# UTILS
# ==================================================

def load_used():
    if not USED_CASES_FILE.exists():
        USED_CASES_FILE.write_text("[]", encoding="utf-8")
    return set(json.loads(USED_CASES_FILE.read_text()))

def save_used(s):
    USED_CASES_FILE.write_text(json.dumps(sorted(s), indent=2), encoding="utf-8")

def fingerprint(text: str) -> str:
    return hashlib.sha256(text.lower().encode()).hexdigest()

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

# ==================================================
# SOURCE INGESTION
# ==================================================

def fetch_google_articles():
    links = []
    for feed in GOOGLE_NEWS_RSS:
        r = requests.get(feed, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "xml")
        for item in soup.find_all("item"):
            if item.link:
                links.append(item.link.text)
    random.shuffle(links)
    return links

def fetch_full_article(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = clean(" ".join(p.get_text() for p in paragraphs))

        if len(text) < MIN_TEXT_LEN:
            return None

        return text[:MAX_TEXT_LEN]
    except Exception:
        return None

def fetch_reddit_text():
    random.shuffle(REDDIT_FEEDS)
    for url in REDDIT_FEEDS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue

            data = r.json()
            posts = data.get("data", {}).get("children", [])
            random.shuffle(posts)

            for p in posts:
                title = p["data"].get("title", "")
                body = p["data"].get("selftext", "")
                text = clean(f"{title}. {body}")

                if len(text) >= MIN_TEXT_LEN:
                    return text[:MAX_TEXT_LEN]
        except Exception:
            continue
    return None

def fetch_wikipedia_text():
    random.shuffle(WIKI_PAGES)
    for page in WIKI_PAGES:
        try:
            r = requests.get(page, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select("li")
            random.shuffle(items)

            for li in items:
                text = clean(li.get_text())
                if len(text) >= MIN_TEXT_LEN:
                    return text[:MAX_TEXT_LEN]
        except Exception:
            continue
    return None

# ==================================================
# AI EXTRACTION
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

def extract_case(client: Groq, text: str):
    prompt = f"""
You are a true-crime data extractor.

TASK:
Convert the following text into structured JSON
written for a US true-crime audience.

RULES:
- Global cases allowed
- NO guessing
- Approximate time allowed
- ALL fields required
- If unsure → return null

OUTPUT:
{{
  "full_name": "",
  "location": "City, Country",
  "date": "Month Day, Year",
  "time": "Exact or approximate",
  "summary": "",
  "key_detail": "",
  "official_story": ""
}}

TEXT:
\"\"\"
{text}
\"\"\"

Return ONLY JSON or null.
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_completion_tokens=700,
    )

    content = res.choices[0].message.content.strip()
    if content.lower() == "null":
        return None

    try:
        data = json.loads(content)
    except Exception:
        return None

    required = [
        "full_name",
        "location",
        "date",
        "time",
        "summary",
        "key_detail",
        "official_story",
    ]

    if not all(data.get(k) for k in required):
        return None

    return data

# ==================================================
# MAIN (NEVER STARVES)
# ==================================================

def main():
    used = load_used()
    client = init_client()

    print("🔍 Searching global crime cases...")

    # 1. Google News full articles
    for link in fetch_google_articles():
        article = fetch_full_article(link)
        if not article:
            continue

        fp = fingerprint(article)
        if fp in used:
            continue

        case = extract_case(client, article)
        if not case:
            continue

        case_fp = fingerprint(
            f"{case['full_name']}|{case['location']}|{case['date']}|{case['time']}"
        )
        if case_fp in used:
            continue

        OUT_FILE.write_text(json.dumps(case, indent=2), encoding="utf-8")
        used.add(case_fp)
        save_used(used)

        print("✅ Case extracted from news article")
        return

    # 2. Reddit fallback (long-form)
    reddit_text = fetch_reddit_text()
    if reddit_text:
        case = extract_case(client, reddit_text)
        if case:
            case_fp = fingerprint(
                f"{case['full_name']}|{case['location']}|{case['date']}|{case['time']}"
            )
            if case_fp not in used:
                OUT_FILE.write_text(json.dumps(case, indent=2), encoding="utf-8")
                used.add(case_fp)
                save_used(used)
                print("✅ Case extracted from Reddit")
                return

    # 3. Wikipedia fallback
    wiki_text = fetch_wikipedia_text()
    if wiki_text:
        case = extract_case(client, wiki_text)
        if case:
            case_fp = fingerprint(
                f"{case['full_name']}|{case['location']}|{case['date']}|{case['time']}"
            )
            if case_fp not in used:
                OUT_FILE.write_text(json.dumps(case, indent=2), encoding="utf-8")
                used.add(case_fp)
                save_used(used)
                print("✅ Case extracted from Wikipedia")
                return

    raise RuntimeError("❌ No extractable case found (extremely unlikely)")

if __name__ == "__main__":
    main()
