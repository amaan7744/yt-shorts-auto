#!/usr/bin/env python3
import random

OUT_SCRIPT = "script.txt"

# Hybrid Shorts scripts:
# Unease-first (for reach) + light human context (for subs)
SCRIPTS = [
    [
        # HOOK — abnormal, no human, no date
        "A car was running in a driveway with nobody inside.",

        # STAKES — immediate danger / irreversibility
        "That leaves no time for a normal explanation.",

        # ODD DETAIL — early, unsettling
        "A child’s backpack sat untouched on the passenger seat.",

        # CONTEXT — human + date ONCE, not leading
        "Police documented the scene in early October.",

        # HUMAN CONNECTION — no questions, no preaching
        "Someone left in a moment that gave no warning.",

        # CONTRADICTION — unresolved unease
        "Nothing at the scene explains how the engine stayed running."
    ],
    [
        "A house security camera recorded a door opening at night.",
        "The footage showed no one entering the frame.",
        "The lock re-engaged seconds later on its own.",
        "Police logged the incident during a routine check.",
        "Whoever was involved had no chance to react.",
        "The system data contradicts what the camera shows."
    ],
    [
        "A phone stopped moving while its owner was still outside.",
        "That kind of stop usually happens suddenly.",
        "The screen remained unlocked for several minutes.",
        "Investigators noted the timeline in an October report.",
        "Events moved faster than anyone could respond.",
        "The signal ended without any clear cause."
    ]
]

def main():
    script = random.choice(SCRIPTS)

    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        for line in script:
            f.write(line.strip() + "\n")

    print("✅ Expert-level Shorts script written")

if __name__ == "__main__":
    main()
