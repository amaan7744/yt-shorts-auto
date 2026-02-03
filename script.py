#!/usr/bin/env python3
"""
True Crime Shorts Generator
ABSOLUTE ASSET-LOCKED MATCHING
ASSET-COMPLETE + CI-SAFE
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

MODEL_CANDIDATES = [
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768"
]

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"
ASSET_DIR = Path("asset")

BLOCK_DURATION = 5.0
TEMPERATURE = 0.25
MAX_ATTEMPTS = 4
RETRY_DELAY = 1.5

CTA_LINE = "Follow for part two."
ENGAGEMENT_QUESTIONS = [
    "What do you think really happened?",
    "Which detail doesn’t add up?",
    "Did you notice what was missing?"
]

# ==================================================
# 🔒 COMPLETE ASSET REGISTRY (EVERY ASSET)
# ==================================================

ASSET_KEYWORDS = {
    # PEOPLE / DISCOVERY
    "5_second_anime_style_cinematic_scene_a_woman_lying.mp4": ["woman lying", "found dead", "body on floor", "living room"],
    "5_second_anime_style_cinematic_scene_a_young_woman.mp4": ["young woman", "collapsed", "discovered"],
    "anime_style_cinematic_video_elderly_woman_lying_near.mp4": ["elderly woman", "lying near", "found at home"],
    "anime_style_cinematic_video_elderly_woman_slumped_near.mp4": ["elderly woman", "slumped", "chair"],
    "anime_style_cartoon_video_elderly_man_seated_in.mp4": ["elderly man", "armchair", "seated"],
    "stylized_anime_cartoon_woman_collapsed_near_a.mp4": ["woman collapsed", "indoors"],

    # ROOMS
    "a_child_s_bedroom_with_toys_scattered_on.mp4": ["child bedroom", "toys", "child room"],
    "anime_style_scene_bedroom_with_ceiling_fan_rotating.mp4": ["bedroom", "ceiling fan"],
    "anime_style_cinematic_scene_dark_bedroom_wall_clock.mp4": ["bedroom", "wall clock"],
    "dark_room.mp4": ["dark room", "no lights"],

    # BATHROOM
    "anime_cartoon_realism_bathroom_door_half_open_bright.mp4": ["bathroom door", "half open"],
    "anime_style_scene_bathroom_door_closed_police_flashlight.mp4": ["bathroom door locked", "police flashlight"],
    "anime_style_scene_sink_overflowing_water_spilling_onto.mp4": ["sink overflowing", "water running"],
    "stylized_anime_cartoon_foggy_bathroom_mirror_with.mp4": ["foggy mirror", "bathroom mirror"],

    # CHILD / EMOTIONAL
    "crayon_drawing_on_the_floor_dark_shapes.mp4": ["child drawing", "crayon"],
    "how_could_a_child_disappear_without_making.mp4": ["child disappear", "missing child"],
    "if_a_child_saw_everything_why_did.mp4": ["child witness"],
    "if_a_child_saw_it_why_was.mp4": ["child saw"],

    # CAFE / TABLE
    "anime_style_video_a_quiet_cafe_at_night.mp4": ["cafe", "coffee shop", "table"],
    "why_was_dinner_still_warm_when_they.mp4": ["dinner table", "food still warm"],

    # STREET / OUTDOOR
    "blurred_alley.mp4": ["alley", "narrow street"],
    "night_alley.mp4": ["dark alley"],
    "what_happened_on_this_street_after_midnight.mp4": ["street after midnight"],
    "empty_bus_stop_at_night_streetlight_flickering.mp4": ["bus stop", "streetlight"],
    "bridge.mp4": ["bridge", "overpass"],
    "window_pov.mp4": ["window", "looking out"],

    # VEHICLES
    "car_pov.mp4": ["driving", "car pov"],
    "person_driving.mp4": ["person driving"],
    "parked_car.mp4": ["parked car"],
    "empty_highway_at_night_car_parked_on.mp4": ["empty highway", "abandoned car"],
    "anime_style_scene_parked_car_at_night_trunk.mp4": ["car trunk"],

    # OFFICE
    "stylized_anime_scene_office_desk_with_laptop.mp4": ["office desk", "laptop"],
    "why_was_his_computer_still_logged_in.mp4": ["computer logged in"],
    "why_did_his_coworkers_hear_nothing_that.mp4": ["coworkers", "office night"],

    # CCTV / POV
    "cctv.mp4": ["cctv", "surveillance"],
    "stylized_anime_scene_elevator_interior_man_standing.mp4": ["elevator"],
    "closing_door.mp4": ["closing door"],

    # HOSPITAL
    "elderly_man_in_a_hospital_bed_heart.mp4": ["hospital bed", "heart monitor"],
    "empty_hospital_hallway_gurney_parked_sideways_shadowy.mp4": ["hospital hallway", "gurney"],

    # ROOFTOP
    "rooftop.mp4": ["rooftop"],
    "what_happened_on_this_rooftop_before_sunrise.mp4": ["rooftop before sunrise"],

    # MISC
    "shadow.mp4": ["shadow", "figure watching"],
    "evidence.mp4": ["evidence", "crime scene"],
    "interogationroom.mp4": ["interrogation"],
    "leftover.mp4": ["left behind", "belongings"],
    "did_he_fall_or_was_he_pushed.mp4": ["fell", "pushed", "stairs"],
    "stylized_anime_cartoon_scene_empty_train_platform.mp4": ["train platform"]
}

# ==================================================
# VALIDATION (MANDATORY)
# ==================================================

def validate_assets():
    disk_assets = sorted(f.name for f in ASSET_DIR.glob("*.mp4"))
    declared_assets = sorted(ASSET_KEYWORDS.keys())

    missing_in_code = set(disk_assets) - set(declared_assets)
    missing_on_disk = set(declared_assets) - set(disk_assets)

    print("\n📦 ASSET REGISTRY (ALL):")
    for a in declared_assets:
        print(" -", a)

    if missing_in_code:
        sys.exit(f"❌ Assets on disk NOT declared: {missing_in_code}")

    if missing_on_disk:
        sys.exit(f"❌ Assets declared but MISSING on disk: {missing_on_disk}")

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
# ASSET PICKING
# ==================================================

def pick_asset(sentence: str) -> str:
    s = sentence.lower()
    matches = [a for a, kws in ASSET_KEYWORDS.items() if any(k in s for k in kws)]
    if not matches:
        raise RuntimeError(f"❌ No asset matches sentence: {sentence}")
    return random.choice(matches)

# ==================================================
# MAIN
# ==================================================

def main():
    validate_assets()   # 🔥 THIS IS THE KEY PART
    client = init_client()
    case = load_case()

    script = [
        "Was this a quiet moment before everything changed?",
        "The incident unfolded at a location tied directly to the case.",
        "Investigators noticed a small but critical detail at the scene.",
        "Police reviewed footage and questioned people connected to it.",
        "One fact didn’t align with the official timeline.",
        "That missing piece still hasn’t been explained.",
        "What do you think really happened?"
    ]

    beats = []
    for i, s in enumerate(script):
        beats.append({
            "beat_id": i + 1,
            "text": s,
            "asset_file": pick_asset(s),
            "duration": BLOCK_DURATION
        })

    final_script = " ".join(script) + " " + CTA_LINE + " " + random.choice(ENGAGEMENT_QUESTIONS)

    Path(SCRIPT_FILE).write_text(final_script)
    Path(BEATS_FILE).write_text(json.dumps({"beats": beats}, indent=2))

    print("\n✅ All assets validated, script generated safely")

# ==================================================
if __name__ == "__main__":
    main()
