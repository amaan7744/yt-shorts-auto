#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (LOCKED v1.0)

HARD CONTRACT (DO NOT BREAK):
- EXACTLY 7 lines
- Lines 1–6: 14–18 words each
- Line 7 (loop): 8–14 words, MUST end with '?'
- Estimated duration: ~30–45 seconds
- ZERO tolerance for deviation (fails fast)

STRUCTURE:
1. Hook (contradiction / authority conflict)
2. Facts (who, where, when)
3. What happened
4. Suspicious detail
5. Official conclusion
6. CTA (name-based, non-question)
7. Loop question
"""

import os
import json
from pathlib import Path
from groq import Groq

# ==================================================
# CONFIG
# ==================================================

WORDS_PER_SECOND = 3

MIN_WORDS = 14
MAX_WORDS = 18

LOOP_MIN = 8
LOOP_MAX = 14

SCRIPT_FILE = Path("script.txt")
CASE_FILE = Path("case.json")

MEMORY_DIR = Path("memory")
USED_CASES_FILE = MEMORY_DIR / "used_cases.json"
USED_HOOKS_FILE = MEMORY_DIR / "used_hooks.json"
USED_CTAS_FILE = MEMORY_DIR / "used_ctas.json"
USED_LOOPS_FILE = MEMORY_DIR / "used_loops.json"

MEMORY_DIR.mkdir(exist_ok=True)

# ==================================================
# HELPERS
# ==================================================

def load_json(path, default):
    if not path.exists():
        path.write_text(json.dumps(default, indent=2))
    return json.loads(path.read_text())

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

def wc(line):
    return len(line.split())

def guard_line(line, min_w, max_w, label):
    count = wc(line)
    if count < min_w or count > max_w:
        raise RuntimeError(f"{label} word count invalid ({count}): {line}")

# ==================================================
# LOAD CASE
# ==================================================

if not CASE_FILE.exists():
    raise RuntimeError("❌ case.json missing")

case = json.loads(CASE_FILE.read_text(encoding="utf-8"))

required = ["full_name", "location", "date", "time", "summary", "key_detail", "official_story"]
for f in required:
    if not case.get(f):
        raise RuntimeError(f"❌ Missing case field: {f}")

case_id = f"{case['full_name']}|{case['location']}|{case['date']}|{case['time']}".lower()
used_cases = load_json(USED_CASES_FILE, [])

if case_id in used_cases:
    raise RuntimeError("❌ Case already used")

# ==================================================
# AI CLIENT
# ==================================================

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("❌ GROQ_API_KEY missing")

client = Groq(api_key=api_key)

# ==================================================
# HOOKS / CTA / LOOP POOLS (ROTATED)
# ==================================================

HOOKS = [
    "Police ruled it suicide, but the physical evidence immediately contradicted that conclusion.",
    "Authorities closed the case quickly, yet multiple details refused to align logically.",
    "Investigators reached a conclusion that the scene itself did not support.",
    "The official report sounded simple, but the evidence told a different story.",
]

CTAS = [
    "Like and subscribe so {name}'s case does not disappear into official silence.",
    "Share this story to keep attention on what really happened to {name}.",
    "Follow for more cases where the official explanation leaves unanswered questions.",
]

LOOPS = [
    "So what detail do you think investigators chose to ignore here?",
    "Does the official explanation actually explain what happened to {name}?",
    "Which part of this case feels the most intentionally overlooked?",
]

def rotate(pool, used_path):
    used = load_json(used_path, [])
    available = [x for x in pool if x not in used] or pool
    choice = available[0]
    used.append(choice)
    save_json(used_path, used)
    return choice

# ==================================================
# GENERATE BODY (4 LINES, HARD GUARDED)
# ==================================================

BODY_PROMPT = f"""
Write EXACTLY 4 factual investigative lines for a true crime short.

STRICT RULES:
- Each line MUST be between {MIN_WORDS} and {MAX_WORDS} words
- NO questions
- NO emotional language
- NO filler
- Each line ONE sentence

STRUCTURE:
1. Establish who, where, when
2. Describe what was found or discovered
3. Present the single most suspicious detail
4. State the official conclusion by authorities

CASE DATA:
Name: {case['full_name']}
Location: {case['location']}
Date: {case['date']} at {case['time']}
Summary: {case['summary']}
Key Detail: {case['key_detail']}
Official Story: {case['official_story']}

Return ONLY the 4 lines separated by newlines.
"""

resp = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": BODY_PROMPT}],
    temperature=0.25,
    max_completion_tokens=400,
)

body = [l.strip() for l in resp.choices[0].message.content.split("\n") if l.strip()]

if len(body) != 4:
    raise RuntimeError(f"❌ Body must be exactly 4 lines, got {len(body)}")

for i, line in enumerate(body, 1):
    guard_line(line, MIN_WORDS, MAX_WORDS, f"Body line {i}")
    if "?" in line:
        raise RuntimeError(f"❌ Questions not allowed in body: {line}")

# ==================================================
# ASSEMBLE SCRIPT
# ==================================================

hook = rotate(HOOKS, USED_HOOKS_FILE)
guard_line(hook, MIN_WORDS, MAX_WORDS, "Hook")

cta = rotate(CTAS, USED_CTAS_FILE).format(name=case["full_name"])
guard_line(cta, MIN_WORDS, MAX_WORDS, "CTA")

loop = rotate(LOOPS, USED_LOOPS_FILE).format(name=case["full_name"])
guard_line(loop, LOOP_MIN, LOOP_MAX, "Loop")

if not loop.endswith("?"):
    raise RuntimeError("❌ Loop must end with a question mark")

script = [
    hook,
    body[0],
    body[1],
    body[2],
    body[3],
    cta,
    loop
]

if len(script) != 7:
    raise RuntimeError("❌ Script must contain exactly 7 lines")

# ==================================================
# FINAL VALIDATION
# ==================================================

total_words = sum(wc(l) for l in script)
duration = total_words / WORDS_PER_SECOND

if duration < 30 or duration > 45:
    raise RuntimeError(f"❌ Script duration invalid: ~{duration:.1f}s")

# ==================================================
# WRITE OUTPUT
# ==================================================

SCRIPT_FILE.write_text("\n".join(script), encoding="utf-8")
used_cases.append(case_id)
save_json(USED_CASES_FILE, used_cases)

print("\n✅ SCRIPT GENERATED (LOCKED)")
print(f"🕒 Estimated duration: ~{duration:.1f}s\n")

for i, line in enumerate(script, 1):
    print(f"{i}. ({wc(line)}w) {line}")
