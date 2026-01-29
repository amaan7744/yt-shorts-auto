#!/usr/bin/env python3
"""
Visual Mapper
Maps script beats → structured visual intent
"""

def map_visual(beat: dict) -> dict:
    text = beat.get("text", "").lower()

    # Default visual intent
    visual = {
        "scene": "neutral",
        "mood": "dark",
    }

    # Scene detection
    if "car" in text or "vehicle" in text:
        visual["scene"] = "car"
        visual["mood"] = "tense"

    elif "police" in text or "sirens" in text:
        visual["scene"] = "police"
        visual["mood"] = "alert"

    elif "room" in text or "bed" in text or "house" in text:
        visual["scene"] = "room"
        visual["mood"] = "quiet"

    elif "street" in text or "road" in text or "outside" in text:
        visual["scene"] = "street"
        visual["mood"] = "dark"

    return visual
