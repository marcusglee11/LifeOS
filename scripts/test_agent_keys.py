#!/usr/bin/env python
"""
Test All Per-Agent API Keys

Verifies that each agent's API key works by making a minimal LLM call.
Outputs a table of results.

Usage:
    python scripts/test_agent_keys.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Define test matrix: (role, key_env, endpoint, model, protocol)
TEST_MATRIX = [
    # Zen keys
    ("designer", "ZEN_DESIGNER_KEY", "https://opencode.ai/zen/v1/chat/completions", "glm-4.7-free", "openai"),
    ("reviewer_architect", "ZEN_REVIEWER_KEY", "https://opencode.ai/zen/v1/chat/completions", "glm-4.7-free", "openai"),
    ("builder", "ZEN_BUILDER_KEY", "https://opencode.ai/zen/v1/messages", "minimax-m2.1-free", "anthropic"),
    ("steward", "ZEN_STEWARD_KEY", "https://opencode.ai/zen/v1/messages", "minimax-m2.1-free", "anthropic"),
    ("autonomous_build_cycle", "ZEN_BUILD_CYCLE_KEY", "https://opencode.ai/zen/v1/chat/completions", "glm-4.7-free", "openai"),
    # OpenRouter keys
    ("designer_fallback", "OPENROUTER_DESIGNER_KEY", "https://openrouter.ai/api/v1/chat/completions", "deepseek/deepseek-v3.2-speciale", "openai"),
    ("reviewer_fallback", "OPENROUTER_REVIEWER_KEY", "https://openrouter.ai/api/v1/chat/completions", "deepseek/deepseek-v3.2-speciale", "openai"),
    ("builder_fallback", "OPENROUTER_BUILDER_KEY", "https://openrouter.ai/api/v1/chat/completions", "x-ai/grok-code-fast-1", "openai"),
    ("build_cycle_fallback", "OPENROUTER_BUILD_CYCLE_KEY", "https://openrouter.ai/api/v1/chat/completions", "deepseek/deepseek-v3.2-speciale", "openai"),
    ("steward_fallback", "STEWARD_OPENROUTER_KEY", "https://openrouter.ai/api/v1/chat/completions", "x-ai/grok-code-fast-1", "openai"),
]


def test_anthropic_key(key: str, endpoint: str, model: str) -> tuple[bool, str]:
    """Test an Anthropic-protocol endpoint."""
    headers = {
        "x-api-key": key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'OK' and nothing else."}],
        "max_tokens": 10
    }
    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return True, "OK"
        return False, f"HTTP {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, str(e)[:50]


def test_openai_key(key: str, endpoint: str, model: str) -> tuple[bool, str]:
    """Test an OpenAI-protocol endpoint."""
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'OK' and nothing else."}],
        "max_tokens": 10
    }
    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return True, "OK"
        return False, f"HTTP {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, str(e)[:50]


def main():
    print("\n" + "=" * 80)
    print("LIFEOS PER-AGENT API KEY VERIFICATION")
    print("=" * 80 + "\n")

    results = []
    for role, key_env, endpoint, model, protocol in TEST_MATRIX:
        key = os.environ.get(key_env)
        if not key:
            results.append((role, key_env, "MISSING", "Key not found in environment"))
            continue

        print(f"Testing {role} ({key_env})...", end=" ", flush=True)

        if protocol == "anthropic":
            success, msg = test_anthropic_key(key, endpoint, model)
        else:
            success, msg = test_openai_key(key, endpoint, model)

        status = "PASS" if success else "FAIL"
        results.append((role, key_env, status, msg))
        print(status)

    # Print summary table
    print("\n" + "-" * 80)
    print(f"{'Role':<25} {'Key Env':<30} {'Status':<8} {'Details'}")
    print("-" * 80)
    for role, key_env, status, msg in results:
        print(f"{role:<25} {key_env:<30} {status:<8} {msg}")
    print("-" * 80)

    # Count
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = sum(1 for r in results if r[2] == "FAIL")
    missing = sum(1 for r in results if r[2] == "MISSING")
    print(f"\nSummary: {passed} PASS, {failed} FAIL, {missing} MISSING")
    print()

    return 0 if failed == 0 and missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
