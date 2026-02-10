#!/usr/bin/env python3
"""
True Crime Shorts – CLEAN SCRIPT GENERATOR (PRODUCTION SAFE)

RULES (ENFORCED):
- EXACTLY 7 lines output
- NO question marks anywhere (XTTS-safe)
- No duration guessing
- No word-count limits
- Hook / CTA / Loop rotate every run
- Audio pacing is source of truth
"""

import os
import json
import random
from pathlib import Path
from groq import Groq

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")
CASE_FILE = Path("case.json")

MEMORY_DIR = Path("memory")
USED_CASES_FILE = MEMORY_DIR / "used_cases.json"
USED_HOOKS_FILE = MEMORY_DIR / "used_hooks.json"

MEMORY_DIR.mkdir(exist_ok=True)

# ==================================================
# LOAD CASE
# ==================================================

if not CASE_FILE.exists():
    raise RuntimeError("❌ case.json missing")

CASE = json.loads(CASE_FILE.read_text(encoding="utf-8"))

REQUIRED = [
    "full_name",
    "location",
    "date",
    "time",
    "summary",
    "key_detail",
    "official_story",
]

for f in REQUIRED:
    if not CASE.get(f):
        raise RuntimeError(f"❌ Missing case field: {f}")

# ==================================================
# MEMORY HELPERS
# ==================================================

def load_json(path: Path, default):
    if not path.exists():
        path.write_text(json.dumps(default, indent=2))
    return json.loads(path.read_text())

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2))

def fingerprint(case):
    return f"{case['full_name']}|{case['location']}|{case['date']}|{case['time']}".lower()

# ==================================================
# HOOK / CTA / LOOP POOLS (NO QUESTIONS)
# ==================================================

HOOKS = [
    "Police ruled it suicide, but the physical evidence contradicted that conclusion",
    "The case was closed quickly, yet the scene told a different story",
    "Authorities reached a conclusion before all the facts were examined",
    "Investigators followed the report, not the evidence",
    "The official explanation ignored a critical detail at the scene",
]

CTAS = [
    "Like and subscribe so this case does not disappear",
    "Follow for more cases that deserve real scrutiny",
    "Share this story so the facts are not forgotten",
    "Subscribe to keep cases like this in the public eye",
]

LOOPS = [
    "The unanswered details remain hidden in plain sight",
    "The evidence still speaks louder than the report",
    "Some conclusions leave more questions than answers",
    "This case remains unsettled beneath the official record",
]

# ==================================================
# AI CLIENT
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

# ==================================================
# BODY GENERATION (FACTUAL, NO QUESTIONS)
# ==================================================

def generate_body(client: Groq, case):
    prompt = f"""
Write EXACTLY 4 factual sentences for a true crime short.

Rules:
- No questions
- No emotional language
- No speculation
- Clear investigative tone
- Each sentence on its own line

Case details:
Name: {case['full_name']}
Location: {case['location']}
Date: {case['date']} at {case['time']}
Summary: {case['summary']}
Key detail: {case['key_detail']}
Official story: {case['official_story']}

Return only 4 lines.
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.25,
        max_completion_tokens=300,
    )

    lines = [
        l.strip().rstrip(".") + "."
        for l in res.choices[0].message.content.split("\n")
        if l.strip()
    ]

    if len(lines) != 4:
        raise RuntimeError(f"❌ Body must be exactly 4 lines, got {len(lines)}")

    for l in lines:
        if "?" in l:
            raise RuntimeError("❌ Question marks are not allowed in body")

    return lines

# ==================================================
# MAIN
# ==================================================

def main():
    used_cases = load_json(USED_CASES_FILE, [])
    used_hooks = load_json(USED_HOOKS_FILE, [])

    cid = fingerprint(CASE)
    if cid in used_cases:
        raise RuntimeError("❌ Case already used")

    # Rotate hook
    hook_pool = [h for h in HOOKS if h not in used_hooks] or HOOKS
    hook = random.choice(hook_pool)
    used_hooks.append(hook)

    cta = random.choice(CTAS)
    loop = random.choice(LOOPS)

    client = init_client()
    body = generate_body(client, CASE)

    script = [
        hook,
        *body,
        cta,
        loop,
    ]

    # Final validation
    if len(script) != 7:
        raise RuntimeError(f"❌ Script must be exactly 7 lines, got {len(script)}")

    for line in script:
        if "?" in line:
            raise RuntimeError("❌ Question marks are not allowed anywhere")

    SCRIPT_FILE.write_text("\n".join(script), encoding="utf-8")

    used_cases.append(cid)
    save_json(USED_CASES_FILE, used_cases)
    save_json(USED_HOOKS_FILE, used_hooks)

    print("✅ Script generated successfully\n")
    for i, l in enumerate(script, 1):
        print(f"{i}. {l}")

if __name__ == "__main__":
    main()
