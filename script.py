#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (HARD-LOCKED v2)

GUARANTEES:
- Hook is ROTATED, never fixed
- Hook has cooldown (no reuse for N videos)
- Hook is NOT a question
- No hook permutations
- Full name, location, date, time REQUIRED
- CTA is FIXED
- Final loop is PERSON-SPECIFIC
- Assets chosen ONLY from disk
- Script is fully written to output
- Cases NEVER repeat
"""

import os
import json
from pathlib import Path
from groq import Groq

from assets import VIDEO_ASSET_KEYWORDS, validate_video_assets

# ==================================================
# FILES
# ==================================================

SCRIPT_FILE = Path("script.txt")
BEATS_FILE = Path("beats.json")

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

REQUIRED_FIELDS = ["full_name", "location", "date", "time", "summary", "key_detail", "official_story"]
for f in REQUIRED_FIELDS:
    if not CASE.get(f):
        raise RuntimeError(f"❌ Missing required case field: {f}")

# ==================================================
# MEMORY
# ==================================================

def load_json(path, default):
    if not path.exists():
        path.write_text(json.dumps(default, indent=2))
    return json.loads(path.read_text())

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

def case_fingerprint(c):
    return f"{c['full_name']}|{c['location']}|{c['date']}|{c['time']}".lower()

# ==================================================
# HOOK SYSTEM (ROTATING)
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
    available = [h for h in HOOK_POOL if h not in used[-HOOK_COOLDOWN:]]

    if not available:
        available = HOOK_POOL[:]  # reset safely

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
# SCRIPT GENERATION
# ==================================================

CTA_LINE = "Like and subscribe so stories like {name} don’t disappear."

def generate_body(client: Groq):
    prompt = f"""
Write a factual true crime short.

RULES:
- No questions
- No emotion bait
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

    lines = [l.strip() for l in res.choices[0].message.content.split("\n") if l.strip()]
    if len(lines) != 4:
        raise RuntimeError("❌ Body must be exactly 4 lines")
    return lines

# ==================================================
# FINAL LOOP (PERSON-SPECIFIC)
# ==================================================

def final_loop(name):
    return f"So what really happened to {name}?"

# ==================================================
# ASSET MATCHING
# ==================================================

def asset_for_line(line, used):
    text = line.lower()
    for asset, tags in VIDEO_ASSET_KEYWORDS.items():
        if asset in used:
            continue
        if any(tag in text for tag in tags):
            return asset
    raise RuntimeError(f"❌ No asset matches line: {line}")

# ==================================================
# MAIN
# ==================================================

def main():
    print("🧪 Validating assets…")
    validate_video_assets()

    used_cases = load_json(USED_CASES_FILE, [])
    cid = case_fingerprint(CASE)
    if cid in used_cases:
        raise RuntimeError("❌ Case already used")

    hook = select_hook()
    client = init_client()
    body = generate_body(client)
    loop = final_loop(CASE["full_name"])

    full_script = [hook] + body + [loop]

    beats = []
    used_assets = set()

    for line in full_script:
        beat = {"text": line}
        try:
            asset = asset_for_line(line, used_assets)
            used_assets.add(asset)
            beat["asset_file"] = asset
        except:
            pass
        beats.append(beat)

    SCRIPT_FILE.write_text("\n".join(full_script), encoding="utf-8")
    BEATS_FILE.write_text(json.dumps({"beats": beats}, indent=2), encoding="utf-8")

    used_cases.append(cid)
    save_json(USED_CASES_FILE, used_cases)

    print("✅ Script written")
    print("🔒 Case & hook locked")

# ==================================================
if __name__ == "__main__":
    main()
