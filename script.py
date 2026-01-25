#!/usr/bin/env python3
"""
YouTube Shorts True Crime Script Generator
Retention-engineered, loop-optimized, policy-safe.
Built for 20–25s Shorts with rewatch bias.
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

    TARGET_WORDS_MIN = 45
    TARGET_WORDS_MAX = 55

    TEMPERATURE = 0.4
    MAX_RETRIES = 5
    RETRY_DELAY = 1.1


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
        if idx > len(trimmed) * 0.65:
            return trimmed[:idx + 1].strip()

    return trimmed.strip()


def load_case() -> Dict:
    path = Path(Config.CASE_FILE)
    if not path.exists():
        print(f"❌ {Config.CASE_FILE} not found")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    required = ["summary", "location"]
    if not all(k in data and data[k] for k in required):
        print("❌ case.json must include summary and location")
        sys.exit(1)

    return data


# ==================================================
# PROMPT (RETENTION-ENGINEERED)
# ==================================================

def build_script_prompt(case: Dict) -> str:
    return f"""
Write a high-retention YouTube Shorts narration about a real unresolved true crime or mystery.

FACTS (do not invent details):
Location: {case['location']}
Summary: {case['summary']}

NON-NEGOTIABLE RULES:
• 45–55 words
• One paragraph
• Detached, investigative tone
• No accusations
• No conclusions
• No emotional language
• Must be safe for on-screen text without audio

STRUCTURE (MANDATORY):
1. Open with a real contradiction or impossible detail
2. Establish time and place quickly
3. State the official explanation
4. Reveal why that explanation fails
5. Escalate the unanswered detail
6. End by denying closure in a way that forces a rewatch

STYLE:
• Short declarative sentences
• Emphasize what does NOT make sense
• Withhold causality
• Never resolve the mystery
• Final sentence must echo the opening contradiction

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
                    "You write viral true crime YouTube Shorts. "
                    "You specialize in contradiction-based hooks and denial of closure."
                )
            },
            {"role": "user", "content": prompt},
        ],
        temperature=Config.TEMPERATURE,
        max_tokens=250,
    )

    text = clean_text(response.choices[0].message.content)
    if not text:
        raise ValueError("Empty AI response")

    return text


# ==================================================
# HOOK SCORING (CONTRADICTION-BASED)
# ==================================================

def hook_score(script: str) -> int:
    first = re.split(r"[.!?]", script)[0].lower()
    score = 0

    contradiction_terms = [
        "locked", "no signs", "declared an accident",
        "camera stopped", "never explained",
        "vanished", "without a trace",
        "still unanswered", "found but"
    ]

    if any(term in first for term in contradiction_terms):
        score += 3

    if "but" in first or "however" in first:
        score += 2

    if 8 <= len(first.split()) <= 16:
        score += 1

    return score


# ==================================================
# VISUAL BEATS (PSYCHOLOGICAL PACING)
# ==================================================

def derive_visual_beats(script: str) -> List[Dict]:
    sentences = re.findall(r"[^.!?]+[.!?]?", script)
    beats = []

    for i, s in enumerate(sentences):
        wc = count_words(s)

        if i == 0:              # Hook
            duration = round(wc / 3.4, 1)
            scene = "HOOK"
        elif i == len(sentences) - 1:  # Loop
            duration = round(wc / 3.8, 1)
            scene = "LOOP"
        elif i == 1:            # Anchor
            duration = round(wc / 2.8, 1)
            scene = "ANCHOR"
        else:                   # Escalation
            duration = round(wc / 2.2, 1)
            scene = "ESCALATION"

        beats.append({
            "beat_id": i + 1,
            "scene_type": scene,
            "text": s.strip(),
            "word_count": wc,
            "estimated_duration": duration
        })

    return beats


# ==================================================
# GENERATION (NEVER HARD FAILS)
# ==================================================

def generate_content(client: ChatCompletionsClient, case: Dict) -> Tuple[str, List[Dict]]:
    prompt = build_script_prompt(case)
    best_script = None
    best_score = -1

    for attempt in range(1, Config.MAX_RETRIES + 1):
        print(f"🔄 Attempt {attempt}/{Config.MAX_RETRIES}")

        try:
            script = call_ai(client, prompt)
            script = smart_trim(script, Config.TARGET_WORDS_MAX)
            wc = count_words(script)

            if wc < Config.TARGET_WORDS_MIN:
                print(f"⚠️ Too short ({wc} words)")
                time.sleep(Config.RETRY_DELAY)
                continue

            score = hook_score(script)
            print(f"ℹ️ Hook score: {score}")

            if score > best_score:
                best_script = script
                best_score = score

            if score >= 3:
                beats = derive_visual_beats(script)
                print(f"✅ Accepted ({wc} words)")
                return script, beats

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(Config.RETRY_DELAY)

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

    print("💾 Outputs saved")


# ==================================================
# MAIN
# ==================================================

def main():
    print("🎬 True Crime Shorts Script Generator")

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
