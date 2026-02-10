#!/usr/bin/env python3
"""
True Crime Shorts – HUMANIZED SCRIPT GENERATOR
Stable, accusatory, XTTS-safe, algorithm-safe.

OUTPUT RULES:
- EXACTLY 7 lines
- No question marks
- Calm investigative tone
- Hook, body, CTA, closing loop
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

REQUIRED_FIELDS = [
    "full_name",
    "location",
    "date",
    "time",
    "summary",
    "key_detail",
    "official_story",
]

for f in REQUIRED_FIELDS:
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
# ROTATING HOOKS (ACCUSATORY, HUMAN)
# ==================================================

HOOKS = [
    "Police reached a conclusion before all the evidence was reviewed.",
    "The case was closed quickly, but the scene raised concerns.",
    "Authorities accepted the report without addressing key details.",
    "Investigators focused on an explanation that left gaps.",
    "The official conclusion did not fully match the scene.",
    "This case was resolved on paper, not through evidence.",
]

# ==================================================
# CTA (SUBTLE, NON-BEGGING)
# ==================================================

CTAS = [
    "Stories like this deserve continued attention.",
    "Cases like this should not fade from memory.",
    "Details matter when conclusions are rushed.",
    "Public attention keeps cases from disappearing.",
]

# ==================================================
# CLOSING LINE (LOOP WITHOUT QUESTIONS)
# ==================================================

CLOSING_LINES = [
    "The evidence still stands apart from the conclusion.",
    "Some details remain unresolved beneath the report.",
    "The record exists, but the truth feels incomplete.",
    "The official story left important details behind.",
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
# BODY GENERATION
# ==================================================

def generate_body(client: Groq, case):
    prompt = f"""
Write EXACTLY four factual sentences for a true crime short.

Rules:
- No questions
- No emotional language
- No speculation
- Calm investigative tone
- One sentence per line

Case:
Name: {case['full_name']}
Location: {case['location']}
Date: {case['date']} at {case['time']}
Summary: {case['summary']}
Key detail: {case['key_detail']}
Official story: {case['official_story']}

Return only four lines.
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
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
            raise RuntimeError("❌ Question marks are not allowed")

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

    # Rotate hook safely
    available_hooks = [h for h in HOOKS if h not in used_hooks] or HOOKS
    hook = random.choice(available_hooks)
    used_hooks.append(hook)

    cta = random.choice(CTAS)
    closing = random.choice(CLOSING_LINES)

    client = init_client()
    body = generate_body(client, CASE)

    script = [
        hook,
        *body,
        cta,
        closing,
    ]

    if len(script) != 7:
        raise RuntimeError(f"❌ Script must be exactly 7 lines, got {len(script)}")

    SCRIPT_FILE.write_text("\n".join(script), encoding="utf-8")

    used_cases.append(cid)
    save_json(USED_CASES_FILE, used_cases)
    save_json(USED_HOOKS_FILE, used_hooks)

    print("✅ Script generated successfully\n")
    for i, line in enumerate(script, 1):
        print(f"{i}. {line}")

if __name__ == "__main__":
    main()
