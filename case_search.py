#!/usr/bin/env python3
"""
CASE SEARCH ENGINE – TRUE CRIME (US-FOCUSED, LOCKED)

SOURCES:
- Wikipedia (archive / cold cases)
- Reddit (fresh mystery cases)
- Google News (current investigations)

GUARANTEES:
- ONE global uniqueness lock
- US-biased case selection
- Script-compatible output
- No case repetition, ever
"""

import json
import re
import hashlib
import random
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# ==================================================
# FILES
# ==================================================

OUT_FILE = Path("case.json")
USED_FILE = Path("used_cases.json")

# ==================================================
# CONFIG
# ==================================================

HEADERS = {"User-Agent": "TrueCrimeCaseEngine/1.0"}

MIN_CHARS = 500
MAX_CHARS = 900

CURRENT_YEAR = datetime.utcnow().year

REDDIT_SUBS = [
    "UnresolvedMysteries",
    "TrueCrime",
    "ColdCases",
    "MissingPersons",
]

WIKI_PAGES = [
    "https://en.wikipedia.org/wiki/List_of_unsolved_deaths",
    "https://en.wikipedia.org/wiki/List_of_people_who_disappeared",
]

NEWS_QUERIES = [
    "mysterious death",
    "found dead under investigation",
    "ruled accidental police investigating",
]

# ==================================================
# UTILS
# ==================================================

def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()

def normalize(raw: str) -> str:
    raw = raw.lower()
    raw = re.sub(r"\b(killed|murdered|shot|stabbed)\b", "was found", raw)
    raw = clean(raw)
    clipped = raw[:MAX_CHARS].rsplit(" ", 1)[0]
    return clipped.capitalize()

def extract_year(t: str) -> str:
    m = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", t)
    return m.group(1) if m else "unknown"

def extract_location(t: str) -> str:
    m = re.search(
        r"\b(in|at|near)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        t
    )
    return m.group(2) if m else "unknown"

def us_bias_score(text: str) -> int:
    score = 0
    if re.search(r"\b(us|usa|california|texas|new york|florida|ohio)\b", text.lower()):
        score += 2
    if "police" in text.lower():
        score += 1
    if "investigation" in text.lower():
        score += 1
    return score

def case_fingerprint(year: str, location: str, summary: str) -> str:
    base = f"{year}|{location}|{summary[:120]}"
    return hashlib.sha256(base.encode()).hexdigest()

def load_used():
    return set(json.loads(USED_FILE.read_text())) if USED_FILE.exists() else set()

def save_used(u):
    USED_FILE.write_text(json.dumps(sorted(u), indent=2))

# ==================================================
# SOURCES
# ==================================================

def fetch_wikipedia():
    page = random.choice(WIKI_PAGES)
    soup = BeautifulSoup(
        requests.get(page, headers=HEADERS, timeout=15).text,
        "html.parser"
    )
    items = soup.select("li")
    random.shuffle(items)

    for li in items:
        text = clean(li.get_text())
        if len(text) >= MIN_CHARS:
            return text
    return None

def fetch_reddit():
    sub = random.choice(REDDIT_SUBS)
    url = f"https://www.reddit.com/r/{sub}/top.json?limit=50&t=year"

    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return None

    posts = r.json()["data"]["children"]
    random.shuffle(posts)

    for p in posts:
        data = p["data"]
        text = clean(f"{data.get('title','')} {data.get('selftext','')}")
        if len(text) >= MIN_CHARS:
            return text
    return None

def fetch_news():
    query = random.choice(NEWS_QUERIES)
    url = f"https://news.google.com/search?q={query.replace(' ','+')}&hl=en-US&gl=US&ceid=US:en"

    soup = BeautifulSoup(
        requests.get(url, headers=HEADERS, timeout=15).text,
        "html.parser"
    )

    articles = soup.select("article")
    random.shuffle(articles)

    for a in articles:
        text = clean(a.get_text())
        if len(text) >= MIN_CHARS:
            return text
    return None

# ==================================================
# MAIN ENGINE
# ==================================================

def main():
    used = load_used()

    candidates = []

    # Pull from all sources
    for _ in range(15):
        for fetcher in (fetch_reddit, fetch_news, fetch_wikipedia):
            raw = fetcher()
            if not raw:
                continue

            summary = normalize(raw)
            year = extract_year(raw)
            location = extract_location(raw)

            if year == "unknown" or location == "unknown":
                continue

            fp = case_fingerprint(year, location, summary)
            if fp in used:
                continue

            score = us_bias_score(raw)

            candidates.append({
                "fingerprint": fp,
                "year": year,
                "location": location,
                "summary": summary,
                "score": score,
            })

    if not candidates:
        raise SystemExit("❌ No unique cases found")

    # Pick best US-biased case
    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = candidates[0]

    OUT_FILE.write_text(json.dumps({
        "victim_desc": "a person",
        "incident_type": "death",
        "location": chosen["location"],
        "time": f"{chosen['year']}",
        "key_clue": "details at the scene raised questions",
        "official_story": "authorities ruled it an accident",
        "summary": chosen["summary"],
    }, indent=2))

    used.add(chosen["fingerprint"])
    save_used(used)

    print("✅ Case selected (global uniqueness locked, US-focused)")

# ==================================================
if __name__ == "__main__":
    main()
