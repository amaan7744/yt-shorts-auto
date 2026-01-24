#!/usr/bin/env python3
"""
YouTube Shorts Script Generator
Creates high-retention, policy-safe mystery narrations with visual beat mapping.
Optimized for virality, mute viewing, and replay loops.
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

    TEMPERATURE = 0.25
    MAX_RETRIES = 4
    RETRY_DELAY = 2


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

    for key in ("summary", "location"):
        if not data.get(key):
            print(f"❌ Missing required field: {key}")
            sys.exit(1)

    return data


# ==================================================
# PROMPT (VIRAL + SAFE)
# ==================================================

def build_script_prompt(case: Dict) -> str:
    return f"""
Write a high-retention YouTube Shorts narration about a real unresolved mystery.

FACTS (do not invent anything):
Location: {case['location']}
Summary: {case['summary']}

HARD RULES:
• 44–52 words total
• One paragraph only
• No emojis, labels, or filler
• Neutral, factual tone
• No accusations or conclusions
• Every sentence must work as on-screen text without audio

MANDATORY STRUCTURE:
1. First sentence: a verified, unsettling fact that sounds impossible
2. Time and location anchor
3. Detail that contradicts expectations
4. Escalating unanswered element
5. Official uncertainty or missing explanation
6. Final line must echo the opening so the video loops cleanly

RETENTION RULES:
• Short, sharp sentences
• No opinions
• Leave the mystery unresolved on purpose

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
                    "You are an expert YouTube Shorts writer. "
                    "You specialize in viral mystery narration that maximizes "
                    "retention, replay loops, and monetization safety."
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
# HOOK VALIDATION (IMPORTANT)
# ==================================================

def hook_is_strong(script: str) -> bool:
    first_sentence = re.split(r"[.!?]", script)[0].lower()
    trigger_words = ["record", "documented", "official", "reported", "logged"]
    return any(word in first_sentence for word in trigger_words)


# ==================================================
# BEAT GENERATION
# ==================================================

def derive_visual_beats(script: str) -> List[Dict]:
    sentences = re.findall(r"[^.!?]+[.!?]?", script)
    beats = []

    for i, s in enumerate(sentences):
        words = count_words(s)
        beats.append({
            "beat_id": i + 1,
            "scene_type": (
                "HOOK" if i == 0 else
                "ANCHOR" if i == 1 else
                "LOOP" if i == len(sentences) - 1 else
                "ESCALATION"
            ),
            "text": s.strip(),
            "word_count": words,
            "estimated_duration": round(words / 2.4, 1)
        })

    return beats


# ==================================================
# GENERATION LOGIC
# ==================================================

def generate_content(client: ChatCompletionsClient, case: Dict) -> Tuple[str, List[Dict]]:
    prompt = build_script_prompt(case)

    for attempt in range(1, Config.MAX_RETRIES + 1):
        try:
            print(f"🔄 Attempt {attempt}/{Config.MAX_RETRIES}")

            script = call_ai(client, prompt)
            wc = count_words(script)

            if wc < Config.TARGET_WORDS_MIN or wc > Config.TARGET_WORDS_MAX:
                print(f"⚠️ Word count off ({wc})")
                raise ValueError("Bad word count")

            if not hook_is_strong(script):
                print("⚠️ Weak hook detected")
                raise ValueError("Weak hook")

            beats = derive_visual_beats(script)
            print(f"✅ Success: {wc} words | {len(beats)} beats")
            return script, beats

        except Exception as e:
            print(f"⚠️ Retry reason: {e}")
            time.sleep(Config.RETRY_DELAY)

    print("❌ Failed after retries")
    sys.exit(1)


# ==================================================
# SAVE OUTPUT
# ==================================================

def save_outputs(script: str, beats: List[Dict]) -> None:
    with open(Config.SCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(script)

    data = {
        "metadata": {
            "words": count_words(script),
            "beats": len(beats),
            "duration_estimate": round(sum(b["estimated_duration"] for b in beats), 1),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "beats": beats
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

    print("\n📜 SCRIPT:")
    print("-" * 50)
    print(script)
    print("-" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("⛔ Cancelled")
