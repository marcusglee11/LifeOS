#!/usr/bin/env python3
"""
Comprehensive Multi-Role API Key Loading Test
==============================================

Tests all 4 agent roles (steward, builder, designer, reviewer_architect) to ensure:
1. Primary keys (ZEN_*_KEY) are loaded correctly from .env
2. Fallback keys (OPENROUTER_*_KEY) are loaded correctly
3. Fallback behavior works when primary is unavailable
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.agents.opencode_client import OpenCodeClient

# Test matrix: all roles and their expected keys
ROLES = ["steward", "builder", "designer", "reviewer_architect"]

PRIMARY_KEYS = {
    "steward": "ZEN_STEWARD_KEY",
    "builder": "ZEN_BUILDER_KEY",
    "designer": "ZEN_DESIGNER_KEY",
    "reviewer_architect": "ZEN_REVIEWER_KEY",
}

FALLBACK_KEYS = {
    "steward": "OPENROUTER_STEWARD_KEY",
    "builder": "OPENROUTER_BUILDER_KEY",
    "designer": "OPENROUTER_DESIGNER_KEY",
    "reviewer_architect": "OPENROUTER_REVIEWER_KEY",
}

def create_test_env_file(keys: dict) -> str:
    """Create a temporary .env file with the given keys."""
    import shutil
    temp_dir = tempfile.mkdtemp()
    env_path = os.path.join(temp_dir, ".env")
    
    with open(env_path, "w") as f:
        for key, value in keys.items():
            f.write(f"{key}={value}\n")
    
    # Also copy models.yaml to temp dir so get_agent_config works
    config_src = os.path.join(os.getcwd(), "config", "models.yaml")
    if os.path.exists(config_src):
        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        shutil.copy(config_src, os.path.join(config_dir, "models.yaml"))
    
    return temp_dir

def test_primary_key_loading():
    """Test that all roles load their primary (Zen) keys correctly."""
    print("\n" + "="*80)
    print("TEST 1: Primary Key Loading (Zen)")
    print("="*80)
    
    # Clear environment to prevent cross-contamination
    all_key_vars = list(PRIMARY_KEYS.values()) + list(FALLBACK_KEYS.values()) + ["ZEN_API_KEY", "OPENROUTER_API_KEY"]
    original_env = {k: os.environ.pop(k, None) for k in all_key_vars}
    
    # Create test .env with all primary keys
    test_keys = {k: f"test-zen-key-{role}" for role, k in PRIMARY_KEYS.items()}
    test_dir = create_test_env_file(test_keys)
    
    # Save original dir and switch to test dir
    original_dir = os.getcwd()
    os.chdir(test_dir)
    
    results = {}
    try:
        for role in ROLES:
            client = OpenCodeClient(role=role)
            loaded_key = client._load_api_key_for_role(role, provider="zen")
            expected_key = test_keys[PRIMARY_KEYS[role]]
            
            status = "✓ PASS" if loaded_key == expected_key else "✗ FAIL"
            results[role] = (status, loaded_key, expected_key)
            
            print(f"{status} | Role: {role:20s} | Expected: {expected_key:30s} | Got: {loaded_key}")
    finally:
        os.chdir(original_dir)
        # Restore environment
        for k, v in original_env.items():
            if v is not None:
                os.environ[k] = v
    
    return all(status == "✓ PASS" for status, _, _ in results.values())

def test_fallback_key_loading():
    """Test that all roles load their fallback (OpenRouter) keys correctly."""
    print("\n" + "="*80)
    print("TEST 2: Fallback Key Loading (OpenRouter)")
    print("="*80)
    
    # Clear environment to prevent cross-contamination
    all_key_vars = list(PRIMARY_KEYS.values()) + list(FALLBACK_KEYS.values()) + ["ZEN_API_KEY", "OPENROUTER_API_KEY"]
    original_env = {k: os.environ.pop(k, None) for k in all_key_vars}
    
    # Create test .env with all fallback keys
    test_keys = {k: f"test-openrouter-key-{role}" for role, k in FALLBACK_KEYS.items()}
    test_dir = create_test_env_file(test_keys)
    
    # Save original dir and switch to test dir
    original_dir = os.getcwd()
    os.chdir(test_dir)
    
    results = {}
    try:
        for role in ROLES:
            client = OpenCodeClient(role=role)
            loaded_key = client._load_api_key_for_role(role, provider="openrouter")
            expected_key = test_keys[FALLBACK_KEYS[role]]
            
            status = "✓ PASS" if loaded_key == expected_key else "✗ FAIL"
            results[role] = (status, loaded_key, expected_key)
            
            print(f"{status} | Role: {role:20s} | Expected: {expected_key:30s} | Got: {loaded_key}")
    finally:
        os.chdir(original_dir)
        # Restore environment
        for k, v in original_env.items():
            if v is not None:
                os.environ[k] = v
    
    return all(status == "✓ PASS" for status, _, _ in results.values())

def test_fallback_behavior():
    """Test that OpenRouter keys are loaded when Zen keys are unavailable."""
    print("\n" + "="*80)
    print("TEST 3: Fallback Behavior (Zen unavailable, OpenRouter available)")
    print("="*80)
    
    # Clear environment to prevent cross-contamination
    all_key_vars = list(PRIMARY_KEYS.values()) + list(FALLBACK_KEYS.values()) + ["ZEN_API_KEY", "OPENROUTER_API_KEY"]
    original_env = {k: os.environ.pop(k, None) for k in all_key_vars}
    
    # Create test .env with ONLY OpenRouter keys (no Zen keys)
    test_keys = {k: f"test-openrouter-fallback-{role}" for role, k in FALLBACK_KEYS.items()}
    test_dir = create_test_env_file(test_keys)
    
    # Save original dir and switch to test dir
    original_dir = os.getcwd()
    os.chdir(test_dir)
    
    results = {}
    try:
        for role in ROLES:
            client = OpenCodeClient(role=role)
            # Request Zen provider, but it should fallback to OpenRouter
            loaded_key = client._load_api_key_for_role(role, provider="zen")
            expected_key = None  # Should be None since we're asking for Zen specifically
            
            # Now try loading without provider filter (should get OpenRouter)
            loaded_key_any = client._load_api_key_for_role(role, provider=None)
            expected_key_any = test_keys[FALLBACK_KEYS[role]]
            
            status = "✓ PASS" if loaded_key_any == expected_key_any else "✗ FAIL"
            results[role] = (status, loaded_key_any, expected_key_any)
            
            print(f"{status} | Role: {role:20s} | Expected: {expected_key_any:30s} | Got: {loaded_key_any}")
    finally:
        os.chdir(original_dir)
        # Restore environment
        for k, v in original_env.items():
            if v is not None:
                os.environ[k] = v
    
    return all(status == "✓ PASS" for status, _, _ in results.values())

def test_real_env_keys():
    """Test loading from the actual .env file in the project root."""
    print("\n" + "="*80)
    print("TEST 4: Real .env File Key Loading")
    print("="*80)
    
    # We're already in the project directory
    if not os.path.exists(".env"):
        print("⚠ WARNING: No .env file found in project root. Skipping real env test.")
        return True
    
    results = {}
    for role in ROLES:
        client = OpenCodeClient(role=role)
        
        # Try primary (Zen)
        zen_key = client._load_api_key_for_role(role, provider="zen")
        zen_status = "✓ FOUND" if zen_key else "✗ MISSING"
        
        # Try fallback (OpenRouter)
        or_key = client._load_api_key_for_role(role, provider="openrouter")
        or_status = "✓ FOUND" if or_key else "✗ MISSING"
        
        print(f"Role: {role:20s} | Zen: {zen_status:10s} | OpenRouter: {or_status:10s}")
        
        results[role] = (zen_key is not None or or_key is not None)
    
    # Pass if at least one key type is available for each role
    return all(results.values())

def main():
    print("\n" + "="*80)
    print("COMPREHENSIVE MULTI-ROLE API KEY LOADING TEST")
    print("="*80)
    
    test_results = {
        "Primary Key Loading": test_primary_key_loading(),
        "Fallback Key Loading": test_fallback_key_loading(),
        "Fallback Behavior": test_fallback_behavior(),
        "Real .env Loading": test_real_env_keys(),
    }
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for test_name, passed in test_results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status} | {test_name}")
    
    all_passed = all(test_results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
