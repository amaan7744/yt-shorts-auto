import random
from typing import Dict


# ---------------------------------
# LOOP ENDING TEMPLATES
# ---------------------------------

LOOP_ENDINGS = [
    "But the final detail was never explained.",
    "And this is where the story gets confusing.",
    "What happened next doesn’t add up.",
    "But that wasn’t the strangest part.",
    "And this raises one disturbing question."
]


def apply_loop(script: str) -> Dict:
    """
    Injects a loop-inducing ending into the script.
    Returns modified script + loop metadata.
    """

    lines = [l.strip() for l in script.split("\n") if l.strip()]
    if not lines:
        return {"script": script, "loop_type": "none"}

    ending = random.choice(LOOP_ENDINGS)

    # Avoid duplicate endings
    if ending.lower() in script.lower():
        ending = LOOP_ENDINGS[0]

    # Replace last line with loop trigger
    original_last = lines[-1]
    lines[-1] = ending

    modified_script = "\n".join(lines)

    return {
        "script": modified_script,
        "loop_type": "unfinished_reveal",
        "replaced_line": original_last
    }
