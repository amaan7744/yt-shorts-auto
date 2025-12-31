#!/usr/bin/env python3
import os
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

OUT_SCRIPT = "script.txt"

TOKEN = os.getenv("GH_MODELS_TOKEN")
if not TOKEN:
    raise SystemExit("❌ GH_MODELS_TOKEN missing")

client = ChatCompletionsClient(
    endpoint="https://models.github.ai/inference",
    credential=AzureKeyCredential(TOKEN),
)

PROMPT = """
Write a 35–45 second YouTube Shorts true crime script.

Rules:
- Start with DATE + LOCATION in first line
- Concrete details only
- No filler phrases
- End with unresolved tension
- Short punchy sentences
"""

response = client.complete(
    model="openai/gpt-5",
    messages=[
        {"role": "system", "content": "You are a viral true-crime Shorts writer."},
        {"role": "user", "content": PROMPT},
    ],
    temperature=0.6,
    max_tokens=300,
)

text = response.choices[0].message.content.strip()

with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
    f.write(text)

print("✅ Script generated with GPT-5")
