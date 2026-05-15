#!/usr/bin/env python3
"""Generate short explanations and translations for grammar entries using DeepSeek API."""

import json
import os
import requests
import time
from pathlib import Path

# Configuration
GRAMMAR_FILE = Path(__file__).parent / "grammar_entries.json"
API_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

def get_api_key():
    """Get API key from environment variable."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "sk-...":
        print("ERROR: DEEPSEEK_API_KEY environment variable not set.")
        print("Set it first with: $env:DEEPSEEK_API_KEY = 'sk-...'")
        return None
    return api_key.strip()

def load_grammar_entries():
    """Load grammar entries from JSON."""
    with open(GRAMMAR_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_grammar_entries(entries):
    """Save grammar entries to JSON."""
    with open(GRAMMAR_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

def generate_explanation_and_translation(grammar_point, sentence, api_key):
    """Call DeepSeek API to generate explanation and translation."""
    if not api_key:
        return None, None
    
    prompt = f"""For the Japanese grammar point "{grammar_point}":
1. Provide a very brief explanation (1 sentence, max 30 words) of what this grammar means.
2. Provide the English translation of this Japanese sentence: "{sentence}"

Respond in this exact JSON format only:
{{"explanation": "brief explanation", "translation": "english translation"}}"""

    try:
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a Japanese language teacher. Respond with valid JSON only. No markdown, no code blocks, no extra text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5,
            "max_tokens": 200
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=15)
        
        if not response.ok:
            error_text = response.text[:300]
            print(f"\n  API {response.status_code}: {error_text}")
            return None, None
        
        data = response.json()
        if "choices" not in data or not data["choices"]:
            print(f"\n  Invalid response: no choices")
            return None, None
        
        content = data["choices"][0].get("message", {}).get("content", "").strip()
        
        if not content:
            print(f"\n  Empty content")
            return None, None
        
        # Parse JSON response
        try:
            result = json.loads(content)
            explanation = result.get("explanation", "").strip()
            translation = result.get("translation", "").strip()
            if explanation and translation:
                return explanation, translation
        except json.JSONDecodeError:
            print(f"\n  Failed to parse: {content[:80]}")
        
        return None, None
            
    except Exception as e:
        print(f"\n  Exception: {e}")
        return None, None

def main():
    print("Loading grammar entries...")
    entries = load_grammar_entries()
    print(f"Loaded {len(entries)} entries\n")
    
    # Get API key
    api_key = get_api_key()
    if not api_key:
        return
    
    print(f"API Key: {api_key[:10]}...{api_key[-10:]}\n")
    
    # Check if already has explanations
    has_all = all("short_explanation" in e and "translation" in e for e in entries)
    if has_all:
        print("✓ All entries already have explanations and translations!")
        return
    
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    
    for i, entry in enumerate(entries, 1):
        entry_id = entry.get("id", i)
        grammar = entry.get("grammar_point", "")[:50]
        sentence = entry.get("sentence", "")
        
        # Skip if already has both fields
        if "short_explanation" in entry and "translation" in entry:
            skipped_count += 1
            if i % 10 == 0:
                print(f"[{i:3d}/{len(entries)}] Skipped", end="\r", flush=True)
            continue
        
        print(f"[{i:3d}/{len(entries)}] {grammar}...", end=" → ", flush=True)
        
        explanation, translation = generate_explanation_and_translation(grammar, sentence, api_key)
        
        if explanation and translation:
            entry["short_explanation"] = explanation
            entry["translation"] = translation
            print("✓")
            updated_count += 1
        else:
            print("✗")
            failed_count += 1
        
        # Rate limiting
        time.sleep(0.3)
    
    print(f"\n{'='*60}")
    print(f"Updated: {updated_count}, Skipped: {skipped_count}, Failed: {failed_count}")
    print(f"Total: {len(entries)}")
    
    if updated_count > 0:
        print("\nSaving updated grammar entries...")
        save_grammar_entries(entries)
        print("✓ Saved to grammar_entries.json")
    else:
        print("No changes made.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
