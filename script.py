#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (DURATION-LOCKED ONLY)

RULES:
- No question marks (XTTS safe)
- 7 lines exactly
- Final duration MUST be 30–50 seconds
- No per-line word limits
- Strong hooks allowed
"""

import os
import json
import random
from pathlib import Path
from groq import Groq

# ==================================================
# CONFIG
# ==================================================

WORDS_PER_SECOND = 3.0
MIN_SECONDS = 30
MAX_SECONDS = 50

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")
CASE_FILE = Path("case.json")

MEMORY_DIR = Path("memory")
USED_CASES = MEMORY_DIR / "used_cases.json"
USED_CTA = MEMORY_DIR / "used_cta.json"
USED_END = MEMORY_DIR / "used_end.json"

MEMORY_DIR.mkdir(exist_ok=True)

# ==================================================
# HELPERS
# ==================================================

def load_json(p, default):
    if not p.exists():
        p.write_text(json.dumps(default, indent=2))
    return json.loads(p.read_text())

def save_json(p, data):
    p.write_text(json.dumps(data, indent=2))

def ensure_no_question(line, label):
    if "?" in line:
        raise RuntimeError(f"{label} contains question mark (XTTS unsafe): {line}")

def estimate_seconds(lines):
    return sum(len(l.split()) for l in lines) / WORDS_PER_SECOND

# ==================================================
# LOAD CASE
# ==================================================

case = json.loads(CASE_FILE.read_text())

name = case["full_name"]
summary = case["summary"].strip()
detail = case["key_detail"].strip()
official = case["official_story"].strip()
location = case["location"]
date = case["date"]
time = case["time"]

fingerprint = f"{name}|{location}|{date}|{time}".lower()
used_cases = load_json(USED_CASES, [])

if fingerprint in used_cases:
    raise RuntimeError("❌ Case already used")

# ==================================================
# HOOKS (STRONG, SHORT, FACTUAL)
# ==================================================

HOOKS = [
    "Police ruled it suicide, but the physical evidence immediately contradicted that conclusion.",
    "Authorities closed the case quickly, even though the scene did not match their explanation.",
    "The official report sounded simple, but the details made no sense at all.",
    "Investigators reached a conclusion that the evidence itself refused to support.",
    "What police claimed happened did not match what was found at the scene."
]

hook = random.choice(HOOKS)
ensure_no_question(hook, "Hook")

# ==================================================
# BODY (FACTUAL, UNRESTRICTED)
# ==================================================

body = [
    f"{name} was found in {location} on {date} at approximately {time}.",
    summary,
    detail,
    official
]

for i, line in enumerate(body, 1):
    ensure_no_question(line, f"Body line {i}")

# ==================================================
# CTA (ROTATING, NON-BEGGING)
# ==================================================

CTA_POOL = [
    f"Cases like {name}'s only move forward when people keep paying attention.",
    f"Stories like {name}'s disappear when they are ignored.",
    f"{name}'s case did not end when the report was written.",
    f"Attention is often the only thing that keeps cases like {name}'s alive."
]

used_cta = load_json(USED_CTA, [])
cta = next((c for c in CTA_POOL if c not in used_cta), CTA_POOL[0])
used_cta.append(cta)
save_json(USED_CTA, used_cta)

ensure_no_question(cta, "CTA")

# ==================================================
# ENDING (STATEMENT, NOT QUESTION)
# ==================================================

ENDINGS = [
    f"The truth about what happened to {name} has never been fully explained.",
    f"Officially the case is closed, but the facts surrounding {name}'s death remain unresolved.",
    f"The evidence left behind still contradicts the conclusion about {name}.",
    f"What truly happened to {name} was never clearly established."
]

used_end = load_json(USED_END, [])
ending = next((e for e in ENDINGS if e not in used_end), ENDINGS[0])
used_end.append(ending)
save_json(USED_END, used_end)

ensure_no_question(ending, "Ending")

# ==================================================
# FINAL SCRIPT
# ==================================================

script = [hook] + body + [cta, ending]

seconds = estimate_seconds(script)
if seconds < MIN_SECONDS:
    raise RuntimeError(f"❌ Script too short: ~{seconds:.1f}s")
if seconds > MAX_SECONDS:
    raise RuntimeError(f"❌ Script too long: ~{seconds:.1f}s")

SCRIPT_FILE.write_text("\n".join(script), encoding="utf-8")

used_cases.append(fingerprint)
save_json(USED_CASES, used_cases)

print("✅ Script generated successfully")
print(f"⏱️ Estimated duration: ~{seconds:.1f} seconds")
