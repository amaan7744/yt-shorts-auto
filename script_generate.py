#!/usr/bin/env python
"""
Generate a calm, neutral, documentary-style 40s true-crime script
using DeepSeek R1T2 Chimera via OpenRouter.

Outputs:
  - script.txt        (plain narration for TTS)
  - script_meta.json  (title, visual keywords, pexels keywords, wiki_title)
  - updates used_topics.txt to avoid repeats
"""

import os
import sys
import json
import time
import string
import pathlib
import requests

USED_TOPICS_PATH = pathlib.Path("used_topics.txt")

# Hard-coded OpenRouter endpoint for chat completions
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_used_titles():
    if not USED_TOPICS_PATH.exists():
        return []
    return [
        line.strip()
        for line in USED_TOPICS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def save_used_title(title: str):
    title = title.strip()
    if not title:
        return
    USED_TOPICS_PATH.parent.mkdir(exist_ok=True, parents=True)
    with USED_TOPICS_PATH.open("a", encoding="utf-8") as f:
        f.write(title + "\n")


def get_deepseek_response(prompt: str, api_key: str, model: str) -> str:
    """
    Call DeepSeek via OpenRouter using OpenAI-style /chat/completions API.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional/OpenRouter-friendly headers:
        "HTTP-Referer": "https://github.com",
        "X-Title": "yt-shorts-auto-deepseek",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6,
        "max_tokens": 900,
    }

    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def clean_script_text(s: str) -> str:
    """
    Remove weird characters, normalize spacing and empty lines.
    """
    allowed = set(string.ascii_letters + string.digits + " ,.'\"?!-:\n")
    s = s.replace("\r", "")
    s = "".join(ch for ch in s if ch in allowed)
    s = s.replace("  ", " ")
    lines = [ln.strip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def count_words(s: str) -> int:
    return len(s.replace("\n", " ").split())


def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    model = os.environ.get("DEEPSEEK_MODEL", "tngtech/deepseek-r1t2-chimera:free")

    if not api_key:
        print("[ERROR] DEEPSEEK_API_KEY missing.", file=sys.stderr)
        sys.exit(1)

    category = os.environ.get("CATEGORY", "mystery")

    used_titles = load_used_titles()
    avoid_clause = "; ".join(used_titles[-80:]) if used_titles else ""

    prompt = f"""
You are writing calm, neutral, documentary-style true-crime scripts for 40-second YouTube Shorts.

Return ONLY valid JSON. No extra text. Use this exact JSON structure:

{{
  "title": "...",
  "script": "...",
  "visual_keywords": ["...", "..."],
  "pexels_keywords": ["...", "..."],
  "wiki_title": "..."
}}

Rules for the STORY:

1) CASE TYPE
- Choose ONE real, documented case related to hidden mysteries or hidden history.
- It must be a verifiable case (murder, disappearance, strange event, historical unresolved crime).
- Prefer cases with a Wikipedia article that likely has at least one real public domain or very old historical image.

2) TONE & STYLE
- Tone: calm, neutral, investigative, like a professional true-crime documentary narrator.
- No sensational language, no horror phrasing, no emotional exaggeration.
- Do NOT use words like: "terrifying, horrifying, chilling, nightmare, insane, shocking".
- Keep language simple, clear, grounded in reality.

3) LENGTH & STRUCTURE
- Target duration: about 40 seconds of speech (≈ 115–130 words total), but this is flexible.
- First line = HOOK:
  - 11 words or fewer.
  - Quiet and direct, not clickbait.
  - Reference a simple everyday moment (night walk, drive, routine job, quiet street, etc.).
- After the hook, continue with a factual-style summary of the case.
- Present key facts in order: who, where, when, what happened, which realistic clues exist.
- Focus on minimal, realistic clues: tire marks, phone records, bank activity, surveillance gaps, missing witness, last seen location.
- Do NOT describe gore or graphic detail.
- The final 1–2 lines should highlight the unresolved part with ONE clear question or single unresolved detail.
- Maximum 2 lines in the entire script should end with "?".

4) SCRIPT FORMAT
- Use short lines separated by "\\n".
- Each line must be 16 words or fewer.
- No emojis. No all caps. No repeated punctuation like "!!!" or "???".
- Do NOT reference "this video", "this channel", "Shorts", "YouTube", or "subscribe".
- Do NOT mention Wikipedia, sources, reports, journalists, or "according to".
- Do NOT invent supernatural explanations. Keep it grounded and realistic.

5) SAFETY & CONTENT LIMITS
- No minors as victims.
- No sexual crimes or explicit abuse.
- No graphic violence.
- PG-13 level only.

6) METADATA FIELDS
- "title": short documentary-style title (max 60 characters), no clickbait, no ALL CAPS.
- "visual_keywords": 3–6 phrases describing realistic visuals to match the story, e.g.:
  "empty street at night", "wet asphalt with distant police lights",
  "small town main road", "old case files on a desk".
- "pexels_keywords": choose 4–8 search keywords for Pexels photos, combining BOTH sets:

Crime realism:
  "empty street at night documentary",
  "wet asphalt police lights",
  "person walking night silhouette",
  "dark alley natural light",
  "rain night real street",
  "city night wide shot",
  "old newspaper crime archive",
  "evidence table documentary"

Mystery realism:
  "quiet night walkway",
  "single street lamp night",
  "abandoned road documentary",
  "footsteps at night real",
  "city night observation",
  "old building exterior night",
  "archive research desk",
  "vintage case notes"

Pick only keywords that fit THIS specific case.

- "wiki_title": the exact title of the most relevant English Wikipedia article for this case.

7) TOPIC REUSE
- You MUST NOT repeat any previously used titles or case topics.
- Avoid these titles/topics if possible: {avoid_clause}

8) OUTPUT FORMAT
- Return ONLY one JSON object, nothing else.
- Escape internal quotes properly so JSON parses without error.
"""

    data = None

    for attempt in range(1, 3 + 1):
        print(f"[script_generate] DeepSeek attempt {attempt}/3", flush=True)
        try:
            content = get_deepseek_response(prompt, api_key, model)
        except Exception as e:
            print(f"[ERROR] DeepSeek request error: {e}", file=sys.stderr)
            time.sleep(3)
            continue

        content = content.strip()
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            print("[ERROR] No JSON object found in response, retrying...", file=sys.stderr)
            time.sleep(3)
            continue

        candidate = content[start:end + 1]

        try:
            data = json.loads(candidate)
        except Exception as e:
            print(f"[ERROR] JSON parse error: {e}", file=sys.stderr)
            time.sleep(3)
            data = None
            continue

        title = (data.get("title") or "").strip()
        script = (data.get("script") or "").strip()
        vk = data.get("visual_keywords")
        pk = data.get("pexels_keywords")
        wiki_title = (data.get("wiki_title") or "").strip()

        if not title or not script or not isinstance(vk, list) or not vk or not isinstance(pk, list) or not pk:
            print("[ERROR] Missing required fields, retrying...", file=sys.stderr)
            data = None
            time.sleep(3)
            continue

        if title in used_titles:
            print("[WARN] Title already used, retrying...", file=sys.stderr)
            data = None
            time.sleep(3)
            continue

        # Clean+analyze script, but do NOT reject on word count
        script = clean_script_text(script)
        wc = count_words(script)
        target_min, target_max = 115, 130
        if wc < 90 or wc > 150:
            print(f"[WARN] Word count {wc} is far from target ({target_min}-{target_max}), accepting anyway.", file=sys.stderr)
        else:
            print(f"[INFO] Word count {wc} within reasonable range.", file=sys.stderr)

        lines = [ln.strip() for ln in script.split("\n") if ln.strip()]
        if not lines:
            print("[ERROR] Script lines empty after cleaning, retrying...", file=sys.stderr)
            data = None
            time.sleep(3)
            continue

        first = lines[0]
        if len(first.split()) > 11:
            print("[WARN] Hook too long (>11 words), retrying...", file=sys.stderr)
            data = None
            time.sleep(3)
            continue

        q_lines = sum(1 for ln in lines if ln.endswith("?"))
        if q_lines > 2:
            print("[WARN] Too many question lines, retrying...", file=sys.stderr)
            data = None
            time.sleep(3)
            continue

        if not wiki_title or len(wiki_title.split()) < 2:
            print("[WARN] wiki_title seems too short, retrying...", file=sys.stderr)
            data = None
            time.sleep(3)
            continue

        data["script"] = script
        break

    if data is None:
        print("[FATAL] DeepSeek failed after 3 attempts.", file=sys.stderr)
        sys.exit(1)

    script_text = data["script"]
    pathlib.Path("script.txt").write_text(script_text, encoding="utf-8")
    pathlib.Path("script_meta.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    title = data["title"].strip()
    print(f"[script_generate] Final title: {title}")
    print(f"[script_generate] Word count: {count_words(script_text)}")

    save_used_title(title)


if __name__ == "__main__":
    main()
