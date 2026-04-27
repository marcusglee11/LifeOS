"""Tests for the WMF Phase 0 validator (scripts/validate_work_items.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parents[1]))
from scripts.validate_work_items import (  # noqa: E402
    WMFViolation,
    validate_backlog,
    validate_backlog_md_header,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

VALID_WORKSTREAMS_YAML = """\
mission_registry:
  component_human_name: "Mission Registry"
  status: CONFIRMED
  created_at: "2026-01-03"
  description: "Tier-3 mission registration interface"
reactive_layer:
  component_human_name: "Reactive Layer"
  status: CONFIRMED
  created_at: "2026-01-02"
  description: "Tier-3 reactive task layer"
build_handoff:
  component_human_name: "Build Handoff"
  status: CONFIRMED
  created_at: "2026-01-04"
  description: "Messaging and handoff architecture"
opencode_integration:
  component_human_name: "OpenCode Integration"
  status: PROVISIONAL
  created_at: "2026-01-02"
  description: "OpenCode API connectivity"
"""

BACKLOG_SCHEMA_VERSION = "backlog.v1"

# A fully valid WMF item (READY state).
VALID_WMF_ITEM: dict = {
    "id": "WI-2026-001",
    "title": "Implement WMF v0.1",
    "description": "Framework doc and validator",
    "dod": "Validator passes",
    "priority": "P1",
    "risk": "low",
    "scope_paths": ["docs/02_protocols/"],
    "status": "READY",
    "requires_approval": False,
    "decision_support_required": False,
    "owner": "claude-code",
    "evidence": "",
    "task_type": "build",
    "tags": ["wmf"],
    "objective_ref": "work-management",
    "created_at": "2026-04-27T00:00:00Z",
    "completed_at": None,
    "github_issue": 48,
    "workstream": "mission_registry",
    "acceptance_criteria": ["Framework doc exists", "Validator passes"],
    "plan_mode": "none",
}

# A legacy T-NNN item.
LEGACY_ITEM: dict = {
    "id": "T-001",
    "title": "Legacy task",
    "description": "",
    "dod": "",
    "priority": "P1",
    "risk": "low",
    "scope_paths": [],
    "status": "pending",
    "requires_approval": False,
    "decision_support_required": False,
    "owner": "",
    "evidence": "",
    "task_type": "build",
    "tags": [],
    "objective_ref": "bootstrap",
    "created_at": "2026-03-05T00:00:00Z",
    "completed_at": None,
}


def _write_backlog(tmp_path: Path, tasks: list) -> Path:
    path = tmp_path / "backlog.yaml"
    path.write_text(
        yaml.dump(
            {"schema_version": BACKLOG_SCHEMA_VERSION, "tasks": tasks},
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_workstreams(tmp_path: Path) -> Path:
    path = tmp_path / "workstreams.yaml"
    path.write_text(VALID_WORKSTREAMS_YAML, encoding="utf-8")
    return path


def _violation_fields(violations: list[WMFViolation]) -> list[str]:
    return [v.field for v in violations]


def _violation_item_ids(violations: list[WMFViolation]) -> list[str]:
    return [v.item_id for v in violations]


# ---------------------------------------------------------------------------
# ID detection and format validation
# ---------------------------------------------------------------------------


class TestIDDetection:
    def test_valid_wmf_id_is_checked(self, tmp_path: Path) -> None:
        backlog = _write_backlog(tmp_path, [VALID_WMF_ITEM])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert violations == []

    def test_malformed_wi_short_year_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "id": "WI-26-001"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any(v.item_id == "WI-26-001" and "id" in v.field for v in violations)

    def test_malformed_wi_short_sequence_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "id": "WI-2026-01"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any(v.item_id == "WI-2026-01" and "id" in v.field for v in violations)

    def test_legacy_t_id_is_skipped(self, tmp_path: Path) -> None:
        backlog = _write_backlog(tmp_path, [LEGACY_ITEM])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert violations == []

    def test_legacy_with_wmf_incompatible_fields_still_skipped(self, tmp_path: Path) -> None:
        item = {**LEGACY_ITEM, "plan_mode": "turbo", "workstream": "nonexistent"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert violations == []


# ---------------------------------------------------------------------------
# Unique ID check
# ---------------------------------------------------------------------------


class TestUniqueIDs:
    def test_duplicate_wi_ids_flagged(self, tmp_path: Path) -> None:
        backlog = _write_backlog(tmp_path, [VALID_WMF_ITEM, VALID_WMF_ITEM])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("duplicate" in v.message.lower() for v in violations)


# ---------------------------------------------------------------------------
# backlog.v1 compatibility checks
# ---------------------------------------------------------------------------


class TestBacklogV1Compat:
    def test_missing_risk_flagged(self, tmp_path: Path) -> None:
        item = {k: v for k, v in VALID_WMF_ITEM.items() if k != "risk"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("risk" in v.field for v in violations)

    def test_missing_task_type_flagged(self, tmp_path: Path) -> None:
        item = {k: v for k, v in VALID_WMF_ITEM.items() if k != "task_type"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("task_type" in v.field for v in violations)

    def test_missing_objective_ref_flagged(self, tmp_path: Path) -> None:
        item = {k: v for k, v in VALID_WMF_ITEM.items() if k != "objective_ref"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("objective_ref" in v.field for v in violations)

    def test_missing_created_at_flagged(self, tmp_path: Path) -> None:
        item = {k: v for k, v in VALID_WMF_ITEM.items() if k != "created_at"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("created_at" in v.field for v in violations)

    def test_scope_paths_not_list_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "scope_paths": "docs/"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("scope_paths" in v.field for v in violations)

    def test_tags_not_list_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "tags": "wmf"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("tags" in v.field for v in violations)

    def test_risk_medium_spelled_out_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "risk": "medium"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("risk" in v.field for v in violations)

    def test_task_type_research_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "task_type": "research"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("task_type" in v.field for v in violations)

    def test_fully_compatible_wi_item_passes(self, tmp_path: Path) -> None:
        backlog = _write_backlog(tmp_path, [VALID_WMF_ITEM])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert violations == []


# ---------------------------------------------------------------------------
# github_issue
# ---------------------------------------------------------------------------


class TestGithubIssue:
    def test_triaged_without_github_issue_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "status": "TRIAGED"}
        item.pop("github_issue", None)
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("github_issue" in v.field for v in violations)

    def test_triaged_with_github_issue_passes(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "status": "TRIAGED", "github_issue": 48}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("github_issue" in v.field for v in violations)

    def test_intake_without_github_issue_ok(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "status": "INTAKE"}
        item.pop("github_issue", None)
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("github_issue" in v.field for v in violations)


# ---------------------------------------------------------------------------
# workstream
# ---------------------------------------------------------------------------


class TestWorkstream:
    def test_missing_workstream_flagged(self, tmp_path: Path) -> None:
        item = {k: v for k, v in VALID_WMF_ITEM.items() if k != "workstream"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("workstream" in v.field and "required" in v.message for v in violations)

    def test_empty_workstream_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "workstream": ""}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("workstream" in v.field and "required" in v.message for v in violations)

    def test_unknown_workstream_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "workstream": "nonexistent_stream"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("workstream" in v.field and "not in" in v.message for v in violations)

    def test_known_workstream_passes(self, tmp_path: Path) -> None:
        backlog = _write_backlog(tmp_path, [VALID_WMF_ITEM])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("workstream" in v.field for v in violations)


# ---------------------------------------------------------------------------
# acceptance_criteria
# ---------------------------------------------------------------------------


class TestAcceptanceCriteria:
    def test_ready_without_ac_or_ar_flagged(self, tmp_path: Path) -> None:
        item = {
            k: v
            for k, v in VALID_WMF_ITEM.items()
            if k not in ("acceptance_criteria", "acceptance_ref")
        }
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("acceptance_criteria" in v.field for v in violations)

    def test_ready_with_empty_list_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "acceptance_criteria": []}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("acceptance_criteria" in v.field for v in violations)

    def test_ready_with_list_str_passes(self, tmp_path: Path) -> None:
        backlog = _write_backlog(tmp_path, [VALID_WMF_ITEM])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("acceptance_criteria" in v.field for v in violations)

    def test_ready_with_str_passes(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "acceptance_criteria": "Framework doc exists"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("acceptance_criteria" in v.field for v in violations)

    def test_ready_with_acceptance_ref_passes(self, tmp_path: Path) -> None:
        item = {k: v for k, v in VALID_WMF_ITEM.items() if k != "acceptance_criteria"}
        item["acceptance_ref"] = "docs/02_protocols/Work_Management_Framework_v0.1.md"
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("acceptance_criteria" in v.field for v in violations)


# ---------------------------------------------------------------------------
# plan_mode
# ---------------------------------------------------------------------------


class TestPlanMode:
    def test_missing_plan_mode_flagged(self, tmp_path: Path) -> None:
        item = {k: v for k, v in VALID_WMF_ITEM.items() if k != "plan_mode"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("plan_mode" in v.field for v in violations)

    def test_plan_mode_none_passes(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "plan_mode": "none"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("plan_mode" in v.field for v in violations)

    def test_plan_mode_plan_lite_passes(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "plan_mode": "plan_lite"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("plan_mode" in v.field for v in violations)

    def test_plan_mode_formal_passes_enum(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "plan_mode": "formal", "plan_path": "artifacts/plans/PLAN_WMF.md"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("plan_mode" in v.field for v in violations)

    def test_plan_mode_lite_invalid_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "plan_mode": "lite"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("plan_mode" in v.field and "not in" in v.message for v in violations)

    def test_formal_without_plan_path_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "plan_mode": "formal"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("plan_path" in v.field for v in violations)

    def test_formal_with_plan_path_passes(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "plan_mode": "formal", "plan_path": "artifacts/plans/PLAN_WMF.md"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("plan_path" in v.field for v in violations)

    def test_formal_p0_plan_followup_still_requires_plan_path(self, tmp_path: Path) -> None:
        """plan_mode=formal + P0 + plan_followup_required=true still needs plan_path."""
        item = {
            **VALID_WMF_ITEM,
            "plan_mode": "formal",
            "priority": "P0",
            "plan_followup_required": True,
        }
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("plan_path" in v.field for v in violations)

    def test_p0_expedited_dispatched_without_plan_path_passes(self, tmp_path: Path) -> None:
        """P0 expedited (plan_lite + plan_followup_required) can be DISPATCHED without plan_path."""
        item = {
            **VALID_WMF_ITEM,
            "status": "DISPATCHED",
            "priority": "P0",
            "plan_mode": "plan_lite",
            "plan_followup_required": True,
        }
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("plan_path" in v.field for v in violations)


# ---------------------------------------------------------------------------
# P0 expedited closure
# ---------------------------------------------------------------------------


class TestP0ExpeditedClosure:
    def _p0_expedited(self) -> dict:
        return {
            **VALID_WMF_ITEM,
            "priority": "P0",
            "plan_mode": "plan_lite",
            "plan_followup_required": True,
        }

    def test_p0_expedited_closed_without_followup_flagged(self, tmp_path: Path) -> None:
        item = {
            **self._p0_expedited(),
            "status": "CLOSED",
            "closure_evidence": [{"type": "commit", "ref": "abc123", "note": "done"}],
        }
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("followup_backlog_item" in v.field for v in violations)

    def test_p0_expedited_closed_with_followup_passes(self, tmp_path: Path) -> None:
        item = {
            **self._p0_expedited(),
            "status": "CLOSED",
            "followup_backlog_item": "WI-2026-002",
            "closure_evidence": [{"type": "commit", "ref": "abc123", "note": "done"}],
        }
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("followup_backlog_item" in v.field for v in violations)


# ---------------------------------------------------------------------------
# Closure evidence
# ---------------------------------------------------------------------------


class TestClosureEvidence:
    def _closed_item(self) -> dict:
        return {
            **VALID_WMF_ITEM,
            "status": "CLOSED",
            "closure_evidence": [{"type": "commit", "ref": "abc123", "note": "done"}],
        }

    def test_closed_without_closure_evidence_flagged(self, tmp_path: Path) -> None:
        item = {**VALID_WMF_ITEM, "status": "CLOSED"}
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("closure_evidence" in v.field for v in violations)

    def test_closed_with_closure_evidence_missing_note_flagged(self, tmp_path: Path) -> None:
        item = {
            **VALID_WMF_ITEM,
            "status": "CLOSED",
            "closure_evidence": [{"type": "commit", "ref": "abc123"}],
        }
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert any("note" in v.field for v in violations)

    def test_closed_with_valid_closure_evidence_passes(self, tmp_path: Path) -> None:
        item = self._closed_item()
        backlog = _write_backlog(tmp_path, [item])
        ws = _write_workstreams(tmp_path)
        violations = validate_backlog(backlog, ws)
        assert not any("closure_evidence" in v.field for v in violations)


# ---------------------------------------------------------------------------
# BACKLOG.md header check
# ---------------------------------------------------------------------------


class TestBacklogMdHeader:
    def test_without_derived_header_flagged(self, tmp_path: Path) -> None:
        md = tmp_path / "BACKLOG.md"
        md.write_text("# BACKLOG\n\nSome content.\n", encoding="utf-8")
        violations = validate_backlog_md_header(md)
        assert any("header" in v.field for v in violations)

    def test_with_derived_header_passes(self, tmp_path: Path) -> None:
        md = tmp_path / "BACKLOG.md"
        md.write_text(
            "# BACKLOG\n<!-- DERIVED VIEW: canonical is backlog.yaml -->\n\nContent.\n",
            encoding="utf-8",
        )
        violations = validate_backlog_md_header(md)
        assert violations == []

    def test_missing_file_returns_no_violations(self, tmp_path: Path) -> None:
        md = tmp_path / "NONEXISTENT_BACKLOG.md"
        violations = validate_backlog_md_header(md)
        assert violations == []


# ---------------------------------------------------------------------------
# Real-repo smoke test
# ---------------------------------------------------------------------------


class TestRealRepo:
    def test_validator_passes_on_real_repo(self) -> None:
        """Run validator against canonical repo files. No WI items → 0 violations."""
        import subprocess

        result = subprocess.run(
            [sys.executable, "scripts/validate_work_items.py"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(Path(__file__).parents[1]),
        )
        assert result.returncode == 0, (
            f"Validator returned exit {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "0 violations" in result.stdout
