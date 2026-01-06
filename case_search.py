#!/usr/bin/env python3

import json
import random
import re
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

OUT_FILE = Path("case.json")
USED_FILE = Path("used_cases.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CaseFinder/3.0)"
}

MIN_SUMMARY_CHARS = 600
MAX_SUMMARY_CHARS = 900

MIN_YEAR = 1800
CURRENT_YEAR = datetime.utcnow().year

# -------------------------------------------------
# SOURCES (GLOBAL + LONG-TERM)
# -------------------------------------------------

WIKI_PAGES = [
    "https://en.wikipedia.org/wiki/List_of_people_who_disappeared",
    "https://en.wikipedia.org/wiki/List_of_unsolved_deaths",
    "https://en.wikipedia.org/wiki/Unidentified_decedents",
]

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=unresolved+case",
    "https://news.google.com/rss/search?q=missing+person+investigation",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
]

REDDIT_FEEDS = [
    "https://www.reddit.com/r/UnresolvedMysteries/new.json?limit=50",
    "https://www.reddit.com/r/TrueCrimeDiscussion/new.json?limit=50",
]

# -------------------------------------------------
# UTIL
# -------------------------------------------------

def load_used():
    if USED_FILE.exists():
        try:
            return set(json.loads(USED_FILE.read_text()))
        except Exception:
            return set()
    return set()

def save_used(used):
    USED_FILE.write_text(json.dumps(sorted(used), indent=2))

def fingerprint(text: str) -> str:
    return hashlib.sha256(text.lower().encode()).hexdigest()

def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_year(text: str) -> str:
    match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", text)
    return match.group(1) if match else "Unknown"

def extract_location(text: str) -> str:
    match = re.search(
        r"in\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        text
    )
    return match.group(1) if match else "Unknown location"

# -------------------------------------------------
# NORMALIZATION (POLICY SAFE)
# -------------------------------------------------

def normalize_summary(raw: str) -> str:
    """
    Converts raw historical/news text into
    an investigative, non-graphic summary.
    """

    replacements = {
        r"\bmurder(ed)?\b": "an unexplained death",
        r"\bkilled\b": "lost their life",
        r"\bshot\b": "was found injured",
        r"\bstabbed\b": "was found injured",
        r"\bbody\b": "remains",
        r"\bdead\b": "unresponsive",
        r"\bassault\b": "incident",
        r"\bweapon\b": "object",
    }

    text = raw.lower()
    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text)

    text = clean_text(text)

    if len(text) > MAX_SUMMARY_CHARS:
        text = text[:MAX_SUMMARY_CHARS].rsplit(" ", 1)[0]

    return text.capitalize()

# -------------------------------------------------
# FETCHERS
# -------------------------------------------------

def fetch_wikipedia():
    page = random.choice(WIKI_PAGES)
    r = requests.get(page, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("li")
    random.shuffle(items)

    for li in items:
        text = clean_text(li.get_text())
        if len(text) >= MIN_SUMMARY_CHARS:
            return text

    return None


def fetch_rss():
    feed = random.choice(RSS_FEEDS)
    r = requests.get(feed, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")
    random.shuffle(items)

    for item in items:
        text = clean_text(item.get_text())
        if len(text) >= MIN_SUMMARY_CHARS:
            return text

    return None


def fetch_reddit():
    """
    Reddit is opportunistic.
    If blocked, we silently skip.
    """

    url = random.choice(REDDIT_FEEDS)

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)

        if r.status_code != 200:
            return None

        if "application/json" not in r.headers.get("Content-Type", ""):
            return None

        payload = r.json()
        children = payload.get("data", {}).get("children", [])
        if not children:
            return None

        random.shuffle(children)

        for post in children:
            d = post.get("data", {})
            text = clean_text(
                f"{d.get('title', '')}. {d.get('selftext', '')}"
            )
            if len(text) >= MIN_SUMMARY_CHARS:
                return text

    except Exception:
        return None

    return None

# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():
    used = load_used()

    fetchers = [
        fetch_wikipedia,
        fetch_rss,
        fetch_reddit,
    ]

    random.shuffle(fetchers)

    for _ in range(30):
        for fetch in fetchers:
            raw = fetch()
            if not raw:
                continue

            fp = fingerprint(raw)
            if fp in used:
                continue

            year = extract_year(raw)
            location = extract_location(raw)
            summary = normalize_summary(raw)

            case = {
                "date": year,
                "location": location,
                "summary": summary,
            }

            OUT_FILE.write_text(json.dumps(case, indent=2))
            used.add(fp)
            save_used(used)

            print("✅ Case selected and normalized")
            return

    raise SystemExit("❌ Unable to find a unique, safe case")

# -------------------------------------------------

if __name__ == "__main__":
    main()
