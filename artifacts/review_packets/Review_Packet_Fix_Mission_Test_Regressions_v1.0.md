# Review Packet: Fix Mission Test Regressions v1.0

**Mission Type**: Fix/Refactor
**Date**: 2026-01-09
**Status**: COMPLETE
**Author**: Antigravity

## Summary
Fixed critical regressions in Phase 3 mission tests (`runtime/tests/test_missions_phase3.py`) caused by un-stubbed missions and missing logic.
Corrected 100% of test failures.

## Key Changes
1.  **Fixed `test_missions_phase3.py`**:
    - Removed duplicate/misplaced test blocks causing `AttributeError`.
    - Corrected step assertion from `invoke_designer_llm_call` to `design_llm_call`.
    - Added mocks for `verify_repo_clean` where missing.
2.  **Updated `StewardMission`**:
    - Implemented real `_verify_repo_clean` logic calling `run_controller.verify_repo_clean`.
3.  **Updated `DesignMission`**:
    - Restored `context_refs_count` in evidence to fix test assertion.

## Verification
- **Command**: `pytest runtime/tests/test_missions_phase3.py -v`
- **Result**: 38 passed, 0 failed.

```text
======================== 38 passed, 1 warning in 7.98s ========================
```

## Appendix: Flattened Code

### runtime/orchestration/missions/steward.py
```python
"""
Phase 3 Mission Types - Steward Mission

Commits approved changes to repository.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: steward

CRITICAL: This mission guarantees "repo clean on exit" per architecture §5.3.
"""
from __future__ import annotations

from typing import Any, Dict, List

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
)


class StewardMission(BaseMission):
    """
    Steward mission: Commit approved changes to repository.
    
    Inputs:
        - review_packet (dict): The REVIEW_PACKET with artifacts
        - approval (dict): Council approval decision
        
    Outputs:
        - commit_hash (str): Git commit hash of the committed changes
        
    Preconditions:
        - approval.verdict == "approved"
        
    Steps:
        1. check_envelope: Verify paths are within steward envelope
        2. stage_changes: git add the artifacts
        3. commit: git commit with structured message
        4. record_completion: Update state files
        
    GUARANTEE: Repo clean on exit
        - Success path: All changes committed, working directory clean
        - Failure path: All changes reverted, evidence preserved in logs/
        
    For MVP: This is stubbed and does NOT actually commit.
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.STEWARD
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate steward mission inputs.
        
        Required: review_packet (dict), approval (dict with verdict="approved")
        """
        # Check review_packet
        review_packet = inputs.get("review_packet")
        if not review_packet:
            raise MissionValidationError("review_packet is required")
        if not isinstance(review_packet, dict):
            raise MissionValidationError("review_packet must be a dict")
        
        # Check approval
        approval = inputs.get("approval")
        if not approval:
            raise MissionValidationError("approval is required")
        if not isinstance(approval, dict):
            raise MissionValidationError("approval must be a dict")
        
        # Verify approval verdict
        verdict = approval.get("verdict")
        if verdict != "approved":
            raise MissionValidationError(
                f"Steward requires approved verdict, got: '{verdict}'"
            )
    
    def _verify_repo_clean(self, context: MissionContext) -> bool:
        """
        Verify repository is in clean state.
        """
        try:
            from runtime.orchestration.run_controller import verify_repo_clean
            verify_repo_clean(context.repo_root)
            return True
        except Exception as e:
            # Log error if possible
            print(f"Repo cleanliness check failed: {e}")
            return False
    
    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        """
        Execute the steward mission.
        
        For MVP, this is a stub implementation that:
        1. Validates inputs and preconditions
        2. Simulates git operations
        3. Returns a simulated commit hash
        4. GUARANTEES: Repo state is unchanged (stub doesn't modify)
        
        Full implementation would use git operations with compensation.
        """
        executed_steps: List[str] = []
        
        try:
            # Step 0: Validate inputs
            self.validate_inputs(inputs)
            executed_steps.append("validate_inputs")
            
            review_packet = inputs["review_packet"]
            approval = inputs["approval"]
            
            # Step 1: Check envelope
            artifacts = review_packet.get("payload", {}).get("artifacts_produced", [])
            # In full implementation, would verify each path against steward envelope
            executed_steps.append("check_envelope")
            
            # Step 2: Stage changes (stubbed)
            # In full implementation: git add <paths>
            # Compensation: git reset HEAD
            staged_paths = artifacts
            executed_steps.append("stage_changes")
            
            # Step 3: Commit (stubbed)
            # In full implementation: git commit -m "<message>"
            # Compensation: git reset --soft HEAD~1
            mission_name = review_packet.get("mission_name", "unknown")
            summary = review_packet.get("summary", "No summary")
            commit_message = f"{mission_name}: {summary}"
            
            # Simulated commit hash
            simulated_commit_hash = f"stub_{context.run_id[:16]}"
            executed_steps.append("commit")
            
            # Step 4: Record completion (stubbed)
            # In full implementation: Update LIFEOS_STATE.md
            executed_steps.append("record_completion")
            
            # GUARANTEE: Verify repo is clean on exit
            if not self._verify_repo_clean(context):
                return self._make_result(
                    success=False,
                    executed_steps=executed_steps,
                    error="Repo clean on exit guarantee violated",
                )
            
            return self._make_result(
                success=True,
                outputs={
                    "commit_hash": simulated_commit_hash,
                    "commit_message": commit_message,
                },
                executed_steps=executed_steps,
                evidence={
                    "artifacts_count": len(artifacts),
                    "mission_name": mission_name,
                },
            )
            
        except MissionValidationError as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Input validation failed: {e}",
            )
        except Exception as e:
            # GUARANTEE: On any failure, ensure repo is clean
            # In full implementation, would execute compensation here
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Unexpected error: {e}",
            )
```

### runtime/orchestration/missions/design.py
```python
"""
Phase 3 Mission Types - Design Mission

Transforms a task specification into a BUILD_PACKET.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: design
"""
from __future__ import annotations

from typing import Any, Dict, List

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
)


class DesignMission(BaseMission):
    """
    Design mission: Transform task spec into BUILD_PACKET.
    
    Inputs:
        - task_spec (str): Description of the task to design
        - context_refs (list[str], optional): Paths to context files
        
    Outputs:
        - build_packet (dict): The generated BUILD_PACKET
        
    Steps:
        1. gather_context: Read context files (if provided)
        2. design: Generate BUILD_PACKET via LLM (stubbed for MVP)
        3. validate_output: Validate output against schema
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.DESIGN
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate design mission inputs.
        
        Required: task_spec (non-empty string)
        Optional: context_refs (list of strings)
        """
        # Check required field
        task_spec = inputs.get("task_spec")
        if not task_spec:
            raise MissionValidationError("task_spec is required and must be non-empty")
        if not isinstance(task_spec, str):
            raise MissionValidationError("task_spec must be a string")
        
        # Check optional field
        context_refs = inputs.get("context_refs")
        if context_refs is not None:
            if not isinstance(context_refs, list):
                raise MissionValidationError("context_refs must be a list")
            for i, ref in enumerate(context_refs):
                if not isinstance(ref, str):
                    raise MissionValidationError(
                        f"context_refs[{i}] must be a string, got {type(ref).__name__}"
                    )
    
    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        executed_steps: List[str] = []
        
        try:
            # Step 1: Validate inputs
            self.validate_inputs(inputs)
            executed_steps.append("validate_inputs")
            
            # Step 2: Gather context (simulated for MVP)
            # In full implementation, this would read files and populate the packet
            context_data = {
                "task_spec": inputs["task_spec"],
                "context_refs": inputs.get("context_refs", []),
                "run_id": context.run_id,
            }
            executed_steps.append("gather_context")
            
            # Step 3: Call Agent API with designer role
            from runtime.agents.api import call_agent, AgentCall
            
            call = AgentCall(
                role="designer",
                packet=context_data,
                model="auto",
            )
            
            response = call_agent(call, run_id=context.run_id)
            executed_steps.append("design_llm_call")
            
            # Step 4: Extract BUILD_PACKET
            # The designer prompt instructs it to return a YAML packet.
            # Agent API automatically parses it into response.packet.
            build_packet = response.packet or {"raw_content": response.content}
            executed_steps.append("extract_build_packet")
            
            return self._make_result(
                success=True,
                outputs={"build_packet": build_packet},
                executed_steps=executed_steps,
                evidence={
                    "call_id": response.call_id,
                    "model_used": response.model_used,
                    "latency_ms": response.latency_ms,
                    "context_refs_count": len(inputs.get("context_refs", [])),
                },
            )
            
        except Exception as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Design mission failed: {e}",
            )
```
