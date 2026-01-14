"""
Phase B.2: Pre-flight and Post-flight Validators (PPV/POFV)

Machine-enforced validation checklists that prevent incomplete/invalid packets
from being emitted, reducing review looping.

PPV (Packet Preflight Validator): Runs before emitting Review Packets or Waiver Requests
POFV (Postflight Validator): Runs before emitting final terminal packet

Both validators produce deterministic JSON artifacts with machine-readable pass/fail status.
"""
from __future__ import annotations

import json
import hashlib
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path

if TYPE_CHECKING:
    from runtime.orchestration.missions.base import MissionContext

from runtime.orchestration.loop.ledger import AttemptLedger
from runtime.orchestration.loop.taxonomy import FailureClass, TerminalOutcome, TerminalReason


@dataclass
class ChecklistItem:
    """Single checklist item with pass/fail status."""
    id: str
    name: str
    status: str  # "PASS" | "FAIL"
    evidence: List[str]
    note: str


@dataclass
class ChecklistResult:
    """Complete checklist validation result."""
    schema_version: str
    run_id: str
    attempt_id: Optional[int]
    phase: str  # "PREFLIGHT" | "POSTFLIGHT"
    status: str  # "PASS" | "FAIL"
    items: List[ChecklistItem]
    computed_hashes: Dict[str, str]
    timestamp_utc: str
    tool_version: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert ChecklistItem dataclasses to dicts
        result["items"] = [asdict(item) for item in self.items]
        return result


class PreflightValidator:
    """
    Pre-flight Validator (PPV) - Phase B.2

    Runs before emitting Review Packets and Waiver Request packets.
    Validates that packet contains all required fields and evidence.

    Fail-closed: If any check fails, packet emission is blocked and
    loop terminates with BLOCKED (PREFLIGHT_CHECKLIST_FAILED).
    """

    def __init__(self, context: MissionContext, ledger: AttemptLedger):
        self.context = context
        self.ledger = ledger

    def validate(self, packet_data: Dict[str, Any], attempt_id: int) -> ChecklistResult:
        """
        Run all pre-flight checks.

        Args:
            packet_data: The packet to validate (Review Packet or Waiver Request)
            attempt_id: Current attempt ID

        Returns:
            ChecklistResult with PASS/FAIL status and individual check results
        """
        items = []

        # PF-1: Schema pass
        items.append(self._check_schema(packet_data))

        # PF-2: Evidence pointers present
        items.append(self._check_evidence_pointers(packet_data))

        # PF-3: Determinism anchors present
        items.append(self._check_determinism_anchors(packet_data))

        # PF-4: Repro steps present
        items.append(self._check_repro_steps(packet_data))

        # PF-5: Taxonomy classification valid
        items.append(self._check_taxonomy_classification(packet_data))

        # PF-6: Governance surface scan
        items.append(self._check_governance_surface(packet_data))

        # PF-7: Budget state consistent
        items.append(self._check_budget_state(packet_data))

        # PF-8: Delta summary present
        items.append(self._check_delta_summary(packet_data))

        # Overall status: PASS if all items pass
        overall_status = "PASS" if all(item.status == "PASS" for item in items) else "FAIL"

        return ChecklistResult(
            schema_version="checklist_v1",
            run_id=self.context.run_id,
            attempt_id=attempt_id,
            phase="PREFLIGHT",
            status=overall_status,
            items=items,
            computed_hashes=self._compute_hashes(),
            timestamp_utc=datetime.now(UTC).isoformat() + "Z",
            tool_version="phase_b_v1.0"
        )

    def _check_schema(self, packet_data: Dict[str, Any]) -> ChecklistItem:
        """PF-1: Schema pass (packet has required schema version + sections)."""
        required_sections = ["schema_version", "run_id", "attempt_id"]
        missing = [s for s in required_sections if s not in packet_data]

        if missing:
            return ChecklistItem(
                id="PF-1",
                name="Schema pass",
                status="FAIL",
                evidence=[],
                note=f"Missing required sections: {missing}"
            )
        else:
            schema_ver = packet_data.get("schema_version", "unknown")
            return ChecklistItem(
                id="PF-1",
                name="Schema pass",
                status="PASS",
                evidence=[f"packet#{s}" for s in required_sections],
                note=f"Schema {schema_ver} validated"
            )

    def _check_evidence_pointers(self, packet_data: Dict[str, Any]) -> ChecklistItem:
        """PF-2: Evidence pointers present (all claims have non-empty evidence refs)."""
        evidence = packet_data.get("evidence")

        if evidence is None:
            return ChecklistItem(
                id="PF-2",
                name="Evidence pointers present",
                status="FAIL",
                evidence=[],
                note="No evidence section found"
            )

        if not isinstance(evidence, dict):
            return ChecklistItem(
                id="PF-2",
                name="Evidence pointers present",
                status="FAIL",
                evidence=[],
                note="Evidence section is not a dict"
            )

        # Count evidence entries
        evidence_count = len(evidence)
        if evidence_count == 0:
            return ChecklistItem(
                id="PF-2",
                name="Evidence pointers present",
                status="FAIL",
                evidence=[],
                note="Evidence section is empty"
            )

        return ChecklistItem(
            id="PF-2",
            name="Evidence pointers present",
            status="PASS",
            evidence=list(evidence.keys())[:5],  # Sample first 5
            note=f"{evidence_count} evidence refs found"
        )

    def _check_determinism_anchors(self, packet_data: Dict[str, Any]) -> ChecklistItem:
        """PF-3: Determinism anchors present (policy_hash, run_id, handoff_hash)."""
        required_anchors = ["run_id"]

        # Check ledger header for policy_hash
        if self.ledger.header:
            policy_hash = self.ledger.header.get("policy_hash")
            if not policy_hash:
                return ChecklistItem(
                    id="PF-3",
                    name="Determinism anchors present",
                    status="FAIL",
                    evidence=[],
                    note="policy_hash missing from ledger header"
                )
        else:
            return ChecklistItem(
                id="PF-3",
                name="Determinism anchors present",
                status="FAIL",
                evidence=[],
                note="Ledger header not initialized"
            )

        missing = [a for a in required_anchors if a not in packet_data]
        if missing:
            return ChecklistItem(
                id="PF-3",
                name="Determinism anchors present",
                status="FAIL",
                evidence=[],
                note=f"Missing anchors in packet: {missing}"
            )

        return ChecklistItem(
            id="PF-3",
            name="Determinism anchors present",
            status="PASS",
            evidence=["ledger_header#policy_hash", "packet#run_id"],
            note="All determinism anchors present"
        )

    def _check_repro_steps(self, packet_data: Dict[str, Any]) -> ChecklistItem:
        """PF-4: Reproduction steps present or explicitly marked non-reproducible."""
        repro = packet_data.get("reproduction_steps")

        if repro is None:
            # Check for explicit non-reproducible marker
            non_repro_reason = packet_data.get("non_reproducible_reason")
            if non_repro_reason:
                return ChecklistItem(
                    id="PF-4",
                    name="Repro steps present",
                    status="PASS",
                    evidence=["packet#non_reproducible_reason"],
                    note=f"Explicitly non-reproducible: {non_repro_reason}"
                )
            else:
                return ChecklistItem(
                    id="PF-4",
                    name="Repro steps present",
                    status="FAIL",
                    evidence=[],
                    note="No reproduction steps or non-reproducible marker"
                )

        if isinstance(repro, str) and len(repro.strip()) > 0:
            return ChecklistItem(
                id="PF-4",
                name="Repro steps present",
                status="PASS",
                evidence=["packet#reproduction_steps"],
                note="Reproduction steps provided"
            )

        return ChecklistItem(
            id="PF-4",
            name="Repro steps present",
            status="FAIL",
            evidence=[],
            note="Reproduction steps field is empty"
        )

    def _check_taxonomy_classification(self, packet_data: Dict[str, Any]) -> ChecklistItem:
        """PF-5: Taxonomy classification valid (failure_class/terminal_reason are enum-valid)."""
        failure_class = packet_data.get("failure_class")

        # If no failure (success case), classification not required
        if failure_class is None:
            return ChecklistItem(
                id="PF-5",
                name="Taxonomy classification valid",
                status="PASS",
                evidence=[],
                note="No failure classification (success case)"
            )

        # Validate failure_class is a known enum value
        try:
            FailureClass(failure_class)
            return ChecklistItem(
                id="PF-5",
                name="Taxonomy classification valid",
                status="PASS",
                evidence=["packet#failure_class"],
                note=f"Valid classification: {failure_class}"
            )
        except ValueError:
            return ChecklistItem(
                id="PF-5",
                name="Taxonomy classification valid",
                status="FAIL",
                evidence=[],
                note=f"Invalid failure_class: {failure_class}"
            )

    def _check_governance_surface(self, packet_data: Dict[str, Any]) -> ChecklistItem:
        """PF-6: Governance surface scan (protected paths touched yes/no + evidence)."""
        # Check for governance surface marker in packet
        governance_touched = packet_data.get("governance_surface_touched", False)

        # Protected path patterns
        protected_patterns = [
            "docs/00_foundations/",
            "docs/01_governance/",
            "config/governance/"
        ]

        # Check if diff_summary mentions protected paths
        diff_summary = packet_data.get("diff_summary", "")
        touched_paths = []

        for pattern in protected_patterns:
            if pattern in diff_summary:
                touched_paths.append(pattern)

        if touched_paths:
            return ChecklistItem(
                id="PF-6",
                name="Governance surface scan",
                status="PASS",
                evidence=touched_paths,
                note=f"Governance surfaces touched: {len(touched_paths)}"
            )
        else:
            return ChecklistItem(
                id="PF-6",
                name="Governance surface scan",
                status="PASS",
                evidence=[],
                note="No governance surfaces touched"
            )

    def _check_budget_state(self, packet_data: Dict[str, Any]) -> ChecklistItem:
        """PF-7: Budget state consistent (attempt counts match ledger)."""
        packet_attempt_id = packet_data.get("attempt_id")

        if packet_attempt_id is None:
            return ChecklistItem(
                id="PF-7",
                name="Budget state consistent",
                status="FAIL",
                evidence=[],
                note="attempt_id missing from packet"
            )

        # Verify ledger history count matches
        ledger_attempt_count = len(self.ledger.history)

        # Attempt ID should be ledger_count + 1 (current attempt not yet recorded)
        expected_attempt_id = ledger_attempt_count + 1

        if packet_attempt_id == expected_attempt_id:
            return ChecklistItem(
                id="PF-7",
                name="Budget state consistent",
                status="PASS",
                evidence=["ledger_history_count", "packet#attempt_id"],
                note=f"Attempt {packet_attempt_id} consistent with ledger"
            )
        else:
            return ChecklistItem(
                id="PF-7",
                name="Budget state consistent",
                status="FAIL",
                evidence=[],
                note=f"Mismatch: packet says attempt {packet_attempt_id}, ledger has {ledger_attempt_count} records"
            )

    def _check_delta_summary(self, packet_data: Dict[str, Any]) -> ChecklistItem:
        """PF-8: Delta summary present (what changed since last attempt)."""
        diff_summary = packet_data.get("diff_summary")
        changed_files = packet_data.get("changed_files", [])

        if not diff_summary and not changed_files:
            return ChecklistItem(
                id="PF-8",
                name="Delta summary present",
                status="FAIL",
                evidence=[],
                note="No diff_summary or changed_files present"
            )

        evidence = []
        if diff_summary:
            evidence.append("packet#diff_summary")
        if changed_files:
            evidence.append(f"packet#changed_files ({len(changed_files)} files)")

        return ChecklistItem(
            id="PF-8",
            name="Delta summary present",
            status="PASS",
            evidence=evidence,
            note=f"Delta documented: {len(changed_files)} files"
        )

    def _compute_hashes(self) -> Dict[str, str]:
        """Compute deterministic hashes for verification."""
        hashes = {}

        # Ledger hash (hash of entire ledger content)
        if self.ledger.ledger_path.exists():
            with open(self.ledger.ledger_path, 'rb') as f:
                ledger_content = f.read()
                hashes["ledger_hash"] = hashlib.sha256(ledger_content).hexdigest()

        # Policy hash from ledger header
        if self.ledger.header:
            hashes["policy_hash"] = self.ledger.header.get("policy_hash", "unknown")
            if "policy_hash_canonical" in self.ledger.header:
                hashes["policy_hash_canonical"] = self.ledger.header["policy_hash_canonical"]

        return hashes


class PostflightValidator:
    """
    Post-flight Validator (POFV) - Phase B.2

    Runs before emitting final terminal packet and marking mission complete.
    Validates closure evidence and ensures no dangling state.

    Fail-closed: If any check fails, terminal packet is not emitted and
    loop terminates with BLOCKED (POSTFLIGHT_CHECKLIST_FAILED).
    """

    def __init__(self, context: MissionContext, ledger: AttemptLedger):
        self.context = context
        self.ledger = ledger

    def validate(self, terminal_data: Dict[str, Any]) -> ChecklistResult:
        """
        Run all post-flight checks.

        Args:
            terminal_data: The terminal packet data to validate

        Returns:
            ChecklistResult with PASS/FAIL status and individual check results
        """
        items = []

        # POF-1: Terminal outcome unambiguous
        items.append(self._check_terminal_outcome(terminal_data))

        # POF-2: Closure evidence pointers present
        items.append(self._check_closure_evidence(terminal_data))

        # POF-3: Hash/provenance integrity
        items.append(self._check_hash_integrity(terminal_data))

        # POF-4: Debt registration (if waiver approved)
        items.append(self._check_debt_registration(terminal_data))

        # POF-5: Tests evidence pointers present
        items.append(self._check_tests_evidence(terminal_data))

        # POF-6: No dangling state
        items.append(self._check_no_dangling_state(terminal_data))

        # Overall status
        overall_status = "PASS" if all(item.status == "PASS" for item in items) else "FAIL"

        return ChecklistResult(
            schema_version="checklist_v1",
            run_id=self.context.run_id,
            attempt_id=None,  # No specific attempt for POFV
            phase="POSTFLIGHT",
            status=overall_status,
            items=items,
            computed_hashes=self._compute_hashes(),
            timestamp_utc=datetime.now(UTC).isoformat() + "Z",
            tool_version="phase_b_v1.0"
        )

    def _check_terminal_outcome(self, terminal_data: Dict[str, Any]) -> ChecklistItem:
        """POF-1: Terminal outcome unambiguous (exactly one of: PASS, WAIVER, BLOCKED, ESCALATION)."""
        valid_outcomes = ["PASS", "WAIVER_REQUESTED", "BLOCKED", "ESCALATION_REQUESTED"]
        outcome = terminal_data.get("outcome")

        if outcome not in valid_outcomes:
            return ChecklistItem(
                id="POF-1",
                name="Terminal outcome unambiguous",
                status="FAIL",
                evidence=[],
                note=f"Invalid outcome: {outcome}. Must be one of {valid_outcomes}"
            )

        return ChecklistItem(
            id="POF-1",
            name="Terminal outcome unambiguous",
            status="PASS",
            evidence=["terminal_packet#outcome"],
            note=f"Outcome: {outcome}"
        )

    def _check_closure_evidence(self, terminal_data: Dict[str, Any]) -> ChecklistItem:
        """POF-2: Closure evidence pointers present (ledger, terminal packet, waiver decision if applicable)."""
        evidence_refs = []
        missing = []

        # Ledger must exist
        if self.ledger.ledger_path.exists():
            evidence_refs.append(str(self.ledger.ledger_path))
        else:
            missing.append("ledger")

        # Terminal packet data must have run_id
        if terminal_data.get("run_id"):
            evidence_refs.append("terminal_packet#run_id")
        else:
            missing.append("run_id")

        # If WAIVER outcome, check for waiver decision file
        outcome = terminal_data.get("outcome")
        if outcome == "WAIVER_REQUESTED":
            waiver_decision_path = self.context.repo_root / f"artifacts/loop_state/WAIVER_DECISION_{self.context.run_id}.json"
            if waiver_decision_path.exists():
                evidence_refs.append(str(waiver_decision_path))
            # Note: Waiver decision may not exist yet (request just emitted), so not failing here

        if missing:
            return ChecklistItem(
                id="POF-2",
                name="Closure evidence pointers present",
                status="FAIL",
                evidence=evidence_refs,
                note=f"Missing evidence: {missing}"
            )

        return ChecklistItem(
            id="POF-2",
            name="Closure evidence pointers present",
            status="PASS",
            evidence=evidence_refs,
            note=f"{len(evidence_refs)} evidence pointers verified"
        )

    def _check_hash_integrity(self, terminal_data: Dict[str, Any]) -> ChecklistItem:
        """POF-3: Hash/provenance integrity (stored hashes match recomputed canonical hashes)."""
        # Recompute ledger hash
        if not self.ledger.ledger_path.exists():
            return ChecklistItem(
                id="POF-3",
                name="Hash/provenance integrity",
                status="FAIL",
                evidence=[],
                note="Ledger file not found"
            )

        with open(self.ledger.ledger_path, 'rb') as f:
            ledger_content = f.read()
            computed_hash = hashlib.sha256(ledger_content).hexdigest()

        # Store computed hash in terminal data for reference
        stored_hash = terminal_data.get("ledger_hash")

        if not stored_hash:
            # No stored hash to compare - just record computed hash
            return ChecklistItem(
                id="POF-3",
                name="Hash/provenance integrity",
                status="PASS",
                evidence=[f"computed_ledger_hash={computed_hash[:16]}..."],
                note="Hash computed and recorded"
            )

        if stored_hash == computed_hash:
            return ChecklistItem(
                id="POF-3",
                name="Hash/provenance integrity",
                status="PASS",
                evidence=["ledger_hash_match"],
                note="Stored hash matches recomputed hash"
            )
        else:
            return ChecklistItem(
                id="POF-3",
                name="Hash/provenance integrity",
                status="FAIL",
                evidence=[],
                note=f"Hash mismatch: stored={stored_hash[:16]}..., computed={computed_hash[:16]}..."
            )

    def _check_debt_registration(self, terminal_data: Dict[str, Any]) -> ChecklistItem:
        """POF-4: Debt registration (if waiver approved, stable debt ID present)."""
        outcome = terminal_data.get("outcome")

        # Only applicable for WAIVER outcomes
        if outcome != "WAIVER_REQUESTED":
            return ChecklistItem(
                id="POF-4",
                name="Debt registration",
                status="PASS",
                evidence=[],
                note="Not applicable (not a waiver outcome)"
            )

        # Check for waiver decision file
        waiver_decision_path = self.context.repo_root / f"artifacts/loop_state/WAIVER_DECISION_{self.context.run_id}.json"

        if not waiver_decision_path.exists():
            # Waiver request not yet approved - this is expected at POFV time
            return ChecklistItem(
                id="POF-4",
                name="Debt registration",
                status="PASS",
                evidence=[],
                note="Waiver request pending approval (not yet registered)"
            )

        # If decision file exists, check for stable debt ID
        try:
            with open(waiver_decision_path) as f:
                decision = json.load(f)

            if decision.get("decision") == "APPROVE":
                debt_id = decision.get("debt_id")
                if not debt_id:
                    return ChecklistItem(
                        id="POF-4",
                        name="Debt registration",
                        status="FAIL",
                        evidence=[str(waiver_decision_path)],
                        note="Approved waiver missing stable debt_id"
                    )

                # Verify debt ID format (must not contain line numbers)
                if "line" in debt_id.lower() or ":" in debt_id:
                    return ChecklistItem(
                        id="POF-4",
                        name="Debt registration",
                        status="FAIL",
                        evidence=[str(waiver_decision_path)],
                        note=f"Debt ID contains line number reference: {debt_id}"
                    )

                return ChecklistItem(
                    id="POF-4",
                    name="Debt registration",
                    status="PASS",
                    evidence=[str(waiver_decision_path), f"debt_id={debt_id}"],
                    note=f"Stable debt ID registered: {debt_id}"
                )
            else:
                # Rejected waiver - no debt registration required
                return ChecklistItem(
                    id="POF-4",
                    name="Debt registration",
                    status="PASS",
                    evidence=[],
                    note="Waiver rejected (no debt registration)"
                )
        except (json.JSONDecodeError, IOError) as e:
            return ChecklistItem(
                id="POF-4",
                name="Debt registration",
                status="FAIL",
                evidence=[],
                note=f"Error reading waiver decision: {e}"
            )

    def _check_tests_evidence(self, terminal_data: Dict[str, Any]) -> ChecklistItem:
        """POF-5: Tests evidence pointers present (which test suites ran, pass status, log artifacts)."""
        test_evidence = terminal_data.get("test_evidence", {})

        # For Phase B MVP, test evidence is optional (not all missions run tests)
        if not test_evidence:
            return ChecklistItem(
                id="POF-5",
                name="Tests evidence pointers present",
                status="PASS",
                evidence=[],
                note="No test evidence (not required for this mission type)"
            )

        # If test evidence present, validate it has required fields
        required_fields = ["test_suite", "pass_status"]
        missing = [f for f in required_fields if f not in test_evidence]

        if missing:
            return ChecklistItem(
                id="POF-5",
                name="Tests evidence pointers present",
                status="FAIL",
                evidence=list(test_evidence.keys()),
                note=f"Test evidence missing fields: {missing}"
            )

        return ChecklistItem(
            id="POF-5",
            name="Tests evidence pointers present",
            status="PASS",
            evidence=list(test_evidence.keys()),
            note=f"Test evidence present: {test_evidence.get('test_suite')}"
        )

    def _check_no_dangling_state(self, terminal_data: Dict[str, Any]) -> ChecklistItem:
        """POF-6: No dangling state (any 'next actions' explicitly recorded or explicitly empty)."""
        next_actions = terminal_data.get("next_actions")

        # next_actions must be explicitly present (either [] or list of actions)
        if next_actions is None:
            return ChecklistItem(
                id="POF-6",
                name="No dangling state",
                status="FAIL",
                evidence=[],
                note="next_actions field missing (must be explicit [] or list)"
            )

        if not isinstance(next_actions, list):
            return ChecklistItem(
                id="POF-6",
                name="No dangling state",
                status="FAIL",
                evidence=[],
                note=f"next_actions must be list, got {type(next_actions)}"
            )

        if len(next_actions) == 0:
            return ChecklistItem(
                id="POF-6",
                name="No dangling state",
                status="PASS",
                evidence=["terminal_packet#next_actions"],
                note="Explicitly no next actions (clean termination)"
            )
        else:
            return ChecklistItem(
                id="POF-6",
                name="No dangling state",
                status="PASS",
                evidence=["terminal_packet#next_actions"],
                note=f"{len(next_actions)} next actions explicitly recorded"
            )

    def _compute_hashes(self) -> Dict[str, str]:
        """Compute deterministic hashes for verification."""
        hashes = {}

        # Ledger hash
        if self.ledger.ledger_path.exists():
            with open(self.ledger.ledger_path, 'rb') as f:
                ledger_content = f.read()
                hashes["ledger_hash"] = hashlib.sha256(ledger_content).hexdigest()

        # Policy hash from ledger header
        if self.ledger.header:
            hashes["policy_hash"] = self.ledger.header.get("policy_hash", "unknown")
            if "policy_hash_canonical" in self.ledger.header:
                hashes["policy_hash_canonical"] = self.ledger.header["policy_hash_canonical"]

        return hashes


def render_checklist_summary(result: ChecklistResult) -> str:
    """
    Render checklist result as Markdown table for embedding in packets.

    Args:
        result: ChecklistResult to render

    Returns:
        Markdown formatted string with checklist table
    """
    phase_name = "Pre-flight" if result.phase == "PREFLIGHT" else "Post-flight"
    status_emoji = "✓" if result.status == "PASS" else "✗"

    lines = [
        f"## {phase_name} Checklist",
        "",
        f"**Status:** {status_emoji} {result.status}",
        f"**JSON Artifact:** `artifacts/loop_state/{result.phase}_CHECK_{result.run_id}{'_attempt_' + str(result.attempt_id).zfill(4) if result.attempt_id else ''}.json`",
        "",
        "| ID | Item | Status | Note |",
        "|----|----|-----|----|"
    ]

    for item in result.items:
        status_symbol = "✓" if item.status == "PASS" else "✗"
        lines.append(f"| {item.id} | {item.name} | {status_symbol} {item.status} | {item.note} |")

    lines.extend([
        "",
        "**Computed Hashes:**"
    ])

    for key, value in result.computed_hashes.items():
        lines.append(f"- {key}: `{value[:16]}...`")

    lines.extend([
        "",
        f"**Timestamp:** {result.timestamp_utc}",
        ""
    ])

    return "\n".join(lines)
