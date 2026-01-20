#!/usr/bin/env python3

import os
import sys
import json
import time
import re
from typing import Tuple, List

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# ==================================================
# CONFIG — HIGH RETENTION (ADJUSTED FOR PACE)
# ==================================================

ENDPOINT = "https://models.github.ai/inference"
PRIMARY_MODEL = "openai/gpt-4o-mini"

CASE_FILE = "case.json"
SCRIPT_FILE = "script.txt"
BEATS_FILE = "beats.json"

# Shorts Retention: 140-160 Words Per Minute
# 45 words is roughly 18-20 seconds.
TARGET_WORDS_MIN = 40
TARGET_WORDS_MAX = 52

# ==================================================
# PROMPT — RETENTION OPTIMIZED (THE "REVEAL" METHOD)
# ==================================================

def build_script_prompt(case: dict) -> str:
    return f"""
Write a 20-second "True Crime Mystery" script. 
Focus: High-retention 'Open Loops' and fast pacing.

HOOK RULE:
- Start with a shocking contrast. 
- Example: "The door was locked from the inside, yet the room was empty."
- Do NOT use "Official conclusion." Start with the ANOMALY.

STYLE:
- Fast-paced, punchy sentences.
- Use "The" or "This" to start sentences to keep momentum.
- No fluff. Every word must build tension.

DATA:
Summary: {case.get("summary")}
Location: {case.get("location")}

OUTPUT:
- Exactly 45-50 words.
- One continuous paragraph.
"""

# ==================================================
# DYNAMIC BEAT GENERATOR (RETENTION FIX)
# ==================================================

def derive_visual_beats(script: str) -> List[dict]:
    """
    Splits by phrases, not just sentences, to ensure 
    visuals change every 2-3 seconds.
    """
    # Split by commas, periods, and "and" to create faster visual cuts
    parts = re.split(r'[,.]| and ', script)
    parts = [p.strip() for p in parts if len(p.strip()) > 5]
    
    beats = []
    for i, text in enumerate(parts):
        # Assign high-energy scene types for retention
        if i == 0: scene = "HOOK_VISUAL"
        elif i == len(parts) - 1: scene = "LOOP_OUTRO"
        else: scene = "EVIDENCE_ZOOM" if i % 2 == 0 else "LOCATION_ATMOSPHERE"

        beats.append({
            "beat_id": i + 1,
            "scene_type": scene,
            "subtitles": text,
            "estimated_duration": round(len(text.split()) / 2.5, 1) # ~2.5 words per sec
        })
    return beats

# ... [Keep your existing call_gpt and load_case functions here] ...

def generate(case: dict) -> Tuple[str, list]:
    prompt = build_script_prompt(case)
    
    # Simple direct call (Add your fallback logic back if needed)
    script = call_gpt(PRIMARY_MODEL, prompt)
    
    # Final cleanup: ensure no "Scene 1:" labels leaked in
    script = re.sub(r'Scene \d+:|Narration:', '', script).strip()
    
    beats = derive_visual_beats(script)
    return script, beats

def main():
    # ... [Keep your existing main() loop] ...
    # Ensure it saves the new beats structure
    pass

if __name__ == "__main__":
    # For testing: 
    # print(derive_visual_beats("The car was found running, the lights were on, but the driver had vanished into the woods."))
