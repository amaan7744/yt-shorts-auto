"""
Asset Registry
DO NOT put script logic here
DO NOT guess filenames
"""

from pathlib import Path
import sys

# =========================
# DIRECTORIES
# =========================

VIDEO_ASSET_DIR = Path("asset")
HOOK_IMAGE_DIR = Path("asset/hook_static")

# =========================
# HOOK CATEGORIES (CANONICAL)
# =========================

CORE_MURDER_SUICIDE_MYSTERY = "CORE_MURDER_SUICIDE_MYSTERY"
PSYCHOLOGICAL_HOOKS = "PSYCHOLOGICAL_HOOKS"
CRIME_SCENE_DOUBT = "CRIME_SCENE_DOUBT"
HUMAN_FOCUSED_HOOKS = "HUMAN_FOCUSED_HOOKS"
DARK_CURIOSITY = "DARK_CURIOSITY"
LOOP_RETENTION_KILLERS = "LOOP_RETENTION_KILLERS"

# =========================
# VIDEO ASSETS (.mp4)
# (unchanged – already correct)
# =========================

VIDEO_ASSET_KEYWORDS = {
    "5_second_anime_style_cinematic_scene_a_woman_lying.mp4": ["woman lying"],
    "5_second_anime_style_cinematic_scene_a_young_woman.mp4": ["young woman"],
    "anime_style_cinematic_video_elderly_woman_lying_near.mp4": ["elderly woman"],
    "anime_style_cinematic_video_elderly_woman_slumped_near.mp4": ["elderly woman"],
    "anime_style_scene_elderly_woman_lying_peacefully_on.mp4": ["elderly woman"],
    "anime_style_cartoon_video_elderly_man_seated_in.mp4": ["elderly man"],
    "elderly_man_lying_on_stair_landing_broken.mp4": ["elderly man"],
    "stylized_anime_cartoon_woman_collapsed_near_a.mp4": ["woman collapsed"],
    "stylized_anime_cartoon_video_a_human_figure.mp4": ["human figure"],

    "a_child_s_bedroom_with_toys_scattered_on.mp4": ["child bedroom"],
    "crayon_drawing_on_the_floor_dark_shapes.mp4": ["crayon drawing"],
    "anime_style_video_school_backpack_on_sidewalk_early.mp4": ["school backpack"],
    "how_could_a_child_disappear_without_making.mp4": ["child disappeared"],
    "if_a_child_saw_everything_why_did.mp4": ["child witness"],
    "if_a_child_saw_it_why_was.mp4": ["child witness"],
    "what_went_wrong_during_a_normal_family.mp4": ["family home"],

    "anime_style_scene_bedroom_with_ceiling_fan_rotating.mp4": ["bedroom"],
    "anime_style_cinematic_scene_dark_bedroom_wall_clock.mp4": ["bedroom"],
    "dark_room.mp4": ["dark room"],
    "hallway.mp4": ["hallway"],
    "animate_the_scene_cabin_in_forest_at.mp4": ["cabin"],
    "anime_style_cinematic_scene_dim_motel_room_neon.mp4": ["motel room"],
    "anime_style_cinematic_video_backyard_at_dawn_uneven.mp4": ["backyard"],
    "anime_style_scene_swing_moving_slowly_by_itself.mp4": ["swing"],

    "animate_why_was_the_door_locked_from.mp4": ["door locked"],
    "closing_door.mp4": ["closing door"],
    "who_rang_the_doorbell_and_never_left.mp4": ["doorbell"],

    "anime_cartoon_realism_bathroom_door_half_open_bright.mp4": ["bathroom"],
    "anime_style_scene_bathroom_door_closed_police_flashlight.mp4": ["bathroom"],
    "anime_style_scene_sink_overflowing_water_spilling_onto.mp4": ["sink"],
    "stylized_anime_cartoon_foggy_bathroom_mirror_with.mp4": ["mirror"],

    "anime_style_video_a_quiet_caf_at_night.mp4": ["cafe"],
    "why_was_dinner_still_warm_when_they.mp4": ["dinner still warm"],

    "blurred_alley.mp4": ["alley"],
    "night_alley.mp4": ["alley"],
    "what_happened_on_this_street_after_midnight.mp4": ["street"],
    "empty_bus_stop_at_night_streetlight_flickering.mp4": ["bus stop"],
    "bridge.mp4": ["bridge"],
    "window_pov.mp4": ["window"],

    "car_pov.mp4": ["car pov"],
    "person driving.mp4": ["person driving"],
    "parked_car.mp4": ["parked car"],
    "empty_highway_at_night_car_parked_on.mp4": ["highway"],
    "anime_style_scene_parked_car_at_night_trunk.mp4": ["trunk"],
    "anime_style_cinematic_shot_man_slumped_in_driver_s.mp4": ["driver seat"],

    "mobilemessage.mp4": ["text"],
    "anime_style_cinematic_close_up_phone_glowing_in_a.mp4": ["phone"],
    "cctv.mp4": ["cctv"],
    "stylized_anime_scene_elevator_interior_man_standing.mp4": ["elevator"],

    "stylized_anime_scene_office_desk_with_laptop.mp4": ["office"],
    "why_was_his_computer_still_logged_in.mp4": ["computer"],
    "why_did_his_coworkers_hear_nothing_that.mp4": ["coworkers"],

    "elderly_man_in_a_hospital_bed_heart.mp4": ["hospital"],
    "empty_hospital_hallway_gurney_parked_sideways_shadowy.mp4": ["hospital hallway"],

    "rooftop.mp4": ["rooftop"],
    "what_happened_on_this_rooftop_before_sunrise.mp4": ["rooftop"],
    "stylized_anime_cartoon_scene_empty_train_platform.mp4": ["train"],

    "shadow.mp4": ["shadow"],
    "evidence.mp4": ["evidence"],
    "interogationroom.mp4": ["interrogation"],
    "leftover.mp4": ["belongings"],
    "did_he_fall_or_was_he_pushed.mp4": ["fell"],
        # DIGITAL / PHONE / EVIDENCE
    "smartphone_lying_on_the_floor_beside_a.mp4": [
        "smartphone",
        "phone on floor"
    ],

    # MEDICAL / HOSPITAL
    "hospital_corridor_at_night_gurney_partially_visible.mp4": [
        "hospital corridor",
        "gurney"
    ],

    # HUMAN / SILHOUETTE / DISCOVERY
    "dimly_lit_scene_showing_a_human_figure.mp4": [
        "human figure",
        "dimly lit"
    ],
    "dimly_lit_scene_showing_a_human_figure (1).mp4": [
        "human figure",
        "dimly lit"
    ],

    # CRIME SCENE / BLOOD
    "a_quiet_location_with_a_single_blood.mp4": [
        "blood",
        "quiet location"
    ],

}

# =========================
# HOOK STATIC IMAGES (.jpeg)
# CATEGORY-DRIVEN MAPPING
# =========================

HOOK_IMAGE_CATEGORIES = {
    # CORE — Murder / Suicide / Mystery
    "anime_style_crime_scene_viewed_from_above_body.jpeg": CORE_MURDER_SUICIDE_MYSTERY,
    "anime_style_crime_scene_viewed_from_above_body (1).jpeg": CORE_MURDER_SUICIDE_MYSTERY,
    "anime_style_crime_scene_viewed_from_above_body (2).jpeg": CORE_MURDER_SUICIDE_MYSTERY,
    "anime_mystery_illustration_spotless_apartment_crime_scene.jpeg": CORE_MURDER_SUICIDE_MYSTERY,

    # PSYCHOLOGICAL HOOKS
    "anime_style_psychological_crime_scene_dim_bedroom_at.jpeg": PSYCHOLOGICAL_HOOKS,
    "anime_style_psychological_crime_scene_dim_bedroom_at (1).jpeg": PSYCHOLOGICAL_HOOKS,
    "anime_style_psychological_crime_scene_dim_bedroom_at (2).jpeg": PSYCHOLOGICAL_HOOKS,
    "anime_style_psychological_crime_scene_dim_bedroom_at (3).jpeg": PSYCHOLOGICAL_HOOKS,
    "anime_style_psychological_crime_scene_dimly_lit_bedroom.jpeg": PSYCHOLOGICAL_HOOKS,

    # CRIME SCENE DOUBT
    "anime_style_close_up_crime_illustration_blood_pattern_on.jpeg": CRIME_SCENE_DOUBT,
    "anime_style_close_up_crime_illustration_blood_pattern_on (1).jpeg": CRIME_SCENE_DOUBT,
    "anime_style_close_up_crime_illustration_blood_pattern_on (2).jpeg": CRIME_SCENE_DOUBT,
    "anime_mystery_scene_evidence_table_under_harsh.jpeg": CRIME_SCENE_DOUBT,
    "anime_mystery_scene_sealed_case_file_on.jpeg": CRIME_SCENE_DOUBT,
    "anime_mystery_scene_sealed_case_file_on (1).jpeg": CRIME_SCENE_DOUBT,

    # HUMAN-FOCUSED HOOKS
    "anime_style_crime_illustration_narrow_apartment_hallway_body.jpeg": HUMAN_FOCUSED_HOOKS,
    "anime_style_crime_illustration_narrow_apartment_hallway_body (1).jpeg": HUMAN_FOCUSED_HOOKS,
    "anime_style_close_up_crime_scene_investigator_s_gloved_hand.jpeg": HUMAN_FOCUSED_HOOKS,

    # DARK CURIOSITY
    "dark_anime_mystery_scene_locked_room_viewed.jpeg": DARK_CURIOSITY,
    "dark_anime_mystery_scene_perfectly_clean_room.jpeg": DARK_CURIOSITY,
    "anime_mystery_illustration_perfectly_clean_apartment_single.jpeg": DARK_CURIOSITY,
    "anime_mystery_illustration_perfectly_clean_apartment_single (1).jpeg": DARK_CURIOSITY,

    # LOOP / RETENTION KILLERS
    "dark_anime_crime_illustration_perfectly_arranged_room.jpeg": LOOP_RETENTION_KILLERS,
    "dark_anime_crime_scene_neatly_arranged_room.jpeg": LOOP_RETENTION_KILLERS,
}

# =========================
# VALIDATION
# =========================

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
