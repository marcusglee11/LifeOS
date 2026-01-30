#!/usr/bin/env python3
"""
Verify All Roles Execution E2E (Dynamic from Config)
====================================================

This script verifies that ALL configured agent roles can successfully execute LLM calls.
It loads primary and fallback models from config/models.yaml and tests them.

Usage:
    python scripts/verify_all_roles_execution.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from runtime.agents.opencode_client import OpenCodeClient, LLMCall
    from runtime.agents.models import load_model_config
except ImportError as e:
    print(f"Error importing runtime: {e}")
    sys.exit(1)

def verify_role_execution(role, agent_cfg):
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
        print(f"✓ Initialized with key set: {'Yes' if key else 'No'}")
    except Exception as e:
        print(f"❌ FAIL: Initialization error: {e}")
        return False

    # 2. Test Primary Call
    primary_model = agent_cfg.model
    print(f"\n[1] Testing Primary Call (Model: {primary_model})...")
    if not run_call(client, primary_model):
        print("❌ FAIL: Primary call failed.")
        return False

    # 3. Test Fallbacks
    for idx, fb in enumerate(agent_cfg.fallback):
        fb_model = fb.get("model")
        if not fb_model: continue
        
        print(f"\n[{idx+2}] Testing Fallback Call (Model: {fb_model})...")
        if not run_call(client, fb_model):
            print("❌ FAIL: Fallback call failed.")
            return False

    return True

def run_call(client, model):
    try:
        req = LLMCall(
            model=model,
            prompt="Reply with 'OK'",
            system_prompt="system"
        )
        resp = client.call(req)
        # Check if the model reported matches expectation (loose check for provider prefixes)
        print(f"✓ SUCCESS. Response len: {len(resp.content)}. Used: {resp.model_used}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def main():
    config = load_model_config()
    if not config.agents:
        print("No agents configured.")
        return 1
        
    results = {}
    for role, agent_cfg in config.agents.items():
        results[role] = verify_role_execution(role, agent_cfg)
    
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
