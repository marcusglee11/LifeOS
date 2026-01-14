#!/usr/bin/env python3
"""
Debug Grok Call
===============
Investigates why OpenCodeClient reports success but returns empty content for Grok calls.
Prints FULL execution details (Env, Command, Stdout, Stderr).
"""
import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.agents.opencode_client import OpenCodeClient, LLMCall

def debug_grok():
    print("DEBUG: Initializing Steward Client (Zen Primary)...")
    client = OpenCodeClient(role="steward")
    
    # We want to inspect the environment that WOULD be used
    # But OpenCodeClient.call constructs it internally.
    # We will replicate the call logic or just call it and print results.
    
    req = LLMCall(
        model="openrouter/x-ai/grok-4.1-fast",
        prompt="Reply with 'GROK_DEBUG_TEST'",
        system_prompt="system"
    )
    
    print(f"\nEXECUTING CALL to {req.model}...")
    try:
        # We need to monkeypatch subprocess.run to see what exactly is persisting
        original_run = subprocess.run
        def logged_run(*args, **kwargs):
            print(f"DEBUG: subprocess.run command: {args[0]}")
            env = kwargs.get('env', {})
            print(f"DEBUG: Env OPENROUTER_API_KEY: {env.get('OPENROUTER_API_KEY')[:10] if env.get('OPENROUTER_API_KEY') else 'None'}...")
            print(f"DEBUG: Env ZEN_API_KEY: {env.get('ZEN_API_KEY')[:10] if env.get('ZEN_API_KEY') else 'None'}...")
            
            # Execute real run
            res = original_run(*args, **kwargs)
            
            print(f"DEBUG: Return Code: {res.returncode}")
            print(f"DEBUG: STDOUT: {res.stdout!r}")
            print(f"DEBUG: STDERR: {res.stderr!r}")
            return res
            
        subprocess.run = logged_run
        
        resp = client.call(req)
        print(f"\nFINAL RESPONSE CONTENT: {resp.content!r}")
        
    except Exception as e:
        print(f"\nEXCEPTION: {e}")

if __name__ == "__main__":
    debug_grok()
