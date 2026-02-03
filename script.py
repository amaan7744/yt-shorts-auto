#!/usr/bin/env python3
"""
True Crime Shorts Generator
ABSOLUTE ASSET-LOCKED MATCHING
FULL ASSET REGISTRY (64 ASSETS)
STRUCTURE-LOCKED SCRIPT
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
MAX_ATTEMPTS = 3
RETRY_DELAY = 1.5

CTA_LINE = "Follow for part two."

# ==================================================
# 🔒 COMPLETE ASSET REGISTRY (EVERY FILE)
# ==================================================

ASSET_KEYWORDS = {
    # PEOPLE / DISCOVERY
    "5_second_anime_style_cinematic_scene_a_woman_lying.mp4": ["woman lying", "body on floor"],
    "5_second_anime_style_cinematic_scene_a_young_woman.mp4": ["young woman", "collapsed"],
    "anime_style_cinematic_video_elderly_woman_lying_near.mp4": ["elderly woman", "lying near"],
    "anime_style_cinematic_video_elderly_woman_slumped_near.mp4": ["elderly woman", "slumped"],
    "anime_style_scene_elderly_woman_lying_peacefully_on.mp4": ["elderly woman", "peacefully lying"],
    "anime_style_cartoon_video_elderly_man_seated_in.mp4": ["elderly man", "armchair"],
    "elderly_man_lying_on_stair_landing_broken.mp4": ["elderly man", "stairs", "fallen"],
    "stylized_anime_cartoon_woman_collapsed_near_a.mp4": ["woman collapsed"],
    "stylized_anime_cartoon_video_a_human_figure.mp4": ["human figure", "silhouette"],

    # CHILD / SCHOOL
    "a_child_s_bedroom_with_toys_scattered_on.mp4": ["child bedroom", "toys"],
    "crayon_drawing_on_the_floor_dark_shapes.mp4": ["crayon drawing", "child drawing"],
    "anime_style_video_school_backpack_on_sidewalk_early.mp4": ["school backpack", "sidewalk"],
    "how_could_a_child_disappear_without_making.mp4": ["child disappeared"],
    "if_a_child_saw_everything_why_did.mp4": ["child witness"],
    "if_a_child_saw_it_why_was.mp4": ["child saw"],
    "what_went_wrong_during_a_normal_family.mp4": ["family home", "normal evening"],

    # ROOMS / INTERIORS
    "anime_style_scene_bedroom_with_ceiling_fan_rotating.mp4": ["bedroom", "ceiling fan"],
    "anime_style_cinematic_scene_dark_bedroom_wall_clock.mp4": ["bedroom", "wall clock"],
    "dark_room.mp4": ["dark room"],
    "hallway.mp4": ["hallway", "corridor"],
    "animate_the_scene_cabin_in_forest_at.mp4": ["cabin", "forest"],
    "anime_style_cinematic_scene_dim_motel_room_neon.mp4": ["motel room", "neon light"],
    "anime_style_cinematic_video_backyard_at_dawn_uneven.mp4": ["backyard", "dawn"],
    "anime_style_scene_swing_moving_slowly_by_itself.mp4": ["swing moving", "playground"],

    # BATHROOM
    "anime_cartoon_realism_bathroom_door_half_open_bright.mp4": ["bathroom door"],
    "anime_style_scene_bathroom_door_closed_police_flashlight.mp4": ["bathroom locked"],
    "anime_style_scene_sink_overflowing_water_spilling_onto.mp4": ["sink overflowing"],
    "stylized_anime_cartoon_foggy_bathroom_mirror_with.mp4": ["foggy mirror"],

    # CAFE / TABLE
    "anime_style_video_a_quiet_cafe_at_night.mp4": ["quiet cafe"],
    "anime_style_video_a_quiet_caf_at_night.mp4": ["quiet cafe"],
    "why_was_dinner_still_warm_when_they.mp4": ["dinner table"],

    # STREET / OUTDOOR
    "blurred_alley.mp4": ["alley"],
    "night_alley.mp4": ["dark alley"],
    "what_happened_on_this_street_after_midnight.mp4": ["street midnight"],
    "empty_bus_stop_at_night_streetlight_flickering.mp4": ["bus stop"],
    "bridge.mp4": ["bridge"],
    "window_pov.mp4": ["window pov"],
    "who_rang_the_doorbell_and_never_left.mp4": ["doorbell"],

    # VEHICLES
    "car_pov.mp4": ["car pov"],
    "person_driving.mp4": ["person driving"],
    "person driving.mp4": ["person driving"],
    "parked_car.mp4": ["parked car"],
    "empty_highway_at_night_car_parked_on.mp4": ["empty highway"],
    "anime_style_scene_parked_car_at_night_trunk.mp4": ["car trunk"],
    "anime_style_cinematic_shot_man_slumped_in_driver_s.mp4": ["man slumped driver"],

    # DIGITAL / PHONE
    "mobilemessage.mp4": ["text message"],
    "anime_style_cinematic_close_up_phone_glowing_in_a.mp4": ["phone glowing"],

    # OFFICE / CCTV
    "stylized_anime_scene_office_desk_with_laptop.mp4": ["office desk"],
    "why_was_his_computer_still_logged_in.mp4": ["computer logged in"],
    "why_did_his_coworkers_hear_nothing_that.mp4": ["coworkers"],
    "cctv.mp4": ["cctv"],
    "stylized_anime_scene_elevator_interior_man_standing.mp4": ["elevator"],
    "closing_door.mp4": ["closing door"],

    # HOSPITAL / MEDICAL
    "elderly_man_in_a_hospital_bed_heart.mp4": ["hospital bed"],
    "empty_hospital_hallway_gurney_parked_sideways_shadowy.mp4": ["hospital hallway"],

    # ROOFTOP / TRAIN
    "rooftop.mp4": ["rooftop"],
    "what_happened_on_this_rooftop_before_sunrise.mp4": ["rooftop sunrise"],
    "stylized_anime_cartoon_scene_empty_train_platform.mp4": ["train platform"],

    # MISC
    "shadow.mp4": ["shadow"],
    "evidence.mp4": ["evidence"],
    "interogationroom.mp4": ["interrogation"],
    "leftover.mp4": ["belongings"],
    "did_he_fall_or_was_he_pushed.mp4": ["fell or pushed"]
}

# ==================================================
# VALIDATION
# ==================================================

def validate_assets():
    disk = sorted(f.name for f in ASSET_DIR.glob("*.mp4"))
    declared = sorted(ASSET_KEYWORDS.keys())

    missing_code = set(disk) - set(declared)
    missing_disk = set(declared) - set(disk)

    if missing_code:
        sys.exit(f"❌ Assets on disk NOT declared: {missing_code}")
    if missing_disk:
        sys.exit(f"❌ Assets declared but missing on disk: {missing_disk}")

# ==================================================
# SCRIPT STRUCTURE (LOCKED)
# ==================================================

FALLBACK_SCRIPT = [
    "Was this just another normal moment before everything changed?",
    "Something happened at a location connected to this case.",
    "The victim was found in circumstances that raised questions.",
    "The discovery happened later than anyone expected.",
    "One detail immediately didn’t add up.",
    "The background makes the timeline even stranger.",
    "Follow for part two, what do you think really happened?"
]

# ==================================================
# MAIN
# ==================================================

def main():
    validate_assets()

    script = FALLBACK_SCRIPT

    beats = []
    for i, line in enumerate(script):
        matches = [a for a, k in ASSET_KEYWORDS.items() if any(w in line.lower() for w in k)]
        if not matches:
            matches = list(ASSET_KEYWORDS.keys())

        beats.append({
            "beat_id": i + 1,
            "text": line,
            "asset_file": random.choice(matches),
            "duration": BLOCK_DURATION
        })

    Path(SCRIPT_FILE).write_text(" ".join(script), encoding="utf-8")
    Path(BEATS_FILE).write_text(json.dumps({"beats": beats}, indent=2), encoding="utf-8")

    print("✅ Script generated. All assets registered and validated.")

if __name__ == "__main__":
    main()
