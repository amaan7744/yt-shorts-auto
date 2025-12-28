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

# Target 60 words for ~28 seconds of high-speed narration
MIN_WORDS, MAX_WORDS = 58, 65

NEWS_QUERIES = [
    "unsolved mystery strange evidence",
    "police discovery cold case night",
    "missing person bizarre details",
]
# ----------------------------------------

def generate_script(context):
    """
    Rewritten Prompt using MrBeast's 'Retention-First' Logic.
    Focuses on: Hook, Progression, Re-Hook, and Loop.
    """
    prompt = f"""
Write a 60-word true crime script for a YouTube Short.

STRICT FORMAT:
1. THE HOOK (0-3s): Start with a shocking visual fact. No "What if" or "Imagine". 
   Example: "Police just found this car abandoned with the engine running."
2. THE MYSTERY (3-15s): Fast, simple sentences. Use visual verbs (saw, found, ran, hidden).
3. THE RE-HOOK (15-20s): Introduce a "twist" using the phrase "But it gets weirder."
4. THE LOOP (20-28s): End on a chilling fact that connects to the first sentence.

STYLE:
- 10-year-old vocabulary (simple and punchy).
- NO fluff. NO intro ("Hey guys").
- Maximum tension.

Context: {context}
"""
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a viral YouTube Shorts scriptwriter specializing in true crime and high-retention storytelling."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    for _ in range(3):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"].strip()
                # Clean any AI 'thought' or markdown
                text = re.sub(r'\[.*?\]|\*|_', '', text)
                wc = len(text.split())
                if MIN_WORDS <= wc <= MAX_WORDS:
                    return text
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)
    return None

# [Rest of the helper functions remain similar to your previous version]
