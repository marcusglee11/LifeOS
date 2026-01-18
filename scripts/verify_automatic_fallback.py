#!/usr/bin/env python3
"""
Verify Automatic Fallback (Force Fail -> Retry)
===============================================
Proves that OpenCodeClient automatically retries with a fallback model 
if the primary attempt fails.

Scenario:
1. Primary Model: "invalid-provider/invalid-model" (Forces Failure)
2. Fallback Model: "openrouter/x-ai/grok-4.1-fast" (Should Succeed)
3. Expectation: Call succeeds and returns content from Grok.
"""
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.agents.opencode_client import OpenCodeClient, LLMCall

# Mock config structure
MOCK_FALLBACK_CONFIG = [
    {
        "model": "openrouter/x-ai/grok-4.1-fast",
        "provider": "openrouter",
        "api_key_env": "OPENROUTER_STEWARD_KEY"
    }
]

def verify_automatic_fallback():
    print("TEST: Verifying Automatic Fallback (Force Fail -> Retry)...\n")
    
    # Initialize client
    client = OpenCodeClient(role="steward", log_calls=False)
    
    # We need to Mock `get_agent_config` in the module where it's defined
    # The client imports it locally, so we patch the source.
    
    with patch("runtime.agents.models.get_agent_config") as mock_get_config:
        # Create a mock config object
        mock_config = MagicMock()
        mock_config.fallback = MOCK_FALLBACK_CONFIG
        mock_get_config.return_value = mock_config
        
        # Define a request with an INVALID Primary Model
        req = LLMCall(
            model="invalid-provider/failed-model", 
            prompt="Reply with 'FALLBACK_SUCCESS'",
            system_prompt="system"
        )
        
        print(f"1. Attempting Call (Primary: {req.model})...")
        print("   (This is EXPECTED to fail and trigger fallback loop)")
        
        try:
            resp = client.call(req)
            
            print(f"\n✓ SUCCESS: Received Response: {resp.content}")
            print(f"✓ Model Used: {resp.model_used}")
            
            if "FALLBACK_SUCCESS" in resp.content:
                print("\n🎉 AUTOMATIC FALLBACK VERIFIED!")
                return 0
            else:
                print("\n❌ Content mismatch. Fallback might have failed or returned wrong data.")
                return 1
                
        except Exception as e:
            print(f"\n❌ FAILED: Exception raised: {e}")
            print("Fallback loop did not catch the failure or fallback itself failed.")
            return 1

if __name__ == "__main__":
    sys.exit(verify_automatic_fallback())
