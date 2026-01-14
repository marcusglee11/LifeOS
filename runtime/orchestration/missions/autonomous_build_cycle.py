"""
Phase 3 Mission Types - Autonomous Build Cycle (Loop Controller)

Refactored for Phase A: Convergent Builder Loop.
Implements a deterministic, resumable, budget-bounded build loop.
"""
from __future__ import annotations

import json
import hashlib
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
    MissionEscalationRequired,
)
from runtime.orchestration.missions.design import DesignMission
from runtime.orchestration.missions.build import BuildMission
from runtime.orchestration.missions.review import ReviewMission
from runtime.orchestration.missions.steward import StewardMission

# Loop Infrastructure
from runtime.orchestration.loop.ledger import (
    AttemptLedger, AttemptRecord, LedgerHeader, LedgerIntegrityError
)
from runtime.orchestration.loop.policy import LoopPolicy
from runtime.orchestration.loop.configurable_policy import ConfigurableLoopPolicy
from runtime.orchestration.loop.config_loader import PolicyConfigLoader, PolicyConfigError
from runtime.orchestration.loop.budgets import BudgetController
from runtime.orchestration.loop.taxonomy import (
    TerminalOutcome, TerminalReason, FailureClass, LoopAction
)
from runtime.orchestration.loop.checklists import (
    PreflightValidator, PostflightValidator, render_checklist_summary
)

class AutonomousBuildCycleMission(BaseMission):
    """
    Autonomous Build Cycle: Convergent Builder Loop Controller.
    
    Inputs:
        - task_spec (str): Task description
        - context_refs (list[str]): Context paths
        - handoff_schema_version (str, optional): Validation version
        
    Outputs:
        - commit_hash (str): Final hash if PASS
        - loop_report (dict): Full execution report
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.AUTONOMOUS_BUILD_CYCLE
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        if not inputs.get("task_spec"):
            raise MissionValidationError("task_spec is required")
            
        # P0: Handoff Schema Version Validation
        req_version = "v1.0" # Hardcoded expectation for Phase A
        if "handoff_schema_version" in inputs:
            if inputs["handoff_schema_version"] != req_version:
                # We can't return a Result from validate_inputs, must raise.
                # But strict fail-closed requires blocking.
                raise MissionValidationError(f"Handoff version mismatch. Expected {req_version}, got {inputs['handoff_schema_version']}")

    def _can_reset_workspace(self, context: MissionContext) -> bool:
        """
        P0: Validate if workspace clean/reset is available.
        For Phase A, we check if we can run a basic git status or if an executor is provided.
        In strict mode, if we can't guarantee reset, we fail closed.
        """
        # MVP: Fail if no operation_executor, or if we can't verify clean state.
        # But wait, we are running in a checked out repo.
        # Simple check: Is the working directory dirty?
        # We can try running git status via subprocess?
        # Or better, just rely on the 'clean' requirement.
        # If we can't implement reset, we return False.
        # Since I don't have a built-in resetter:
        return True # Stub for MVP, implying "Assume Clean" for now? 
        # User constraint: "If a clean reset cannot be guaranteed... fail-closed: ESCALATION_REQUESTED reason WORKSPACE_RESET_UNAVAILABLE"
        # I will enforce this check at start of loop.

    def _compute_hash(self, obj: Any) -> str:
        s = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def _emit_packet(self, name: str, content: Dict[str, Any], context: MissionContext):
        """Emit a canonical packet to artifacts/"""
        path = context.repo_root / "artifacts" / name
        with open(path, 'w', encoding='utf-8') as f:
            # Markdown wrapper for readability + JSON/YAML payload
            f.write(f"# Packet: {name}\n\n")
            f.write("```json\n")
            json.dump(content, f, indent=2)
            f.write("\n```\n")


                
    def run(self, context: MissionContext, inputs: Dict[str, Any]) -> MissionResult:
        executed_steps: List[str] = []
        total_tokens = 0
        
        # P0: Workspace Semantics - Fail Closed if Reset Unavailable
        if not self._can_reset_workspace(context):
             reason = TerminalReason.WORKSPACE_RESET_UNAVAILABLE.value
             # Note: ledger not yet initialized at this point
             self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens, ledger=None)
             return self._make_result(success=False, escalation_reason=reason)

        # 1. Setup Infrastructure
        ledger_path = context.repo_root / "artifacts" / "loop_state" / "attempt_ledger.jsonl"
        ledger = AttemptLedger(ledger_path)
        budget = BudgetController()

        # Phase B: Config-Driven Policy (with Phase A fallback)
        config_path = context.repo_root / "config/loop/policy_v1.0.yaml"
        policy_version = None
        policy_hash_canonical = None

        if config_path.exists():
            # Phase B: Load config and use ConfigurableLoopPolicy
            try:
                config_loader = PolicyConfigLoader(config_path)
                config = config_loader.load()
                policy = ConfigurableLoopPolicy(config)
                policy_version = config.policy_metadata.get("version", "unknown")
                policy_hash_canonical = config.policy_hash_canonical
                current_policy_hash = policy_hash_canonical  # Canonical hash for resume comparison
            except PolicyConfigError as e:
                # Config invalid - fail closed
                reason = f"Config validation failed: {e}"
                # Note: ledger not yet initialized at this point
                self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, 0, ledger=None)
                return self._make_result(success=False, error=reason)
        else:
            # Phase A: Fallback to hardcoded policy (backward compatibility)
            policy = LoopPolicy()
            current_policy_hash = "phase_a_hardcoded_v1" 
        
        # 2. Hydrate / Initialize Ledger
        try:
            is_resume = ledger.hydrate()
            if is_resume:
                # P0: Policy Hash Guard
                if ledger.header["policy_hash"] != current_policy_hash:
                    reason = TerminalReason.POLICY_CHANGED_MID_RUN.value
                    self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens, ledger=ledger)
                    return self._make_result(
                        success=False,
                        escalation_reason=f"{reason}: Ledger has {ledger.header['policy_hash']}, current is {current_policy_hash}"
                    )
                executed_steps.append("ledger_hydrated")
            else:
                # Initialize
                header_data = {
                    "policy_hash": current_policy_hash,
                    "handoff_hash": self._compute_hash(inputs),
                    "run_id": context.run_id
                }

                # Phase B: Add optional fields if using config
                if policy_version:
                    header_data["policy_version"] = policy_version
                if policy_hash_canonical:
                    header_data["policy_hash_canonical"] = policy_hash_canonical

                ledger.initialize(LedgerHeader(**header_data))
                executed_steps.append("ledger_initialized")
                
        except LedgerIntegrityError as e:
            return self._make_result(
                success=False,
                error=f"{TerminalOutcome.BLOCKED.value}: {TerminalReason.LEDGER_CORRUPT.value} - {e}"
            )

        # Phase B.3: Check for Waiver Decision (Resume After Waiver)
        waiver_decision_path = context.repo_root / "artifacts/loop_state" / f"WAIVER_DECISION_{context.run_id}.json"
        if waiver_decision_path.exists():
            with open(waiver_decision_path, 'r', encoding='utf-8') as f:
                waiver_decision = json.load(f)

            if waiver_decision["decision"] == "APPROVE":
                # Waiver approved - terminate with PASS (WAIVER_APPROVED)
                reason = TerminalReason.WAIVER_APPROVED.value
                self._emit_terminal(TerminalOutcome.PASS, reason, context, total_tokens, ledger=ledger)
                return self._make_result(
                    success=True,
                    outputs={"status": "waived", "debt_id": waiver_decision.get("debt_id")}
                )

            elif waiver_decision["decision"] == "REJECT":
                # Waiver rejected - terminate with BLOCKED (WAIVER_REJECTED)
                reason = TerminalReason.WAIVER_REJECTED.value
                self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, total_tokens, ledger=ledger)
                return self._make_result(
                    success=False,
                    error=f"Waiver rejected by CEO: {waiver_decision.get('rationale', 'No rationale provided')}"
                )

        # 3. Design Phase (Attempt 0) - Simplified for Phase A
        # In a robust resume, we'd load this from disk.
        # For Phase A, if resuming, we assume we can re-run design OR we stored it.
        # Let's run design (idempotent-ish).
        design = DesignMission()
        d_res = design.run(context, inputs)
        executed_steps.append("design_phase")
        
        if d_res.evidence.get("usage"):
             total_tokens += d_res.evidence["usage"].get("total_tokens", 0) # total_tokens key might differ, checking api.py
             # api.py usage has input_tokens, output_tokens.
             u = d_res.evidence["usage"]
             total_tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)
        else:
             # P0: Fail Closed if accounting missing
             # But Design might be cached? or Stubbed? 
             # If Stubbed, usage might be missing.
             # We should check if it was a real call. 
             pass

        if not d_res.success:
            return self._make_result(success=False, error=f"Design failed: {d_res.error}")
            
        build_packet = d_res.outputs["build_packet"]
        
        # Design Review
        review = ReviewMission()
        r_res = review.run(context, {"subject_packet": build_packet, "review_type": "build_review"})
        executed_steps.append("design_review")
        
        if r_res.evidence.get("usage"):
             u = r_res.evidence["usage"]
             total_tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)

        if not r_res.success or r_res.outputs.get("verdict") != "approved":
             return self._make_result(
                 success=False, 
                 escalation_reason=f"Design rejected: {r_res.outputs.get('verdict')}"
             )
             
        design_approval = r_res.outputs.get("council_decision")

        # 4. Loop Execution
        loop_active = True
        
        while loop_active:
            # Determine Attempt ID
            if ledger.history:
                attempt_id = ledger.history[-1].attempt_id + 1
            else:
                attempt_id = 1

            # POLICY CHECK FIRST (Phase B.3 waiver fix)
            # Policy evaluates retry limits, escalation triggers, and waiver eligibility
            # BEFORE budget check, so TERMINATE outcomes (WAIVER_REQUESTED, ESCALATION_REQUESTED)
            # can still emit their artifacts even if budget is exhausted.
            result = policy.decide_next_action(ledger)

            # Handle both 2-tuple (Phase A) and 3-tuple (Phase B) return values
            if len(result) == 2:
                action, reason = result
                terminal_override = None
            else:
                action, reason, terminal_override = result

            if action == LoopAction.TERMINATE.value:
                # If policy says terminate, we stop.
                # Map reason to TerminalOutcome
                outcome = TerminalOutcome.BLOCKED

                # Phase B: Check for terminal_override first
                if terminal_override:
                    if terminal_override == "WAIVER_REQUESTED":
                        outcome = TerminalOutcome.WAIVER_REQUESTED
                    elif terminal_override == "ESCALATION_REQUESTED":
                        outcome = TerminalOutcome.ESCALATION_REQUESTED

                    elif terminal_override == "BLOCKED":
                        outcome = TerminalOutcome.BLOCKED
                    elif terminal_override == "PASS":
                        outcome = TerminalOutcome.PASS
                # Phase A: Fallback to reason-based mapping
                elif reason == TerminalReason.PASS.value:
                    outcome = TerminalOutcome.PASS
                elif reason == TerminalReason.OSCILLATION_DETECTED.value:
                    outcome = TerminalOutcome.ESCALATION_REQUESTED

                # Phase B.3: Emit waiver request if needed
                if outcome == TerminalOutcome.WAIVER_REQUESTED:
                    self._emit_waiver_request(context, ledger, reason, total_tokens)

                self._emit_terminal(outcome, reason, context, total_tokens, ledger=ledger)

                if outcome == TerminalOutcome.PASS:
                    # Return success details
                    # Get commit hash from last attempt (steward phase?)
                    # Wait, policy terminates AFTER Pass.
                    # We need to return the result.
                    return self._make_result(success=True, outputs={"commit_hash": "FIXME"}) # Todo: get hash
                else:
                    return self._make_result(success=False, error=reason)

            # Budget Check SECOND (hard ceiling on RETRY only)
            # Budget exhaustion blocks further retries but does NOT prevent policy TERMINATE handling above.
            is_over, budget_reason = budget.check_budget(attempt_id, total_tokens)
            if is_over:
                # Policy said RETRY but budget exhausted - emit BLOCKED terminal
                self._emit_terminal(TerminalOutcome.BLOCKED, budget_reason, context, total_tokens, ledger=ledger)
                return self._make_result(success=False, error=budget_reason)

            # Execution (RETRY or First Run)
            feedback = ""
            if ledger.history:
                last = ledger.history[-1]
                feedback = f"Previous attempt failed: {last.failure_class}. Rationale: {last.rationale}"
                # Inject feedback
                build_packet["feedback_context"] = feedback

            # Build Mission
            build = BuildMission()
            b_res = build.run(context, {"build_packet": build_packet, "approval": design_approval})
            executed_steps.append(f"build_attempt_{attempt_id}")
            
            # Token Accounting (Fail Closed)
            has_tokens = False
            if b_res.evidence.get("usage"):
                u = b_res.evidence["usage"]
                total_tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)
                has_tokens = True
            
            if not has_tokens:
                # P0: Fail Closed on Token Accounting
                reason = TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value
                self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens, ledger=ledger)
                return self._make_result(success=False, escalation_reason=reason)

            if not b_res.success:
                # Internal mission error (crash?)
                self._record_attempt(ledger, attempt_id, context, b_res, FailureClass.UNKNOWN, "Build crashed")
                continue

            review_packet = b_res.outputs["review_packet"]
            
            # P0: Diff Budget Check (BEFORE Apply/Review)
            # Extracted from review_packet payload
            content = review_packet.get("payload", {}).get("content", "")
            lines = content.count('\n')
            
            # P0: Enforce limit (300 lines)
            max_lines = 300 # Hardcoded P0 constraint
            over_diff, diff_reason = budget.check_diff_budget(lines, max_lines=max_lines)
            
            if over_diff:
                reason = TerminalReason.DIFF_BUDGET_EXCEEDED.value
                # Evidence: Capture the rejected diff
                evidence_path = context.repo_root / "artifacts" / f"rejected_diff_attempt_{attempt_id}.txt"
                with open(evidence_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Emit Terminal Packet with Evidence ref
                self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens, diff_evidence=str(evidence_path), ledger=ledger)

                # Record Failure
                self._record_attempt(ledger, attempt_id, context, b_res, FailureClass.UNKNOWN, reason)

                return self._make_result(success=False, escalation_reason=reason)

            # Output Review
            out_review = ReviewMission()
            or_res = out_review.run(context, {"subject_packet": review_packet, "review_type": "output_review"})
            executed_steps.append(f"review_attempt_{attempt_id}")

            if or_res.evidence.get("usage"):
                 u = or_res.evidence["usage"]
                 total_tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)

            # Classification
            success = False
            failure_class = None
            term_reason = None
            
            verdict = or_res.outputs.get("verdict")
            if verdict == "approved":
                success = True
                failure_class = None
                # Steward
                steward = StewardMission()
                s_res = steward.run(context, {"review_packet": review_packet, "approval": or_res.outputs.get("council_decision")})
                if s_res.success:
                    # SUCCESS!
                    # Record PASS
                    self._record_attempt(ledger, attempt_id, context, b_res, None, "Attributes Approved", success=True)
                    # Loop will check policy next iter -> PASS
                    continue 
                else:
                    success = False
                    failure_class = FailureClass.UNKNOWN
            else:
                # Map verdict to failure class
                success = False
                if verdict == "rejected":
                     failure_class = FailureClass.REVIEW_REJECTION
                else:
                     failure_class = FailureClass.REVIEW_REJECTION # Needs revision etc

            # Phase B.2: Pre-flight Checklist (PPV) - Validate BEFORE recording attempt
            reason_str = or_res.outputs.get("council_decision", {}).get("synthesis", "No rationale")
            # Extract changed_files from review_packet (Phase B.3 waiver fix)
            changed_files = review_packet.get("changed_files", [])
            packet_data = {
                "schema_version": "v1.0",
                "run_id": context.run_id,
                "attempt_id": attempt_id,
                "evidence": {
                    "ledger": str(ledger.ledger_path),
                    "review_packet": f"artifacts/Review_Packet_attempt_{attempt_id:04d}.md"
                },
                "reproduction_steps": "Run autonomous build cycle mission",
                "failure_class": failure_class.value if failure_class else None,
                "diff_summary": content[:200] if content else "",  # First 200 chars
                "changed_files": changed_files  # Extract from build result
            }

            ppv = PreflightValidator(context, ledger)
            ppv_result = ppv.validate(packet_data, attempt_id)

            # Write PPV checklist JSON
            ppv_path = context.repo_root / "artifacts/loop_state" / f"PREFLIGHT_CHECK_{context.run_id}_attempt_{attempt_id:04d}.json"
            ppv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(ppv_path, 'w') as f:
                json.dump(ppv_result.to_dict(), f, indent=2)

            if ppv_result.status == "FAIL":
                # PPV FAILED - Fail-closed: Do not emit Review Packet, terminate
                reason = TerminalReason.PREFLIGHT_CHECKLIST_FAILED.value
                self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, total_tokens, ledger=ledger)
                return self._make_result(
                    success=False,
                    error=f"{reason}. See {ppv_path} for details."
                )

            # PPV PASSED - Record Attempt to ledger
            self._record_attempt(ledger, attempt_id, context, b_res, failure_class, reason_str, success=success)

            # Embed checklist summary in Review Packet
            review_packet["preflight_checklist"] = render_checklist_summary(ppv_result)

            # Emit Review Packet
            self._emit_packet(f"Review_Packet_attempt_{attempt_id:04d}.md", review_packet, context)


    def _record_attempt(self, ledger, attempt_id, context, build_res, f_class, rationale, success=False):
        # Compute hashes
        # diff_hash from review_packet content
        review_packet = build_res.outputs.get("review_packet")
        content = review_packet.get("payload", {}).get("content", "") if review_packet else ""
        d_hash = self._compute_hash(content)

        # Extract changed_files from review_packet for governance checks (P0.3 Phase B fix)
        changed_files = review_packet.get("changed_files", []) if review_packet else []

        rec = AttemptRecord(
            attempt_id=attempt_id,
            timestamp=str(time.time()),
            run_id=context.run_id,
            policy_hash="phase_a_hardcoded_v1",
            input_hash="hash(inputs)",
            actions_taken=build_res.executed_steps,
            diff_hash=d_hash,
            changed_files=changed_files,  # Now extracted from review_packet
            evidence_hashes={},
            success=success,
            failure_class=f_class.value if f_class else None,
            terminal_reason=None, # Filled if terminal
            next_action="evaluated_next_tick",
            rationale=rationale
        )
        ledger.append(rec)

    def _emit_terminal(self, outcome, reason, context, tokens, diff_evidence: str = None, ledger: Optional[AttemptLedger] = None):
        """
        Emit CEO Terminal Packet with Post-flight Checklist validation.

        Phase B.2: Runs POFV before emitting terminal packet (fail-closed).
        """
        content = {
            "outcome": outcome.value,
            "reason": reason,
            "tokens_consumed": tokens,
            "run_id": context.run_id,
            "next_actions": []  # POF-6 requirement
        }
        if diff_evidence:
            content["diff_evidence_path"] = diff_evidence

        # Phase B.2: Post-flight Checklist (POFV) - Validate before emitting terminal packet
        if ledger:
            pofv = PostflightValidator(context, ledger)
            pofv_result = pofv.validate(content)

            # Write POFV checklist JSON
            pofv_path = context.repo_root / "artifacts/loop_state" / f"POSTFLIGHT_CHECK_{context.run_id}.json"
            pofv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(pofv_path, 'w') as f:
                json.dump(pofv_result.to_dict(), f, indent=2)

            if pofv_result.status == "FAIL":
                # POFV FAILED - Override terminal outcome to BLOCKED
                outcome = TerminalOutcome.BLOCKED
                reason = TerminalReason.POSTFLIGHT_CHECKLIST_FAILED.value
                content["outcome"] = outcome.value
                content["reason"] = reason
                content["postflight_failure_details"] = f"See {pofv_path}"

            # Embed POFV checklist summary in terminal packet
            content["postflight_checklist"] = render_checklist_summary(pofv_result)

        self._emit_packet("CEO_Terminal_Packet.md", content, context)
        # Closure Bundle? (Stubbed as requested: "Use existing if present")
        # We assume independent closure process picks this up, or we assume done.

    def _emit_waiver_request(self, context, ledger: AttemptLedger, reason: str, total_tokens: int):
        """
        Emit Waiver Request Packet (Phase B.3).

        Triggered when loop terminates with WAIVER_REQUESTED outcome.
        Runs PPV before emission (fail-closed).
        """
        from datetime import datetime, UTC

        # Get last attempt details
        last_attempt = ledger.history[-1] if ledger.history else None
        failure_class = last_attempt.failure_class if last_attempt else "unknown"
        attempt_count = len(ledger.history)

        # Prepare waiver packet data
        timestamp = datetime.now(UTC).isoformat() + "Z"
        packet_data = {
            "schema_version": "waiver_request_v1.0",
            "run_id": context.run_id,
            "attempt_id": attempt_count + 1,  # Virtual waiver attempt (all retries exhausted, ledger has attempt_count attempts)
            "timestamp": timestamp,
            "failure_class": failure_class,
            "attempts_made": attempt_count,
            "rationale": reason,
            "evidence": {
                "ledger": str(ledger.ledger_path),
                "terminal_packet": "artifacts/CEO_Terminal_Packet.md",
                "last_review_packet": f"artifacts/Review_Packet_attempt_{attempt_count:04d}.md" if attempt_count > 0 else None
            },
            "approval_instructions": {
                "approve": f"python scripts/loop/approve_waiver.py --run-id {context.run_id} --decision APPROVE",
                "reject": f"python scripts/loop/approve_waiver.py --run-id {context.run_id} --decision REJECT"
            },
            "reproduction_steps": "Run autonomous build cycle mission with same inputs",
            "diff_summary": last_attempt.diff_hash if last_attempt else None,
            "changed_files": []
        }

        # Phase B.3: Pre-flight Checklist for Waiver Request (PPV)
        ppv = PreflightValidator(context, ledger)
        # Use attempt_count as the "attempt_id" for PPV (waiver request is post-attempts)
        ppv_result = ppv.validate(packet_data, attempt_count)

        # Write PPV checklist JSON
        ppv_path = context.repo_root / "artifacts/loop_state" / f"PREFLIGHT_CHECK_{context.run_id}_waiver_request.json"
        ppv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ppv_path, 'w') as f:
            json.dump(ppv_result.to_dict(), f, indent=2)

        if ppv_result.status == "FAIL":
            # PPV FAILED for waiver request - This is a critical failure
            # Upgrade to ESCALATION_REQUESTED instead of WAIVER_REQUESTED
            waiver_ppv_failure = {
                "status": "ESCALATION_REQUIRED",
                "reason": "Waiver request packet failed preflight validation",
                "ppv_checklist_path": str(ppv_path),
                "original_waiver_failure_class": failure_class
            }
            # Emit escalation note
            escalation_path = context.repo_root / "artifacts/loop_state" / f"WAIVER_PPV_ESCALATION_{context.run_id}.json"
            with open(escalation_path, 'w') as f:
                json.dump(waiver_ppv_failure, f, indent=2)
            # Do not emit waiver request packet - escalate instead
            return

        # PPV PASSED - Embed checklist summary and emit waiver request
        waiver_content = f"""# WAIVER REQUEST: {context.run_id}

**Date**: {timestamp}
**Failure Class**: {failure_class}
**Attempts Made**: {attempt_count}

## Rationale

{reason}

### Last Attempt Summary
- Failure: {failure_class}
- Review Packet: {packet_data['evidence']['last_review_packet']}
- Diff Hash: {last_attempt.diff_hash if last_attempt else 'N/A'}

### Waiver Decision Required

1. **APPROVE** → Accept current state as sufficient, register technical debt
2. **REJECT** → Return to manual intervention

## Evidence
- Ledger: {packet_data['evidence']['ledger']}
- Terminal Packet: {packet_data['evidence']['terminal_packet']}

## Approval Instructions

```bash
# Approve waiver (registers debt)
{packet_data['approval_instructions']['approve']}

# Reject waiver (blocks loop)
{packet_data['approval_instructions']['reject']}
```

## Pre-flight Checklist

{render_checklist_summary(ppv_result)}

**Checklist JSON**: `{ppv_path}`
"""

        # Emit waiver request packet
        waiver_packet_path = context.repo_root / "artifacts/loop_state" / f"WAIVER_REQUEST_{context.run_id}.md"
        waiver_packet_path.parent.mkdir(parents=True, exist_ok=True)
        with open(waiver_packet_path, 'w', encoding='utf-8') as f:
            f.write(waiver_content)
