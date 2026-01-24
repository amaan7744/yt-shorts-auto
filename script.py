#!/usr/bin/env python3
"""
YouTube Shorts Script Generator
Stable, viral-oriented, policy-safe mystery narration generator.
Designed to NEVER fail on hook validation loops.
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

    TEMPERATURE = 0.35
    MAX_RETRIES = 4
    RETRY_DELAY = 1.2


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
    for p in [".", "?", "!"]:
        idx = trimmed.rfind(p)
        if idx > len(trimmed) * 0.6:
            return trimmed[:idx + 1].strip()

    return trimmed.strip()


def load_case() -> Dict:
    path = Path(Config.CASE_FILE)
    if not path.exists():
        print(f"❌ {Config.CASE_FILE} not found")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data.get("summary") or not data.get("location"):
        print("❌ case.json must contain summary and location")
        sys.exit(1)

    return data


# ==================================================
# PROMPT (FIXED)
# ==================================================

def build_script_prompt(case: Dict) -> str:
    return f"""
Write a high-retention YouTube Shorts narration about a real unresolved mystery.

FACTS (do not invent details):
Location: {case['location']}
Summary: {case['summary']}

RULES:
• Aim for 50–60 words (will be trimmed)
• One paragraph only
• Neutral, factual tone
• No accusations or conclusions
• Works as on-screen text without audio

STRUCTURE:
1. First sentence: an impossible-sounding real situation
2. Clear time and place
3. What doesn’t add up
4. Escalating unanswered detail
5. Official uncertainty or missing explanation
6. Ending line must echo the opening for a seamless loop

STYLE:
• Short, sharp sentences
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
                    "You write viral YouTube Shorts mystery scripts. "
                    "Your openings create immediate curiosity. "
                    "Your endings loop naturally."
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
# HUMAN-LIKE HOOK SCORING (NO HARD FAIL)
# ==================================================

def hook_score(script: str) -> int:
    first = re.split(r"[.!?]", script)[0].lower()
    score = 0

    if 6 <= len(first.split()) <= 18:
        score += 1

    curiosity_terms = [
        "vanished", "disappeared", "locked", "never explained",
        "no one knows", "without a trace", "unsolved",
        "found", "last seen", "still unanswered"
    ]

    if any(term in first for term in curiosity_terms):
        score += 2

    return score


# ==================================================
# BEATS
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
# GENERATION (NEVER HARD FAILS)
# ==================================================

def generate_content(client: ChatCompletionsClient, case: Dict) -> Tuple[str, List[Dict]]:
    prompt = build_script_prompt(case)
    best = None
    best_score = -1

    for attempt in range(1, Config.MAX_RETRIES + 1):
        print(f"🔄 Attempt {attempt}/{Config.MAX_RETRIES}")

        try:
            script = call_ai(client, prompt)
            script = smart_trim(script, Config.TARGET_WORDS_MAX)
            wc = count_words(script)

            if wc < Config.TARGET_WORDS_MIN:
                print(f"⚠️ Too short ({wc}), retrying...")
                time.sleep(Config.RETRY_DELAY)
                continue

            score = hook_score(script)
            print(f"ℹ️ Hook score: {score}")

            if score > best_score:
                best = script
                best_score = score

            if score >= 2:
                beats = derive_visual_beats(script)
                print(f"✅ Accepted: {wc} words")
                return script, beats

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(Config.RETRY_DELAY)

    # Fallback: always return best attempt
    print("⚠️ Using best available script")
    beats = derive_visual_beats(best)
    return best, beats


# ==================================================
# SAVE
# ==================================================

def save_outputs(script: str, beats: List[Dict]) -> None:
    with open(Config.SCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(script)

    data = {
        "metadata": {
            "words": count_words(script),
            "beats": len(beats),
            "estimated_duration": round(sum(b["estimated_duration"] for b in beats), 1),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "beats": beats
    }

    with open(Config.BEATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("💾 Saved outputs")


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
    main()
