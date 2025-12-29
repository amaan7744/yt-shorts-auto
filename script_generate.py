#!/usr/bin/env python3
import os
import json
import hashlib
import random
import time
import requests
import re

# ---------------- CONFIG ----------------
OUT_SCRIPT = "script.txt"
USED_TOPICS_FILE = "used_topics.json"
API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# RELAXED Word count for better reliability in GitHub Actions
MIN_WORDS, MAX_WORDS = 55, 70 

NEWS_QUERIES = [
    "unsolved mystery strange evidence",
    "police discovery cold case night",
    "missing person bizarre details",
]

FALLBACK_SCRIPT = "This abandoned car was found with the engine still running. Police found no struggle, no blood, and no signs of the driver. But it gets weirder. The driver's phone was on the dashboard, recording a video of the empty seat. This mystery remains unsolved because the footage shows the door opening itself."
# ----------------------------------------

def load_used():
    if os.path.exists(USED_TOPICS_FILE):
        try:
            with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except: return set()
    return set()

def save_used(used):
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(used)), f, indent=2)

def clean_rss_text(xml):
    # Extracting titles and descriptions from Google News RSS
    titles = re.findall(r"<title>(.*?)</title>", xml)
    return " ".join(titles[1:5])[:1000]

def fetch_news():
    q = random.choice(NEWS_QUERIES)
    url = f"https://news.google.com/rss/search?q={q}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return clean_rss_text(r.text)
    except: pass
    return None

def generate_script(context):
    prompt = f"""
Write a 60-word true crime script for a YouTube Short.
1. THE HOOK: Shocking visual fact. 
2. THE MYSTERY: Use visual verbs.
3. THE RE-HOOK: Use the phrase "But it gets weirder."
4. THE LOOP: Chilling ending.
Context: {context}
"""
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a viral YouTube Shorts scriptwriter. Use simple vocabulary. No fluff."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    for attempt in range(3):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"].strip()
                text = re.sub(r'\[.*?\]|\*|_', '', text)
                wc = len(text.split())
                print(f"Attempt {attempt+1}: {wc} words.")
                if MIN_WORDS <= wc <= MAX_WORDS:
                    return text
        except Exception as e:
            print(f"API Error: {e}")
            time.sleep(2)
    return None

def main():
    if not API_KEY:
        print("Error: DEEPSEEK_API_KEY is missing!")
        # We write fallback so the rest of the pipeline doesn't crash
        with open(OUT_SCRIPT, "w") as f: f.write(FALLBACK_SCRIPT)
        return

    used = load_used()
    news_context = fetch_news()
    
    # Try to generate script
    script = generate_script(news_context if news_context else "mysterious disappearance")
    
    if script:
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(script)
        print("✅ Success: AI Script Generated.")
    else:
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(FALLBACK_SCRIPT)
        print("⚠️ Warning: Using Fallback Script (API or Wordcount failed).")

if __name__ == "__main__":
    main()

