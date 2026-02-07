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
# VIDEO ASSETS (.mp4)
# =========================

VIDEO_ASSET_KEYWORDS = {
    "5_second_anime_style_cinematic_scene_a_woman_lying.mp4": ["woman", "lying", "body", "victim", "death", "dead"],
    "5_second_anime_style_cinematic_scene_a_young_woman.mp4": ["young", "woman", "victim", "female"],
    "anime_style_cinematic_video_elderly_woman_lying_near.mp4": ["elderly", "woman", "victim", "body", "lying"],
    "anime_style_cinematic_video_elderly_woman_slumped_near.mp4": ["elderly", "woman", "slumped", "victim"],
    "anime_style_scene_elderly_woman_lying_peacefully_on.mp4": ["elderly", "woman", "lying", "peaceful"],
    "anime_style_cartoon_video_elderly_man_seated_in.mp4": ["elderly", "man", "seated", "victim"],
    "elderly_man_lying_on_stair_landing_broken.mp4": ["elderly", "man", "lying", "stairs", "fall", "broken"],
    "stylized_anime_cartoon_woman_collapsed_near_a.mp4": ["woman", "collapsed", "victim", "body"],
    "stylized_anime_cartoon_video_a_human_figure.mp4": ["human", "figure", "silhouette", "victim", "body"],

    "a_child_s_bedroom_with_toys_scattered_on.mp4": ["child", "bedroom", "toys", "scattered"],
    "crayon_drawing_on_the_floor_dark_shapes.mp4": ["crayon", "drawing", "floor", "child"],
    "anime_style_video_school_backpack_on_sidewalk_early.mp4": ["school", "backpack", "sidewalk", "child"],
    "how_could_a_child_disappear_without_making.mp4": ["child", "disappear", "missing"],
    "if_a_child_saw_everything_why_did.mp4": ["child", "witness", "saw"],
    "if_a_child_saw_it_why_was.mp4": ["child", "witness", "saw"],
    "what_went_wrong_during_a_normal_family.mp4": ["family", "home", "normal"],

    "anime_style_scene_bedroom_with_ceiling_fan_rotating.mp4": ["bedroom", "ceiling", "fan", "room"],
    "anime_style_cinematic_scene_dark_bedroom_wall_clock.mp4": ["bedroom", "dark", "clock", "night"],
    "dark_room.mp4": ["dark", "room", "shadowy"],
    "hallway.mp4": ["hallway", "corridor", "passage"],
    "animate_the_scene_cabin_in_forest_at.mp4": ["cabin", "forest", "woods", "isolated"],
    "anime_style_cinematic_scene_dim_motel_room_neon.mp4": ["motel", "room", "hotel", "neon"],
    "anime_style_cinematic_video_backyard_at_dawn_uneven.mp4": ["backyard", "yard", "dawn", "morning"],
    "anime_style_scene_swing_moving_slowly_by_itself.mp4": ["swing", "moving", "playground", "eerie"],

    "animate_why_was_the_door_locked_from.mp4": ["door", "locked", "inside"],
    "closing_door.mp4": ["door", "closing", "shut"],
    "who_rang_the_doorbell_and_never_left.mp4": ["doorbell", "rang", "visitor"],

    "anime_cartoon_realism_bathroom_door_half_open_bright.mp4": ["bathroom", "door", "open"],
    "anime_style_scene_bathroom_door_closed_police_flashlight.mp4": ["bathroom", "door", "police", "flashlight"],
    "anime_style_scene_sink_overflowing_water_spilling_onto.mp4": ["sink", "water", "overflow", "spilling"],
    "stylized_anime_cartoon_foggy_bathroom_mirror_with.mp4": ["mirror", "bathroom", "foggy", "steam"],

    "anime_style_video_a_quiet_caf_at_night.mp4": ["cafe", "coffee", "shop", "night", "quiet"],
    "why_was_dinner_still_warm_when_they.mp4": ["dinner", "food", "warm", "meal"],

    "blurred_alley.mp4": ["alley", "alleyway", "street", "blur"],
    "night_alley.mp4": ["alley", "night", "dark", "street"],
    "what_happened_on_this_street_after_midnight.mp4": ["street", "midnight", "night", "road"],
    "empty_bus_stop_at_night_streetlight_flickering.mp4": ["bus", "stop", "night", "streetlight"],
    "bridge.mp4": ["bridge", "overpass"],
    "window_pov.mp4": ["window", "view", "looking"],

    "car_pov.mp4": ["car", "driving", "vehicle", "road"],
    "person driving.mp4": ["person", "driving", "driver", "car"],
    "parked_car.mp4": ["parked", "car", "vehicle"],
    "empty_highway_at_night_car_parked_on.mp4": ["highway", "night", "car", "parked", "road"],
    "anime_style_scene_parked_car_at_night_trunk.mp4": ["trunk", "car", "night", "parked"],
    "anime_style_cinematic_shot_man_slumped_in_driver_s.mp4": ["driver", "seat", "slumped", "car", "man"],

    "anime_style_cinematic_close_up_phone_glowing_in_a.mp4": ["phone", "cellphone", "mobile", "glow"],
    "cctv.mp4": ["cctv", "camera", "surveillance", "security"],
    "stylized_anime_scene_elevator_interior_man_standing.mp4": ["elevator", "lift", "man", "standing"],

    "stylized_anime_scene_office_desk_with_laptop.mp4": ["office", "desk", "laptop", "work"],
    "why_was_his_computer_still_logged_in.mp4": ["computer", "logged", "screen", "desktop"],
    "why_did_his_coworkers_hear_nothing_that.mp4": ["coworkers", "office", "colleagues", "work"],

    "elderly_man_in_a_hospital_bed_heart.mp4": ["hospital", "bed", "elderly", "man", "patient"],
    "empty_hospital_hallway_gurney_parked_sideways_shadowy.mp4": ["hospital", "hallway", "corridor", "gurney", "medical"],

    "rooftop.mp4": ["rooftop", "roof", "building", "top"],
    "what_happened_on_this_rooftop_before_sunrise.mp4": ["rooftop", "sunrise", "morning", "roof"],
    "stylized_anime_cartoon_scene_empty_train_platform.mp4": ["train", "platform", "station", "railway"],

    "shadow.mp4": ["shadow", "silhouette", "dark", "figure"],
    "evidence.mp4": ["evidence", "clue", "proof", "investigation"],
    "interogationroom.mp4": ["interrogation", "interview", "questioning", "police"],
    "leftover.mp4": ["belongings", "items", "possessions", "leftover"],
    "did_he_fall_or_was_he_pushed.mp4": ["fall", "fell", "pushed", "drop"],

    "smartphone_lying_on_the_floor_beside_a.mp4": ["smartphone", "phone", "floor", "cellphone"],

    "hospital_corridor_at_night_gurney_partially_visible.mp4": ["hospital", "corridor", "night", "gurney"],

    "dimly_lit_scene_showing_a_human_figure.mp4": ["dimly", "lit", "human", "figure", "shadow"],
    "dimly_lit_scene_showing_a_human_figure (1).mp4": ["dimly", "lit", "human", "figure", "shadow"],

    "a_quiet_location_with_a_single_blood.mp4": ["blood", "quiet", "location", "crime", "scene"],
}

# =========================
# HOOK STATIC IMAGES (.jpeg)
# KEYWORD-BASED MATCHING
# =========================

HOOK_IMAGE_CATEGORIES = {
    # Crime scene overhead views
    "anime_style_crime_scene_viewed_from_above_body.jpeg": [
        "crime", "scene", "body", "dead", "death", "murder", "killed", "victim", 
        "found", "discovered", "died", "mystery", "suspicious", "investigation"
    ],
    "anime_style_crime_scene_viewed_from_above_body (1).jpeg": [
        "crime", "scene", "body", "dead", "death", "murder", "killed", "victim",
        "found", "discovered", "died", "mystery", "suspicious", "investigation"
    ],
    "anime_style_crime_scene_viewed_from_above_body (2).jpeg": [
        "crime", "scene", "body", "dead", "death", "murder", "killed", "victim",
        "found", "discovered", "died", "mystery", "suspicious", "investigation"
    ],
    "anime_mystery_illustration_spotless_apartment_crime_scene.jpeg": [
        "crime", "scene", "apartment", "spotless", "clean", "mystery", "suspicious",
        "strange", "unusual", "odd", "weird"
    ],

    # Psychological/bedroom scenes
    "anime_style_psychological_crime_scene_dim_bedroom_at.jpeg": [
        "bedroom", "psychological", "dim", "dark", "night", "mysterious", "eerie",
        "strange", "suicide", "death", "found", "died"
    ],
    "anime_style_psychological_crime_scene_dim_bedroom_at (1).jpeg": [
        "bedroom", "psychological", "dim", "dark", "night", "mysterious", "eerie",
        "strange", "suicide", "death", "found", "died"
    ],
    "anime_style_psychological_crime_scene_dim_bedroom_at (2).jpeg": [
        "bedroom", "psychological", "dim", "dark", "night", "mysterious", "eerie",
        "strange", "suicide", "death", "found", "died"
    ],
    "anime_style_psychological_crime_scene_dim_bedroom_at (3).jpeg": [
        "bedroom", "psychological", "dim", "dark", "night", "mysterious", "eerie",
        "strange", "suicide", "death", "found", "died"
    ],
    "anime_style_psychological_crime_scene_dimly_lit_bedroom.jpeg": [
        "bedroom", "psychological", "dimly", "lit", "dark", "mysterious", "eerie",
        "strange", "suicide", "death", "found", "died"
    ],

    # Blood/evidence close-ups
    "anime_style_close_up_crime_illustration_blood_pattern_on.jpeg": [
        "blood", "pattern", "evidence", "close", "detail", "forensic", "clue",
        "murder", "killed", "violence", "attacked"
    ],
    "anime_style_close_up_crime_illustration_blood_pattern_on (1).jpeg": [
        "blood", "pattern", "evidence", "close", "detail", "forensic", "clue",
        "murder", "killed", "violence", "attacked"
    ],
    "anime_style_close_up_crime_illustration_blood_pattern_on (2).jpeg": [
        "blood", "pattern", "evidence", "close", "detail", "forensic", "clue",
        "murder", "killed", "violence", "attacked"
    ],
    "anime_mystery_scene_evidence_table_under_harsh.jpeg": [
        "evidence", "table", "investigation", "clue", "proof", "forensic",
        "police", "detective", "case", "mystery"
    ],
    "anime_mystery_scene_sealed_case_file_on.jpeg": [
        "case", "file", "sealed", "documents", "investigation", "police",
        "detective", "mystery", "unsolved", "cold"
    ],
    "anime_mystery_scene_sealed_case_file_on (1).jpeg": [
        "case", "file", "sealed", "documents", "investigation", "police",
        "detective", "mystery", "unsolved", "cold"
    ],

    # Hallway/body discoveries
    "anime_style_crime_illustration_narrow_apartment_hallway_body.jpeg": [
        "hallway", "apartment", "body", "corridor", "victim", "found",
        "discovered", "dead", "death", "murder", "killed"
    ],
    "anime_style_crime_illustration_narrow_apartment_hallway_body (1).jpeg": [
        "hallway", "apartment", "body", "corridor", "victim", "found",
        "discovered", "dead", "death", "murder", "killed"
    ],
    "anime_style_close_up_crime_scene_investigator_s_gloved_hand.jpeg": [
        "investigator", "gloved", "hand", "forensic", "evidence", "detective",
        "police", "examining", "clue", "investigation"
    ],

    # Locked/clean rooms
    "dark_anime_mystery_scene_locked_room_viewed.jpeg": [
        "locked", "room", "door", "sealed", "mystery", "impossible",
        "strange", "unusual", "bizarre", "curious"
    ],
    "dark_anime_mystery_scene_perfectly_clean_room.jpeg": [
        "clean", "room", "perfect", "spotless", "neat", "tidy", "suspicious",
        "strange", "unusual", "odd", "weird"
    ],
    "anime_mystery_illustration_perfectly_clean_apartment_single.jpeg": [
        "clean", "apartment", "perfect", "spotless", "neat", "suspicious",
        "strange", "unusual", "mysterious", "odd"
    ],
    "anime_mystery_illustration_perfectly_clean_apartment_single (1).jpeg": [
        "clean", "apartment", "perfect", "spotless", "neat", "suspicious",
        "strange", "unusual", "mysterious", "odd"
    ],

    # Arranged/staged scenes
    "dark_anime_crime_illustration_perfectly_arranged_room.jpeg": [
        "arranged", "room", "staged", "perfect", "neat", "organized",
        "suspicious", "planned", "deliberate", "intentional"
    ],
    "dark_anime_crime_scene_neatly_arranged_room.jpeg": [
        "arranged", "room", "neat", "organized", "perfect", "suspicious",
        "staged", "planned", "deliberate", "intentional"
    ],

    # Crime board/investigation
    "anime_style_crime_board_scene_detective_room_with.jpeg": [
        "crime", "board", "detective", "investigation", "clues", "evidence",
        "police", "case", "solving", "mystery", "photos", "strings"
    ],

    # Hallway scenes
    "anime_style_illustration_of_a_crime_scene_hallway.jpeg": [
        "crime", "scene", "hallway", "corridor", "investigation", "police",
        "tape", "evidence", "mystery", "suspicious"
    ],

    # Investigator close-up
    "close_up_anime_crime_scene_shot_investigator_s_gloved.jpeg": [
        "investigator", "gloved", "hand", "close", "forensic", "detective",
        "evidence", "examining", "police", "clue"
    ],

    # Bedroom crime scene
    "anime_style_crime_scene_illustration_dimly_lit_bedroom.jpeg": [
        "crime", "scene", "bedroom", "dimly", "lit", "dark", "death",
        "suspicious", "mysterious", "investigation", "found", "died"
    ],
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
