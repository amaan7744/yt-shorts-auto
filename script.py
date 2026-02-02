#!/usr/bin/env python3
"""
True Crime Shorts Generator
ABSOLUTE ASSET-LOCKED MATCHING

RULES:
• EVERY asset has explicit keywords
• Sentence MUST match keywords
• Asset picked ONLY from matching keywords
• NO random atmosphere
• FAIL if no match
• MODEL-SAFE (handles Groq deprecations)
"""

import os
import sys
import json
import time
import re
import random
from pathlib import Path
from groq import Groq

# ==================================================
# CONFIG
# ==================================================

# Groq-safe models (ordered)
MODEL_CANDIDATES = [
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768"
]

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"
ASSET_DIR = Path("asset")

BLOCK_DURATION = 5.0
TEMPERATURE = 0.35
MAX_ATTEMPTS = 4
RETRY_DELAY = 1.5

CTA_LINE = "Follow for part two."
ENGAGEMENT_QUESTIONS = [
    "What do you think really happened?",
    "Which detail doesn’t add up?",
    "Did you notice what was missing?"
]

# ==================================================
# 🔒 ASSET → KEYWORDS (EVERY FILE INCLUDED)
# ==================================================

ASSET_KEYWORDS = {
    "5_second_anime_style_cinematic_scene_a_woman_lying.mp4":
        ["woman lying", "found dead", "living room", "body on floor"],
    "5_second_anime_style_cinematic_scene_a_young_woman.mp4":
        ["young woman", "collapsed", "discovered"],
    "anime_style_cinematic_video_elderly_woman_lying_near.mp4":
        ["elderly woman", "lying near", "found at home"],
    "anime_style_cinematic_video_elderly_woman_slumped_near.mp4":
        ["elderly woman", "slumped", "chair", "collapsed"],
    "anime_style_cartoon_video_elderly_man_seated_in.mp4":
        ["elderly man", "seated", "armchair"],
    "stylized_anime_cartoon_woman_collapsed_near_a.mp4":
        ["woman collapsed", "indoors"],

    "a_child_s_bedroom_with_toys_scattered_on.mp4":
        ["child bedroom", "toys", "child room"],
    "anime_style_scene_bedroom_with_ceiling_fan_rotating.mp4":
        ["bedroom", "ceiling fan", "night"],
    "anime_style_cinematic_scene_dark_bedroom_wall_clock.mp4":
        ["bedroom", "wall clock", "late night"],
    "dark_room.mp4":
        ["dark room", "inside", "no lights"],

    "anime_cartoon_realism_bathroom_door_half_open_bright.mp4":
        ["bathroom door", "half open"],
    "anime_style_scene_bathroom_door_closed_police_flashlight.mp4":
        ["bathroom door locked", "police flashlight"],
    "anime_style_scene_sink_overflowing_water_spilling_onto.mp4":
        ["sink overflowing", "water running", "bathroom"],
    "stylized_anime_cartoon_foggy_bathroom_mirror_with.mp4":
        ["foggy mirror", "bathroom mirror"],

    "crayon_drawing_on_the_floor_dark_shapes.mp4":
        ["child drawing", "crayon drawing"],

    "anime_style_video_a_quiet_cafe_at_night.mp4":
        ["cafe", "coffee shop", "table", "cup"],

    "blurred_alley.mp4":
        ["alley", "narrow street"],
    "night_alley.mp4":
        ["dark alley", "night street"],

    "car_pov.mp4":
        ["driving", "car pov"],
    "parked_car.mp4":
        ["parked car"],

    "elderly_man_in_a_hospital_bed_heart.mp4":
        ["hospital bed", "heart monitor"],
    "empty_hospital_hallway_gurney_parked_sideways_shadowy.mp4":
        ["hospital hallway", "gurney"],

    "rooftop.mp4":
        ["rooftop"],

    "cctv.mp4":
        ["cctv", "surveillance"],
    "closing_door.mp4":
        ["closing door", "last moment"],

    "shadow.mp4":
        ["shadow", "figure watching"],
    "evidence.mp4":
        ["evidence", "crime scene"],
    "interogationroom.mp4":
        ["interrogation", "questioned"]
}

# ==================================================
# INIT
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        sys.exit("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

def load_case():
    return json.loads(Path(CASE_FILE).read_text())

# ==================================================
# ASSET PICKING (STRICT)
# ==================================================

def pick_asset(sentence: str) -> str:
    s = sentence.lower()
    matches = [a for a, kws in ASSET_KEYWORDS.items() if any(k in s for k in kws)]

    if not matches:
        raise RuntimeError(f"❌ No asset matches sentence: {sentence}")

    asset = random.choice(matches)
    if not (ASSET_DIR / asset).exists():
        raise FileNotFoundError(f"❌ Asset missing: {asset}")

    return asset

# ==================================================
# SCRIPT GENERATION (MODEL-SAFE)
# ==================================================

def generate_script(client, summary):
    for model in MODEL_CANDIDATES:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                res = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Write visual-first true crime Shorts."},
                        {"role": "user", "content": summary}
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=240
                )

                text = res.choices[0].message.content.strip()
                sentences = re.findall(r"[^.!?]+[.!?]?", text)

                if len(sentences) == 7:
                    print(f"✅ Script generated using {model}")
                    return sentences

            except Exception as e:
                msg = str(e).lower()

                # model is dead → skip permanently
                if "decommissioned" in msg or "does not exist" in msg or "model_not_found" in msg:
                    print(f"⛔ Model disabled: {model}")
                    break

                print(f"⚠️ {model} attempt {attempt} failed: {e}")
                time.sleep(RETRY_DELAY)

    raise RuntimeError("❌ All models failed")

# ==================================================
# MAIN
# ==================================================

def main():
    client = init_client()
    case = load_case()

    script = generate_script(client, case["summary"])

    beats = []
    for i, s in enumerate(script):
        beats.append({
            "beat_id": i + 1,
            "text": s,
            "asset_file": pick_asset(s),
            "duration": BLOCK_DURATION
        })

    final_script = (
        " ".join(script)
        + " "
        + CTA_LINE
        + " "
        + random.choice(ENGAGEMENT_QUESTIONS)
    )

    Path(SCRIPT_FILE).write_text(final_script, encoding="utf-8")
    Path(BEATS_FILE).write_text(json.dumps({"beats": beats}, indent=2), encoding="utf-8")

    print("✅ Script + assets matched with ZERO guesswork")

# ==================================================
if __name__ == "__main__":
    main()
