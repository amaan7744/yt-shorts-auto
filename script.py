#!/usr/bin/env python3
"""
YouTube Shorts Mystery Script Generator
- Strong hooks
- Script → visual locked beats
- CI safe
- Azure / GH Models compatible
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Tuple

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

    WORDS_MIN = 45
    WORDS_MAX = 65

    TEMPERATURE = 0.4
    MAX_ATTEMPTS = 4
    RETRY_DELAY = 1.5


# ==================================================
# CLIENT
# ==================================================

def init_client() -> ChatCompletionsClient:
    token = os.getenv("GH_MODELS_TOKEN")
    if not token:
        print("⚠️ GH_MODELS_TOKEN missing, exiting gracefully")
        sys.exit(0)

    return ChatCompletionsClient(
        endpoint=Config.ENDPOINT,
        credential=AzureKeyCredential(token),
    )


# ==================================================
# UTIL
# ==================================================

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def wc(text: str) -> int:
    return len(text.split())


def load_case() -> Dict:
    path = Path(Config.CASE_FILE)
    if not path.exists():
        print("⚠️ case.json missing")
        sys.exit(0)

    data = json.loads(path.read_text())
    if not data.get("summary") or not data.get("location"):
        print("⚠️ case.json incomplete")
        sys.exit(0)

    return data


# ==================================================
# PROMPT
# ==================================================

def build_prompt(case: Dict) -> str:
    return f"""
Write a short narration for a YouTube Short about a real unresolved mystery.

Location: {case['location']}
Background: {case['summary']}

Rules:
• 45–60 words
• One paragraph
• Calm, investigative tone
• Start with a confusing or disturbing detail
• No accusations
• No conclusions
• End on uncertainty
• Suitable for subtitles

Output ONLY the narration text.
"""


# ==================================================
# AI CALL
# ==================================================

def call_ai(client: ChatCompletionsClient, prompt: str) -> str:
    res = client.complete(
        model=Config.MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You write short, high-retention mystery narrations "
                    "for investigative YouTube Shorts."
                )
            },
            {"role": "user", "content": prompt},
        ],
        temperature=Config.TEMPERATURE,
        max_tokens=250,
    )

    return clean(res.choices[0].message.content)


# ==================================================
# VISUAL PROMPT MAPPER (KEY PART)
# ==================================================

def sentence_to_image_prompt(sentence: str) -> str:
    s = sentence.lower()

    if "car" in s and ("dead" in s or "found" in s or "died" in s):
        return (
            "3D cartoon style, night scene, man slumped lifeless in driver seat of a car, "
            "streetlight outside window, cinematic lighting, dark mood, no gore"
        )

    if "room" in s or "apartment" in s or "home" in s:
        return (
            "3D cartoon style, dark bedroom crime scene, bed visible, "
            "knife on floor, subtle blood stain, moody cinematic lighting"
        )

    if "police" in s or "investigation" in s:
        return (
            "3D cartoon style, police officers examining a crime scene at night, "
            "flashlight beams, serious atmosphere, cinematic shadows"
        )

    if "missing" in s or "disappeared" in s:
        return (
            "3D cartoon style, empty street at night, parked car, "
            "foggy atmosphere, mysterious mood, cinematic lighting"
        )

    return (
        "3D cartoon style, mysterious crime-related scene, "
        "cinematic lighting, investigative mood"
    )


# ==================================================
# BEAT DERIVATION
# ==================================================

def derive_beats(script: str) -> List[Dict]:
    sentences = re.findall(r"[^.!?]+[.!?]?", script)
    beats = []

    for i, s in enumerate(sentences):
        words = wc(s)

        if i == 0:
            scene = "HOOK"
            dur = round(words / 3.2, 1)
        elif i == len(sentences) - 1:
            scene = "LOOP"
            dur = round(words / 3.6, 1)
        else:
            scene = "ESCALATION"
            dur = round(words / 2.4, 1)

        beats.append({
            "beat_id": i + 1,
            "scene_type": scene,
            "text": s.strip(),
            "word_count": words,
            "estimated_duration": dur,
            "image_prompt": sentence_to_image_prompt(s)
        })

    return beats


# ==================================================
# GENERATION LOOP
# ==================================================

def generate(client: ChatCompletionsClient, case: Dict) -> Tuple[str, List[Dict]]:
    prompt = build_prompt(case)
    best = None

    for attempt in range(1, Config.MAX_ATTEMPTS + 1):
        print(f"🔄 Attempt {attempt}/{Config.MAX_ATTEMPTS}")

        try:
            script = call_ai(client, prompt)
            words = wc(script)

            if words < Config.WORDS_MIN:
                print(f"⚠️ Too short ({words} words)")
                time.sleep(Config.RETRY_DELAY)
                continue

            if words > Config.WORDS_MAX:
                print(f"⚠️ Too long ({words} words)")
                time.sleep(Config.RETRY_DELAY)
                continue

            beats = derive_beats(script)
            return script, beats

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(Config.RETRY_DELAY)

        best = script

    beats = derive_beats(best)
    return best, beats


# ==================================================
# SAVE
# ==================================================

def save(script: str, beats: List[Dict]):
    Path(Config.SCRIPT_FILE).write_text(script, encoding="utf-8")

    payload = {
        "metadata": {
            "words": wc(script),
            "beats": len(beats),
            "estimated_duration": round(sum(b["estimated_duration"] for b in beats), 1),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "beats": beats
    }

    Path(Config.BEATS_FILE).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("💾 script.txt and beats.json saved")


# ==================================================
# MAIN
# ==================================================

def main():
    print("🎬 Mystery Script Generator")

    case = load_case()
    client = init_client()

    script, beats = generate(client, case)
    save(script, beats)

    print("\n📜 SCRIPT")
    print("-" * 50)
    print(script)
    print("-" * 50)


if __name__ == "__main__":
    main()
