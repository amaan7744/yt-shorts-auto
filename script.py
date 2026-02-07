#!/usr/bin/env python3
"""
True Crime Shorts – Script Generator (ENHANCED WEIGHTED VERSION)

TIMING: 35-45 seconds (strict)
STRUCTURE: 7 lines exactly
- Hook (statement) - 3-4 sec
- Facts (name/place/time) - 5-6 sec
- Context (who they were) - 5-6 sec
- Contradiction (the weight) - 7-8 sec
- Official Story - 7-8 sec
- CTA (fixed) - 4-5 sec
- Loop (question) - 4-5 sec

TONE: Heavy, investigative, weighted - NOT storytelling
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
# WEIGHTED HOOKS (STATEMENT FORMAT - NO QUESTIONS)
# ==================================================

WEIGHTED_HOOKS = {
    "locked_impossible": [
        "A locked door. No forced entry. No explanation.",
        "The room was sealed from inside. The body was inside. The killer was not.",
        "Investigators found the door locked. The windows sealed. The scene impossible.",
        "Every exit was secured. Every entry was blocked. Someone still got in.",
    ],
    
    "timeline_shattered": [
        "The timeline didn't just break. It shattered everything they thought they knew.",
        "Forty-seven minutes. That's how long the alibi held before forensics proved otherwise.",
        "The clock said one thing. The body temperature said another. Someone was lying.",
        "They had twelve hours. The evidence showed twelve minutes. The case fell apart.",
    ],
    
    "evidence_vanished": [
        "The weapon vanished. The motive stayed. The questions multiplied.",
        "Three critical pieces of evidence. Three unexplained disappearances. One conclusion.",
        "What wasn't at the scene told investigators more than what was.",
        "The evidence they needed most was the evidence that disappeared first.",
    ],
    
    "too_perfect": [
        "The scene was too clean. Too organized. Too perfectly wrong.",
        "Everything was in place. Except the truth.",
        "Staged scenes leave patterns. This one left fingerprints all over the lie.",
        "When a crime scene looks rehearsed, someone rehearsed it.",
    ],
    
    "witness_collapse": [
        "Three witnesses. Three versions. Three lies that fell apart under pressure.",
        "The story changed every time they told it. The truth never did.",
        "What they saw didn't match. What they heard didn't align. What they knew stayed buried.",
        "Eyewitness accounts crumbled. Physical evidence didn't.",
    ],
    
    "rushed_verdict": [
        "The case closed in forty-eight hours. The questions lasted decades.",
        "They called it solved before the autopsy came back. They were wrong.",
        "An answer came fast. Too fast. The real investigation never happened.",
        "When authorities rush to judgment, they rush past the truth.",
    ],
    
    "buried_detail": [
        "One detail buried in the report. One detail that changed everything.",
        "Investigators missed it the first time. The second time, it was too late.",
        "The evidence was there. Filed away. Ignored. Critical.",
        "What they overlooked became what they couldn't explain.",
    ],
    
    "double_existence": [
        "The person everyone knew never existed. The person no one knew was real.",
        "A public life. A secret life. A fatal collision between the two.",
        "They thought they knew them. They didn't know anything.",
        "Two identities. One body. Infinite questions.",
    ],
    
    "motiveless": [
        "No enemies. No motive. No reason anyone could see. Except one.",
        "The question wasn't who wanted them dead. It was who benefited from the secret staying buried.",
        "When there's no apparent motive, the real motive is buried deeper.",
        "Follow the money, they said. The money led nowhere. The truth led somewhere else.",
    ],
    
    "forensic_warfare": [
        "The autopsy revealed what the scene concealed.",
        "Forensic evidence doesn't lie. Crime scenes do.",
        "The medical examiner saw what detectives missed. And it changed everything.",
        "Science said one thing. The official story said another. Science won.",
    ],
    
    "final_communication": [
        "The last message they sent. The one no one understood until after.",
        "Their final words weren't random. They were a warning.",
        "What they said in their last moments stayed silent until investigators listened.",
        "The message was there. Encrypted in plain sight. Deadly accurate.",
    ],
    
    "wrong_conviction": [
        "They arrested the obvious suspect. Charged them. Convicted them. And got it wrong.",
        "A confession under pressure. Evidence that didn't fit. A verdict that couldn't stand.",
        "The right person went to prison. For the wrong crime. While the real killer walked.",
        "Justice served doesn't mean truth found.",
    ],
    
    "location_speaks": [
        "The place they died told investigators exactly how they died. If only they'd listened.",
        "Location matters. Timing matters. Both together reveal intent.",
        "That specific spot. That specific moment. Nothing about it was coincidence.",
        "Geography doesn't lie about motive.",
    ],
}

HOOK_COOLDOWN = 20

def match_hook_to_case(case, case_type):
    """Select best hook category based on case details"""
    text = f"{case['summary']} {case['key_detail']} {case['official_story']}".lower()
    
    scores = {}
    
    if any(word in text for word in ["locked", "sealed", "closed door", "no entry", "impossible"]):
        scores["locked_impossible"] = 10
    
    if any(word in text for word in ["timeline", "time", "minutes", "hours", "when", "alibi", "clock"]):
        scores["timeline_shattered"] = 9
    
    if any(word in text for word in ["missing", "never found", "disappeared", "weapon", "evidence", "vanished"]):
        scores["evidence_vanished"] = 9
    
    if any(word in text for word in ["staged", "arranged", "too clean", "perfect", "organized", "rehearsed"]):
        scores["too_perfect"] = 10
    
    if any(word in text for word in ["witness", "saw", "heard", "reported", "statement", "testimony", "account"]):
        scores["witness_collapse"] = 8
    
    if any(word in text for word in ["quickly", "closed", "ruled", "determined", "concluded", "rushed", "hours", "days"]):
        scores["rushed_verdict"] = 8
    
    if any(word in text for word in ["detail", "discovered", "found", "revealed", "uncovered", "missed", "overlooked"]):
        scores["buried_detail"] = 7
    
    if any(word in text for word in ["secret", "hidden", "unknown", "double", "affair", "identity", "life"]):
        scores["double_existence"] = 9
    
    if any(word in text for word in ["no motive", "no reason", "why", "unexplained", "no enemies"]):
        scores["motiveless"] = 8
    
    if any(word in text for word in ["forensic", "autopsy", "body", "examination", "pathologist", "medical examiner"]):
        scores["forensic_warfare"] = 8
    
    if any(word in text for word in ["last", "final", "message", "call", "text", "note", "wrote", "said"]):
        scores["final_communication"] = 10
    
    if any(word in text for word in ["arrest", "suspect", "charged", "convicted", "wrong", "innocent"]):
        scores["wrong_conviction"] = 9
    
    if any(word in text for word in ["location", "place", "where", "scene", "found at", "spot"]):
        scores["location_speaks"] = 6
    
    if not scores:
        return ["rushed_verdict", "buried_detail", "motiveless"]
    
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [cat for cat, score in sorted_categories[:3]]

def select_hook(case, case_type):
    """Select best hook using case-aware matching with cooldown"""
    used_hooks = load_json(USED_HOOKS_FILE, [])
    recent = used_hooks[-HOOK_COOLDOWN:] if len(used_hooks) >= HOOK_COOLDOWN else used_hooks
    
    relevant_categories = match_hook_to_case(case, case_type)
    
    available = []
    for category in relevant_categories:
        if category in WEIGHTED_HOOKS:
            category_hooks = [h for h in WEIGHTED_HOOKS[category] if h not in recent]
            available.extend(category_hooks)
    
    if not available:
        all_hooks = [h for category in WEIGHTED_HOOKS.values() for h in category]
        available = [h for h in all_hooks if h not in recent]
    
    if not available:
        available = [h for category in WEIGHTED_HOOKS.values() for h in category]
    
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
# CTA VARIATIONS (ALL USE NAME)
# ==================================================

CTA_TEMPLATES = {
    "cold_case": "Like and subscribe so {name}'s story isn't forgotten.",
    "murder": "Like and subscribe so {name} gets justice.",
    "suspicious_death": "Like and subscribe so {name}'s questions get answered.",
    "suspicious_suicide": "Like and subscribe so {name}'s truth comes out.",
    "missing_found": "Like and subscribe so {name} isn't just another statistic.",
    "suspicious_accident": "Like and subscribe so {name}'s accident gets investigated.",
    "mystery": "Like and subscribe so {name}'s mystery gets solved.",
}

def get_cta(case_type, name):
    """Get appropriate CTA for case type"""
    template = CTA_TEMPLATES.get(case_type, CTA_TEMPLATES["mystery"])
    return template.format(name=name)

# ==================================================
# FINAL LOOP VARIATIONS (QUESTION FORMAT, NAME-SPECIFIC)
# ==================================================

LOOP_TEMPLATES = {
    "cold_case": "So what really happened to {name}?",
    "murder": "Who killed {name}?",
    "suspicious_death": "So what really happened to {name}?",
    "suspicious_suicide": "Did {name} really take their own life?",
    "missing_found": "What happened to {name} before they were found?",
    "suspicious_accident": "Was {name}'s death really an accident?",
    "mystery": "So what really happened to {name}?",
}

def get_final_loop(case_type, name):
    """Get appropriate final loop question"""
    template = LOOP_TEMPLATES.get(case_type, LOOP_TEMPLATES["mystery"])
    return template.format(name=name)

# ==================================================
# WEIGHTED SCRIPT GENERATION (7-LINE STRUCTURE)
# ==================================================

def generate_weighted_script(client: Groq, case, case_type):
    """
    Generate 7-line script with weighted, investigative tone
    
    STRUCTURE:
    1. HOOK - already generated (statement)
    2. FACTS - name, place, time (5-6 sec / 15-18 words)
    3. CONTEXT - who they were (5-6 sec / 15-18 words)
    4. CONTRADICTION - the weight, the detail (7-8 sec / 21-24 words)
    5. OFFICIAL STORY - what authorities say (7-8 sec / 21-24 words)
    6. CTA - already generated (4-5 sec)
    7. LOOP - already generated (question)
    """
    
    cta_text = get_cta(case_type, case['full_name'])
    
    prompt = f"""You are writing a TRUE CRIME INVESTIGATION SCRIPT. This is NOT storytelling. This is WEIGHTED, HEAVY, FACTUAL reporting.

CRITICAL TONE REQUIREMENTS:
- Write like a forensic investigator presenting evidence
- Every word carries weight
- No dramatic flourishes or emotional language
- State facts that make the audience lean in
- Use SHORT, IMPACTFUL sentences
- Create weight through WHAT you say, not HOW you say it

CASE TYPE: {case_type.replace('_', ' ').title()}

Generate EXACTLY 5 LINES (lines 2-6 of the full script):

LINE 2 - FACTS (15-18 words, 5-6 seconds):
State: Full name, exact location, specific date, exact time.
Format: "[Full Name]. [Location]. [Date]. [Time]."
Example: "Rebecca Zahau. Coronado, California. July 13th, 2011. 6:48 AM."
Make it hit like case file entries.

LINE 3 - CONTEXT (15-18 words, 5-6 seconds):
Who they were. Their role. Their connection. Make it matter.
Example: "The girlfriend of a pharmaceutical executive. Found hanging in his mansion. Just days after his son's fatal accident."
NO generic descriptions. Specific details that add weight.

LINE 4 - CONTRADICTION (21-24 words, 7-8 seconds):
The ONE detail that doesn't fit. The weight of the case. What makes this suspicious.
State it like evidence. Make it impossible to ignore.
Example: "Her hands were bound behind her back. Her feet were bound. Her mouth was not. The sheriff called it suicide."
This line should make the viewer's stomach drop.

LINE 5 - OFFICIAL STORY (21-24 words, 7-8 seconds):
What authorities concluded. What they ruled. What they're investigating.
State it factually, let the contradiction speak.
Example: "The San Diego County Sheriff ruled it suicide. No charges filed. The family hired independent forensics. The contradictions multiplied."

LINE 6 - CTA (MUST BE EXACT):
"{cta_text}"

CASE DATA:
Name: {case['full_name']}
Location: {case['location']}
Date: {case['date']}
Time: {case['time']}
Summary: {case['summary']}
Key Detail: {case['key_detail']}
Official Story: {case['official_story']}

CRITICAL RULES:
- NO questions in lines 2-6 (questions ONLY in final loop)
- NO storytelling language ("little did they know", "what they found was shocking")
- NO emotional manipulations
- Use PERIODS for weight, not ellipses
- Each fact should feel like a case file entry
- Make contradictions UNDENIABLE through facts alone
- Line 6 MUST be EXACTLY the CTA provided above

Write ONLY the 5 lines (2-6), nothing else. No labels, no numbering:
"""
    
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_completion_tokens=500,
    )
    
    lines = [
        l.strip()
        for l in res.choices[0].message.content.split("\n")
        if l.strip() 
        and not l.strip().startswith("#") 
        and not l.strip().startswith("LINE")
        and not l.strip().startswith("Line")
        and not l.strip().lower().startswith("here")
    ]
    
    # Filter out any explanatory text
    lines = [l for l in lines if len(l) > 20 and not l.startswith("(")]
    
    if len(lines) != 5:
        raise RuntimeError(f"❌ Script body must be exactly 5 lines, got {len(lines)}")
    
    # Validate no questions in body
    for i, line in enumerate(lines, 2):
        if "?" in line:
            raise RuntimeError(f"❌ Questions not allowed in line {i}: {line}")
    
    # Validate word counts for timing
    word_counts = [len(line.split()) for line in lines[:4]]  # Exclude CTA
    
    if not (12 <= word_counts[0] <= 20):  # FACTS
        print(f"⚠️  Warning: FACTS line word count {word_counts[0]} (target: 15-18)")
    
    if not (12 <= word_counts[1] <= 20):  # CONTEXT
        print(f"⚠️  Warning: CONTEXT line word count {word_counts[1]} (target: 15-18)")
    
    if not (18 <= word_counts[2] <= 28):  # CONTRADICTION
        print(f"⚠️  Warning: CONTRADICTION line word count {word_counts[2]} (target: 21-24)")
    
    if not (18 <= word_counts[3] <= 28):  # OFFICIAL STORY
        print(f"⚠️  Warning: OFFICIAL STORY line word count {word_counts[3]} (target: 21-24)")
    
    return lines

# ==================================================
# VALIDATION
# ==================================================

def validate_script(lines, case):
    """Validate script quality and timing"""
    
    if len(lines) != 7:
        raise RuntimeError(f"❌ Script must be exactly 7 lines, got {len(lines)}")
    
    # Estimate timing (assuming 3 words per second)
    total_words = sum(len(line.split()) for line in lines)
    estimated_seconds = total_words / 3
    
    if estimated_seconds < 35:
        raise RuntimeError(f"❌ Script too short: ~{estimated_seconds:.1f}s (need 35-45s)")
    
    if estimated_seconds > 45:
        raise RuntimeError(f"❌ Script too long: ~{estimated_seconds:.1f}s (need 35-45s)")
    
    # Check name appears
    name_parts = case['full_name'].split()
    name_found = any(part in " ".join(lines) for part in name_parts if len(part) > 3)
    
    if not name_found:
        raise RuntimeError(f"❌ Name '{case['full_name']}' not found in script")
    
    # Check final line is question
    if not lines[-1].endswith("?"):
        raise RuntimeError(f"❌ Final loop must be a question: '{lines[-1]}'")
    
    # Check only final line has question
    for i, line in enumerate(lines[:-1], 1):
        if "?" in line:
            raise RuntimeError(f"❌ Questions only allowed in final loop (line {i}): '{line}'")
    
    # Check for storytelling language
    bad_phrases = [
        "little did they know",
        "what they found was",
        "shocking",
        "chilling",
        "horrifying",
        "terrifying",
        "unbelievable",
        "unimaginable",
    ]
    
    script_text = " ".join(lines).lower()
    for phrase in bad_phrases:
        if phrase in script_text:
            print(f"⚠️  Warning: Storytelling language detected: '{phrase}'")
    
    print(f"✅ Script validation passed (~{estimated_seconds:.1f} seconds)")

# ==================================================
# MAIN
# ==================================================

def main():
    print("="*60)
    print("🎬 WEIGHTED SCRIPT GENERATOR - 35-45 SECOND FORMAT")
    print("="*60)
    
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
    
    # 1. HOOK (statement)
    hook = select_hook(CASE, case_type)
    print(f"🎣 Hook: '{hook}'")
    
    # 2-6. Generate weighted body
    body = generate_weighted_script(client, CASE, case_type)
    print(f"📝 Body generated: {len(body)} lines")
    
    # 7. LOOP (question)
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
    print("✅ WEIGHTED SCRIPT GENERATED")
    print("="*60)
    print(f"📊 Structure: HOOK → FACTS → CONTEXT → CONTRADICTION → OFFICIAL → CTA → LOOP")
    print(f"👤 Case: {CASE['full_name']}")
    print(f"⏱️  Timing: 35-45 seconds")
    print(f"🎯 Tone: Investigative, weighted, factual")
    print("="*60)
    
    # Display script with timing
    print("\n📋 GENERATED SCRIPT:")
    print("-"*60)
    labels = ["HOOK", "FACTS", "CONTEXT", "CONTRADICTION", "OFFICIAL STORY", "CTA", "LOOP"]
    
    for i, (line, label) in enumerate(zip(full_script, labels), 1):
        word_count = len(line.split())
        est_time = word_count / 3
        print(f"{i}. [{label}] ({word_count} words / ~{est_time:.1f}s)")
        print(f"   {line}")
        print()
    
    total_words = sum(len(line.split()) for line in full_script)
    total_time = total_words / 3
    print("-"*60)
    print(f"TOTAL: {total_words} words / ~{total_time:.1f} seconds")
    print("-"*60)

if __name__ == "__main__":
    main()
