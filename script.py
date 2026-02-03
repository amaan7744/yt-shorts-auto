#!/usr/bin/env python3
"""
True Crime Shorts Generator
ABSOLUTE ASSET-LOCKED MATCHING

RULES:
• EVERY asset on disk MUST be declared
• Filenames must match EXACTLY
• NO script changes
• FAIL if mismatch
"""

import sys
import json
import random
from pathlib import Path

# ==================================================
# CONFIG
# ==================================================

ASSET_DIR = Path("asset")
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"
BLOCK_DURATION = 5.0

CTA_LINE = "Follow for part two — what do you think really happened?"

# ==================================================
# 🔒 EXACT ASSET REGISTRY (VERBATIM)
# ==================================================

ASSET_KEYWORDS = {

    # PEOPLE / DISCOVERY
    "5_second_anime_style_cinematic_scene_a_woman_lying.mp4": ["woman lying"],
    "5_second_anime_style_cinematic_scene_a_young_woman.mp4": ["young woman"],
    "anime_style_cinematic_video_elderly_woman_lying_near.mp4": ["elderly woman"],
    "anime_style_cinematic_video_elderly_woman_slumped_near.mp4": ["elderly woman"],
    "anime_style_scene_elderly_woman_lying_peacefully_on.mp4": ["elderly woman"],
    "anime_style_cartoon_video_elderly_man_seated_in.mp4": ["elderly man"],
    "elderly_man_lying_on_stair_landing_broken.mp4": ["elderly man"],
    "stylized_anime_cartoon_woman_collapsed_near_a.mp4": ["woman collapsed"],
    "stylized_anime_cartoon_video_a_human_figure.mp4": ["human figure"],

    # CHILD / FAMILY
    "a_child_s_bedroom_with_toys_scattered_on.mp4": ["child bedroom"],
    "crayon_drawing_on_the_floor_dark_shapes.mp4": ["crayon drawing"],
    "anime_style_video_school_backpack_on_sidewalk_early.mp4": ["school backpack"],
    "how_could_a_child_disappear_without_making.mp4": ["child disappeared"],
    "if_a_child_saw_everything_why_did.mp4": ["child witness"],
    "if_a_child_saw_it_why_was.mp4": ["child witness"],
    "what_went_wrong_during_a_normal_family.mp4": ["family home"],

    # ROOMS / INTERIORS
    "anime_style_scene_bedroom_with_ceiling_fan_rotating.mp4": ["bedroom"],
    "anime_style_cinematic_scene_dark_bedroom_wall_clock.mp4": ["bedroom"],
    "dark_room.mp4": ["dark room"],
    "hallway.mp4": ["hallway"],
    "animate_the_scene_cabin_in_forest_at.mp4": ["cabin"],
    "anime_style_cinematic_scene_dim_motel_room_neon.mp4": ["motel room"],
    "anime_style_cinematic_video_backyard_at_dawn_uneven.mp4": ["backyard"],
    "anime_style_scene_swing_moving_slowly_by_itself.mp4": ["swing"],

    # DOORS
    "animate_why_was_the_door_locked_from.mp4": ["door locked"],
    "closing_door.mp4": ["closing door"],
    "who_rang_the_doorbell_and_never_left.mp4": ["doorbell"],

    # BATHROOM
    "anime_cartoon_realism_bathroom_door_half_open_bright.mp4": ["bathroom"],
    "anime_style_scene_bathroom_door_closed_police_flashlight.mp4": ["bathroom"],
    "anime_style_scene_sink_overflowing_water_spilling_onto.mp4": ["sink overflowing"],
    "stylized_anime_cartoon_foggy_bathroom_mirror_with.mp4": ["foggy mirror"],

    # CAFE / TABLE (BOTH VARIANTS — EXACT)
    "anime_style_video_a_quiet_cafe_at_night.mp4": ["cafe"],
    "anime_style_video_a_quiet_caf_at_night.mp4": ["cafe"],

    "why_was_dinner_still_warm_when_they.mp4": ["dinner table"],

    # STREET / OUTDOOR
    "blurred_alley.mp4": ["alley"],
    "night_alley.mp4": ["alley"],
    "what_happened_on_this_street_after_midnight.mp4": ["street midnight"],
    "empty_bus_stop_at_night_streetlight_flickering.mp4": ["bus stop"],
    "bridge.mp4": ["bridge"],
    "window_pov.mp4": ["window"],

    # VEHICLES (BOTH VARIANTS — EXACT)
    "car_pov.mp4": ["car pov"],
    "person_driving.mp4": ["person driving"],
    "person driving.mp4": ["person driving"],

    "parked_car.mp4": ["parked car"],
    "empty_highway_at_night_car_parked_on.mp4": ["empty highway"],
    "anime_style_scene_parked_car_at_night_trunk.mp4": ["car trunk"],
    "anime_style_cinematic_shot_man_slumped_in_driver_s.mp4": ["driver seat"],

    # DIGITAL / CCTV
    "mobilemessage.mp4": ["text message"],
    "anime_style_cinematic_close_up_phone_glowing_in_a.mp4": ["phone glowing"],
    "cctv.mp4": ["cctv"],
    "stylized_anime_scene_elevator_interior_man_standing.mp4": ["elevator"],

    # OFFICE
    "stylized_anime_scene_office_desk_with_laptop.mp4": ["office desk"],
    "why_was_his_computer_still_logged_in.mp4": ["computer"],
    "why_did_his_coworkers_hear_nothing_that.mp4": ["coworkers"],

    # MEDICAL
    "elderly_man_in_a_hospital_bed_heart.mp4": ["hospital bed"],
    "empty_hospital_hallway_gurney_parked_sideways_shadowy.mp4": ["hospital hallway"],

    # ROOFTOP / TRAIN
    "rooftop.mp4": ["rooftop"],
    "what_happened_on_this_rooftop_before_sunrise.mp4": ["rooftop"],
    "stylized_anime_cartoon_scene_empty_train_platform.mp4": ["train platform"],

    # MISC
    "shadow.mp4": ["shadow"],
    "evidence.mp4": ["evidence"],
    "interogationroom.mp4": ["interrogation"],
    "leftover.mp4": ["belongings"],
    "did_he_fall_or_was_he_pushed.mp4": ["fell or pushed"],
}

# ==================================================
# VALIDATION
# ==================================================

def validate_assets():
    disk_assets = sorted(f.name for f in ASSET_DIR.glob("*.mp4"))
    declared_assets = sorted(ASSET_KEYWORDS.keys())

    missing_declared = set(disk_assets) - set(declared_assets)
    missing_disk = set(declared_assets) - set(disk_assets)

    if missing_declared:
        sys.exit(f"❌ Assets on disk NOT declared: {missing_declared}")
    if missing_disk:
        sys.exit(f"❌ Assets declared but MISSING on disk: {missing_disk}")

# ==================================================
# SCRIPT (UNCHANGED)
# ==================================================

SCRIPT_LINES = [
    "Was this just a normal moment before everything changed?",
    "Something unexpected happened at a location tied to this case.",
    "The incident involved someone who should have been safe there.",
    "The discovery was made later, raising immediate questions.",
    "One detail didn’t match the official explanation.",
    "The surrounding context only made the timeline stranger.",
    CTA_LINE
]

# ==================================================
# MAIN
# ==================================================

def main():
    validate_assets()

    assets = list(ASSET_KEYWORDS.keys())
    beats = []

    for i, line in enumerate(SCRIPT_LINES):
        beats.append({
            "beat_id": i + 1,
            "text": line,
            "asset_file": random.choice(assets),
            "duration": BLOCK_DURATION
        })

    Path(SCRIPT_FILE).write_text(" ".join(SCRIPT_LINES), encoding="utf-8")
    Path(BEATS_FILE).write_text(json.dumps({"beats": beats}, indent=2), encoding="utf-8")

    print("✅ All assets validated. Script generated successfully.")

if __name__ == "__main__":
    main()
