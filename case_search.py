#!/usr/bin/env python3
import json, random, re, hashlib, requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

OUT_FILE = Path("case.json")
USED_FILE = Path("used_cases.json")

HEADERS = {"User-Agent": "CaseFinder/4.0"}

MIN_SUMMARY_CHARS = 600
MAX_SUMMARY_CHARS = 900
CURRENT_YEAR = datetime.utcnow().year

WIKI_PAGES = [
    "https://en.wikipedia.org/wiki/List_of_unsolved_deaths",
    "https://en.wikipedia.org/wiki/List_of_people_who_disappeared",
]

def fingerprint(text): return hashlib.sha256(text.lower().encode()).hexdigest()

def clean(t): return re.sub(r"\s+", " ", t).strip()

def extract_year(t):
    m = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", t)
    return m.group(1) if m else "Unknown"

def extract_location(t):
    m = re.search(r"in\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", t)
    return m.group(1) if m else "Unknown"

def detect_flags(t):
    return {
        "mistake": bool(re.search(r"missed|ignored|overlooked|error|failed", t)),
        "delay": bool(re.search(r"years later|days later|delayed", t)),
        "unclear": bool(re.search(r"unknown|unsolved|unexplained", t)),
    }

def normalize(raw):
    raw = raw.lower()
    raw = re.sub(r"\b(killed|murdered|stabbed|shot)\b", "was found", raw)
    raw = clean(raw)
    return raw[:MAX_SUMMARY_CHARS].rsplit(" ", 1)[0].capitalize()

def load_used():
    return set(json.loads(USED_FILE.read_text())) if USED_FILE.exists() else set()

def save_used(u): USED_FILE.write_text(json.dumps(sorted(u), indent=2))

def fetch_wiki():
    page = random.choice(WIKI_PAGES)
    soup = BeautifulSoup(requests.get(page, headers=HEADERS).text, "html.parser")
    items = soup.select("li")
    random.shuffle(items)
    for li in items:
        t = clean(li.get_text())
        if len(t) >= MIN_SUMMARY_CHARS:
            return t
    return None

def main():
    used = load_used()
    for _ in range(25):
        raw = fetch_wiki()
        if not raw: continue
        fp = fingerprint(raw)
        if fp in used: continue

        summary = normalize(raw)
        case = {
            "date": extract_year(raw),
            "location": extract_location(raw),
            "summary": summary,
            "flags": detect_flags(summary)
        }

        OUT_FILE.write_text(json.dumps(case, indent=2))
        used.add(fp)
        save_used(used)
        print("✅ Case selected (story-aware)")
        return

    raise SystemExit("❌ No suitable case found")

if __name__ == "__main__":
    main()
