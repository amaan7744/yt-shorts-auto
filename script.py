#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (ULTIMATE VERSION)

FEATURES:
- 50+ case-aware hooks (matched to case details)
- Dynamic script structure (4-7 lines based on case complexity)
- Multiple CTA variations (all use person's name)
- Smart final loop (question format, name-specific)
- Case type detection (murder/suicide/missing/cold case/suspicious)
- Enhanced contradiction building
- Emotional arc construction
- Never repeats cases or hooks (with cooldown)
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
HOOK_PERFORMANCE_FILE = MEMORY_DIR / "hook_performance.json"

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
    
    # Priority order matters
    if any(word in text for word in ["cold case", "decades", "years later", "unsolved", "solved after"]):
        return "cold_case"
    
    if any(word in text for word in ["missing", "disappeared", "found dead", "found body"]):
        return "missing_found"
    
    if any(word in text for word in ["suicide", "self-inflicted", "took own life", "killed himself", "killed herself"]):
        return "suspicious_suicide"
    
    if any(word in text for word in ["murder", "homicide", "killed", "slain", "shot", "stabbed"]):
        return "murder"
    
    if any(word in text for word in ["suspicious", "unexplained", "mysterious", "unclear", "investigating"]):
        return "suspicious_death"
    
    if any(word in text for word in ["accident", "fell", "drowning", "overdose"]):
        return "suspicious_accident"
    
    return "mystery"

# ==================================================
# EXPANDED HOOK SYSTEM (CASE-AWARE)
# ==================================================

HOOK_CATEGORIES = {
    "locked_impossible": [
        "A locked door. No forced entry. No explanation.",
        "An impossible scene. No witnesses. No answers.",
        "Sealed from inside. No way out. No sense.",
        "A locked room. A body. An impossibility.",
    ],
    
    "timeline_contradiction": [
        "The timeline didn't add up.",
        "The clock told one story. The evidence told another.",
        "Twenty minutes. That's all it took. Or was it.",
        "The timeline broke. The alibi held. Something was wrong.",
    ],
    
    "evidence_missing": [
        "The weapon was never found.",
        "Evidence disappeared. Questions remained.",
        "What wasn't there mattered more than what was.",
        "The missing piece changed everything.",
        "Something was taken. Something that mattered.",
    ],
    
    "staged_scene": [
        "Too perfect. Too clean. Too staged.",
        "A scene arranged. A story prepared. A lie exposed.",
        "Nothing out of place. Except everything.",
        "The scene told a story. But not the real one.",
    ],
    
    "witness_contradiction": [
        "Two witnesses. Two stories. One lie.",
        "Everyone saw something different.",
        "The stories didn't match. Someone was lying.",
        "What they said changed. What they knew stayed hidden.",
    ],
    
    "quick_conclusion": [
        "Case closed. Questions ignored.",
        "An answer that came too fast.",
        "They stopped looking. They shouldn't have.",
        "The investigation ended. The mystery didn't.",
        "Solved in hours. Doubted for years.",
    ],
    
    "hidden_detail": [
        "One detail changed everything.",
        "What they found changed what they knew.",
        "A small detail. A massive lie.",
        "The truth was in what they almost missed.",
    ],
    
    "double_life": [
        "A secret life. A public death.",
        "Everyone knew them. No one knew the truth.",
        "Two lives. One person. Fatal secrets.",
        "The person they knew never existed.",
    ],
    
    "no_motive": [
        "No motive. No suspect. No sense.",
        "Who benefits when no one should.",
        "A death without reason. Or so it seemed.",
        "The motive was there. Hidden in plain sight.",
    ],
    
    "forensic_contradiction": [
        "The body told a different story.",
        "Forensics revealed what investigators missed.",
        "The science didn't match the scene.",
        "What killed them wasn't what they thought.",
    ],
    
    "final_message": [
        "The last thing they said changed everything.",
        "A final call. A cryptic message. A warning unheeded.",
        "Their last words held the answer.",
        "What they wrote before they died.",
    ],
    
    "wrong_person": [
        "The suspect everyone believed. The truth no one saw.",
        "An arrest. A conviction. A mistake.",
        "They got their killer. But not the right one.",
        "Justice served. Truth buried.",
    ],
    
    "location_significance": [
        "That place. That time. Not a coincidence.",
        "The location told its own story.",
        "Why there. Why then. The answers mattered.",
        "Geography revealed intent.",
    ],
}

HOOK_COOLDOWN = 20  # videos before reusing same hook

def match_hook_to_case(case, case_type):
    """Select best hook category based on case details"""
    text = f"{case['summary']} {case['key_detail']} {case['official_story']}".lower()
    
    # Score each category
    scores = {}
    
    # Locked/impossible
    if any(word in text for word in ["locked", "sealed", "closed door", "no entry", "impossible"]):
        scores["locked_impossible"] = 10
    
    # Timeline
    if any(word in text for word in ["timeline", "time", "minutes", "hours", "when", "alibi"]):
        scores["timeline_contradiction"] = 8
    
    # Missing evidence
    if any(word in text for word in ["missing", "never found", "disappeared", "weapon", "evidence"]):
        scores["evidence_missing"] = 9
    
    # Staged
    if any(word in text for word in ["staged", "arranged", "too clean", "perfect", "organized"]):
        scores["staged_scene"] = 10
    
    # Witness issues
    if any(word in text for word in ["witness", "saw", "heard", "reported", "statement", "testimony"]):
        scores["witness_contradiction"] = 7
    
    # Quick conclusion
    if any(word in text for word in ["quickly", "closed", "ruled", "determined", "concluded"]):
        scores["quick_conclusion"] = 8
    
    # Hidden detail
    if any(word in text for word in ["detail", "discovered", "found", "revealed", "uncovered"]):
        scores["hidden_detail"] = 6
    
    # Double life
    if any(word in text for word in ["secret", "hidden", "unknown", "double", "affair"]):
        scores["double_life"] = 9
    
    # No motive
    if any(word in text for word in ["no motive", "no reason", "why", "unexplained"]):
        scores["no_motive"] = 8
    
    # Forensic
    if any(word in text for word in ["forensic", "autopsy", "body", "examination", "pathologist"]):
        scores["forensic_contradiction"] = 7
    
    # Final message
    if any(word in text for word in ["last", "final", "message", "call", "text", "note", "wrote"]):
        scores["final_message"] = 10
    
    # Wrong person
    if any(word in text for word in ["arrest", "suspect", "charged", "convicted", "wrong"]):
        scores["wrong_person"] = 9
    
    # Location
    if any(word in text for word in ["location", "place", "where", "scene", "found at"]):
        scores["location_significance"] = 5
    
    # Return top scoring categories (or default to mystery)
    if not scores:
        return ["quick_conclusion", "hidden_detail", "no_motive"]
    
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [cat for cat, score in sorted_categories[:3]]

def select_hook(case, case_type):
    """Select best hook using case-aware matching with cooldown"""
    used_hooks = load_json(USED_HOOKS_FILE, [])
    recent = used_hooks[-HOOK_COOLDOWN:] if len(used_hooks) >= HOOK_COOLDOWN else used_hooks
    
    # Get relevant categories for this case
    relevant_categories = match_hook_to_case(case, case_type)
    
    # Collect available hooks from relevant categories
    available = []
    for category in relevant_categories:
        if category in HOOK_CATEGORIES:
            category_hooks = [h for h in HOOK_CATEGORIES[category] if h not in recent]
            available.extend(category_hooks)
    
    # Fallback: use any hook not in recent
    if not available:
        all_hooks = [h for category in HOOK_CATEGORIES.values() for h in category]
        available = [h for h in all_hooks if h not in recent]
    
    # Emergency fallback: reset if all hooks used
    if not available:
        available = [h for category in HOOK_CATEGORIES.values() for h in category]
    
    # Select first available (deterministic)
    hook = available[0]
    
    # Update used hooks
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
# CTA VARIATIONS (ALL USE NAME)
# ==================================================

CTA_TEMPLATES = {
    "cold_case": [
        "Like and subscribe so {name}'s story isn't forgotten.",
        "Share this so {name}'s case stays alive.",
        "Don't let {name}'s story disappear.",
    ],
    "murder": [
        "Like and subscribe so {name} gets justice.",
        "Share this. {name} deserves to be remembered.",
        "Don't scroll past {name}'s story.",
    ],
    "suspicious_death": [
        "Like and subscribe so {name}'s questions get answered.",
        "Share this. {name} deserves the truth.",
        "Don't let {name}'s case go cold.",
    ],
    "suspicious_suicide": [
        "Like and subscribe so {name}'s truth comes out.",
        "Share this. {name}'s family deserves answers.",
        "Don't ignore what happened to {name}.",
    ],
    "missing_found": [
        "Like and subscribe so {name} isn't just another statistic.",
        "Share this. {name} was found. The questions weren't.",
        "Don't let {name} be forgotten.",
    ],
    "suspicious_accident": [
        "Like and subscribe so {name}'s accident gets investigated.",
        "Share this. {name} deserves a real investigation.",
        "Don't accept the easy answer for {name}.",
    ],
    "mystery": [
        "Like and subscribe so {name}'s mystery gets solved.",
        "Share this. {name} deserves answers.",
        "Don't let {name}'s case stay unsolved.",
    ],
}

def get_cta(case_type, name):
    """Get appropriate CTA for case type"""
    templates = CTA_TEMPLATES.get(case_type, CTA_TEMPLATES["mystery"])
    # Use first template (deterministic)
    return templates[0].format(name=name)

# ==================================================
# FINAL LOOP VARIATIONS (QUESTION FORMAT, NAME-SPECIFIC)
# ==================================================

LOOP_TEMPLATES = {
    "cold_case": [
        "So what really happened to {name}?",
        "Who killed {name}?",
        "Will {name} ever get justice?",
    ],
    "murder": [
        "So what really happened to {name}?",
        "Who killed {name}?",
        "Why did {name} have to die?",
    ],
    "suspicious_death": [
        "So what really happened to {name}?",
        "How did {name} really die?",
        "Was {name}'s death really an accident?",
    ],
    "suspicious_suicide": [
        "Did {name} really take their own life?",
        "So what really happened to {name}?",
        "Was {name}'s suicide what it seemed?",
    ],
    "missing_found": [
        "What happened to {name} before they were found?",
        "So what really happened to {name}?",
        "Who killed {name}?",
    ],
    "suspicious_accident": [
        "Was {name}'s death really an accident?",
        "So what really happened to {name}?",
        "Did {name} fall, or were they pushed?",
    ],
    "mystery": [
        "So what really happened to {name}?",
        "What's the truth about {name}?",
        "Will we ever know what happened to {name}?",
    ],
}

def get_final_loop(case_type, name):
    """Get appropriate final loop question"""
    templates = LOOP_TEMPLATES.get(case_type, LOOP_TEMPLATES["mystery"])
    # Use first template (deterministic)
    return templates[0].format(name=name)

# ==================================================
# SCRIPT GENERATION (ENHANCED)
# ==================================================

def generate_body(client: Groq, case, case_type):
    """Generate script body with dynamic structure"""
    
    # Determine script complexity based on case details
    detail_count = len(case['key_detail']) + len(case['summary'])
    use_extended = detail_count > 300  # Longer cases get more lines
    
    cta_text = get_cta(case_type, case['full_name'])
    
    if use_extended:
        # 5-line body for complex cases
        prompt = f"""
Write a factual true crime short script.

CRITICAL RULES:
- NO questions anywhere in the script
- NO emotional language or dramatic phrases
- Clear, direct investigative tone
- State facts, evidence, and contradictions
- EXACTLY 5 lines

CASE TYPE: {case_type.replace('_', ' ').title()}

STRUCTURE (5 LINES):
Line 1: Full name, location, date, time - establish the facts
Line 2: What was discovered - the scene, the body, the initial finding
Line 3: The key contradiction - what didn't fit, what investigators noticed
Line 4: What forensics/evidence revealed - the critical detail that changed things
Line 5: Official story - what authorities concluded or are investigating

CRITICAL: 
- Line 5 MUST be EXACTLY: "{cta_text}"
- NO questions in any line
- Keep each line under 20 words
- Use factual, investigative language

CASE DATA:
Name: {case['full_name']}
Location: {case['location']}
Date: {case['date']}
Time: {case['time']}
Key detail: {case['key_detail']}
Official story: {case['official_story']}
Summary: {case['summary']}

Write ONLY the 5 lines, nothing else:
"""
    else:
        # 4-line body for standard cases
        prompt = f"""
Write a factual true crime short script.

CRITICAL RULES:
- NO questions anywhere in the script
- NO emotional language or dramatic phrases
- Clear, direct investigative tone
- State facts, evidence, and contradictions
- EXACTLY 4 lines

CASE TYPE: {case_type.replace('_', ' ').title()}

STRUCTURE (4 LINES):
Line 1: Full name, location, date, time - establish the facts
Line 2: The key contradiction - what didn't fit, what was suspicious
Line 3: What investigators found or concluded - the official story
Line 4: MUST be EXACTLY: "{cta_text}"

CRITICAL:
- Line 4 MUST be word-for-word: "{cta_text}"
- NO questions in any line
- Keep each line under 20 words
- Use factual, investigative language

CASE DATA:
Name: {case['full_name']}
Location: {case['location']}
Date: {case['date']}
Time: {case['time']}
Key detail: {case['key_detail']}
Official story: {case['official_story']}
Summary: {case['summary']}

Write ONLY the 4 lines, nothing else:
"""
    
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_completion_tokens=400,
    )
    
    lines = [
        l.strip()
        for l in res.choices[0].message.content.split("\n")
        if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("Line")
    ]
    
    expected_lines = 5 if use_extended else 4
    
    if len(lines) != expected_lines:
        raise RuntimeError(f"❌ Script body must be exactly {expected_lines} lines, got {len(lines)}")
    
    # Validate no questions
    for line in lines:
        if "?" in line:
            raise RuntimeError(f"❌ Questions not allowed in script body: {line}")
    
    return lines

# ==================================================
# VALIDATION
# ==================================================

def validate_script(lines, case):
    """Validate script quality and accuracy"""
    
    # Check minimum length
    if len(lines) < 6:
        raise RuntimeError(f"❌ Script too short: {len(lines)} lines")
    
    # Check each line has content
    for i, line in enumerate(lines, 1):
        if len(line) < 10:
            raise RuntimeError(f"❌ Line {i} too short: '{line}'")
        if len(line) > 200:
            raise RuntimeError(f"❌ Line {i} too long: '{line}'")
    
    # Check name appears in script
    name_parts = case['full_name'].split()
    name_found = any(part in " ".join(lines) for part in name_parts if len(part) > 3)
    
    if not name_found:
        raise RuntimeError(f"❌ Name '{case['full_name']}' not found in script")
    
    # Check final line is a question
    if not lines[-1].endswith("?"):
        raise RuntimeError(f"❌ Final loop must be a question: '{lines[-1]}'")
    
    # Check only final line has question mark
    for line in lines[:-1]:
        if "?" in line:
            raise RuntimeError(f"❌ Questions only allowed in final loop: '{line}'")
    
    print("✅ Script validation passed")

# ==================================================
# MAIN
# ==================================================

def main():
    print("="*60)
    print("🎬 SCRIPT GENERATOR - ULTIMATE VERSION")
    print("="*60)
    
    # Check for duplicate case
    used_cases = load_json(USED_CASES_FILE, [])
    cid = case_fingerprint(CASE)
    
    if cid in used_cases:
        raise RuntimeError("❌ Case already used")
    
    # Detect case type
    case_type = detect_case_type(CASE)
    print(f"📊 Case type detected: {case_type.replace('_', ' ').title()}")
    
    # Select hook
    hook = select_hook(CASE, case_type)
    print(f"🎣 Hook selected: '{hook}'")
    
    # Generate body
    client = init_client()
    body = generate_body(client, CASE, case_type)
    print(f"📝 Body generated: {len(body)} lines")
    
    # Generate final loop
    loop = get_final_loop(case_type, CASE["full_name"])
    print(f"🔄 Loop: '{loop}'")
    
    # Assemble full script
    full_script = [hook] + body + [loop]
    
    # Validate
    validate_script(full_script, CASE)
    
    # Write to file
    SCRIPT_FILE.write_text("\n".join(full_script), encoding="utf-8")
    
    # Update memory
    used_cases.append(cid)
    save_json(USED_CASES_FILE, used_cases)
    
    print("\n" + "="*60)
    print("✅ SCRIPT WRITTEN SUCCESSFULLY")
    print("="*60)
    print(f"📄 Total lines: {len(full_script)}")
    print(f"🎯 Structure: Hook + {len(body)} body + Loop")
    print(f"👤 Featured: {CASE['full_name']}")
    print(f"🔒 Case fingerprint saved")
    print(f"📜 Ready for visual assignment")
    print("="*60)
    
    # Display script
    print("\n📋 GENERATED SCRIPT:")
    print("-"*60)
    for i, line in enumerate(full_script, 1):
        print(f"{i}. {line}")
    print("-"*60)

# ==================================================
if __name__ == "__main__":
    main()
