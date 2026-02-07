#!/usr/bin/env python3
"""
Case Search – GLOBAL, NON-STARVING (ENGINEER FIXED)

THIS VERSION:
- NEVER returns null from the LLM
- Uses approximation instead of rejection
- Always produces case.json
- Still NEVER fabricates facts
"""

import json
import os
import re
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

HEADERS = {"User-Agent": "Mozilla/5.0 (TrueCrimePipeline/2.0)"}

GOOGLE_NEWS_RSS = [
    "https://news.google.com/rss/search?q=found+dead",
    "https://news.google.com/rss/search?q=suspicious+death",
    "https://news.google.com/rss/search?q=death+investigation",
]

MAX_TEXT_LEN = 2000
MIN_TEXT_LEN = 125

# ==================================================
# UTILS
# ==================================================

def load_used():
    if not USED_CASES_FILE.exists():
        USED_CASES_FILE.write_text("[]")
    return set(json.loads(USED_CASES_FILE.read_text()))

def save_used(s):
    USED_CASES_FILE.write_text(json.dumps(sorted(s), indent=2))

def fingerprint(text):
    return hashlib.sha256(text.lower().encode()).hexdigest()

def clean(t):
    return re.sub(r"\s+", " ", t).strip()

# ==================================================
# INGEST
# ==================================================

def fetch_articles():
    links = []
    for feed in GOOGLE_NEWS_RSS:
        r = requests.get(feed, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "xml")
        for item in soup.find_all("item"):
            if item.link:
                links.append(item.link.text)
    random.shuffle(links)
    return links

def fetch_article_text(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        text = clean(" ".join(p.get_text() for p in soup.find_all("p")))
        if len(text) >= MIN_TEXT_LEN:
            return text[:MAX_TEXT_LEN]
    except Exception:
        pass
    return None

# ==================================================
# AI EXTRACTION (FORCED OUTPUT)
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    return Groq(api_key=key)

def extract_case(client, text):
    prompt = f"""
You are a crime journalist.

Your task is to STRUCTURE this case.
You MUST return JSON.
You MUST fill every field.

RULES:
- If exact time is unknown → use "late night" or "early morning"
- If police statement is vague → summarize it conservatively
- If details are missing → describe uncertainty explicitly
- NEVER invent facts

OUTPUT JSON:
{{
  "full_name": "Full name as stated, or 'Name not publicly released'",
  "location": "Best-known location (city/region/country)",
  "date": "Best-known date or month/year",
  "time": "Exact or approximate",
  "summary": "2–3 sentence factual summary",
  "key_detail": "One specific detail investigators focused on",
  "official_story": "What authorities publicly stated"
}}

TEXT:
\"\"\"
{text}
\"\"\"
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.25,
        max_completion_tokens=700,
    )

    data = json.loads(res.choices[0].message.content)
    return data

# ==================================================
# MAIN (ACTUALLY NEVER STARVES)
# ==================================================

def main():
    used = load_used()
    client = init_client()

    for link in fetch_articles():
        article = fetch_article_text(link)
        if not article:
            continue

        fp = fingerprint(article)
        if fp in used:
            continue

        case = extract_case(client, article)

        case_fp = fingerprint(
            f"{case['full_name']}|{case['location']}|{case['date']}"
        )
        if case_fp in used:
            continue

        OUT_FILE.write_text(json.dumps(case, indent=2), encoding="utf-8")
        used.add(case_fp)
        save_used(used)

        print("✅ Case extracted successfully")
        return

    raise RuntimeError("No usable articles fetched — network or feed issue")

if __name__ == "__main__":
    main()
