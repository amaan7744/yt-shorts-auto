#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (RETENTION ENGINE v4)

FEATURES:
- Rotating HOOK styles (no repetition)
- Rotating CTA intent (pressure / warning / accountability / curiosity)
- Rotating LOOP question types (replay triggers)
- Case-aware selection
- Speech-locked (30–50s)
- Pipeline safe (visuals, subs, beats)
"""

import os
import json
from pathlib import Path
from groq import Groq

# ==================================================
# CONSTANTS
# ==================================================

WORDS_PER_SECOND = 3
MIN_SECONDS = 30
MAX_SECONDS = 50

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")
MEMORY_DIR = Path("memory")
MEMORY_DIR.mkdir(exist_ok=True)

USED_CASES_FILE = MEMORY_DIR / "used_cases.json"
USED_HOOK_STYLE_FILE = MEMORY_DIR / "used_hook_styles.json"
USED_CTA_STYLE_FILE = MEMORY_DIR / "used_cta_styles.json"
USED_LOOP_STYLE_FILE = MEMORY_DIR / "used_loop_styles.json"

CASE = json.loads(Path("case.json").read_text(encoding="utf-8"))

# ==================================================
# MEMORY HELPERS
# ==================================================

def load_json(path, default):
    if not path.exists():
        path.write_text(json.dumps(default, indent=2))
    return json.loads(path.read_text())

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

def fingerprint(c):
    return f"{c['full_name']}|{c['location']}|{c['date']}|{c['time']}".lower()

# ==================================================
# CASE TYPE DETECTION
# ==================================================

def detect_case_type(c):
    t = f"{c['summary']} {c['key_detail']} {c['official_story']}".lower()
    if "suicide" in t:
        return "suspicious_suicide"
    if "murder" in t or "killed" in t:
        return "murder"
    if "missing" in t:
        return "missing_found"
    if "accident" in t:
        return "suspicious_accident"
    if "cold case" in t or "years later" in t:
        return "cold_case"
    return "mystery"

# ==================================================
# HOOK SYSTEM (STYLE ROTATION)
# ==================================================

HOOK_STYLES = {
    "contradiction": [
        "Police reached a conclusion, but the evidence pointed elsewhere.",
        "The report said one thing. The scene said another.",
    ],
    "impossibility": [
        "The scene shouldn’t have been possible.",
        "What investigators found shouldn’t have happened.",
    ],
    "timeline": [
        "The timeline only works if one detail is ignored.",
        "The clock didn’t agree with the official story.",
    ],
    "authority_conflict": [
        "Authorities closed the case before all questions were answered.",
        "Investigators ruled quickly, but the facts didn’t cooperate.",
    ],
    "evidence_focus": [
        "One piece of evidence never fit the explanation.",
        "The most important detail was treated as irrelevant.",
    ],
}

def select_rotating_style(style_dict, memory_file):
    used = load_json(memory_file, [])
    styles = list(style_dict.keys())

    for s in styles:
        if not used or s != used[-1]:
            used.append(s)
            save_json(memory_file, used)
            return s

    used.append(styles[0])
    save_json(memory_file, used)
    return styles[0]

def select_hook(case_type):
    style = select_rotating_style(HOOK_STYLES, USED_HOOK_STYLE_FILE)
    return HOOK_STYLES[style][0]

# ==================================================
# CTA SYSTEM (INTENT ROTATION)
# ==================================================

CTA_STYLES = {
    "pressure": [
        "If no one keeps asking, {name}'s story ends here.",
    ],
    "warning": [
        "Cases like {name}'s disappear when attention fades.",
    ],
    "accountability": [
        "Someone is responsible for what happened to {name}.",
    ],
    "curiosity": [
        "There’s more to {name}'s case than the report admits.",
    ],
}

def select_cta(name):
    style = select_rotating_style(CTA_STYLES, USED_CTA_STYLE_FILE)
    return CTA_STYLES[style][0].format(name=name)

# ==================================================
# LOOP SYSTEM (REPLAY TRIGGERS)
# ==================================================

LOOP_STYLES = {
    "contradiction": [
        "So how does the official story explain that detail?",
    ],
    "timeline": [
        "Where does the timeline stop making sense?",
    ],
    "motive": [
        "Who benefited from what happened next?",
    ],
    "evidence": [
        "Which piece of evidence would you want explained?",
    ],
}

def select_loop():
    style = select_rotating_style(LOOP_STYLES, USED_LOOP_STYLE_FILE)
    return LOOP_STYLES[style][0]

# ==================================================
# AI CLIENT
# ==================================================

def client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("❌ GROQ_API_KEY missing")
    return Groq(api_key=key)

# ==================================================
# BODY GENERATION (FACTUAL, TENSION LADDER)
# ==================================================

def generate_body(c, case):
    prompt = f"""
Write 4–5 factual lines for a true crime short.

RULES:
- No questions
- One sentence per line
- Investigative tone
- Focus on facts and contradictions

INCLUDE:
- Identity + time/place
- What was found
- One inconsistency
- Official conclusion

CASE:
Name: {case['full_name']}
Location: {case['location']}
Date: {case['date']} at {case['time']}
Summary: {case['summary']}
Key detail: {case['key_detail']}
Official story: {case['official_story']}

Return only the lines.
"""

    r = c.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        max_completion_tokens=300,
    )

    lines = [l.strip() for l in r.choices[0].message.content.split("\n") if l.strip()]
    return lines[:5]

# ==================================================
# VALIDATION
# ==================================================

def validate(lines):
    seconds = sum(len(l.split()) for l in lines) / WORDS_PER_SECOND
    if not (MIN_SECONDS <= seconds <= MAX_SECONDS):
        raise RuntimeError(f"❌ Script duration {seconds:.1f}s out of bounds")
    if not lines[-1].endswith("?"):
        raise RuntimeError("❌ Final line must be a question")

# ==================================================
# MAIN
# ==================================================

def main():
    used_cases = load_json(USED_CASES_FILE, [])
    cid = fingerprint(CASE)
    if cid in used_cases:
        raise RuntimeError("❌ Case already used")

    c = client()
    case_type = detect_case_type(CASE)

    hook = select_hook(case_type)
    body = generate_body(c, CASE)
    cta = select_cta(CASE["full_name"])
    loop = select_loop()

    script = [hook] + body + [cta, loop]
    validate(script)

    SCRIPT_FILE.write_text("\n".join(script), encoding="utf-8")
    used_cases.append(cid)
    save_json(USED_CASES_FILE, used_cases)

    print("\n✅ SCRIPT GENERATED (ROTATION ACTIVE)\n")
    for i, line in enumerate(script, 1):
        print(f"{i}. {line}")

if __name__ == "__main__":
    main()
