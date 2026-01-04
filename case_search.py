#!/usr/bin/env python3

import os
import json
import hashlib
import random
import re
import requests
import datetime
from bs4 import BeautifulSoup

OUT_CASE = "case.json"
USED_CASES = "used_cases.json"

HEADERS = {
    "User-Agent": "CrimeShortsBot/2.0 (research)"
}

CURRENT_YEAR = datetime.datetime.now().year
MIN_YEAR = 1800

# -------------------------------------------------
# SOURCE ENDPOINTS
# -------------------------------------------------

REDDIT_ENDPOINTS = [
    "https://www.reddit.com/r/UnresolvedMysteries/top.json?limit=100&t=year",
    "https://www.reddit.com/r/TrueCrime/top.json?limit=100&t=year",
]

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

ALJAZEERA_RSS = "https://www.aljazeera.com/xml/rss/all.xml"

WIKI_SEARCH_TERMS = [
    "unsolved murder",
    "mysterious death",
    "missing person",
    "cold case",
    "disappearance",
    "unidentified remains",
]

# -------------------------------------------------
# UTIL
# -------------------------------------------------

def load_used():
    if os.path.exists(USED_CASES):
        try:
            return set(json.load(open(USED_CASES)))
        except:
            return set()
    return set()

def save_used(used):
    with open(USED_CASES, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)

def fingerprint(text: str) -> str:
    return hashlib.sha256(text.lower().encode("utf-8")).hexdigest()

def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# -------------------------------------------------
# FETCHERS
# -------------------------------------------------

def fetch_reddit():
    url = random.choice(REDDIT_ENDPOINTS)
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    posts = r.json()["data"]["children"]
    random.shuffle(posts)

    for p in posts:
        d = p["data"]
        text = clean(f"{d.get('title','')} {d.get('selftext','')}")
        if len(text) > 800 and not d.get("stickied"):
            return {"summary": text, "source": "reddit"}

    return None

def fetch_google_news():
    year = random.randint(MIN_YEAR, CURRENT_YEAR)
    query = random.choice(WIKI_SEARCH_TERMS)
    url = GOOGLE_NEWS_RSS.format(query=f"{query} {year}")

    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")
    if not items:
        return None

    summaries = []
    for item in items[:5]:
        summaries.append(item.title.text)

    text = clean(" ".join(summaries))
    return {"summary": text, "source": "google_news"}

def fetch_aljazeera():
    r = requests.get(ALJAZEERA_RSS, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")
    random.shuffle(items)

    for item in items[:10]:
        title = item.title.text
        if any(k in title.lower() for k in ["killed", "murder", "dead", "missing"]):
            return {"summary": clean(title), "source": "aljazeera"}

    return None

def fetch_wikipedia():
    term = random.choice(WIKI_SEARCH_TERMS)
    search_url = (
        "https://en.wikipedia.org/w/api.php"
        "?action=query&list=search&srsearch="
        + term + "&format=json"
    )

    r = requests.get(search_url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    results = r.json().get("query", {}).get("search", [])
    random.shuffle(results)

    for res in results[:5]:
        title = res.get("title")
        page = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ','%20')}",
            headers=HEADERS,
            timeout=20
        )
        if page.status_code != 200:
            continue

        summary = page.json().get("extract")
        if summary and len(summary) > 800:
            return {"summary": clean(summary), "source": "wikipedia"}

    return None

# -------------------------------------------------
# FACT EXTRACTION
# -------------------------------------------------

def extract_facts(raw: dict) -> dict:
    text = raw["summary"]

    year_match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", text)
    location_match = re.search(
        r"in\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        text
    )

    return {
        "date": year_match.group(0) if year_match else "Unknown year",
        "location": location_match.group(1) if location_match else "Unknown location",
        "summary": text,
        "source": raw["source"]
    }

# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():
    used = load_used()
    fetchers = [fetch_reddit, fetch_google_news, fetch_aljazeera, fetch_wikipedia]
    random.shuffle(fetchers)

    for _ in range(30):
        for fetch in fetchers:
            raw = fetch()
            if not raw:
                continue

            fp = fingerprint(raw["summary"])
            if fp in used:
                continue

            facts = extract_facts(raw)

            # HARD QUALITY GATES
            if len(facts["summary"]) < 700:
                continue

            with open(OUT_CASE, "w", encoding="utf-8") as f:
                json.dump(facts, f, indent=2)

            used.add(fp)
            save_used(used)

            print(f"✅ Case saved from {facts['source']}")
            return

    raise SystemExit("❌ Unable to find a valid unique case")

if __name__ == "__main__":
    main()
