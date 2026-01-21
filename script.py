#!/usr/bin/env python3
"""
YouTube Shorts Script Generator
Generates optimized 20-second true crime narrations with visual beat mapping.
"""

import os
import sys
import json
import time
import re
from typing import Tuple, List, Dict
from pathlib import Path

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# ==================================================
# CONFIGURATION
# ==================================================

class Config:
    """Centralized configuration for the script generator."""
    ENDPOINT = "https://models.github.ai/inference"
    MODEL = "openai/gpt-4o-mini"
    
    CASE_FILE = "case.json"
    SCRIPT_FILE = "script.txt"
    BEATS_FILE = "beats.json"
    
    # 18-22 seconds at ~155 WPM
    TARGET_WORDS_MIN = 44
    TARGET_WORDS_MAX = 52
    TARGET_DURATION = 20  # seconds
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    TEMPERATURE = 0.3


# ==================================================
# CLIENT INITIALIZATION
# ==================================================

def initialize_client() -> ChatCompletionsClient:
    """Initialize and return the Azure AI client."""
    token = os.getenv("GH_MODELS_TOKEN")
    if not token:
        print("❌ Error: GH_MODELS_TOKEN environment variable is not set.")
        print("   Set it with: export GH_MODELS_TOKEN='your-token-here'")
        sys.exit(1)
    
    return ChatCompletionsClient(
        endpoint=Config.ENDPOINT,
        credential=AzureKeyCredential(token),
    )


# ==================================================
# UTILITIES
# ==================================================

def clean_text(text: str) -> str:
    """Remove extra whitespace and normalize text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def load_case() -> Dict:
    """Load and validate the input case file."""
    case_path = Path(Config.CASE_FILE)
    
    if not case_path.is_file():
        print(f"❌ Error: {Config.CASE_FILE} not found in current directory")
        sys.exit(1)
    
    try:
        with open(case_path, "r", encoding="utf-8") as f:
            case = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: {Config.CASE_FILE} contains invalid JSON")
        print(f"   Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading {Config.CASE_FILE}: {e}")
        sys.exit(1)
    
    # Validate required fields
    required_fields = ["summary", "location"]
    missing_fields = [field for field in required_fields if not case.get(field)]
    
    if missing_fields:
        print(f"❌ Error: {Config.CASE_FILE} missing required fields: {', '.join(missing_fields)}")
        print(f"   Required fields: summary, location")
        sys.exit(1)
    
    return case


def smart_trim(text: str, max_words: int = Config.TARGET_WORDS_MAX) -> str:
    """
    Trim text to word limit, preferring to end at sentence boundaries.
    
    Args:
        text: The text to trim
        max_words: Maximum word count
        
    Returns:
        Trimmed text ending at a sentence if possible
    """
    words = text.split()
    
    if len(words) <= max_words:
        return text
    
    # Get text up to word limit
    trimmed = " ".join(words[:max_words])
    
    # Find the last sentence-ending punctuation
    sentence_ends = ['.', '?', '!']
    last_punct_pos = -1
    
    for punct in sentence_ends:
        pos = trimmed.rfind(punct)
        if pos > last_punct_pos:
            last_punct_pos = pos
    
    # If we found punctuation and it's not too early in the text
    if last_punct_pos > len(trimmed) * 0.6:  # At least 60% of target length
        return trimmed[:last_punct_pos + 1].strip()
    
    # Otherwise, just trim at word boundary
    return trimmed.strip()


# ==================================================
# PROMPT CONSTRUCTION
# ==================================================

def build_script_prompt(case: Dict) -> str:
    """
    Construct the prompt for script generation.
    
    Args:
        case: Dictionary containing case details
        
    Returns:
        Formatted prompt string
    """
    return f"""Write a compelling {Config.TARGET_DURATION}-second YouTube Shorts narration about this unresolved case.

CASE DETAILS:
• Location: {case.get('location')}
• Summary: {case.get('summary')}

OPTIMIZATION REQUIREMENTS:
• Hook: Open with a specific, impossible-sounding fact that creates immediate intrigue
• Atmosphere: Maintain calm authority while building tension
• Mute-Ready: Every sentence must work as standalone on-screen text
• Pacing: Natural rhythm that flows when read aloud

STRICT CONSTRAINTS:
• Word count: {Config.TARGET_WORDS_MIN}-{Config.TARGET_WORDS_MAX} words (HARD LIMIT)
• Format: Single flowing paragraph, no labels or section markers
• No introduction or conclusion phrases
• End with a thought-provoking line that loops perfectly for repeat viewing

NARRATIVE STRUCTURE:
1. Impossible fact hook (grabs attention instantly)
2. Time/place anchor (grounds the mystery)
3. Contradictory detail (deepens intrigue)
4. Escalating mystery element (raises stakes)
5. Unresolved official record or theory (shows complexity)
6. Subtle preservation call-to-action (engages audience)
7. Circular ending line (enables seamless loop)

OUTPUT FORMAT:
Return ONLY the narration text. No preamble, no explanations, no metadata."""


# ==================================================
# API INTERACTION
# ==================================================

def call_ai_model(client: ChatCompletionsClient, prompt: str) -> str:
    """
    Call the AI model with error handling.
    
    Args:
        client: Initialized ChatCompletionsClient
        prompt: The prompt to send
        
    Returns:
        Generated text response
        
    Raises:
        ValueError: If response is empty
        HttpResponseError: If API call fails
    """
    response = client.complete(
        model=Config.MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an expert YouTube Shorts scriptwriter specializing in high-retention true crime content. You write concise, impactful narratives optimized for mobile viewing and mute-friendly consumption."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        temperature=Config.TEMPERATURE,
        max_tokens=300,  # Safety limit
    )
    
    text = clean_text(response.choices[0].message.content)
    
    if not text:
        raise ValueError("Model returned empty response")
    
    return text


# ==================================================
# BEAT GENERATION
# ==================================================

def derive_visual_beats(script: str) -> List[Dict]:
    """
    Break script into visual beats for video production.
    
    Args:
        script: The complete script text
        
    Returns:
        List of beat dictionaries with scene information
    """
    # Split into sentences while preserving punctuation
    sentences = re.findall(r'[^.!?]+[.!?]+', script)
    
    # Handle edge case where last sentence might not have punctuation
    if sentences:
        combined = ''.join(sentences)
        if len(combined) < len(script):
            remaining = script[len(combined):].strip()
            if remaining:
                sentences.append(remaining)
    else:
        # Fallback if regex fails
        sentences = [s.strip() + '.' for s in script.split('.') if s.strip()]
    
    beats = []
    total = len(sentences)
    
    # Define scene types based on narrative structure
    scene_mapping = {
        0: "HOOK",
        1: "ANCHOR",
        -2: "IMPLICATION",
        -1: "LOOP"
    }
    
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Determine scene type
        if i in scene_mapping:
            scene_type = scene_mapping[i]
        elif i == total - 2:
            scene_type = "IMPLICATION"
        elif i == total - 1:
            scene_type = "LOOP"
        elif i < total // 2:
            scene_type = "ESCALATION_EARLY"
        else:
            scene_type = "ESCALATION_LATE"
        
        beats.append({
            "beat_id": i + 1,
            "scene_type": scene_type,
            "text": sentence,
            "word_count": count_words(sentence),
            "estimated_duration": round(count_words(sentence) / 2.58, 1)  # ~155 WPM
        })
    
    return beats


# ==================================================
# CONTENT GENERATION
# ==================================================

def generate_content(client: ChatCompletionsClient, case: Dict) -> Tuple[str, List[Dict]]:
    """
    Generate script and visual beats with retry logic.
    
    Args:
        client: Initialized AI client
        case: Case data dictionary
        
    Returns:
        Tuple of (script_text, beats_list)
    """
    prompt = build_script_prompt(case)
    
    for attempt in range(1, Config.MAX_RETRIES + 1):
        try:
            print(f"🔄 Generation attempt {attempt}/{Config.MAX_RETRIES}...")
            
            raw_script = call_ai_model(client, prompt)
            word_count = count_words(raw_script)
            
            print(f"   Generated {word_count} words")
            
            # Trim if necessary
            if word_count > Config.TARGET_WORDS_MAX:
                print(f"   ✂️  Trimming to target length...")
                final_script = smart_trim(raw_script)
            else:
                final_script = raw_script
            
            # Generate visual beats
            beats = derive_visual_beats(final_script)
            
            # Validate output
            final_word_count = count_words(final_script)
            if final_word_count < Config.TARGET_WORDS_MIN:
                print(f"   ⚠️  Script too short ({final_word_count} words), retrying...")
                if attempt < Config.MAX_RETRIES:
                    time.sleep(Config.RETRY_DELAY)
                    continue
            
            print(f"   ✅ Generated {final_word_count} words, {len(beats)} beats")
            return final_script, beats
            
        except HttpResponseError as e:
            print(f"   ⚠️  API error: {e}")
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
        
        if attempt < Config.MAX_RETRIES:
            print(f"   ⏳ Waiting {Config.RETRY_DELAY}s before retry...")
            time.sleep(Config.RETRY_DELAY)
    
    print("❌ Failed to generate script after multiple attempts")
    sys.exit(1)


# ==================================================
# FILE OPERATIONS
# ==================================================

def save_outputs(script: str, beats: List[Dict]) -> None:
    """
    Save script and beats to files.
    
    Args:
        script: The generated script text
        beats: List of visual beat dictionaries
    """
    try:
        # Save script
        with open(Config.SCRIPT_FILE, "w", encoding="utf-8") as f:
            f.write(script)
        print(f"✅ Script saved to {Config.SCRIPT_FILE}")
        
        # Save beats with metadata
        output_data = {
            "metadata": {
                "total_beats": len(beats),
                "total_words": count_words(script),
                "estimated_duration": sum(b.get("estimated_duration", 0) for b in beats),
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "beats": beats
        }
        
        with open(Config.BEATS_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Visual beats saved to {Config.BEATS_FILE}")
        
    except Exception as e:
        print(f"❌ Error saving files: {e}")
        sys.exit(1)


# ==================================================
# MAIN EXECUTION
# ==================================================

def main():
    """Main execution function."""
    print("=" * 60)
    print("🎬 YouTube Shorts Script Generator")
    print("=" * 60)
    
    # Initialize
    print("\n📋 Loading case data...")
    case_data = load_case()
    print(f"   Location: {case_data.get('location')}")
    print(f"   Summary: {case_data.get('summary')[:80]}...")
    
    print("\n🤖 Initializing AI client...")
    client = initialize_client()
    
    # Generate content
    print("\n✍️  Generating optimized script...")
    script, beats = generate_content(client, case_data)
    
    # Save outputs
    print("\n💾 Saving outputs...")
    save_outputs(script, beats)
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 GENERATION SUMMARY")
    print("=" * 60)
    print(f"Total words: {count_words(script)}")
    print(f"Visual beats: {len(beats)}")
    print(f"Estimated duration: ~{sum(b.get('estimated_duration', 0) for b in beats):.1f}s")
    print("\n📜 SCRIPT PREVIEW:")
    print("-" * 60)
    print(script)
    print("-" * 60)
    print("\n✨ Generation complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
