#!/usr/bin/env python3
import os
import json
import hashlib
import random
import re
import datetime
import requests

OUT_CASE = "case.json"
USED_CASES = "used_cases.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (CrimeBot/1.0)"}

# ----------------------------------------
# SOURCES
# ----------------------------------------
REDDIT_ENDPOINTS = [
    "https://www.reddit.com/r/UnresolvedMysteries/new.json?limit=100",
    "https://www.reddit.com/r/TrueCrime/new.json?limit=100",
]

NEWS_QUERIES = [
    "missing person",
    "abandoned car police",
    "unidentified remains",
    "cold case reopened",
    "last seen at night",
]

CURRENT_YEAR = datetime.datetime.now().year
MIN_YEAR = 1990

# ----------------------------------------
# UTIL
# ----------------------------------------
def load_used():
    if os.path.exists(USED_CASES):
        try:
            return set(json.load(open(USED_CASES)))
        except Exception:
            return set()
    return set()

def save_used(used):
    with open(USED_CASES, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)

def fingerprint(text: str) -> str:
    return hashlib.sha256(text.lower().encode("utf-8")).hexdigest()

def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ----------------------------------------
# FETCHERS
# ----------------------------------------
def fetch_reddit_case():
    url = random.choice(REDDIT_ENDPOINTS)
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    posts = r.json()["data"]["children"]
    random.shuffle(posts)

    for p in posts:
        d = p["data"]
        title = d.get("title", "")
        body = d.get("selftext", "")
        text = clean(f"{title}. {body}")
        if len(text) > 400 and not d.get("stickied"):
            return text
    return None

def fetch_news_case():
    year = random.randint(MIN_YEAR, CURRENT_YEAR)
    query = random.choice(NEWS_QUERIES)
    q = f"{query} {year}"

    url = (
        "https://news.google.com/rss/search"
        f"?q={q}&hl=en-US&gl=US&ceid=US:en"
    )

    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        return None

    matches = re.findall(r"<title>(.*?)</title>", r.text)
    if len(matches) < 2:
        return None

    return clean(" ".join(matches[1:4]))

# ----------------------------------------
# FACT EXTRACTION (HEURISTIC, REAL)
# ----------------------------------------
def extract_facts(text: str) -> dict:
    date_match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
        text
    )

    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)

    location_match = re.search(
        r"in\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        text
    )

    return {
        "date": date_match.group(0) if date_match else (year_match.group(0) if year_match else "Unknown"),
        "location": location_match.group(1) if location_match else "United States",
        "summary": text[:800]
    }

# ----------------------------------------
# MAIN
# ----------------------------------------
def main():
    used = load_used()

    fetchers = [fetch_reddit_case, fetch_news_case]
    random.shuffle(fetchers)

    for _ in range(15):
        for fetch in fetchers:
            raw = fetch()
            if not raw:
                continue

            fp = fingerprint(raw)
            if fp in used:
                continue

            facts = extract_facts(raw)

            with open(OUT_CASE, "w", encoding="utf-8") as f:
                json.dump(facts, f, indent=2)

            used.add(fp)
            save_used(used)

            print("✅ New real-world case saved")
            return

    raise SystemExit("❌ Unable to find a new unique case")

if __name__ == "__main__":
    main()
