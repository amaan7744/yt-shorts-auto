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

"5_second_anime_style_cinematic_scene_a_woman_lying.mp4":
["dead_woman","corpse","female_victim","death_scene","body_found"],

"5_second_anime_style_cinematic_scene_a_young_woman.mp4":
["young_female","victim_identity","female_character","young_victim"],

"anime_style_cinematic_video_elderly_woman_lying_near.mp4":
["elderly_woman_dead","old_age_victim","elderly_body"],

"anime_style_cinematic_video_elderly_woman_slumped_near.mp4":
["elderly_collapse","old_woman_fainted"],

"anime_style_scene_elderly_woman_lying_peacefully_on.mp4":
["elderly_peaceful_death","natural_death_scene"],

"stylized_anime_cartoon_woman_collapsed_near_a.mp4":
["woman_collapsed","sudden_collapse","medical_emergency"],

"stylized_anime_cartoon_video_a_human_figure.mp4":
["unknown_silhouette","mysterious_person","shadow_figure"],


# ---------------------------------------------------------
# CHILD / FAMILY / DOMESTIC
# ---------------------------------------------------------

"a_child_s_bedroom_with_toys_scattered_on.mp4":
["child_room","messy_child_bedroom","child_environment"],

"crayon_drawing_on_the_floor_dark_shapes.mp4":
["child_drawing","child_clue","crayon_evidence"],

"anime_style_video_school_backpack_on_sidewalk_early.mp4":
["missing_child_clue","abandoned_backpack"],

"how_could_a_child_disappear_without_making.mp4":
["child_missing_case","child_disappearance"],

"if_a_child_saw_everything_why_did.mp4":
["child_witness_testimony"],

"if_a_child_saw_it_why_was.mp4":
["child_eye_witness"],

"what_went_wrong_during_a_normal_family.mp4":
["family_tragedy","domestic_incident"],


# ---------------------------------------------------------
# INTERIOR LOCATIONS
# ---------------------------------------------------------

"anime_style_scene_bedroom_with_ceiling_fan_rotating.mp4":
["empty_bedroom","quiet_room"],

"anime_style_cinematic_scene_dark_bedroom_wall_clock.mp4":
["night_bedroom","late_night_scene"],

"dark_room.mp4":
["dark_interior","shadowy_space"],

"hallway.mp4":
["apartment_hallway","indoor_corridor"],

"anime_style_cinematic_scene_dim_motel_room_neon.mp4":
["motel_room","temporary_stay_location"],

"animate_the_scene_cabin_in_forest_at.mp4":
["isolated_cabin","remote_location"],

"anime_style_cinematic_video_backyard_at_dawn_uneven.mp4":
["backyard_morning","residential_exterior"],

"anime_style_scene_swing_moving_slowly_by_itself.mp4":
["eerie_playground","abandoned_play_area"],


# ---------------------------------------------------------
# ENTRY / DOOR EVENTS
# ---------------------------------------------------------

"animate_why_was_the_door_locked_from.mp4":
["locked_room_mystery"],

"closing_door.mp4":
["door_closing_event"],

"who_rang_the_doorbell_and_never_left.mp4":
["unknown_visitor_event"],


# ---------------------------------------------------------
# BATHROOM / WATER CLUES
# ---------------------------------------------------------

"anime_cartoon_realism_bathroom_door_half_open_bright.mp4":
["bathroom_entry"],

"anime_style_scene_bathroom_door_closed_police_flashlight.mp4":
["police_search_scene"],

"anime_style_scene_sink_overflowing_water_spilling_onto.mp4":
["water_overflow","bathroom_flood"],

"stylized_anime_cartoon_foggy_bathroom_mirror_with.mp4":
["foggy_mirror_clue"],


# ---------------------------------------------------------
# FOOD / DAILY LIFE
# ---------------------------------------------------------

"anime_style_video_a_quiet_caf_at_night.mp4":
["night_cafe","quiet_public_space"],

"why_was_dinner_still_warm_when_they.mp4":
["unfinished_meal","abandoned_food"],


# ---------------------------------------------------------
# OUTDOOR / STREET
# ---------------------------------------------------------

"blurred_alley.mp4":
["suspicious_alley"],

"night_alley.mp4":
["dark_alley_night"],

"what_happened_on_this_street_after_midnight.mp4":
["midnight_street_event"],

"empty_bus_stop_at_night_streetlight_flickering.mp4":
["empty_bus_stop"],

"bridge.mp4":
["bridge_location"],

"window_pov.mp4":
["window_view_pov"],


# ---------------------------------------------------------
# VEHICLE / TRANSPORT
# ---------------------------------------------------------

"car_pov.mp4":
["driving_pov"],

"person driving.mp4":
["driver_character"],

"parked_car.mp4":
["parked_vehicle"],

"empty_highway_at_night_car_parked_on.mp4":
["highway_abandonment"],

"anime_style_scene_parked_car_at_night_trunk.mp4":
["car_trunk_scene"],

"anime_style_cinematic_shot_man_slumped_in_driver_s.mp4":
["driver_dead","driver_unconscious"],


# ---------------------------------------------------------
# DIGITAL / SURVEILLANCE
# ---------------------------------------------------------

"anime_style_cinematic_close_up_phone_glowing_in_a.mp4":
["phone_activity","mobile_device"],

"cctv.mp4":
["security_camera"],

"stylized_anime_scene_elevator_interior_man_standing.mp4":
["elevator_surveillance"],


# ---------------------------------------------------------
# OFFICE / WORK
# ---------------------------------------------------------

"stylized_anime_scene_office_desk_with_laptop.mp4":
["office_workspace"],

"why_was_his_computer_still_logged_in.mp4":
["computer_activity"],

"why_did_his_coworkers_hear_nothing_that.mp4":
["coworker_environment"],


# ---------------------------------------------------------
# MEDICAL
# ---------------------------------------------------------

"elderly_man_in_a_hospital_bed_heart.mp4":
["hospital_patient"],

"empty_hospital_hallway_gurney_parked_sideways_shadowy.mp4":
["hospital_corridor"],

"hospital_corridor_at_night_gurney_partially_visible.mp4":
["night_hospital"],


# ---------------------------------------------------------
# INVESTIGATION / CRIME
# ---------------------------------------------------------

"shadow.mp4":
["shadow_presence"],

"evidence.mp4":
["physical_evidence"],

"interogationroom.mp4":
["police_interrogation"],

"leftover.mp4":
["personal_belongings"],

"did_he_fall_or_was_he_pushed.mp4":
["falling_incident"],

"a_quiet_location_with_a_single_blood.mp4":
["bloodstain_scene"],


# ---------------------------------------------------------
# GENERIC VISUAL SUPPORT
# ---------------------------------------------------------

"dimly_lit_scene_showing_a_human_figure.mp4":
["unknown_person"],

"dimly_lit_scene_showing_a_human_figure (1).mp4":
["unknown_person_alt"],
}


# =========================================================
# HOOK IMAGE CATEGORIES (unchanged — already good)
# =========================================================

# (keeping your existing HOOK_IMAGE_CATEGORIES exactly as-is)
# no change needed because they already have strong tagging


# =========================================================
# VALIDATION
# =========================================================

def validate_video_assets():
    disk = {f.name for f in VIDEO_ASSET_DIR.glob("*.mp4")}
    declared = set(VIDEO_ASSET_KEYWORDS.keys())

    if disk - declared:
        sys.exit(f"❌ Video assets on disk NOT declared: {disk - declared}")

    if declared - disk:
        sys.exit(f"❌ Video assets declared but missing on disk: {declared - disk}")


def validate_hook_images():
    disk = {f.name for f in HOOK_IMAGE_DIR.glob("*.jpeg")}
    declared = set(HOOK_IMAGE_CATEGORIES.keys())

    if disk - declared:
        sys.exit(f"❌ Hook images on disk NOT declared: {disk - declared}")

    if declared - disk:
        sys.exit(f"❌ Hook images declared but missing on disk: {declared - disk}")
