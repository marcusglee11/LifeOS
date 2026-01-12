"""
Phase 3 Mission Types - Steward Mission

Commits approved changes to repository.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: steward

CRITICAL: This mission guarantees "repo clean on exit" per architecture §5.3.
HARDENED: Deterministic repo-clean evidence; no print-only paths.
MVP STUB: Does NOT actually commit - all steps are explicitly marked *_stub.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

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
        - simulated_commit_hash (str): Simulated Git commit hash (MVP STUB)
        
    Preconditions:
        - approval.verdict == "approved"
        
    Steps (all *_stub for MVP):
        1. check_envelope_stub: Verify paths are within steward envelope (STUB)
        2. stage_changes_stub: git add the artifacts (STUB)
        3. commit_stub: git commit with structured message (STUB)
        4. record_completion_stub: Update state files (STUB)
        5. verify_repo_clean: Verify repo is clean on exit (REAL)
        
    GUARANTEE: Repo clean on exit
        - Success path: All changes committed, working directory clean
        - Failure path: All changes reverted, evidence preserved in logs/
        
    MVP STUB: This does NOT actually commit. All git operations are stubbed.
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
    
    def _verify_repo_clean(self, context: MissionContext) -> Tuple[bool, str]:
        """
        Verify repository is in clean state.
        
        HARDENED: Returns structured (ok, reason) tuple for deterministic error capture.
        No print() statements - all errors are captured in return value.
        
        Returns:
            (ok: bool, reason: str) - reason is deterministic error message or "clean"
        """
        try:
            from runtime.orchestration.run_controller import verify_repo_clean
            verify_repo_clean(context.repo_root)
            return (True, "clean")
        except Exception as e:
            # Capture error deterministically - no print()
            error_type = type(e).__name__
            error_msg = str(e)
            # Truncate long error messages for determinism
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "...[truncated]"
            return (False, f"{error_type}: {error_msg}")
    
    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        """
        Execute the steward mission.
        
        MVP STUB: This is a stub implementation that:
        1. Validates inputs and preconditions
        2. Simulates git operations (all marked *_stub)
        3. Returns a simulated commit hash
        4. GUARANTEES: Repo state is unchanged (stub doesn't modify)
        
        HARDENED: All stubbed steps are explicitly marked. Repo-clean errors
        are deterministic and auditable.
        """
        executed_steps: List[str] = []
        evidence: Dict[str, Any] = {
            "stubbed": True,
            "simulated_steps": [],
        }
        
        try:
            # Step 0: Validate inputs
            self.validate_inputs(inputs)
            executed_steps.append("validate_inputs")
            
            review_packet = inputs["review_packet"]
            
            # Step 1: Check envelope (STUB)
            artifacts = review_packet.get("payload", {}).get("artifacts_produced", [])
            # In full implementation, would verify each path against steward envelope
            executed_steps.append("check_envelope_stub")
            evidence["simulated_steps"].append("check_envelope_stub")
            
            # Step 2: Stage changes (STUB)
            # In full implementation: git add <paths>
            # Compensation: git reset HEAD
            executed_steps.append("stage_changes_stub")
            evidence["simulated_steps"].append("stage_changes_stub")
            
            # Step 3: Commit (STUB)
            # In full implementation: git commit -m "<message>"
            # Compensation: git reset --soft HEAD~1
            mission_name = review_packet.get("mission_name", "unknown")
            summary = review_packet.get("summary", "No summary")
            commit_message = f"{mission_name}: {summary}"
            
            # Simulated commit hash - clearly labeled
            simulated_commit_hash = f"stub_{context.run_id[:16]}"
            executed_steps.append("commit_stub")
            evidence["simulated_steps"].append("commit_stub")
            
            # Step 4: Record completion (STUB)
            # In full implementation: Update LIFEOS_STATE.md
            executed_steps.append("record_completion_stub")
            evidence["simulated_steps"].append("record_completion_stub")
            
            # Step 5: GUARANTEE - Verify repo is clean on exit (REAL)
            repo_clean_ok, repo_clean_reason = self._verify_repo_clean(context)
            executed_steps.append("verify_repo_clean")
            evidence["repo_clean_result"] = repo_clean_reason
            
            if not repo_clean_ok:
                return self._make_result(
                    success=False,
                    executed_steps=executed_steps,
                    error=f"Repo clean on exit guarantee violated: {repo_clean_reason}",
                    evidence=evidence,
                )
            
            # Add final evidence
            evidence["artifacts_count"] = len(artifacts)
            evidence["mission_name"] = mission_name
            
            return self._make_result(
                success=True,
                outputs={
                    "simulated_commit_hash": simulated_commit_hash,
                    "commit_message": commit_message,
                },
                executed_steps=executed_steps,
                evidence=evidence,
            )
            
        except MissionValidationError as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Input validation failed: {e}",
                evidence=evidence,
            )
        except Exception as e:
            # GUARANTEE: On any failure, re-run repo-clean verification
            # and include results in evidence deterministically
            repo_clean_ok, repo_clean_reason = self._verify_repo_clean(context)
            evidence["repo_clean_on_failure"] = repo_clean_reason
            evidence["repo_clean_on_failure_ok"] = repo_clean_ok
            
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Unexpected error: {e}",
                evidence=evidence,
            )
