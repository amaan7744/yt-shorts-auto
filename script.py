#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (RETENTION-OPTIMIZED)

STRUCTURE: EXACTLY 7 LINES
1. Hook (authority conflict / contradiction)
2–5. Body (tension ladder)
6. CTA (non-begging, investigative)
7. Loop (replay trigger)

TIMING: Enforced 30–50 seconds (speech-locked)
Tone: Investigative, factual, unsettling
"""

import os
import json
from pathlib import Path
from groq import Groq

# ==================================================
# CONSTANTS
# ==================================================

MIN_SECONDS = 30
MAX_SECONDS = 50
WORDS_PER_SECOND = 3

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")
MEMORY_DIR = Path("memory")
USED_CASES_FILE = MEMORY_DIR / "used_cases.json"
USED_HOOKS_FILE = MEMORY_DIR / "used_hooks.json"

MEMORY_DIR.mkdir(exist_ok=True)

CASE_FILE = Path("case.json")
if not CASE_FILE.exists():
    raise RuntimeError("❌ case.json missing")

CASE = json.loads(CASE_FILE.read_text(encoding="utf-8"))

# ==================================================
# REQUIRED CASE FIELDS
# ==================================================

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
# CASE TYPE DETECTION
# ==================================================

def detect_case_type(case):
    text = f"{case['summary']} {case['key_detail']} {case['official_story']}".lower()

    if "cold case" in text or "decades" in text:
        return "cold_case"
    if "missing" in text:
        return "missing_found"
    if "suicide" in text:
        return "suspicious_suicide"
    if "murder" in text or "killed" in text:
        return "murder"
    if "accident" in text:
        return "suspicious_accident"
    if "suspicious" in text or "unexplained" in text:
        return "suspicious_death"

    return "mystery"

# ==================================================
# RETENTION HOOKS (UPGRADED)
# ==================================================

HOOKS = {
    "suspicious_suicide": [
        "Police called it suicide. The scene said otherwise.",
        "The report said suicide. One detail made that impossible.",
        "Authorities closed the case in hours. The evidence didn't.",
        "If this was suicide, someone staged it perfectly.",
    ],
    "murder": [
        "Someone was killed. The investigation barely started.",
        "The body told one story. Police told another.",
        "They ruled out murder before checking the evidence.",
        "A killer walked free the day this case was closed.",
    ],
    "missing_found": [
        "She disappeared. Where they found her raised more questions.",
        "The search ended. The mystery doubled.",
        "She vanished quietly. The discovery was anything but.",
        "What happened between missing and found was never explained.",
    ],
    "cold_case": [
        "The case went cold. One detail never made sense.",
        "They stopped looking. The questions stayed.",
        "Decades passed. The truth stayed buried.",
        "This case was closed without being solved.",
    ],
    "suspicious_accident": [
        "They called it an accident. Accidents leave patterns.",
        "The scene looked wrong from the start.",
        "One mistake turned an accident into a mystery.",
        "If this was an accident, it was a perfect one.",
    ],
    "mystery": [
        "One detail in the report doesn't belong there.",
        "This case only makes sense if the official story is wrong.",
        "Everything points one way. The report points another.",
        "The truth was written down. Then ignored.",
    ],
}

HOOK_COOLDOWN = 20

def select_hook(case_type):
    used = load_json(USED_HOOKS_FILE, [])
    recent = used[-HOOK_COOLDOWN:]

    options = HOOKS.get(case_type, HOOKS["mystery"])
    available = [h for h in options if h not in recent] or options

    hook = available[0]
    used.append(hook)
    save_json(USED_HOOKS_FILE, used)
    return hook

# ==================================================
# CTA & LOOP (RETENTION SAFE)
# ==================================================

CTA_TEMPLATES = {
    "murder": "This case deserves attention, not silence.",
    "suspicious_death": "Cases like this don't solve themselves.",
    "suspicious_suicide": "Stories like this disappear without pressure.",
    "missing_found": "Someone knows what really happened.",
    "cold_case": "Cold cases only stay cold when people forget.",
    "suspicious_accident": "Accidents don't explain everything.",
    "mystery": "The truth usually surfaces when people keep asking.",
}

LOOP_TEMPLATES = {
    "murder": "Who benefited most from {name}'s death?",
    "suspicious_suicide": "Would you call this suicide if you saw the scene?",
    "missing_found": "What happened in the hours nobody accounted for?",
    "cold_case": "Which detail do you think investigators ignored?",
    "suspicious_accident": "Where did the official story fall apart?",
    "mystery": "Which explanation actually makes sense here?",
}

# ==================================================
# AI CLIENT
# ==================================================

def init_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

# ==================================================
# BODY GENERATION (TENSION LADDER)
# ==================================================

def generate_body(client, case):
    prompt = f"""
Write EXACTLY 4 lines for a true crime short.

Rules:
- Each line is ONE sentence.
- Tone: investigative, factual, unsettling.
- No filler. No hype.

Line 1: Establish time, place, and person.
Line 2: Describe what happened neutrally.
Line 3: Introduce ONE detail that does not fit.
Line 4: Explain how authorities closed the case anyway.

Case:
Name: {case['full_name']}
Location: {case['location']}
Date: {case['date']} at {case['time']}
Summary: {case['summary']}
Key Detail: {case['key_detail']}
Official Story: {case['official_story']}

Return only the 4 lines separated by newlines.
"""

    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.45,
        max_completion_tokens=350,
    )

    lines = [l.strip() for l in r.choices[0].message.content.split("\n") if l.strip()]
    return lines[:4]

# ==================================================
# VALIDATION (STRICT 30–50s)
# ==================================================

def validate_script(lines):
    words = sum(len(l.split()) for l in lines)
    seconds = words / WORDS_PER_SECOND

    if seconds < MIN_SECONDS:
        raise RuntimeError(f"❌ Script too short: {seconds:.1f}s")

    if seconds > MAX_SECONDS:
        raise RuntimeError(f"❌ Script too long: {seconds:.1f}s")

    if not lines[-1].endswith("?"):
        raise RuntimeError("❌ Final line must be a question")

    print(f"✅ Script locked at ~{seconds:.1f}s")

# ==================================================
# MAIN
# ==================================================

def main():
    used_cases = load_json(USED_CASES_FILE, [])
    cid = case_fingerprint(CASE)
    if cid in used_cases:
        raise RuntimeError("❌ Case already used")

    case_type = detect_case_type(CASE)
    client = init_client()

    hook = select_hook(case_type)
    body = generate_body(client, CASE)
    cta = CTA_TEMPLATES[case_type]
    loop = LOOP_TEMPLATES[case_type].format(name=CASE["full_name"])

    script = [hook] + body + [cta, loop]
    validate_script(script)

    SCRIPT_FILE.write_text("\n".join(script), encoding="utf-8")
    used_cases.append(cid)
    save_json(USED_CASES_FILE, used_cases)

    print("\n✅ SCRIPT GENERATED\n")
    for i, line in enumerate(script, 1):
        print(f"{i}. {line}")

if __name__ == "__main__":
    main()
