import random
import re
from typing import Dict, List


# ----------------------------
# CONFIG
# ----------------------------

MAX_HASHTAGS = 5
MAX_TAGS = 12

BASE_HASHTAGS = [
    "truecrime",
    "unsolved",
    "crimecase",
    "mystery",
    "realcrime",
    "shorts"
]

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on",
    "this", "that", "is", "was", "were", "to"
}


# ----------------------------
# UTILITIES
# ----------------------------

def clean_words(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 3]


# ----------------------------
# TITLE BUILDER
# ----------------------------

def build_title(hook_line: str) -> str:
    """
    Builds a Shorts-optimized title.
    40–70 chars, curiosity-based.
    """

    hook_line = hook_line.strip()

    # Hard truncate if needed
    if len(hook_line) > 70:
        hook_line = hook_line[:67] + "..."

    # Capitalize first letter only (human feel)
    return hook_line[0].upper() + hook_line[1:]


# ----------------------------
# DESCRIPTION BUILDER
# ----------------------------

def build_description(title: str, context_line: str = "") -> str:
    """
    Minimal, clean description.
    """

    lines = []

    lines.append(title)

    if context_line:
        context_line = context_line.strip()
        if len(context_line) > 120:
            context_line = context_line[:117] + "..."
        lines.append(context_line)

    return "\n".join(lines)


# ----------------------------
# HASHTAG BUILDER
# ----------------------------

def build_hashtags(script: str) -> List[str]:
    """
    Builds 3–5 relevant hashtags.
    """

    words = clean_words(script)

    dynamic = []
    for w in words:
        if w in ("murder", "missing", "police", "death", "case"):
            dynamic.append(w)

    hashtags = list(dict.fromkeys(BASE_HASHTAGS + dynamic))
    hashtags = hashtags[:MAX_HASHTAGS]

    return [f"#{h}" for h in hashtags]


# ----------------------------
# TAG BUILDER
# ----------------------------

def build_tags(script: str) -> List[str]:
    """
    Builds backend tags (low impact but safe).
    """

    words = clean_words(script)

    tags = []
    for w in words:
        if w not in tags:
            tags.append(w)

    tags = tags[:MAX_TAGS]
    return tags


# ----------------------------
# MASTER BUILDER
# ----------------------------

def build_seo(script: str) -> Dict:
    """
    Main entry point.
    Returns title, description, hashtags, tags.
    """

    lines = [l.strip() for l in script.split("\n") if l.strip()]
    hook_line = lines[0]
    context_line = lines[1] if len(lines) > 1 else ""

    title = build_title(hook_line)
    description = build_description(title, context_line)
    hashtags = build_hashtags(script)
    tags = build_tags(script)

    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "tags": tags
    }
