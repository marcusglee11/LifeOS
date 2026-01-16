#!/usr/bin/env python3
"""
Reproduction Script: OpenCodeClient Fallback Failure
====================================================

This script executes an OpenCodeClient call targeting 'x-ai/grok-4.1-fast'.
Since the Steward role is configured with Zen as primary, OpenCodeClient
loads the Zen key into self.api_key.

Hypothesis: exact fallback execution will result in using the Zen key 
for OpenRouter, causing a 401 failure.
"""

import os
import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.agents.opencode_client import OpenCodeClient, LLMCall

def test_fallback_call():
    print("\n" + "="*80)
    print("TEST: Explicit Non-Zen Model Call (Targeting OpenRouter)")
    print("="*80)
    
    # Initialize as steward (Zen primary)
    print("DEBUG: Checking environment...")
    print(f"ZEN_STEWARD_KEY in os.environ: {'ZEN_STEWARD_KEY' in os.environ}")
    print(f"OPENROUTER_STEWARD_KEY in os.environ: {'OPENROUTER_STEWARD_KEY' in os.environ}")
    if 'ZEN_STEWARD_KEY' in os.environ:
        print(f"ZEN_STEWARD_KEY value: {os.environ['ZEN_STEWARD_KEY'][:10]}...")
    if 'OPENROUTER_STEWARD_KEY' in os.environ:
        print(f"OPENROUTER_STEWARD_KEY value: {os.environ['OPENROUTER_STEWARD_KEY'][:10]}...")
    
    # Check .env manually
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "ZEN_STEWARD_KEY" in line:
                    print(f"Found in .env: {line.strip()[:25]}...")

    client = OpenCodeClient(role="steward", log_calls=True)
    
    # Verify what key loaded (obfuscated)
    key_prefix = client.api_key[:10] if client.api_key else "None"
    print(f"DEBUG: Client initialized with key: {key_prefix}...")
    
    req = LLMCall(
        model="x-ai/grok-4.1-fast",
        prompt="Reply with 'FALLBACK_OK'",
        system_prompt="You are a test assistant."
    )
    
    try:
        print(f"Executing call to {req.model}...")
        resp = client.call(req)
        print(f"SUCCESS: {resp.content}")
        return True
    except Exception as e:
        print(f"FAILURE: {e}")
        return False

if __name__ == "__main__":
    success = test_fallback_call()
    sys.exit(0 if success else 1)
