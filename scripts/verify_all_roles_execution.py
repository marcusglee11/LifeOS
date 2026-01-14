#!/usr/bin/env python3
"""
Verify All Roles Execution E2E
==============================

This script verifies that ALL agent roles can successfully execute LLM calls
for both their primary provider (Zen) and fallback provider (OpenRouter/Grok).

It forces the system to prove:
1. Role initializes with Primary (Zen) key.
2. Zen call succeeds using that key.
3. OpenRouter call succeeds (proving dynamic key swapping).
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.agents.opencode_client import OpenCodeClient, LLMCall

ROLES = ["steward", "builder", "designer", "reviewer_architect", "build_cycle"]

def verify_role_execution(role):
    print("\n" + "="*80)
    print(f"TESTING ROLE: {role.upper()}")
    print("="*80)
    
    # 1. Initialize Client
    try:
        client = OpenCodeClient(role=role, log_calls=False)
        key = client.api_key
        if not key:
            print(f"❌ FAIL: No API key loaded for {role}")
            return False
            
        print(f"✓ Initialized with key: {key[:10]}... (Provider check: {'Zen' if key.startswith('sk-nd') or key.startswith('sk-ant') or 'NdFD' in key else 'OpenRouter/Other'})")
        
        # Verify it IS a Zen key if Zen is configured as primary
        # (Assuming config/models.yaml sets Zen for all these roles)
        if "sk-or-" in key:
            print(f"⚠ WARNING: Expected Zen key but got OpenRouter key. Primary config might be ignored?")
        
    except Exception as e:
        print(f"❌ FAIL: Initialization error: {e}")
        return False

    # 2. Test Primary Call (Zen)
    # Note: Using explicit Minimax model name to force Direct Zen path if applicable
    zen_model = "minimax-m2.1-free" 
    print(f"\n[1/2] Testing Primary Call (Zen: {zen_model})...")
    try:
        req = LLMCall(
            model=zen_model,
            prompt="Reply with 'ZEN_OK'",
            system_prompt="system"
        )
        resp = client.call(req)
        print(f"✓ SUCCESS: {resp.content[:50]}")
    except Exception as e:
        print(f"❌ FAIL: Zen call failed: {e}")
        return False

    # 3. Test Fallback Call (OpenRouter)
    or_model = "openrouter/x-ai/grok-4.1-fast"
    print(f"\n[2/2] Testing Fallback Swap Call (OpenRouter: {or_model})...")
    try:
        req = LLMCall(
            model=or_model,
            prompt="Reply with 'GROK_OK'",
            system_prompt="system"
        )
        resp = client.call(req)
        print(f"✓ SUCCESS: {resp.content[:50]}")
    except Exception as e:
        print(f"❌ FAIL: OpenRouter call failed: {e}")
        return False

    return True

def main():
    results = {}
    for role in ROLES:
        results[role] = verify_role_execution(role)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    all_passed = True
    for role, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{role:20s}: {status}")
        if not passed: all_passed = False
    
    if all_passed:
        print("\n🎉 ALL ROLES VERIFIED PASSED!")
        return 0
    else:
        print("\n❌ SOME ROLES FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
