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
"""

import os, sys, json, time, re, random
from pathlib import Path
from groq import Groq

# ==================================================
# CONFIG
# ==================================================

PRIMARY_MODEL = "llama-3.3-70b-instruct"
FALLBACK_MODEL = "llama-3.1-8b-instant"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"
ASSET_DIR = Path("asset")

BLOCK_DURATION = 5.0
TEMPERATURE = 0.35
MAX_ATTEMPTS = 4
RETRY_DELAY = 1.5

CTA_LINE = "Part 2 is already up.”
ENGAGEMENT_QUESTIONS = [
    "What do you think really happened?",
    "Which detail doesn’t add up?",
    "Did you notice what was missing?"
]

# ==================================================
# 🔒 ASSET → KEYWORDS (EVERY FILE INCLUDED)
# ==================================================

ASSET_KEYWORDS = {
    # ───────────── PEOPLE / DISCOVERY ─────────────
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

    # ───────────── ROOMS ─────────────
    "a_child_s_bedroom_with_toys_scattered_on.mp4":
        ["child bedroom", "toys", "child room"],

    "anime_style_scene_bedroom_with_ceiling_fan_rotating.mp4":
        ["bedroom", "ceiling fan", "night"],

    "anime_style_cinematic_scene_dark_bedroom_wall_clock.mp4":
        ["bedroom", "wall clock", "late night"],

    "dark_room.mp4":
        ["dark room", "inside", "no lights"],

    # ───────────── BATHROOM ─────────────
    "anime_cartoon_realism_bathroom_door_half_open_bright.mp4":
        ["bathroom door", "half open"],

    "anime_style_scene_bathroom_door_closed_police_flashlight.mp4":
        ["bathroom door locked", "police flashlight"],

    "anime_style_scene_sink_overflowing_water_spilling_onto.mp4":
        ["sink overflowing", "water running", "bathroom"],

    "stylized_anime_cartoon_foggy_bathroom_mirror_with.mp4":
        ["foggy mirror", "bathroom mirror"],

    # ───────────── CHILD / EMOTIONAL ─────────────
    "crayon_drawing_on_the_floor_dark_shapes.mp4":
        ["child drawing", "crayon drawing"],

    "how_could_a_child_disappear_without_making.mp4":
        ["child disappear", "missing child"],

    "if_a_child_saw_everything_why_did.mp4":
        ["child witness", "saw everything"],

    "if_a_child_saw_it_why_was.mp4":
        ["child saw", "ignored witness"],

    # ───────────── CAFÉ / TABLE ─────────────
    "anime_style_video_a_quiet_cafe_at_night.mp4":
        ["cafe", "coffee shop", "table", "cup"],

    "why_was_dinner_still_warm_when_they.mp4":
        ["dinner table", "food still warm"],

    # ───────────── STREET / OUTDOOR ─────────────
    "blurred_alley.mp4":
        ["alley", "narrow street"],

    "night_alley.mp4":
        ["dark alley", "night street"],

    "what_happened_on_this_street_after_midnight.mp4":
        ["street after midnight"],

    "empty_bus_stop_at_night_streetlight_flickering.mp4":
        ["bus stop", "streetlight"],

    "bridge.mp4":
        ["bridge", "overpass"],

    "window_pov.mp4":
        ["window", "looking out"],

    # ───────────── VEHICLES ─────────────
    "car_pov.mp4":
        ["driving", "car pov"],

    "person_driving.mp4":
        ["person driving"],

    "parked_car.mp4":
        ["parked car"],

    "empty_highway_at_night_car_parked_on.mp4":
        ["empty highway", "abandoned car"],

    "anime_style_scene_parked_car_at_night_trunk.mp4":
        ["car trunk", "parked car trunk"],

    # ───────────── OFFICE / WORK ─────────────
    "stylized_anime_scene_office_desk_with_laptop.mp4":
        ["office desk", "laptop"],

    "why_was_his_computer_still_logged_in.mp4":
        ["computer logged in", "office computer"],

    "why_did_his_coworkers_hear_nothing_that.mp4":
        ["coworkers", "office night"],

    # ───────────── CCTV / POV ─────────────
    "cctv.mp4":
        ["cctv", "surveillance"],

    "stylized_anime_scene_elevator_interior_man_standing.mp4":
        ["elevator", "last seen"],

    "closing_door.mp4":
        ["closing door", "last moment"],

    # ───────────── HOSPITAL ─────────────
    "elderly_man_in_a_hospital_bed_heart.mp4":
        ["hospital bed", "heart monitor"],

    "empty_hospital_hallway_gurney_parked_sideways_shadowy.mp4":
        ["hospital hallway", "gurney"],

    # ───────────── ROOFTOP ─────────────
    "rooftop.mp4":
        ["rooftop"],

    "what_happened_on_this_rooftop_before_sunrise.mp4":
        ["rooftop before sunrise"],

    # ───────────── MISC ─────────────
    "shadow.mp4":
        ["shadow", "figure watching"],

    "evidence.mp4":
        ["evidence", "crime scene"],

    "interogationroom.mp4":
        ["interrogation", "questioned"],

    "leftover.mp4":
        ["left behind", "belongings"],

    "did_he_fall_or_was_he_pushed.mp4":
        ["fell", "pushed", "stairs"],

    "stylized_anime_cartoon_scene_empty_train_platform.mp4":
        ["train platform", "empty station"]
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
# SCENE MATCHING (STRICT)
# ==================================================

def pick_asset(sentence: str) -> str:
    s = sentence.lower()
    matches = []

    for asset, keywords in ASSET_KEYWORDS.items():
        if any(k in s for k in keywords):
            matches.append(asset)

    if not matches:
        raise ValueError(f"❌ No asset matches sentence: {sentence}")

    asset = random.choice(matches)
    if not (ASSET_DIR / asset).exists():
        raise FileNotFoundError(f"❌ Asset missing: {asset}")

    return asset

# ==================================================
# MAIN
# ==================================================

def main():
    client = init_client()
    case = load_case()

    script = None
    for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
        for _ in range(MAX_ATTEMPTS):
            res = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Write visual-first true crime Shorts."},
                    {"role": "user", "content": case["summary"]}
                ],
                temperature=TEMPERATURE,
                max_tokens=240
            )
            text = res.choices[0].message.content.strip()
            sentences = re.findall(r"[^.!?]+[.!?]?", text)
            if len(sentences) == 7:
                script = sentences
                break
        if script:
            break

    if not script:
        sys.exit("❌ Script generation failed")

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

    print("✅ Script + assets matched with ZERO guesswork")

# ==================================================
if __name__ == "__main__":
    main()
