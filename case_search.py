#!/usr/bin/env python3
"""
Case Search + AI Enrichment (PRODUCTION – HARDENED)

OUTPUT GUARANTEES:
- full_name
- location (City, State, United States)
- date (human readable)
- time (exact or approximate)
- summary
- key_detail
- official_story

If ANY field cannot be confidently inferred → case is discarded.
Pipeline NEVER crashes due to source failure.
"""

import json
import os
import re
import hashlib
import random
import requests
from pathlib import Path
from datetime import datetime
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
    "User-Agent": "Mozilla/5.0 (CrimeCaseFinder/5.0; +https://example.com)"
}

MIN_TEXT_LEN = 120
MAX_TEXT_LEN = 1200

GOOGLE_NEWS_RSS = [
    "https://news.google.com/rss/search?q=death+investigation+United+States",
    "https://news.google.com/rss/search?q=body+found+United+States",
    "https://news.google.com/rss/search?q=unsolved+death+United+States",
]

REDDIT_ENDPOINTS = [
    "https://www.reddit.com/r/TrueCrime/.json?limit=50",
    "https://www.reddit.com/r/UnresolvedMysteries/.json?limit=50",
]

WIKI_BACKUP = "https://en.wikipedia.org/wiki/List_of_unsolved_deaths"

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
# RAW CASE FETCHERS (FAIL-SAFE)
# ==================================================

def fetch_google_news():
    try:
        feed = random.choice(GOOGLE_NEWS_RSS)
        resp = requests.get(feed, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        random.shuffle(items)

        for item in items:
            text = clean(item.description.text if item.description else "")
            if len(text) >= MIN_TEXT_LEN:
                return text
    except Exception:
        return None

    return None

def fetch_reddit():
    url = random.choice(REDDIT_ENDPOINTS)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None

        try:
            data = resp.json()
        except Exception:
            return None

        posts = data.get("data", {}).get("children", [])
        random.shuffle(posts)

        for p in posts:
            body = p.get("data", {}).get("selftext", "")
            text = clean(body)
            if len(text) >= MIN_TEXT_LEN:
                return text

    except Exception:
        return None

    return None

def fetch_wikipedia():
    try:
        resp = requests.get(WIKI_BACKUP, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("li")
        random.shuffle(items)

        for li in items:
            text = clean(li.get_text())
            if len(text) >= MIN_TEXT_LEN:
                return text
    except Exception:
        return None

    return None

# ==================================================
# AI ENRICHMENT (STRICT SCHEMA)
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

def enrich_case(client: Groq, raw_text: str) -> dict | None:
    prompt = f"""
You are a crime data extraction system.

TASK:
Convert the raw text below into STRICT JSON.

RULES:
- US cases ONLY
- No guessing
- If time is unknown, use approximate wording (e.g. "late night")
- If ANY required field cannot be inferred, output null

REQUIRED JSON SCHEMA:
{{
  "full_name": "",
  "location": "City, State, United States",
  "date": "Month Day, Year",
  "time": "Exact or approximate",
  "summary": "",
  "key_detail": "",
  "official_story": ""
}}

RAW TEXT:
\"\"\"
{raw_text[:MAX_TEXT_LEN]}
\"\"\"

Return ONLY valid JSON or null.
"""

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_completion_tokens=500,
        )
    except Exception:
        return None

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

    if "United States" not in data["location"]:
        return None

    return data

# ==================================================
# MAIN
# ==================================================

def main():
    used = load_used()
    client = init_client()

    sources = [fetch_google_news, fetch_reddit, fetch_wikipedia]

    for _ in range(40):
        raw = None
        random.shuffle(sources)

        for src in sources:
            raw = src()
            if raw:
                break

        if not raw:
            continue

        raw_fp = fingerprint(raw)
        if raw_fp in used:
            continue

        enriched = enrich_case(client, raw)
        if not enriched:
            continue

        case_fp = fingerprint(
            f"{enriched['full_name']}|{enriched['location']}|{enriched['date']}|{enriched['time']}"
        )

        if case_fp in used:
            continue

        OUT_FILE.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
        used.add(case_fp)
        save_used(used)

        print("✅ Case selected, enriched, and locked")
        return

    raise RuntimeError("❌ No valid case found after exhaustive search")

if __name__ == "__main__":
    main()
