import re
from typing import Dict

STRONG_TRIGGER_WORDS = [
    "dead", "missing", "disappeared", "murder",
    "found", "last", "final", "police", "lied",
    "wrong", "mistake", "secret", "unknown"
]

WEAK_OPENINGS = [
    "this is the story",
    "this case happened",
    "in the year",
    "this crime took place"
]


def score_idea(title: str, script: str) -> Dict:
    """
    Scores an idea BEFORE production.
    Returns kill/pass decision with reasoning.
    """

    score = 100
    reasons = []

    first_lines = script.strip().split("\n")[:3]
    opening = " ".join(first_lines).lower()

    # Weak opening penalty
    for phrase in WEAK_OPENINGS:
        if phrase in opening:
            score -= 30
            reasons.append("weak_opening")

    # Trigger word analysis
    trigger_hits = sum(1 for w in STRONG_TRIGGER_WORDS if w in opening)
    if trigger_hits == 0:
        score -= 25
        reasons.append("no_emotional_trigger")

    # Length feasibility
    word_count = len(script.split())
    if word_count > 140:
        score -= 20
        reasons.append("too_long_for_shorts")

    # Curiosity gap (question or contradiction)
    if "?" not in opening and "but" not in opening:
        score -= 15
        reasons.append("no_curiosity_gap")

    kill = score < 70

    return {
        "score": max(score, 0),
        "kill": kill,
        "reasons": reasons
    }
