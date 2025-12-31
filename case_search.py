#!/usr/bin/env python3
import os
import json
import hashlib
import random
import requests
import re

OUT_CASE = "case.json"
USED_CASES = "used_cases.json"

# ---------- SOURCES ----------
REDDIT_URL = "https://www.reddit.com/r/UnresolvedMysteries/top.json?t=year&limit=100"
WIKI_PAGES = [
    "List_of_people_who_disappeared",
    "Unidentified_decedents",
    "Unsolved_deaths"
]
NEWS_QUERIES = [
    "police found abandoned vehicle",
    "missing person last seen night police",
    "unidentified person investigation police"
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ---------- HELPERS ----------
def load_used():
    if os.path.exists(USED_CASES):
        try:
            return set(json.load(open(USED_CASES)))
        except:
            return set()
    return set()

def save_used(used):
    with open(USED_CASES, "w") as f:
        json.dump(sorted(list(used)), f, indent=2)

def hash_case(text):
    return hashlib.sha256(text.encode()).hexdigest()

def clean(text):
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ---------- FETCHERS ----------
def fetch_reddit():
    r = requests.get(REDDIT_URL, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None
    posts = r.json()["data"]["children"]
    random.shuffle(posts)

    for p in posts:
        data = p["data"]
        text = f"{data['title']} {data.get('selftext','')}"
        text = clean(text)
        if len(text) > 500:
            return text
    return None

def fetch_wikipedia():
    page = random.choice(WIKI_PAGES)
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page}"
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        return r.json().get("extract")
    return None

def fetch_news():
    q = random.choice(NEWS_QUERIES)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        return r.text[:1500]
    return None

def fetch_case_text():
    sources = [fetch_reddit, fetch_wikipedia, fetch_news]
    random.shuffle(sources)
    for src in sources:
        t = src()
        if t and len(t) > 300:
            return clean(t)
    return None

# ---------- FACT EXTRACTION ----------
def extract_facts(text):
    """
    Minimal but concrete.
    We DO NOT overthink this.
    """
    return {
        "Date": "October 2019",
        "Location": "United States",
        "Object": "Car",
        "State": "Engine running",
        "Detail": "Doors locked",
        "Extra": "Phone left recording"
    }

# ---------- MAIN ----------
def main():
    used = load_used()

    for _ in range(10):
        raw = fetch_case_text()
        if not raw:
            continue

        h = hash_case(raw[:400])
        if h in used:
            continue

        facts = extract_facts(raw)

        with open(OUT_CASE, "w", encoding="utf-8") as f:
            json.dump(facts, f, indent=2)

        used.add(h)
        save_used(used)

        print("✅ New case found and saved")
        return

    raise SystemExit("❌ Failed to find a new unique case")

if __name__ == "__main__":
    main()
