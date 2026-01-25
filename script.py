#!/usr/bin/env python3
"""
YouTube Shorts Mystery Script Generator
Retention-aware, Azure-safe, CI-stable.
Designed for modern crime and historical mysteries.
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

    WORDS_MIN = 40
    WORDS_SOFT_MAX = 65   # soft ceiling, not enforced

    TEMPERATURE = 0.4
    MAX_ATTEMPTS = 4
    RETRY_DELAY = 1.5


# ==================================================
# CLIENT
# ==================================================

def initialize_client() -> ChatCompletionsClient:
    token = os.getenv("GH_MODELS_TOKEN")
    if not token:
        print("⚠️ GH_MODELS_TOKEN not set, exiting gracefully")
        sys.exit(0)

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
        print("⚠️ case.json missing, exiting gracefully")
        sys.exit(0)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data.get("summary") or not data.get("location"):
        print("⚠️ case.json incomplete, exiting gracefully")
        sys.exit(0)

    return data


# ==================================================
# PROMPT (AZURE-SAFE)
# ==================================================

def build_script_prompt(case: Dict) -> str:
    return f"""
Write a short narration suitable for a YouTube Short about a real unresolved mystery.

Context:
Location: {case['location']}
Background: {case['summary']}

Guidelines:
• Around 45–60 words
• One paragraph
• Calm, investigative tone
• Avoid accusations or conclusions
• Focus on uncertainty, contradiction, or unanswered details
• Suitable for on-screen text

Suggested flow:
• Begin with a detail that seems unclear or disputed
• Briefly establish time and place
• Mention the accepted explanation or historical record
• Explain why it remains questioned
• End by highlighting what is still unknown

Please provide only the narration text.
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
                    "You write concise mystery narrations for short-form video. "
                    "Your tone is neutral and investigative."
                )
            },
            {"role": "user", "content": prompt},
        ],
        temperature=Config.TEMPERATURE,
        max_tokens=250,
    )

    text = clean_text(response.choices[0].message.content)
    if not text:
        raise ValueError("Empty response")

    return text


# ==================================================
# HOOK SCORING (ADAPTIVE, NON-BLOCKING)
# ==================================================

def hook_score(script: str) -> int:
    first = re.split(r"[.!?]", script)[0].lower()
    score = 0

    contradiction_terms = [
        "unclear", "disputed", "contradict",
        "records differ", "still unknown",
        "never explained", "questioned"
    ]

    if any(t in first for t in contradiction_terms):
        score += 2

    if "but" in first or "however" in first:
        score += 1

    if 6 <= len(first.split()) <= 20:
        score += 1

    return score


# ==================================================
# VISUAL BEATS (RETENTION-AWARE)
# ==================================================

def derive_visual_beats(script: str) -> List[Dict]:
    sentences = re.findall(r"[^.!?]+[.!?]?", script)
    beats = []

    for i, s in enumerate(sentences):
        wc = count_words(s)

        if i == 0:
            scene = "HOOK"
            duration = round(wc / 3.2, 1)
        elif i == len(sentences) - 1:
            scene = "LOOP"
            duration = round(wc / 3.6, 1)
        else:
            scene = "ESCALATION"
            duration = round(wc / 2.4, 1)

        beats.append({
            "beat_id": i + 1,
            "scene_type": scene,
            "text": s.strip(),
            "word_count": wc,
            "estimated_duration": duration
        })

    return beats


# ==================================================
# GENERATION (CI-SAFE, NEVER FAILS)
# ==================================================

def generate_content(client: ChatCompletionsClient, case: Dict) -> Tuple[str, List[Dict]]:
    prompt = build_script_prompt(case)
    best_script = None
    best_score = -1

    for attempt in range(1, Config.MAX_ATTEMPTS + 1):
        print(f"🔄 Attempt {attempt}/{Config.MAX_ATTEMPTS}")

        try:
            script = call_ai(client, prompt)
            wc = count_words(script)

            if wc < Config.WORDS_MIN:
                print(f"⚠️ Too short ({wc} words), retrying")
                time.sleep(Config.RETRY_DELAY)
                continue

            score = hook_score(script)
            print(f"ℹ️ Hook score: {score}")

            if score > best_score:
                best_script = script
                best_score = score

            # Accept early if decent
            if score >= 2:
                beats = derive_visual_beats(script)
                return script, beats

        except Exception as e:
            print(f"⚠️ API issue: {e}")
            time.sleep(Config.RETRY_DELAY)

    # Fallback (never fail)
    print("⚠️ Using best available script")
    beats = derive_visual_beats(best_script)
    return best_script, beats


# ==================================================
# SAVE OUTPUTS
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

    print("💾 Outputs saved successfully")


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
