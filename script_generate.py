import os
import json
import hashlib
import random
import time
import requests
import re

OUT_SCRIPT = "script.txt"
USED_TOPICS_FILE = "used_topics.json"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

NEWS_QUERIES = [
    "unsolved cold case mystery details",
    "missing person forensic evidence",
    "unidentified remains investigation 2024",
    "police appeal cold case files"
]

def load_used():
    if os.path.exists(USED_TOPICS_FILE):
        return set(json.load(open(USED_TOPICS_FILE, "r")))
    return set()

def save_used(used):
    json.dump(sorted(list(used)), open(USED_TOPICS_FILE, "w"), indent=2)

def hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def clean_rss_text(xml_text):
    """Extracts just titles and descriptions from RSS to give the AI clean data."""
    titles = re.findall(r'<title>(.*?)</title>', xml_text)
    descriptions = re.findall(r'<description>(.*?)</description>', xml_text)
    combined = " ".join(titles[1:5] + descriptions[1:5]) # Skip first item (channel title)
    return combined[:2000]

def fetch_news_text():
    q = random.choice(NEWS_QUERIES)
    url = f"https://news.google.com/rss/search?q={q}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and r.text:
            return clean_rss_text(r.text)
    except Exception as e:
        print(f"Error fetching news: {e}")
    return None

def generate_script(raw_context):
    # This prompt uses 'Chain of Thought' to help the AI structure the narrative
    prompt = f"""
You are a professional true-crime documentary scriptwriter. 
Create a 40-60 second script based on the source material provided.

[STRUCTURE]
1. HOOK: A gripping first sentence that sets the stakes.
2. CONTEXT: Name, year, and specific location.
3. THE MYSTERY: 2-3 sentences explaining what went wrong or what was found.
4. THE INVESTIGATION: Mention a specific piece of evidence or a dead end.
5. OUTRO: A haunting question or an unresolved fact.

[STYLE RULES]
- Tone: Somber, objective, and cinematic.
- Pacing: Use short, punchy sentences.
- Vocabulary: Use descriptive, atmospheric words (e.g., "disturbed," "silent," "fragmented").
- NO clichés like "In a world where..." or "Little did they know..."
- Word count: Strict 110-140 words.

[SOURCE MATERIAL]
{raw_context}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a specialized true-crime scriptwriter."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7, # Increased slightly for better creativity
        "max_tokens": 500,
    }

    for _ in range(3):
        try:
            r = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=60)
            if r.status_code == 200:
                result = r.json()["choices"][0]["message"]["content"].strip()
                # Clean up any AI 'chatter' (like "Here is your script:")
                if "---" in result: result = result.split("---")[-1]
                return result
        except Exception as e:
            print(f"API Error: {e}")
        time.sleep(2)

    return "Error generating script. Please check API settings."

def main():
    used = load_used()
    print("Searching for new crime cases...")

    for _ in range(5):
        raw = fetch_news_text()
        if not raw or len(raw) < 100:
            continue

        h = hash_text(raw[:100]) # Hash the start of the news to avoid repeats
        if h in used:
            continue

        script = generate_script(raw)
        with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
            f.write(script)

        used.add(h)
        save_used(used)

        print("-" * 30)
        print("SCRIPT GENERATED SUCCESSFULLY:")
        print(script)
        print("-" * 30)
        return

    print("Could not find new or unique topics.")

if __name__ == "__main__":
    main()
