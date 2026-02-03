#!/usr/bin/env python3
"""
Script Generator
NO asset filenames here
"""

import json
import random
from pathlib import Path
from assets import ASSET_KEYWORDS, validate_assets

SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"
BLOCK_DURATION = 5.0

SCRIPT_LINES = [
    "Was this just a normal moment before everything changed?",
    "Something unexpected happened at a location tied to this case.",
    "The incident involved someone who should have been safe there.",
    "The discovery was made later, raising immediate questions.",
    "One detail didn’t match the official explanation.",
    "The surrounding context only made the timeline stranger.",
    "Follow for part two — what do you think really happened?"
]

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

    print("✅ Script generated. Assets validated.")

if __name__ == "__main__":
    main()
