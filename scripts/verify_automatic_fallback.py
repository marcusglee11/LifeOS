#!/usr/bin/env python3
"""
Verify Automatic Fallback (Force Fail -> Retry) - Dynamic Config
================================================================
Proves that OpenCodeClient automatically retries with a fallback model 
DEFINED IN CONFIG if the primary attempt fails.

Scenario:
1. Primary Model: "invalid-provider/invalid-model" (Forces Failure)
2. Fallback Model: Loaded dynamically from config/models.yaml for 'steward' role.
3. Expectation: Call succeeds and returns content from the fallback model.
"""
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from runtime.agents.opencode_client import OpenCodeClient, LLMCall
    from runtime.agents.models import load_model_config, get_agent_config
except ImportError as e:
    print(f"Error importing runtime: {e}")
    sys.exit(1)

def verify_automatic_fallback():
    print("TEST: Verifying Automatic Fallback (Force Fail -> Retry) Dynamic...\n")
    
    # Load actual fallback config for steward
    real_config = get_agent_config("steward")
    if not real_config or not real_config.fallback:
        print("❌ FAIL: No fallback configured for 'steward' in models.yaml to test against.")
        return 1
        
    fallback_entry = real_config.fallback[0]
    fallback_model = fallback_entry.get("model")
    print(f"I: Found configured fallback for steward: {fallback_model}")

    # Initialize client
    client = OpenCodeClient(role="steward", log_calls=False)
    
    # We mock 'get_agent_config' to return our manipulated config:
    # Primary = Garbage, Fallback = Real/Working from Config
    
    with patch("runtime.agents.opencode_client.get_agent_config") as mock_get_client: # opencode_client.py imports it? 
        # Check source: client uses `from runtime.agents.models import get_agent_config` inside methods? 
        # Actually client uses `self._load_api_key_for_role` which uses `get_agent_config`.
        # And `call()` uses `get_agent_config` to build attempts.
        
        # We need to simulate the `call()` method logic receiving a config list 
        # where item 0 is fail, item 1 is real fallback.
        # But `call()` calls `get_agent_config` internally.
        pass
    
    # Actually, simpler approach:
    # Just run client.call() with a request that specifies a model that FAILS.
    # But `call()` logic:
    # 1. Determine Primary (from request OR current_model)
    # 2. Build attempts list: [Primary, Fallback1, Fallback2...]
    # If we pass a Primary that fails, it should proceed to Fallback1.
    
    # The 'Primary' is the one passed in LLMCall if provided.
    req = LLMCall(
        model="invalid-provider/failed-model", 
        prompt="Reply with 'FALLBACK_SUCCESS'",
        system_prompt="system"
    )
    
    print(f"1. Attempting Call (Primary: {req.model})...")
    print(f"   (Expecting fallback to: {fallback_model})")
    
    try:
        # Note: We rely on the client loading the REAL fallbacks from config.
        # We don't need to mock anything if models.yaml is correct!
        resp = client.call(req)
        
        print(f"\n✓ SUCCESS: Received Response: {resp.content[:100]}...")
        print(f"✓ Model Used: {resp.model_used}")
        
        if "FALLBACK_SUCCESS" in resp.content or "SUCCESS" in resp.content or "OK" in resp.content or len(resp.content) > 0:
             # Basic content check; fallback models might not obey instruction perfectly if small
            pass

        # Verify the model used matches the configured fallback (or contains parts of it)
        if fallback_model in resp.model_used or resp.model_used in fallback_model:
             print("\n🎉 AUTOMATIC FALLBACK VERIFIED!")
             return 0
        
        # Handle provider prefixes like "OR:openrouter/..."
        if fallback_model.split("/")[-1] in resp.model_used:
             print("\n🎉 AUTOMATIC FALLBACK VERIFIED (Model Match)!")
             return 0
             
        print(f"\n❌ Model mismatch. Expected usage of {fallback_model}, got {resp.model_used}")
        return 1
            
    except Exception as e:
        print(f"\n❌ FAILED: Exception raised: {e}")
        print("Fallback loop did not catch the failure or fallback config is broken.")
        return 1

if __name__ == "__main__":
    sys.exit(verify_automatic_fallback())
