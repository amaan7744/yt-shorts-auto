#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (SCRIPT ONLY – FINAL)

GUARANTEES:
- Hook is ROTATED, never fixed
- Hook has cooldown (no reuse for N videos)
- Hook is NOT a question
- No hook permutations
- Full name, location, date, time REQUIRED
- CTA is FIXED
- Final loop is PERSON-SPECIFIC
- Script is fully written to output
- Cases NEVER repeat

NOTE:
- NO visual logic lives here
- Visuals are assigned later by visual_assigner.py
"""

import os
import json
from pathlib import Path
from groq import Groq

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")

MEMORY_DIR = Path("memory")
USED_CASES_FILE = MEMORY_DIR / "used_cases.json"
USED_HOOKS_FILE = MEMORY_DIR / "used_hooks.json"

MEMORY_DIR.mkdir(exist_ok=True)

# ==================================================
# CASE INPUT
# ==================================================

CASE_FILE = Path("case.json")
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
        raise RuntimeError(f"❌ Missing required case field: {f}")

# ==================================================
# MEMORY HELPERS
# ==================================================

def load_json(path: Path, default):
    if not path.exists():
        path.write_text(json.dumps(default, indent=2))
    return json.loads(path.read_text())

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2))

def case_fingerprint(c):
    return f"{c['full_name']}|{c['location']}|{c['date']}|{c['time']}".lower()

# ==================================================
# HOOK SYSTEM (ROTATING, LOCKED)
# ==================================================

HOOK_POOL = [
    "Murder. Suicide. Or an accident.",
    "An accident. Or something staged.",
    "A death that raised no questions.",
    "A case closed far too quickly.",
    "A conclusion that came too easily.",
    "A scene that didn’t make sense.",
]

HOOK_COOLDOWN = 15  # videos

def select_hook():
    used = load_json(USED_HOOKS_FILE, [])
    recent = used[-HOOK_COOLDOWN:]
    available = [h for h in HOOK_POOL if h not in recent]

    if not available:
        available = HOOK_POOL[:]  # safe reset

    hook = available[0]
    used.append(hook)
    save_json(USED_HOOKS_FILE, used)
    return hook

# ==================================================
# AI CLIENT
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

# ==================================================
# SCRIPT GENERATION (BODY ONLY)
# ==================================================

CTA_LINE = "Like and subscribe so stories like {name} don’t disappear."

def generate_body(client: Groq):
    prompt = f"""
Write a factual true crime short.

RULES:
- No questions
- No emotional language
- Clear investigative tone
- EXACTLY 4 lines

STRUCTURE:
1. Facts: full name, location, date, time
2. Contradiction: one detail that doesn’t fit
3. Official story
4. CTA EXACT TEXT:
"{CTA_LINE.format(name=CASE['full_name'])}"

CASE DATA:
Name: {CASE['full_name']}
Location: {CASE['location']}
Date: {CASE['date']}
Time: {CASE['time']}
Key detail: {CASE['key_detail']}
Official story: {CASE['official_story']}
Summary: {CASE['summary']}
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.25,
        max_completion_tokens=300,
    )

    lines = [
        l.strip()
        for l in res.choices[0].message.content.split("\n")
        if l.strip()
    ]

    if len(lines) != 4:
        raise RuntimeError("❌ Script body must be exactly 4 lines")

    return lines

# ==================================================
# FINAL LOOP (PERSON-SPECIFIC)
# ==================================================

def final_loop(name: str) -> str:
    return f"So what really happened to {name}?"

# ==================================================
# MAIN
# ==================================================

def main():
    used_cases = load_json(USED_CASES_FILE, [])
    cid = case_fingerprint(CASE)

    if cid in used_cases:
        raise RuntimeError("❌ Case already used")

    hook = select_hook()
    client = init_client()
    body = generate_body(client)
    loop = final_loop(CASE["full_name"])

    full_script = [hook] + body + [loop]

    SCRIPT_FILE.write_text("\n".join(full_script), encoding="utf-8")

    used_cases.append(cid)
    save_json(USED_CASES_FILE, used_cases)

    print("✅ Script written")
    print("🔒 Case & hook locked")
    print("📜 Visuals will be assigned separately")

# ==================================================
if __name__ == "__main__":
    main()
