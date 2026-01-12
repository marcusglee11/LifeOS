import os
import sys
from pathlib import Path
from runtime.orchestration.engine import Orchestrator, WorkflowDefinition, StepSpec, ExecutionContext

# Import canonical defaults from single source of truth
try:
    from runtime.agents.models import DEFAULT_MODEL, validate_config
except ImportError:
    DEFAULT_MODEL = "minimax-m2.1-free"
    def validate_config():
        return True, "Fallback"

def main():
    # Validate API key availability using canonical validation
    ok, msg = validate_config()
    if not ok:
        print(f"ERROR: {msg}")
        sys.exit(1)

    # Use STEWARD_MODEL from environment if set, otherwise use canonical default
    model = os.environ.get("STEWARD_MODEL", DEFAULT_MODEL)
    os.environ["STEWARD_MODEL"] = model

    orchestrator = Orchestrator()
    
    # Define a simple 1-step workflow
    workflow = WorkflowDefinition(
        id="verification-call",
        name="verification-call",
        steps=[
            StepSpec(
                id="step1",
                kind="runtime",
                payload={
                    "operation": "llm_call",
                    "prompt": "Hello! Reply with exactly one word: 'READY'.",
                    "output_key": "verification_result"
                }
            )
        ]
    )
    
    ctx = ExecutionContext(
        initial_state={},
        metadata={"run_id": "verify-opencode"}
    )
    
    print(f"Executing verification call with model: {os.environ['STEWARD_MODEL']}...")
    try:
        result = orchestrator.run_workflow(workflow, ctx)
        
        if result.success:
            print("SUCCESS!")
            print(f"Response: {result.final_state.get('verification_result')}")
            print(f"Model used: {result.final_state.get('verification_result_metadata', {}).get('model_used')}")
            
            # Check for logs
            log_dir = Path("logs/agent_calls")
            logs = list(log_dir.glob("*.json"))
            if logs:
                print(f"Found {len(logs)} local log(s) in {log_dir}")
            else:
                print("WARNING: No local logs found!")
        else:
            print(f"FAILED: {result.error_message}")
            
    finally:
        orchestrator._cleanup_llm_client()

if __name__ == "__main__":
    main()
