"""
ASSET REGISTRY — STRUCTURED & DISAMBIGUATED

GOALS
✔ No overlapping semantic meaning between assets
✔ Clear visual intent per asset
✔ Organized categories
✔ Stronger semantic matching
✔ No script logic here
✔ No filename guessing
"""

from pathlib import Path
import sys


# =========================================================
# DIRECTORIES
# =========================================================

VIDEO_ASSET_DIR = Path("asset")
HOOK_IMAGE_DIR = Path("asset/hook_static")


# =========================================================
# VIDEO ASSETS — STRUCTURED BY CATEGORY
# Each asset = unique scene intent
# Avoid generic words like "figure", "scene", "room"
# =========================================================

VIDEO_ASSET_KEYWORDS = {

    # ---------------------------------------------------------
    # BODY / VICTIM / COLLAPSE SCENES
    # ---------------------------------------------------------

    "5_second_anime_style_cinematic_scene_a_woman_lying.mp4": [
        "dead_woman", "corpse", "female_victim", "death_scene", "body_found"
    ],

    "5_second_anime_style_cinematic_scene_a_young_woman.mp4": [
        "young_female", "victim_identity", "female_character", "young_victim"
    ],

    "anime_style_cinematic_video_elderly_woman_lying_near.mp4": [
        "elderly_woman_dead", "old_age_victim", "elderly_body"
    ],

    "anime_style_cinematic_video_elderly_woman_slumped_near.mp4": [
        "elderly_collapse", "old_woman_fainted"
    ],

    "anime_style_scene_elderly_woman_lying_peacefully_on.mp4": [
        "elderly_peaceful_death", "natural_death_scene"
    ],

    "stylized_anime_cartoon_woman_collapsed_near_a.mp4": [
        "woman_collapsed", "sudden_collapse", "medical_emergency"
    ],

    "stylized_anime_cartoon_video_a_human_figure.mp4": [
        "unknown_silhouette", "mysterious_person", "shadow_figure"
    ],

    "anime_style_cinematic_shot_man_slumped_in_driver_s.mp4": [
        "driver_dead", "driver_unconscious", "car_victim"
    ],

    "elderly_man_lying_on_stair_landing_broken.mp4": [
        "elderly_fall_victim", "staircase_accident", "fall_death"
    ],


    # ---------------------------------------------------------
    # CHILD / FAMILY / DOMESTIC
    # ---------------------------------------------------------

    "a_child_s_bedroom_with_toys_scattered_on.mp4": [
        "child_room", "messy_child_bedroom", "child_environment"
    ],

    "crayon_drawing_on_the_floor_dark_shapes.mp4": [
        "child_drawing", "child_clue", "crayon_evidence"
    ],

    "anime_style_video_school_backpack_on_sidewalk_early.mp4": [
        "missing_child_clue", "abandoned_backpack"
    ],

    "how_could_a_child_disappear_without_making.mp4": [
        "child_missing_case", "child_disappearance"
    ],

    "if_a_child_saw_everything_why_did.mp4": [
        "child_witness_testimony"
    ],

    "if_a_child_saw_it_why_was.mp4": [
        "child_eye_witness"
    ],

    "what_went_wrong_during_a_normal_family.mp4": [
        "family_tragedy", "domestic_incident"
    ],


    # ---------------------------------------------------------
    # INTERIOR LOCATIONS
    # ---------------------------------------------------------

    "anime_style_scene_bedroom_with_ceiling_fan_rotating.mp4": [
        "empty_bedroom", "quiet_room"
    ],

    "anime_style_cinematic_scene_dark_bedroom_wall_clock.mp4": [
        "night_bedroom", "late_night_scene"
    ],

    "dark_room.mp4": [
        "dark_interior", "shadowy_space"
    ],

    "hallway.mp4": [
        "apartment_hallway", "indoor_corridor"
    ],

    "anime_style_cinematic_scene_dim_motel_room_neon.mp4": [
        "motel_room", "temporary_stay_location"
    ],

    "animate_the_scene_cabin_in_forest_at.mp4": [
        "isolated_cabin", "remote_location"
    ],

    "anime_style_cinematic_video_backyard_at_dawn_uneven.mp4": [
        "backyard_morning", "residential_exterior"
    ],

    "anime_style_scene_swing_moving_slowly_by_itself.mp4": [
        "eerie_playground", "abandoned_play_area"
    ],


    # ---------------------------------------------------------
    # ENTRY / DOOR EVENTS
    # ---------------------------------------------------------

    "animate_why_was_the_door_locked_from.mp4": [
        "locked_room_mystery"
    ],

    "closing_door.mp4": [
        "door_closing_event"
    ],

    "who_rang_the_doorbell_and_never_left.mp4": [
        "unknown_visitor_event"
    ],


    # ---------------------------------------------------------
    # BATHROOM / WATER CLUES
    # ---------------------------------------------------------

    "anime_cartoon_realism_bathroom_door_half_open_bright.mp4": [
        "bathroom_entry"
    ],

    "anime_style_scene_bathroom_door_closed_police_flashlight.mp4": [
        "police_search_scene"
    ],

    "anime_style_scene_sink_overflowing_water_spilling_onto.mp4": [
        "water_overflow", "bathroom_flood"
    ],

    "stylized_anime_cartoon_foggy_bathroom_mirror_with.mp4": [
        "foggy_mirror_clue"
    ],


    # ---------------------------------------------------------
    # FOOD / DAILY LIFE
    # ---------------------------------------------------------

    "anime_style_video_a_quiet_caf_at_night.mp4": [
        "night_cafe", "quiet_public_space"
    ],

    "why_was_dinner_still_warm_when_they.mp4": [
        "unfinished_meal", "abandoned_food"
    ],

    "anime_style_cartoon_video_elderly_man_seated_in.mp4": [
        "elderly_man_sitting", "old_man_character"
    ],


    # ---------------------------------------------------------
    # OUTDOOR / STREET
    # ---------------------------------------------------------

    "blurred_alley.mp4": [
        "suspicious_alley"
    ],

    "night_alley.mp4": [
        "dark_alley_night"
    ],

    "what_happened_on_this_street_after_midnight.mp4": [
        "midnight_street_event"
    ],

    "empty_bus_stop_at_night_streetlight_flickering.mp4": [
        "empty_bus_stop"
    ],

    "bridge.mp4": [
        "bridge_location"
    ],

    "window_pov.mp4": [
        "window_view_pov"
    ],

    "what_happened_on_this_rooftop_before_sunrise.mp4": [
        "rooftop_scene", "rooftop_incident"
    ],

    "rooftop.mp4": [
        "rooftop_location", "building_top"
    ],

    "stylized_anime_cartoon_scene_empty_train_platform.mp4": [
        "train_station", "empty_platform"
    ],


    # ---------------------------------------------------------
    # VEHICLE / TRANSPORT
    # ---------------------------------------------------------

    "car_pov.mp4": [
        "driving_pov"
    ],

    "person driving.mp4": [
        "driver_character"
    ],

    "parked_car.mp4": [
        "parked_vehicle"
    ],

    "empty_highway_at_night_car_parked_on.mp4": [
        "highway_abandonment"
    ],

    "anime_style_scene_parked_car_at_night_trunk.mp4": [
        "car_trunk_scene"
    ],


    # ---------------------------------------------------------
    # DIGITAL / SURVEILLANCE
    # ---------------------------------------------------------

    "anime_style_cinematic_close_up_phone_glowing_in_a.mp4": [
        "phone_activity", "mobile_device"
    ],

    "cctv.mp4": [
        "security_camera"
    ],

    "stylized_anime_scene_elevator_interior_man_standing.mp4": [
        "elevator_surveillance"
    ],

    "smartphone_lying_on_the_floor_beside_a.mp4": [
        "dropped_phone", "phone_evidence"
    ],


    # ---------------------------------------------------------
    # OFFICE / WORK
    # ---------------------------------------------------------

    "stylized_anime_scene_office_desk_with_laptop.mp4": [
        "office_workspace"
    ],

    "why_was_his_computer_still_logged_in.mp4": [
        "computer_activity"
    ],

    "why_did_his_coworkers_hear_nothing_that.mp4": [
        "coworker_environment"
    ],


    # ---------------------------------------------------------
    # MEDICAL
    # ---------------------------------------------------------

    "elderly_man_in_a_hospital_bed_heart.mp4": [
        "hospital_patient"
    ],

    "empty_hospital_hallway_gurney_parked_sideways_shadowy.mp4": [
        "hospital_corridor"
    ],

    "hospital_corridor_at_night_gurney_partially_visible.mp4": [
        "night_hospital"
    ],


    # ---------------------------------------------------------
    # INVESTIGATION / CRIME
    # ---------------------------------------------------------

    "shadow.mp4": [
        "shadow_presence"
    ],

    "evidence.mp4": [
        "physical_evidence"
    ],

    "interogationroom.mp4": [
        "police_interrogation"
    ],

    "leftover.mp4": [
        "personal_belongings"
    ],

    "did_he_fall_or_was_he_pushed.mp4": [
        "falling_incident"
    ],

    "a_quiet_location_with_a_single_blood.mp4": [
        "bloodstain_scene"
    ],


    # ---------------------------------------------------------
    # GENERIC VISUAL SUPPORT
    # ---------------------------------------------------------

    "dimly_lit_scene_showing_a_human_figure (1).mp4": [
        "unknown_person", "unidentified_silhouette"
    ],

    "dimly_lit_scene_showing_a_human_figure.mp4": [
        "unknown_person_alt", "mysterious_silhouette"
    ],
}


# =========================================================
# HOOK IMAGE CATEGORIES — STATIC THUMBNAILS
# =========================================================

HOOK_IMAGE_CATEGORIES = {

    # ---------------------------------------------------------
    # CLEAN APARTMENT / PRISTINE SCENES
    # ---------------------------------------------------------

    "anime_mystery_illustration_perfectly_clean_apartment_single (1).jpeg": [
        "clean_apartment", "pristine_room", "organized_space", "perfect_order"
    ],

    "anime_mystery_illustration_perfectly_clean_apartment_single.jpeg": [
        "spotless_apartment", "tidy_interior", "immaculate_room"
    ],


    # ---------------------------------------------------------
    # CRIME SCENES / SPOTLESS BUT SUSPICIOUS
    # ---------------------------------------------------------

    "anime_mystery_illustration_spotless_apartment_crime_scene.jpeg": [
        "cleaned_crime_scene", "too_clean", "suspicious_tidiness", "sanitized_scene"
    ],


    # ---------------------------------------------------------
    # EVIDENCE / INVESTIGATION ITEMS
    # ---------------------------------------------------------

    "anime_mystery_scene_evidence_table_under_harsh.jpeg": [
        "evidence_table", "investigation_items", "collected_evidence", "police_evidence"
    ],

    "anime_mystery_scene_sealed_case_file_on (1).jpeg": [
        "case_file", "sealed_documents", "investigation_folder"
    ],

    "anime_mystery_scene_sealed_case_file_on.jpeg": [
        "confidential_file", "case_documents", "sealed_records"
    ],


    # ---------------------------------------------------------
    # BLOOD / FORENSIC EVIDENCE
    # ---------------------------------------------------------

    "anime_style_close_up_crime_illustration_blood_pattern_on (1).jpeg": [
        "blood_spatter", "blood_evidence", "forensic_pattern", "blood_trace"
    ],

    "anime_style_close_up_crime_illustration_blood_pattern_on (2).jpeg": [
        "blood_pattern_analysis", "spatter_evidence", "blood_stain"
    ],

    "anime_style_close_up_crime_illustration_blood_pattern_on.jpeg": [
        "blood_forensics", "blood_splatter", "crime_blood"
    ],


    # ---------------------------------------------------------
    # INVESTIGATOR / DETECTIVE SCENES
    # ---------------------------------------------------------

    "anime_style_close_up_crime_scene_investigator_s_gloved_hand.jpeg": [
        "gloved_hand", "forensic_investigator", "evidence_collection", "csi_hand"
    ],


    # ---------------------------------------------------------
    # CRIME BOARD / DETECTIVE WORK
    # ---------------------------------------------------------

    "anime_style_crime_board_scene_detective_room_with.jpeg": [
        "crime_board", "detective_office", "investigation_wall", "case_board"
    ],


    # ---------------------------------------------------------
    # BODY / VICTIM SCENES
    # ---------------------------------------------------------

    "anime_style_crime_illustration_narrow_apartment_hallway_body (1).jpeg": [
        "hallway_body", "corridor_victim", "apartment_death"
    ],

    "anime_style_crime_illustration_narrow_apartment_hallway_body.jpeg": [
        "narrow_hallway_victim", "hallway_crime_scene"
    ],


    # ---------------------------------------------------------
    # BEDROOM SCENES
    # ---------------------------------------------------------

    "anime_style_crime_scene_illustration_dimly_lit_bedroom.jpeg": [
        "dim_bedroom", "dark_bedroom_scene", "nighttime_bedroom"
    ],

    "anime_style_crime_scene_viewed_from_above_body (1).jpeg": [
        "overhead_crime_scene", "aerial_view_victim", "top_down_body"
    ],

    "anime_style_crime_scene_viewed_from_above_body (2).jpeg": [
        "birds_eye_view_crime", "above_victim", "overhead_death_scene"
    ],

    "anime_style_crime_scene_viewed_from_above_body.jpeg": [
        "overhead_perspective", "top_view_crime", "aerial_victim"
    ],


    # ---------------------------------------------------------
    # HALLWAY / CORRIDOR SCENES
    # ---------------------------------------------------------

    "anime_style_illustration_of_a_crime_scene_hallway.jpeg": [
        "crime_hallway", "corridor_investigation", "hallway_scene"
    ],


    # ---------------------------------------------------------
    # PSYCHOLOGICAL / ATMOSPHERIC
    # ---------------------------------------------------------

    "anime_style_psychological_crime_scene_dim_bedroom_at (1).jpeg": [
        "psychological_scene", "unsettling_bedroom", "ominous_room"
    ],

    "anime_style_psychological_crime_scene_dim_bedroom_at (2).jpeg": [
        "disturbing_bedroom", "eerie_bedroom", "dark_atmosphere"
    ],

    "anime_style_psychological_crime_scene_dim_bedroom_at (3).jpeg": [
        "sinister_bedroom", "haunting_scene", "creepy_bedroom"
    ],

    "anime_style_psychological_crime_scene_dim_bedroom_at.jpeg": [
        "atmospheric_crime", "moody_bedroom", "tense_scene"
    ],

    "anime_style_psychological_crime_scene_dimly_lit_bedroom.jpeg": [
        "psychological_bedroom", "mystery_bedroom", "shadowy_bedroom"
    ],


    # ---------------------------------------------------------
    # LOCKED / SEALED ROOMS
    # ---------------------------------------------------------

    "dark_anime_mystery_scene_locked_room_viewed.jpeg": [
        "locked_room", "sealed_chamber", "mystery_room", "inaccessible_room"
    ],


    # ---------------------------------------------------------
    # PERFECTLY CLEAN / ORGANIZED ROOMS
    # ---------------------------------------------------------

    "dark_anime_mystery_scene_perfectly_clean_room.jpeg": [
        "perfectly_ordered", "suspiciously_clean", "unnaturally_tidy"
    ],


    # ---------------------------------------------------------
    # NEATLY ARRANGED SCENES
    # ---------------------------------------------------------

    "dark_anime_crime_scene_neatly_arranged_room.jpeg": [
        "arranged_room", "staged_scene", "organized_crime_scene"
    ],


    # ---------------------------------------------------------
    # INVESTIGATOR CLOSE-UPS
    # ---------------------------------------------------------

    "close_up_anime_crime_scene_shot_investigator_s_gloved.jpeg": [
        "investigator_closeup", "detective_hand", "forensic_detail"
    ],

}


# =========================================================
# VALIDATION
# =========================================================

def validate_video_assets():
    """Validate that all video files on disk are declared and vice versa."""
    disk = {f.name for f in VIDEO_ASSET_DIR.glob("*.mp4")}
    declared = set(VIDEO_ASSET_KEYWORDS.keys())

    missing_in_code = disk - declared
    missing_on_disk = declared - disk

    if missing_in_code:
        print(f"⚠️  WARNING: Video assets on disk NOT declared in code:")
        for filename in sorted(missing_in_code):
            print(f"   - {filename}")

    if missing_on_disk:
        print(f"⚠️  WARNING: Video assets declared in code but missing on disk:")
        for filename in sorted(missing_on_disk):
            print(f"   - {filename}")

    if missing_in_code or missing_on_disk:
        sys.exit(1)

    print(f"✅ All {len(declared)} video assets validated successfully!")


def validate_hook_images():
    """Validate that all hook images on disk are declared and vice versa."""
    disk = {f.name for f in HOOK_IMAGE_DIR.glob("*.jpeg")}
    declared = set(HOOK_IMAGE_CATEGORIES.keys())

    missing_in_code = disk - declared
    missing_on_disk = declared - disk

    if missing_in_code:
        print(f"⚠️  WARNING: Hook images on disk NOT declared in code:")
        for filename in sorted(missing_in_code):
            print(f"   - {filename}")

    if missing_on_disk:
        print(f"⚠️  WARNING: Hook images declared in code but missing on disk:")
        for filename in sorted(missing_on_disk):
            print(f"   - {filename}")

    if missing_in_code or missing_on_disk:
        sys.exit(1)

    print(f"✅ All {len(declared)} hook images validated successfully!")


def validate_all():
    """Run all validations."""
    print("=" * 60)
    print("ASSET REGISTRY VALIDATION")
    print("=" * 60)
    
    print("\n📹 Validating Video Assets...")
    validate_video_assets()
    
    print("\n🖼️  Validating Hook Images...")
    validate_hook_images()
    
    print("\n" + "=" * 60)
    print("✅ ALL ASSETS VALIDATED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    validate_all()
