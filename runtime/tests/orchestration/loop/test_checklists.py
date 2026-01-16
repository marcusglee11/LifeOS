"""
Unit tests for Pre-flight and Post-flight Validators (Phase B.2)

Tests PPV/POFV checklist validation logic with pass/fail scenarios.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock

from runtime.orchestration.loop.checklists import (
    PreflightValidator,
    PostflightValidator,
    ChecklistResult,
    ChecklistItem,
    render_checklist_summary
)
from runtime.orchestration.loop.ledger import AttemptLedger, LedgerHeader
from runtime.orchestration.missions.base import MissionContext


@pytest.fixture
def mock_context(tmp_path):
    """Create mock MissionContext."""
    return MissionContext(
        repo_root=tmp_path,
        baseline_commit="abc123",
        run_id="test_run_001",
        operation_executor=None
    )


@pytest.fixture
def mock_ledger(tmp_path):
    """Create mock ledger with initialized header."""
    ledger_path = tmp_path / "artifacts" / "loop_state" / "attempt_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    ledger = AttemptLedger(ledger_path)
    ledger.initialize(LedgerHeader(
        policy_hash="test_policy_hash",
        policy_hash_canonical="canonical_hash_123",
        handoff_hash="handoff_123",
        run_id="test_run_001"
    ))

    return ledger


class TestPreflightValidatorBasics:
    """Test basic PPV initialization and simple validations."""

    def test_ppv_initialization(self, mock_context, mock_ledger):
        """PPV initializes with context and ledger."""
        ppv = PreflightValidator(mock_context, mock_ledger)
        assert ppv.context == mock_context
        assert ppv.ledger == mock_ledger

    def test_valid_packet_passes_all_checks(self, mock_context, mock_ledger):
        """Valid packet with all required fields passes PPV."""
        packet = {
            "schema_version": "v1.0",
            "run_id": "test_run_001",
            "attempt_id": 1,
            "evidence": {
                "ledger": "artifacts/loop_state/attempt_ledger.jsonl",
                "diff": "artifacts/diff_001.txt"
            },
            "reproduction_steps": "Run pytest to reproduce",
            "failure_class": None,  # Success case
            "diff_summary": "Modified runtime/foo.py",
            "changed_files": ["runtime/foo.py"]
        }

        ppv = PreflightValidator(mock_context, mock_ledger)
        result = ppv.validate(packet, attempt_id=1)

        assert result.status == "PASS"
        assert result.phase == "PREFLIGHT"
        assert result.run_id == "test_run_001"
        assert result.attempt_id == 1
        assert len(result.items) == 8  # 8 PF checks


class TestPreflightPF1Schema:
    """Test PF-1: Schema pass."""

    def test_pf1_pass_with_required_sections(self, mock_context, mock_ledger):
        """Packet with all required sections passes PF-1."""
        packet = {
            "schema_version": "v1.0",
            "run_id": "test_run",
            "attempt_id": 1
        }

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_schema(packet)

        assert item.status == "PASS"
        assert "v1.0" in item.note

    def test_pf1_fail_missing_schema_version(self, mock_context, mock_ledger):
        """Packet missing schema_version fails PF-1."""
        packet = {
            "run_id": "test_run",
            "attempt_id": 1
        }

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_schema(packet)

        assert item.status == "FAIL"
        assert "schema_version" in item.note

    def test_pf1_fail_missing_multiple_sections(self, mock_context, mock_ledger):
        """Packet missing multiple sections fails PF-1."""
        packet = {}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_schema(packet)

        assert item.status == "FAIL"
        assert "schema_version" in item.note
        assert "run_id" in item.note


class TestPreflightPF2Evidence:
    """Test PF-2: Evidence pointers present."""

    def test_pf2_pass_with_evidence(self, mock_context, mock_ledger):
        """Packet with evidence section passes PF-2."""
        packet = {
            "evidence": {
                "ledger": "artifacts/ledger.jsonl",
                "diff": "artifacts/diff.txt",
                "review": "artifacts/review.md"
            }
        }

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_evidence_pointers(packet)

        assert item.status == "PASS"
        assert "3 evidence refs" in item.note

    def test_pf2_fail_no_evidence_section(self, mock_context, mock_ledger):
        """Packet without evidence section fails PF-2."""
        packet = {}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_evidence_pointers(packet)

        assert item.status == "FAIL"
        assert "No evidence section" in item.note

    def test_pf2_fail_empty_evidence(self, mock_context, mock_ledger):
        """Packet with empty evidence dict fails PF-2."""
        packet = {"evidence": {}}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_evidence_pointers(packet)

        assert item.status == "FAIL"
        assert "empty" in item.note.lower()


class TestPreflightPF3DeterminismAnchors:
    """Test PF-3: Determinism anchors present."""

    def test_pf3_pass_with_all_anchors(self, mock_context, mock_ledger):
        """Packet with run_id and ledger with policy_hash passes PF-3."""
        packet = {"run_id": "test_run_001"}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_determinism_anchors(packet)

        assert item.status == "PASS"
        assert "anchors present" in item.note

    def test_pf3_fail_missing_run_id(self, mock_context, mock_ledger):
        """Packet missing run_id fails PF-3."""
        packet = {}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_determinism_anchors(packet)

        assert item.status == "FAIL"
        assert "run_id" in item.note


class TestPreflightPF4ReproSteps:
    """Test PF-4: Reproduction steps present."""

    def test_pf4_pass_with_repro_steps(self, mock_context, mock_ledger):
        """Packet with reproduction_steps passes PF-4."""
        packet = {"reproduction_steps": "Run pytest -v"}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_repro_steps(packet)

        assert item.status == "PASS"

    def test_pf4_pass_with_explicit_non_reproducible(self, mock_context, mock_ledger):
        """Packet with non_reproducible_reason passes PF-4."""
        packet = {"non_reproducible_reason": "Intermittent network issue"}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_repro_steps(packet)

        assert item.status == "PASS"
        assert "non-reproducible" in item.note.lower()

    def test_pf4_fail_no_repro_info(self, mock_context, mock_ledger):
        """Packet without repro steps or non-repro marker fails PF-4."""
        packet = {}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_repro_steps(packet)

        assert item.status == "FAIL"

    def test_pf4_fail_empty_repro_steps(self, mock_context, mock_ledger):
        """Packet with empty reproduction_steps fails PF-4."""
        packet = {"reproduction_steps": ""}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_repro_steps(packet)

        assert item.status == "FAIL"


class TestPreflightPF5TaxonomyClassification:
    """Test PF-5: Taxonomy classification valid."""

    def test_pf5_pass_valid_failure_class(self, mock_context, mock_ledger):
        """Packet with valid failure_class passes PF-5."""
        packet = {"failure_class": "test_failure"}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_taxonomy_classification(packet)

        assert item.status == "PASS"

    def test_pf5_pass_no_failure_class_success_case(self, mock_context, mock_ledger):
        """Packet with no failure_class (success) passes PF-5."""
        packet = {"failure_class": None}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_taxonomy_classification(packet)

        assert item.status == "PASS"
        assert "success case" in item.note.lower()

    def test_pf5_fail_invalid_failure_class(self, mock_context, mock_ledger):
        """Packet with invalid failure_class fails PF-5."""
        packet = {"failure_class": "invalid_unknown_class"}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_taxonomy_classification(packet)

        assert item.status == "FAIL"
        assert "Invalid" in item.note


class TestPreflightPF6GovernanceSurface:
    """Test PF-6: Governance surface scan."""

    def test_pf6_pass_governance_paths_detected(self, mock_context, mock_ledger):
        """Packet with governance paths in diff_summary passes PF-6 with evidence."""
        packet = {
            "diff_summary": "Modified docs/01_governance/Constitution.md and runtime/foo.py"
        }

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_governance_surface(packet)

        assert item.status == "PASS"
        assert "docs/01_governance/" in item.evidence

    def test_pf6_pass_no_governance_paths(self, mock_context, mock_ledger):
        """Packet with no governance paths passes PF-6."""
        packet = {
            "diff_summary": "Modified runtime/foo.py"
        }

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_governance_surface(packet)

        assert item.status == "PASS"
        assert "No governance surfaces" in item.note


class TestPreflightPF7BudgetState:
    """Test PF-7: Budget state consistent."""

    def test_pf7_pass_attempt_id_matches_ledger(self, mock_context, mock_ledger):
        """Packet attempt_id matches ledger count passes PF-7."""
        # Ledger is empty (0 attempts recorded), so next attempt should be 1
        packet = {"attempt_id": 1}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_budget_state(packet)

        assert item.status == "PASS"

    def test_pf7_fail_missing_attempt_id(self, mock_context, mock_ledger):
        """Packet missing attempt_id fails PF-7."""
        packet = {}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_budget_state(packet)

        assert item.status == "FAIL"

    def test_pf7_fail_attempt_id_mismatch(self, mock_context, mock_ledger):
        """Packet with wrong attempt_id fails PF-7."""
        # Ledger is empty, so attempt_id should be 1, not 5
        packet = {"attempt_id": 5}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_budget_state(packet)

        assert item.status == "FAIL"
        assert "Mismatch" in item.note


class TestPreflightPF8DeltaSummary:
    """Test PF-8: Delta summary present."""

    def test_pf8_pass_with_diff_summary(self, mock_context, mock_ledger):
        """Packet with diff_summary passes PF-8."""
        packet = {"diff_summary": "Modified 3 files"}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_delta_summary(packet)

        assert item.status == "PASS"

    def test_pf8_pass_with_changed_files(self, mock_context, mock_ledger):
        """Packet with changed_files passes PF-8."""
        packet = {"changed_files": ["runtime/foo.py", "runtime/bar.py"]}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_delta_summary(packet)

        assert item.status == "PASS"
        assert "2 files" in item.note

    def test_pf8_fail_no_delta_info(self, mock_context, mock_ledger):
        """Packet without diff_summary or changed_files fails PF-8."""
        packet = {}

        ppv = PreflightValidator(mock_context, mock_ledger)
        item = ppv._check_delta_summary(packet)

        assert item.status == "FAIL"


class TestPostflightValidatorBasics:
    """Test basic POFV initialization and simple validations."""

    def test_pofv_initialization(self, mock_context, mock_ledger):
        """POFV initializes with context and ledger."""
        pofv = PostflightValidator(mock_context, mock_ledger)
        assert pofv.context == mock_context
        assert pofv.ledger == mock_ledger

    def test_valid_terminal_passes_all_checks(self, mock_context, mock_ledger):
        """Valid terminal data passes all POFV checks."""
        terminal_data = {
            "outcome": "PASS",
            "reason": "pass",
            "run_id": "test_run_001",
            "next_actions": []
        }

        pofv = PostflightValidator(mock_context, mock_ledger)
        result = pofv.validate(terminal_data)

        assert result.status == "PASS"
        assert result.phase == "POSTFLIGHT"
        assert result.run_id == "test_run_001"
        assert result.attempt_id is None  # No specific attempt
        assert len(result.items) == 6  # 6 POF checks


class TestPostflightPOF1TerminalOutcome:
    """Test POF-1: Terminal outcome unambiguous."""

    def test_pof1_pass_valid_pass_outcome(self, mock_context, mock_ledger):
        """Terminal with PASS outcome passes POF-1."""
        terminal_data = {"outcome": "PASS"}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_terminal_outcome(terminal_data)

        assert item.status == "PASS"
        assert "PASS" in item.note

    def test_pof1_pass_valid_waiver_outcome(self, mock_context, mock_ledger):
        """Terminal with WAIVER_REQUESTED outcome passes POF-1."""
        terminal_data = {"outcome": "WAIVER_REQUESTED"}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_terminal_outcome(terminal_data)

        assert item.status == "PASS"

    def test_pof1_fail_invalid_outcome(self, mock_context, mock_ledger):
        """Terminal with invalid outcome fails POF-1."""
        terminal_data = {"outcome": "INVALID_OUTCOME"}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_terminal_outcome(terminal_data)

        assert item.status == "FAIL"
        assert "Invalid outcome" in item.note


class TestPostflightPOF2ClosureEvidence:
    """Test POF-2: Closure evidence pointers present."""

    def test_pof2_pass_with_ledger_and_run_id(self, mock_context, mock_ledger):
        """Terminal with ledger file and run_id passes POF-2."""
        terminal_data = {"run_id": "test_run_001"}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_closure_evidence(terminal_data)

        assert item.status == "PASS"
        assert len(item.evidence) >= 2  # Ledger path + run_id

    def test_pof2_fail_missing_run_id(self, mock_context, mock_ledger):
        """Terminal missing run_id fails POF-2."""
        terminal_data = {}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_closure_evidence(terminal_data)

        assert item.status == "FAIL"
        assert "run_id" in item.note


class TestPostflightPOF3HashIntegrity:
    """Test POF-3: Hash/provenance integrity."""

    def test_pof3_pass_hash_computed(self, mock_context, mock_ledger):
        """Terminal with ledger file passes POF-3 with computed hash."""
        terminal_data = {}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_hash_integrity(terminal_data)

        assert item.status == "PASS"
        assert "Hash computed" in item.note


class TestPostflightPOF4DebtRegistration:
    """Test POF-4: Debt registration (if waiver approved)."""

    def test_pof4_pass_not_waiver_outcome(self, mock_context, mock_ledger):
        """Terminal with non-waiver outcome passes POF-4 as N/A."""
        terminal_data = {"outcome": "PASS"}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_debt_registration(terminal_data)

        assert item.status == "PASS"
        assert "Not applicable" in item.note

    def test_pof4_pass_waiver_pending(self, mock_context, mock_ledger):
        """Terminal with WAIVER_REQUESTED but no decision yet passes POF-4."""
        terminal_data = {"outcome": "WAIVER_REQUESTED"}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_debt_registration(terminal_data)

        assert item.status == "PASS"
        assert "pending" in item.note.lower()

    def test_pof4_fail_approved_waiver_missing_debt_id(self, mock_context, tmp_path):
        """Approved waiver without debt_id fails POF-4."""
        # Create waiver decision file without debt_id
        decision_path = tmp_path / "artifacts/loop_state/WAIVER_DECISION_test_run_001.json"
        decision_path.parent.mkdir(parents=True, exist_ok=True)

        with open(decision_path, 'w') as f:
            json.dump({"decision": "APPROVE"}, f)

        ledger_path = tmp_path / "artifacts/loop_state/attempt_ledger.jsonl"
        ledger = AttemptLedger(ledger_path)
        ledger.initialize(LedgerHeader(
            policy_hash="test", handoff_hash="test", run_id="test_run_001"
        ))

        context = MissionContext(
            repo_root=tmp_path,
            baseline_commit="abc",
            run_id="test_run_001",
            operation_executor=None
        )

        terminal_data = {"outcome": "WAIVER_REQUESTED"}

        pofv = PostflightValidator(context, ledger)
        item = pofv._check_debt_registration(terminal_data)

        assert item.status == "FAIL"
        assert "missing stable debt_id" in item.note

    def test_pof4_fail_debt_id_with_line_number(self, mock_context, tmp_path):
        """Approved waiver with line-number debt_id fails POF-4."""
        decision_path = tmp_path / "artifacts/loop_state/WAIVER_DECISION_test_run_001.json"
        decision_path.parent.mkdir(parents=True, exist_ok=True)

        with open(decision_path, 'w') as f:
            json.dump({
                "decision": "APPROVE",
                "debt_id": "BACKLOG:line:123"  # Contains line number - INVALID
            }, f)

        ledger_path = tmp_path / "artifacts/loop_state/attempt_ledger.jsonl"
        ledger = AttemptLedger(ledger_path)
        ledger.initialize(LedgerHeader(
            policy_hash="test", handoff_hash="test", run_id="test_run_001"
        ))

        context = MissionContext(
            repo_root=tmp_path,
            baseline_commit="abc",
            run_id="test_run_001",
            operation_executor=None
        )

        terminal_data = {"outcome": "WAIVER_REQUESTED"}

        pofv = PostflightValidator(context, ledger)
        item = pofv._check_debt_registration(terminal_data)

        assert item.status == "FAIL"
        assert "line number reference" in item.note


class TestPostflightPOF5TestsEvidence:
    """Test POF-5: Tests evidence pointers present."""

    def test_pof5_pass_no_test_evidence_optional(self, mock_context, mock_ledger):
        """Terminal without test_evidence passes POF-5 (optional)."""
        terminal_data = {}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_tests_evidence(terminal_data)

        assert item.status == "PASS"
        assert "not required" in item.note.lower()

    def test_pof5_pass_with_test_evidence(self, mock_context, mock_ledger):
        """Terminal with complete test_evidence passes POF-5."""
        terminal_data = {
            "test_evidence": {
                "test_suite": "pytest",
                "pass_status": "all_pass",
                "log_path": "artifacts/test_log.txt"
            }
        }

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_tests_evidence(terminal_data)

        assert item.status == "PASS"

    def test_pof5_fail_incomplete_test_evidence(self, mock_context, mock_ledger):
        """Terminal with incomplete test_evidence fails POF-5."""
        terminal_data = {
            "test_evidence": {
                "test_suite": "pytest"
                # Missing pass_status
            }
        }

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_tests_evidence(terminal_data)

        assert item.status == "FAIL"
        assert "pass_status" in item.note


class TestPostflightPOF6NoDanglingState:
    """Test POF-6: No dangling state."""

    def test_pof6_pass_empty_next_actions(self, mock_context, mock_ledger):
        """Terminal with explicit empty next_actions passes POF-6."""
        terminal_data = {"next_actions": []}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_no_dangling_state(terminal_data)

        assert item.status == "PASS"
        assert "no next actions" in item.note.lower()

    def test_pof6_pass_with_next_actions(self, mock_context, mock_ledger):
        """Terminal with explicit next_actions list passes POF-6."""
        terminal_data = {
            "next_actions": ["Review debt backlog", "Update documentation"]
        }

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_no_dangling_state(terminal_data)

        assert item.status == "PASS"
        assert "2 next actions" in item.note

    def test_pof6_fail_missing_next_actions(self, mock_context, mock_ledger):
        """Terminal without next_actions field fails POF-6."""
        terminal_data = {}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_no_dangling_state(terminal_data)

        assert item.status == "FAIL"
        assert "missing" in item.note.lower()

    def test_pof6_fail_wrong_type_next_actions(self, mock_context, mock_ledger):
        """Terminal with non-list next_actions fails POF-6."""
        terminal_data = {"next_actions": "some string"}

        pofv = PostflightValidator(mock_context, mock_ledger)
        item = pofv._check_no_dangling_state(terminal_data)

        assert item.status == "FAIL"
        assert "must be list" in item.note


class TestChecklistRendering:
    """Test checklist result rendering."""

    def test_render_preflight_pass(self, mock_context, mock_ledger):
        """Render PASS preflight checklist as Markdown."""
        packet = {
            "schema_version": "v1.0",
            "run_id": "test_run_001",
            "attempt_id": 1,
            "evidence": {"ledger": "test"},
            "reproduction_steps": "pytest",
            "diff_summary": "Modified foo.py",
            "changed_files": ["foo.py"]
        }

        ppv = PreflightValidator(mock_context, mock_ledger)
        result = ppv.validate(packet, attempt_id=1)

        markdown = render_checklist_summary(result)

        assert "## Pre-flight Checklist" in markdown
        assert "✓ PASS" in markdown
        assert "| PF-1 |" in markdown
        assert "**Computed Hashes:**" in markdown

    def test_render_postflight_fail(self, mock_context, mock_ledger):
        """Render FAIL postflight checklist as Markdown."""
        terminal_data = {"outcome": "INVALID"}  # Will fail POF-1

        pofv = PostflightValidator(mock_context, mock_ledger)
        result = pofv.validate(terminal_data)

        markdown = render_checklist_summary(result)

        assert "## Post-flight Checklist" in markdown
        assert "✗ FAIL" in markdown
        assert "| POF-1 |" in markdown
