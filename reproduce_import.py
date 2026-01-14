
import sys
import os

# Add repo root to path
sys.path.insert(0, os.getcwd())

print("Attempting to import runtime.agents...")
try:
    import runtime.agents
    print("runtime.agents imported.")
    print(f"runtime.agents dir: {dir(runtime.agents)}")
except Exception as e:
    print(f"Failed to import runtime.agents: {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to import OpenCodeClient from runtime.agents...")
try:
    from runtime.agents import OpenCodeClient
    print("SUCCESS: OpenCodeClient imported.")
except ImportError as e:
    print(f"FAILURE: {e}")
except Exception as e:
    print(f"FAILURE (Other): {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting direct import of runtime.agents.opencode_client...")
try:
    import runtime.agents.opencode_client
    print("SUCCESS: runtime.agents.opencode_client imported.")
    print(f"OpenCodeClient in module: {'OpenCodeClient' in dir(runtime.agents.opencode_client)}")
except Exception as e:
    print(f"FAILURE to import module directly: {e}")
    import traceback
    traceback.print_exc()
