#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (SIMPLIFIED, FLEXIBLE, ROBUST)

TIMING: 25+ seconds (flexible, not forced)
STRUCTURE: 7 lines exactly
1. Hook (powerful opening statement)
2-5. Body (flexible content from case)
6. CTA (call to action)
7. Loop (closing question)

TONE: Investigative, factual, engaging
NO rigid word count requirements
NO wasting LLM calls on formatting
Simple and direct content
"""

import os
import json
import re
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
# CASE TYPE DETECTION
# ==================================================

def detect_case_type(case):
    """Detect case type from summary and details"""
    text = f"{case['summary']} {case['key_detail']} {case['official_story']}".lower()
    
    if any(word in text for word in ["cold case", "decades", "years later", "unsolved", "solved after"]):
        return "cold_case"
    if any(word in text for word in ["missing", "disappeared", "found dead", "found body"]):
        return "missing_found"
    if any(word in text for word in ["suicide", "self-inflicted", "took own life"]):
        return "suspicious_suicide"
    if any(word in text for word in ["murder", "homicide", "killed", "slain", "shot", "stabbed"]):
        return "murder"
    if any(word in text for word in ["suspicious", "unexplained", "mysterious"]):
        return "suspicious_death"
    if any(word in text for word in ["accident", "fell", "drowning", "overdose"]):
        return "suspicious_accident"
    
    return "mystery"

# ==================================================
# HOOKS (SIMPLE, DIRECT)
# ==================================================

HOOKS = {
    "cold_case": [
        "Decades later, the questions remain unanswered.",
        "The case went cold. The mystery never did.",
        "Time passed. The truth didn't.",
        "They closed the case. The answers stayed hidden.",
    ],
    "murder": [
        "Someone died. Nobody paid for it.",
        "A life was taken. Justice was denied.",
        "Murder was ruled out. The victim wasn't.",
        "The scene told a story nobody wanted to hear.",
    ],
    "suspicious_death": [
        "The death was ruled natural. Everything about it was strange.",
        "They called it an accident. The evidence disagreed.",
        "One detail changes everything.",
        "The official story had holes from the start.",
    ],
    "suspicious_suicide": [
        "They called it suicide. But the evidence suggested murder.",
        "An impossible death ruled an easy conclusion.",
        "The details didn't add up. They closed the case anyway.",
        "What they reported and what happened were two different stories.",
    ],
    "missing_found": [
        "She vanished without a trace. What they found was worse.",
        "Missing for days. Found under impossible circumstances.",
        "Disappeared. Then discovered in a way that raised more questions.",
        "The search ended. The mystery didn't.",
    ],
    "suspicious_accident": [
        "An accident, they said. But accidents don't usually happen like this.",
        "The scene looked staged. The conclusion looked rushed.",
        "Too convenient to be coincidence.",
        "The official story was simpler than the facts.",
    ],
    "mystery": [
        "One detail buried in the report. One detail that changed everything.",
        "The case closed in forty-eight hours. The questions lasted decades.",
        "What they found and what they reported were not the same thing.",
        "The answer was there all along. Nobody looked for it.",
    ],
}

HOOK_COOLDOWN = 20

def select_hook(case, case_type):
    """Select best hook using case type"""
    used_hooks = load_json(USED_HOOKS_FILE, [])
    recent = used_hooks[-HOOK_COOLDOWN:] if len(used_hooks) >= HOOK_COOLDOWN else used_hooks
    
    hooks = HOOKS.get(case_type, HOOKS["mystery"])
    available = [h for h in hooks if h not in recent]
    
    if not available:
        available = hooks
    
    hook = available[0]
    used_hooks.append(hook)
    save_json(USED_HOOKS_FILE, used_hooks)
    
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
# CTA & LOOP TEMPLATES
# ==================================================

CTA_TEMPLATES = {
    "cold_case": "Like and subscribe so {name}'s story isn't forgotten.",
    "murder": "Like and subscribe so {name} gets justice.",
    "suspicious_death": "Like and subscribe so {name}'s questions get answered.",
    "suspicious_suicide": "Like and subscribe so {name}'s truth comes out.",
    "missing_found": "Like and subscribe so {name} isn't just another statistic.",
    "suspicious_accident": "Like and subscribe so {name}'s death gets investigated.",
    "mystery": "Like and subscribe so {name}'s mystery gets solved.",
}

LOOP_TEMPLATES = {
    "cold_case": "So what really happened to {name}?",
    "murder": "Who killed {name}?",
    "suspicious_death": "So what really happened to {name}?",
    "suspicious_suicide": "Did {name} really take their own life?",
    "missing_found": "What happened to {name} before they were found?",
    "suspicious_accident": "Was {name}'s death really an accident?",
    "mystery": "So what really happened to {name}?",
}

def get_cta(case_type, name):
    template = CTA_TEMPLATES.get(case_type, CTA_TEMPLATES["mystery"])
    return template.format(name=name)

def get_loop(case_type, name):
    template = LOOP_TEMPLATES.get(case_type, LOOP_TEMPLATES["mystery"])
    return template.format(name=name)

# ==================================================
# SCRIPT GENERATION (SIMPLE & FLEXIBLE)
# ==================================================

def generate_body(client: Groq, case, case_type):
    """
    Generate 4 body lines simply and directly.
    No forced word counts. Just good content.
    """
    
    prompt = f"""Create 4 powerful lines for a true crime short video script.
The case: {case['full_name']}. {case['location']}. {case['date']}.

Context: {case['summary']}
Key detail: {case['key_detail']}
Official story: {case['official_story']}

Write exactly 4 lines. Each line should be ONE complete sentence or thought.
- Line 1: Facts (name, location, date, time)
- Line 2: Who they were, what happened
- Line 3: The key suspicious detail
- Line 4: What authorities concluded

Make each line powerful and factual. No preamble, just the 4 lines.
Separate lines with newlines only.
No numbering. No labels. Just the content."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_completion_tokens=400,
    )
    
    content = response.choices[0].message.content.strip()
    
    # Simple split by newlines
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    
    # Take first 4 valid lines
    body = lines[:4]
    
    # If we got less than 4, pad with case data
    if len(body) < 4:
        print(f"⚠️  Got {len(body)} lines, using case data to fill")
        if len(body) == 0:
            body = [
                f"{case['full_name']}. {case['location']}. {case['date']}.",
                case['summary'],
                case['key_detail'],
                case['official_story'],
            ]
        else:
            # Pad with remaining case data
            while len(body) < 4:
                if len(body) == 1:
                    body.append(case['summary'])
                elif len(body) == 2:
                    body.append(case['key_detail'])
                else:
                    body.append(case['official_story'])
    
    return body[:4]  # Ensure exactly 4 lines

# ==================================================
# VALIDATION
# ==================================================

def validate_script(lines, case):
    """Validate script structure and timing"""
    
    if len(lines) != 7:
        raise RuntimeError(f"❌ Script must be 7 lines, got {len(lines)}")
    
    # Estimate timing (3 words per second)
    total_words = sum(len(line.split()) for line in lines)
    estimated_seconds = total_words / 3
    
    if estimated_seconds < 25:
        print(f"⚠️  Warning: Script is {estimated_seconds:.1f}s (target: 25+s)")
    
    if estimated_seconds > 60:
        raise RuntimeError(f"❌ Script too long: {estimated_seconds:.1f}s (max 60s)")
    
    # Check name appears
    name_parts = case['full_name'].split()
    name_found = any(part in " ".join(lines) for part in name_parts if len(part) > 3)
    
    if not name_found:
        print(f"⚠️  Warning: Name '{case['full_name']}' not strongly present in script")
    
    # Check final line is question
    if not lines[-1].endswith("?"):
        raise RuntimeError(f"❌ Final loop must be a question")
    
    print(f"✅ Script validation passed (~{estimated_seconds:.1f} seconds)")

# ==================================================
# MAIN
# ==================================================

def main():
    print("=" * 60)
    print("🎬 WEIGHTED SCRIPT GENERATOR")
    print("=" * 60)
    
    # Check for duplicate case
    used_cases = load_json(USED_CASES_FILE, [])
    cid = case_fingerprint(CASE)
    
    if cid in used_cases:
        raise RuntimeError("❌ Case already used")
    
    # Detect case type
    case_type = detect_case_type(CASE)
    print(f"📊 Case type: {case_type.replace('_', ' ').title()}")
    
    # Generate components
    client = init_client()
    
    # 1. Hook
    hook = select_hook(CASE, case_type)
    print(f"🎣 Hook: '{hook}'")
    
    # 2-5. Body (4 lines)
    print("📝 Generating body...")
    body = generate_body(client, CASE, case_type)
    print(f"   Got {len(body)} lines")
    
    # 6. CTA
    cta = get_cta(case_type, CASE["full_name"])
    print(f"📢 CTA: '{cta}'")
    
    # 7. Loop
    loop = get_loop(case_type, CASE["full_name"])
    print(f"🔄 Loop: '{loop}'")
    
    # Assemble full script
    full_script = [hook] + body + [cta, loop]
    
    # Validate
    validate_script(full_script, CASE)
    
    # Write to file
    SCRIPT_FILE.write_text("\n".join(full_script), encoding="utf-8")
    
    # Update memory
    used_cases.append(cid)
    save_json(USED_CASES_FILE, used_cases)
    
    # Display
    print()
    print("=" * 60)
    print("✅ SCRIPT GENERATED")
    print("=" * 60)
    print()
    
    labels = ["HOOK", "FACTS", "CONTEXT", "DETAIL", "OFFICIAL", "CTA", "LOOP"]
    for i, (line, label) in enumerate(zip(full_script, labels), 1):
        word_count = len(line.split())
        time_est = word_count / 3
        print(f"{i}. [{label}] ({word_count} words / ~{time_est:.1f}s)")
        print(f"   {line}")
        print()
    
    total_words = sum(len(line.split()) for line in full_script)
    total_time = total_words / 3
    
    print("=" * 60)
    print(f"TOTAL: {total_words} words / ~{total_time:.1f} seconds")
    print("=" * 60)
    print(f"📁 Script saved to: {SCRIPT_FILE}")

if __name__ == "__main__":
    main()
