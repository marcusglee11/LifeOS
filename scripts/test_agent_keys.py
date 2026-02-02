#!/usr/bin/env python
"""
Test All Per-Agent API Keys (Dynamic from Config)

Verifies that each agent's API key works by making a minimal LLM call.
Loads configuration from config/models.yaml ensures Single Source of Truth.

Usage:
    python scripts/test_agent_keys.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
    import yaml
    from dotenv import load_dotenv
    from runtime.agents.models import load_model_config
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    sys.exit(1)

# Load .env file
load_dotenv()

def infer_protocol(endpoint: str, model: str) -> str:
    """Infer protocol from endpoint or model name."""
    if "opencode.ai/zen" in endpoint:
        # Zen usually uses Anthropic format for Minimax, but check model
        if "minimax" in model:
            return "anthropic"
        return "openai" # Zen wrapping usage
    if "anthropic.com" in endpoint:
        return "anthropic"
    return "openai" # Default to OpenAI (OpenRouter, etc)

def test_anthropic_key(key: str, endpoint: str, model: str) -> tuple[bool, str]:
    """Test an Anthropic-protocol endpoint."""
    headers = {
        "x-api-key": key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    # Zen/Minimax sanitize logic
    sanitized_model = model.replace("minimax/", "").replace("zen/", "")
    
    payload = {
        "model": sanitized_model,
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
    # OpenRouter sanitize
    sanitized_model = model.replace("openrouter/", "") if "openrouter" in endpoint else model
    
    payload = {
        "model": sanitized_model,
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
    print("LIFEOS PER-AGENT API KEY VERIFICATION (DYNAMIC)")
    print("=" * 80 + "\n")

    # Load config dynamically
    config = load_model_config()
    if not config.agents:
        print("No agents found in config/models.yaml")
        return 1

    results = []
    
    # Iterate over all configured agents
    for role, agent_cfg in config.agents.items():
        # Check Primary
        env_key = agent_cfg.api_key_env
        key = os.environ.get(env_key)
        
        test_case = {
            "role": role,
            "type": "Primary",
            "key_env": env_key,
            "endpoint": agent_cfg.endpoint,
            "model": agent_cfg.model
        }
        
        run_test(test_case, key, results)
        
        # Check Fallbacks
        for idx, fb in enumerate(agent_cfg.fallback):
            env_key = fb.get("api_key_env")
            if not env_key: continue
            
            key = os.environ.get(env_key)
            test_case = {
                "role": role,
                "type": f"Fallback #{idx+1}",
                "key_env": env_key,
                "endpoint": fb.get("endpoint"),
                "model": fb.get("model")
            }
            run_test(test_case, key, results)

    # Print summary table
    print("\n" + "-" * 100)
    print(f"{'Role':<20} {'Type':<15} {'Key Env':<25} {'Protocol':<10} {'Status':<8} {'Details'}")
    print("-" * 100)
    for res in results:
        print(f"{res['role']:<20} {res['type']:<15} {res['key_env']:<25} {res['protocol']:<10} {res['status']:<8} {res['msg']}")
    print("-" * 100)

    # Count
    passed = sum(1 for r in results if r['status'] == "PASS")
    failed = sum(1 for r in results if r['status'] == "FAIL")
    missing = sum(1 for r in results if r['status'] == "MISSING")
    print(f"\nSummary: {passed} PASS, {failed} FAIL, {missing} MISSING")
    
    return 0 if failed == 0 else 1

def run_test(case, key, results):
    if not key:
        results.append({**case, "protocol": "-", "status": "MISSING", "msg": "Key not in env"})
        print(f"Skipping {case['role']} ({case['type']}): Missing Key")
        return

    protocol = infer_protocol(case["endpoint"], case["model"])
    print(f"Testing {case['role']} ({case['type']}) via {protocol}...", end=" ", flush=True)
    
    if protocol == "anthropic":
        success, msg = test_anthropic_key(key, case["endpoint"], case["model"])
    else:
        success, msg = test_openai_key(key, case["endpoint"], case["model"])
        
    status = "PASS" if success else "FAIL"
    print(status)
    results.append({**case, "protocol": protocol, "status": status, "msg": msg})

if __name__ == "__main__":
    sys.exit(main())
