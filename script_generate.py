#!/usr/bin/env python3
import os, json, hashlib, requests, random, sys, time

USED_FILE = "used_topics.json"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

def load_used():
    if not os.path.exists(USED_FILE):
        return set()
    try:
        data = json.load(open(USED_FILE,"r"))
        return set(data)
    except:
        return set()

def save_used(hashset):
    json.dump(list(hashset), open(USED_FILE, "w"), indent=2)

def hash_topic(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_sources():
    out = []

    # Wikipedia PD categories
    wiki = [
        "List_of_missing_persons_cases",
        "List_of_unsolved_murder_cases_in_the_United_States",
        "List_of_people_who_disappeared_mysteriously"
    ]

    for page in wiki:
        out.append(f"wikipedia:{page}")

    # Reddit (new)
    out.append("reddit:truecrime")
    out.append("reddit:darkmysteries")

    # Google News
    out.append("news:crime")

    return out

def pick_topic(used):
    sources = get_sources()
    random.shuffle(sources)

    for src in sources:
        if src in used:
            continue
        return src
    return random.choice(sources)

def fetch_content(src):
    if src.startswith("wikipedia:"):
        page = src.split(":",1)[1]
        url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&format=json&titles={page}&explaintext=1"
        j = requests.get(url).json()
        text = list(j["query"]["pages"].values())[0].get("extract","")
        return text[:5000]

    if src.startswith("reddit:"):
        sub = src.split(":",1)[1]
        url = f"https://www.reddit.com/r/{sub}/new.json?limit=20"
        j = requests.get(url, headers={"User-Agent":"Mozilla"}).json()
        posts = j.get("data",{}).get("children",[])
        bodies = []
        for p in posts:
            d = p["data"]
            if d.get("selftext"):
                bodies.append(d["selftext"])
        return random.choice(bodies)[:5000] if bodies else "Crime case description."

    if src.startswith("news:"):
        url = "https://news.google.com/rss/search?q=crime&hl=en-US&gl=US&ceid=US:en"
        import feedparser
        feed = feedparser.parse(url)
        if feed.entries:
            return feed.entries[0].title + ". " + feed.entries[0].summary
        return "Recent crime report."

    return "Unknown source."

def generate_script(topic_text):
    prompt = f"""
Write a 40-second true-crime documentary narration.
Tone: calm, investigative, realistic.
Rules:
- Start with a simple quiet moment leading into the crime.
- Use only factual-style wording.
- Avoid drama, exaggeration, cinematic wording.
- Use short clear sentences.
- End with one concise unresolved question.
- No repetition, no filler.
- Do NOT mention Wikipedia, Reddit, or news.

Topic material:
{topic_text[:2000]}
"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role":"user","content":prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.6
    }

    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    j = r.json()
    text = j["choices"][0]["message"]["content"]
    return text.strip()

def main():
    used = load_used()
    chosen = pick_topic(used)
    content = fetch_content(chosen)
    script = generate_script(content)

    # Save script
    open("script.txt","w",encoding="utf-8").write(script)

    # Mark topic as used
    used.add(hash_topic(chosen))
    save_used(used)

    print("[SCRIPT] Generated successfully.")

if __name__ == "__main__":
    main()

