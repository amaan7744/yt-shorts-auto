#!/usr/bin/env python3
"""
YouTube Shorts Script Generator
High-retention, policy-safe mystery narrations with visual beat mapping.
Built for virality, replay loops, and automation stability.
"""

import os
import sys
import json
import time
import re
from typing import Dict, List, Tuple
from pathlib import Path

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# ==================================================
# CONFIG
# ==================================================

class Config:
    ENDPOINT = "https://models.github.ai/inference"
    MODEL = "openai/gpt-4o-mini"

    CASE_FILE = "case.json"
    SCRIPT_FILE = "script.txt"
    BEATS_FILE = "beats.json"

    TARGET_WORDS_MIN = 44
    TARGET_WORDS_MAX = 52
    TARGET_DURATION = 20

    TEMPERATURE = 0.3
    MAX_RETRIES = 5
    RETRY_DELAY = 1.5


# ==================================================
# CLIENT
# ==================================================

def initialize_client() -> ChatCompletionsClient:
    token = os.getenv("GH_MODELS_TOKEN")
    if not token:
        print("❌ GH_MODELS_TOKEN not set")
        sys.exit(1)

    return ChatCompletionsClient(
        endpoint=Config.ENDPOINT,
        credential=AzureKeyCredential(token),
    )


# ==================================================
# UTILITIES
# ==================================================

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def count_words(text: str) -> int:
    return len(text.split())


def smart_trim(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text

    trimmed = " ".join(words[:max_words])
    last_punct = max(trimmed.rfind("."), trimmed.rfind("?"), trimmed.rfind("!"))
    if last_punct > len(trimmed) * 0.6:
        return trimmed[:last_punct + 1].strip()

    return trimmed.strip()


def load_case() -> Dict:
    path = Path(Config.CASE_FILE)
    if not path.exists():
        print(f"❌ {Config.CASE_FILE} not found")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Invalid JSON: {e}")
        sys.exit(1)

    for field in ("summary", "location"):
        if not data.get(field):
            print(f"❌ Missing required field: {field}")
            sys.exit(1)

    return data


# ==================================================
# PROMPT
# ==================================================

def build_script_prompt(case: Dict) -> str:
    return f"""
Write a viral-ready YouTube Shorts narration about a real unresolved mystery.

FACTS (do not invent):
Location: {case['location']}
Summary: {case['summary']}

RULES:
• Aim for 50–60 words (will be trimmed later)
• One paragraph only
• Neutral, factual tone
• No accusations, no conclusions
• Every sentence must work as on-screen text without audio

STRUCTURE:
1. First line: unsettling but verifiable fact
2. Time and place anchor
3. Detail that contradicts expectations
4. Escalating unanswered element
5. Official uncertainty or missing explanation
6. Ending line must echo the opening for a seamless loop

STYLE:
• Short sentences
• Calm authority
• Leave the mystery unresolved

OUTPUT:
Return ONLY the narration text.
"""


# ==================================================
# AI CALL
# ==================================================

def call_ai(client: ChatCompletionsClient, prompt: str) -> str:
    response = client.complete(
        model=Config.MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a YouTube Shorts scriptwriter specializing in "
                    "high-retention mystery content that is safe for monetization."
                )
            },
            {"role": "user", "content": prompt},
        ],
        temperature=Config.TEMPERATURE,
        max_tokens=300,
    )

    text = clean_text(response.choices[0].message.content)
    if not text:
        raise ValueError("Empty response")

    return text


# ==================================================
# HOOK CHECK (SOFT, REALISTIC)
# ==================================================

def hook_is_good(script: str) -> bool:
    first = re.split(r"[.!?]", script)[0].lower()
    credibility_signals = [
        "record",
        "documented",
        "official",
        "police",
        "authorities",
        "reported",
        "according to",
        "files",
        "archive",
    ]
    return any(s in first for s in credibility_signals) and len(first.split()) <= 16


# ==================================================
# BEAT GENERATION
# ==================================================

def derive_visual_beats(script: str) -> List[Dict]:
    sentences = re.findall(r"[^.!?]+[.!?]?", script)
    beats = []

    for i, s in enumerate(sentences):
        wc = count_words(s)
        beats.append({
            "beat_id": i + 1,
            "scene_type": (
                "HOOK" if i == 0 else
                "ANCHOR" if i == 1 else
                "LOOP" if i == len(sentences) - 1 else
                "ESCALATION"
            ),
            "text": s.strip(),
            "word_count": wc,
            "estimated_duration": round(wc / 2.4, 1)
        })

    return beats


# ==================================================
# GENERATION LOGIC (FIXED)
# ==================================================

def generate_content(client: ChatCompletionsClient, case: Dict) -> Tuple[str, List[Dict]]:
    prompt = build_script_prompt(case)

    best_script = None

    for attempt in range(1, Config.MAX_RETRIES + 1):
        try:
            print(f"🔄 Attempt {attempt}/{Config.MAX_RETRIES}")

            script = call_ai(client, prompt)

            if not hook_is_good(script):
                print("⚠️ Weak hook, retrying...")
                time.sleep(Config.RETRY_DELAY)
                continue

            script = smart_trim(script, Config.TARGET_WORDS_MAX)
            wc = count_words(script)

            if wc < Config.TARGET_WORDS_MIN:
                print(f"⚠️ Too short after trim ({wc})")
                time.sleep(Config.RETRY_DELAY)
                continue

            beats = derive_visual_beats(script)
            print(f"✅ Success: {wc} words | {len(beats)} beats")
            return script, beats

        except Exception as e:
            print(f"⚠️ Retry reason: {e}")
            time.sleep(Config.RETRY_DELAY)

    print("❌ Failed to generate valid script")
    sys.exit(1)


# ==================================================
# SAVE OUTPUT
# ==================================================

def save_outputs(script: str, beats: List[Dict]) -> None:
    with open(Config.SCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(script)

    data = {
        "metadata": {
            "total_words": count_words(script),
            "total_beats": len(beats),
            "estimated_duration": round(sum(b["estimated_duration"] for b in beats), 1),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "beats": beats,
    }

    with open(Config.BEATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("💾 Outputs saved")


# ==================================================
# MAIN
# ==================================================

def main():
    print("🎬 YouTube Shorts Script Generator")

    case = load_case()
    client = initialize_client()

    script, beats = generate_content(client, case)
    save_outputs(script, beats)

    print("\n📜 SCRIPT")
    print("-" * 50)
    print(script)
    print("-" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔ Cancelled")
