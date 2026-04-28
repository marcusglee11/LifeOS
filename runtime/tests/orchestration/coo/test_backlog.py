"""Tests for COO structured backlog schema and CRUD functions."""

from __future__ import annotations

import subprocess as _subprocess
from pathlib import Path

import pytest
import yaml

from runtime.orchestration.coo.backlog import (
    BACKLOG_SCHEMA_VERSION,
    BacklogValidationError,
    TaskEntry,
    filter_actionable,
    load_backlog,
    mark_blocked,
    mark_completed,
    mark_in_progress,
    save_backlog,
)

MINIMAL_WMF_TASK = {
    "id": "WI-2026-001",
    "title": "WMF test item",
    "description": "A WMF test work item",
    "dod": "Tests pass",
    "priority": "P1",
    "risk": "low",
    "scope_paths": ["docs/"],
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
    "workstream": "mission_registry",
    "acceptance_criteria": ["Framework doc exists", "Validator passes"],
    "plan_mode": "none",
    "github_issue": 48,
}


def _find_repo_root() -> Path:
    result = _subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(Path(__file__).parent),
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return Path(__file__).resolve().parents[4]


REPO_ROOT = _find_repo_root()

MINIMAL_VALID_TASK = {
    "id": "T-001",
    "title": "Test task",
    "description": "A test task",
    "dod": "Tests pass",
    "priority": "P1",
    "risk": "low",
    "scope_paths": ["runtime/"],
    "status": "pending",
    "requires_approval": False,
    "decision_support_required": False,
    "owner": "codex",
    "evidence": "",
    "task_type": "build",
    "tags": ["test"],
    "objective_ref": "bootstrap",
    "created_at": "2026-03-05T00:00:00Z",
    "completed_at": None,
}


def _make_backlog_yaml(tasks: list[dict]) -> str:
    return yaml.dump(
        {"schema_version": BACKLOG_SCHEMA_VERSION, "tasks": tasks},
        default_flow_style=False,
        sort_keys=False,
    )


class TestLoadBacklog:
    def test_valid_single_task(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([MINIMAL_VALID_TASK]))
        tasks = load_backlog(path)
        assert len(tasks) == 1
        assert tasks[0].id == "T-001"
        assert tasks[0].priority == "P1"
        assert tasks[0].status == "pending"

    def test_empty_tasks_list(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([]))
        tasks = load_backlog(path)
        assert tasks == []

    def test_wrong_schema_version_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.yaml"
        path.write_text(yaml.dump({"schema_version": "backlog.v99", "tasks": [MINIMAL_VALID_TASK]}))
        with pytest.raises(BacklogValidationError, match="schema_version"):
            load_backlog(path)

    def test_invalid_priority_raises(self, tmp_path: Path) -> None:
        bad = {**MINIMAL_VALID_TASK, "priority": "HIGH"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([bad]))
        with pytest.raises(BacklogValidationError, match="priority"):
            load_backlog(path)

    def test_invalid_status_raises(self, tmp_path: Path) -> None:
        bad = {**MINIMAL_VALID_TASK, "status": "todo"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([bad]))
        with pytest.raises(BacklogValidationError, match="status"):
            load_backlog(path)

    def test_invalid_risk_raises(self, tmp_path: Path) -> None:
        bad = {**MINIMAL_VALID_TASK, "risk": "extreme"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([bad]))
        with pytest.raises(BacklogValidationError, match="risk"):
            load_backlog(path)

    def test_invalid_task_type_raises(self, tmp_path: Path) -> None:
        bad = {**MINIMAL_VALID_TASK, "task_type": "unknown"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([bad]))
        with pytest.raises(BacklogValidationError, match="task_type"):
            load_backlog(path)

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        bad = {k: v for k, v in MINIMAL_VALID_TASK.items() if k != "objective_ref"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([bad]))
        with pytest.raises(BacklogValidationError, match="objective_ref"):
            load_backlog(path)

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.yaml"
        path.write_text("schema_version: [\nunclosed")
        with pytest.raises(BacklogValidationError, match="Invalid YAML"):
            load_backlog(path)

    def test_non_mapping_root_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.yaml"
        path.write_text("- item1\n- item2\n")
        with pytest.raises(BacklogValidationError, match="mapping"):
            load_backlog(path)


class TestFilterActionable:
    def _make_task(self, task_id: str, status: str, priority: str) -> TaskEntry:
        return TaskEntry(
            id=task_id,
            title=f"Task {task_id}",
            description="",
            dod="",
            priority=priority,
            risk="low",
            scope_paths=[],
            status=status,
            requires_approval=False,
            owner="",
            evidence="",
            task_type="build",
            tags=[],
            objective_ref="bootstrap",
            created_at="2026-03-05T00:00:00Z",
            completed_at=None,
            decision_support_required=False,
        )

    def test_excludes_completed_and_blocked(self) -> None:
        tasks = [
            self._make_task("T-1", "pending", "P1"),
            self._make_task("T-2", "completed", "P0"),
            self._make_task("T-3", "in_progress", "P2"),
            self._make_task("T-4", "blocked", "P0"),
        ]
        result = filter_actionable(tasks)
        ids = [t.id for t in result]
        assert "T-1" in ids
        assert "T-3" in ids
        assert "T-2" not in ids
        assert "T-4" not in ids

    def test_sorted_p0_before_p3(self) -> None:
        tasks = [
            self._make_task("T-3", "pending", "P3"),
            self._make_task("T-0", "pending", "P0"),
            self._make_task("T-2", "pending", "P2"),
            self._make_task("T-1", "pending", "P1"),
        ]
        result = filter_actionable(tasks)
        priorities = [t.priority for t in result]
        assert priorities == ["P0", "P1", "P2", "P3"]

    def test_empty_input_returns_empty(self) -> None:
        assert filter_actionable([]) == []


class TestMarkCompleted:
    def _tasks(self) -> list[TaskEntry]:
        path = REPO_ROOT / "config" / "tasks" / "backlog.yaml"
        if path.exists():
            return load_backlog(path)
        return [
            TaskEntry(
                id="T-001",
                title="Task 1",
                description="",
                dod="",
                priority="P0",
                risk="low",
                scope_paths=[],
                status="pending",
                requires_approval=False,
                owner="",
                evidence="",
                task_type="build",
                tags=[],
                objective_ref="bootstrap",
                created_at="2026-03-05T00:00:00Z",
                completed_at=None,
                decision_support_required=False,
            )
        ]

    def test_marks_task_completed(self) -> None:
        tasks = self._tasks()
        original_id = tasks[0].id
        result = mark_completed(tasks, original_id, evidence="abc123")
        completed = next(t for t in result if t.id == original_id)
        assert completed.status == "completed"
        assert completed.evidence == "abc123"
        assert completed.completed_at is not None

    def test_does_not_mutate_original(self) -> None:
        tasks = self._tasks()
        original_id = tasks[0].id
        original_status = tasks[0].status
        mark_completed(tasks, original_id)
        assert tasks[0].status == original_status

    def test_unknown_task_id_raises(self) -> None:
        tasks = self._tasks()
        with pytest.raises(BacklogValidationError, match="not found"):
            mark_completed(tasks, "NONEXISTENT-999")

    def test_other_tasks_unchanged(self) -> None:
        tasks = self._tasks()
        if len(tasks) < 2:
            pytest.skip("Need at least 2 tasks")
        result = mark_completed(tasks, tasks[0].id)
        assert result[1].status == tasks[1].status


class TestSaveLoadRoundtrip:
    def test_roundtrip(self, tmp_path: Path) -> None:
        original = [
            TaskEntry(
                id="RT-001",
                title="Roundtrip task",
                description="Test description",
                dod="Tests pass",
                priority="P0",
                risk="high",
                scope_paths=["runtime/", "config/"],
                status="pending",
                requires_approval=True,
                owner="claude-code",
                evidence="",
                task_type="build",
                tags=["tag1", "tag2"],
                objective_ref="bootstrap",
                created_at="2026-03-05T12:00:00Z",
                completed_at=None,
                decision_support_required=True,
            )
        ]
        path = tmp_path / "backlog.yaml"
        save_backlog(path, original)
        loaded = load_backlog(path)
        assert len(loaded) == 1
        t = loaded[0]
        assert t.id == "RT-001"
        assert t.priority == "P0"
        assert t.risk == "high"
        assert t.scope_paths == ["runtime/", "config/"]
        assert t.requires_approval is True
        assert t.decision_support_required is True
        assert t.tags == ["tag1", "tag2"]
        assert t.completed_at is None


class TestIntegration:
    def test_canonical_backlog_yaml_loads(self) -> None:
        """The canonical config/tasks/backlog.yaml must load without error."""
        path = REPO_ROOT / "config" / "tasks" / "backlog.yaml"
        assert path.exists(), f"config/tasks/backlog.yaml not found at {path}"
        tasks = load_backlog(path)
        assert len(tasks) > 0, "Backlog must have at least one task"
        # Verify T-001 is present as the first bootstrap task
        ids = {t.id for t in tasks}
        assert "T-001" in ids, "T-001 (Step 1A) must be in seed backlog"


def _make_task(task_id: str, status: str = "pending") -> TaskEntry:
    return TaskEntry(
        id=task_id,
        title=f"Task {task_id}",
        description="",
        dod="",
        priority="P1",
        risk="low",
        scope_paths=[],
        status=status,
        requires_approval=False,
        owner="",
        evidence="",
        task_type="build",
        tags=[],
        objective_ref="bootstrap",
        created_at="2026-03-05T00:00:00Z",
        completed_at=None,
        decision_support_required=False,
    )


class TestMarkInProgress:
    def test_mark_in_progress_sets_status(self) -> None:
        tasks = [_make_task("T-010", "pending")]
        result = mark_in_progress(tasks, "T-010", evidence="dispatched ORD-T-010-001")
        assert result[0].status == "in_progress"
        assert result[0].evidence == "dispatched ORD-T-010-001"

    def test_mark_in_progress_does_not_mutate_original(self) -> None:
        tasks = [_make_task("T-010", "pending")]
        mark_in_progress(tasks, "T-010")
        assert tasks[0].status == "pending"

    def test_mark_in_progress_not_found(self) -> None:
        tasks = [_make_task("T-010", "pending")]
        with pytest.raises(BacklogValidationError, match="not found"):
            mark_in_progress(tasks, "NONEXISTENT-999")

    def test_mark_in_progress_preserves_other_tasks(self) -> None:
        tasks = [_make_task("T-010", "pending"), _make_task("T-011", "pending")]
        result = mark_in_progress(tasks, "T-010")
        assert result[1].status == "pending"
        assert result[1].id == "T-011"

    def test_mark_in_progress_sets_completed_at_none(self) -> None:
        tasks = [_make_task("T-010", "pending")]
        result = mark_in_progress(tasks, "T-010")
        assert result[0].completed_at is None

    def test_mark_in_progress_preserves_decision_support_required(self) -> None:
        tasks = [_make_task("T-010", "pending")]
        tasks[0].decision_support_required = True
        result = mark_in_progress(tasks, "T-010")
        assert result[0].decision_support_required is True


class TestMarkBlocked:
    def test_mark_blocked_sets_status_and_evidence(self) -> None:
        tasks = [_make_task("T-012", "in_progress")]
        result = mark_blocked(tasks, "T-012", evidence="CLEAN_FAIL: repo dirty (ORD-T-012-001)")
        assert result[0].status == "blocked"
        assert "CLEAN_FAIL" in result[0].evidence

    def test_mark_blocked_does_not_mutate_original(self) -> None:
        tasks = [_make_task("T-012", "in_progress")]
        mark_blocked(tasks, "T-012")
        assert tasks[0].status == "in_progress"

    def test_mark_blocked_not_found(self) -> None:
        tasks = [_make_task("T-012", "in_progress")]
        with pytest.raises(BacklogValidationError, match="not found"):
            mark_blocked(tasks, "NONEXISTENT-999")

    def test_mark_blocked_preserves_other_tasks(self) -> None:
        tasks = [_make_task("T-012", "in_progress"), _make_task("T-013", "pending")]
        result = mark_blocked(tasks, "T-012")
        assert result[1].status == "pending"
        assert result[1].id == "T-013"

    def test_mark_blocked_preserves_decision_support_required(self) -> None:
        tasks = [_make_task("T-012", "in_progress")]
        tasks[0].decision_support_required = True
        result = mark_blocked(tasks, "T-012")
        assert result[0].decision_support_required is True


class TestMarkCompletedDecisionSupport:
    def test_mark_completed_preserves_decision_support_required(self) -> None:
        tasks = [_make_task("T-014", "in_progress")]
        tasks[0].decision_support_required = True
        result = mark_completed(tasks, "T-014")
        assert result[0].decision_support_required is True


class TestWMFIdValidation:
    """WMF ID format is validated in backlog.py, not only in the standalone validator."""

    def test_valid_wmf_id_loads(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([MINIMAL_WMF_TASK]))
        tasks = load_backlog(path)
        assert tasks[0].id == "WI-2026-001"

    def test_wmf_short_year_raises(self, tmp_path: Path) -> None:
        bad = {**MINIMAL_WMF_TASK, "id": "WI-26-001"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([bad]))
        with pytest.raises(BacklogValidationError, match="WMF id format"):
            load_backlog(path)

    def test_wmf_short_sequence_raises(self, tmp_path: Path) -> None:
        bad = {**MINIMAL_WMF_TASK, "id": "WI-2026-01"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([bad]))
        with pytest.raises(BacklogValidationError, match="WMF id format"):
            load_backlog(path)

    def test_legacy_id_remains_valid(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([MINIMAL_VALID_TASK]))
        tasks = load_backlog(path)
        assert tasks[0].id == "T-001"


class TestWMFStatusRouting:
    """Status validation routes to WMF set for WI-* items, legacy set for T-* items."""

    def test_legacy_pending_passes(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([MINIMAL_VALID_TASK]))
        tasks = load_backlog(path)
        assert tasks[0].status == "pending"

    def test_legacy_wmf_status_raises(self, tmp_path: Path) -> None:
        bad = {**MINIMAL_VALID_TASK, "status": "READY"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([bad]))
        with pytest.raises(BacklogValidationError, match="status"):
            load_backlog(path)

    def test_wmf_ready_passes(self, tmp_path: Path) -> None:
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([MINIMAL_WMF_TASK]))
        tasks = load_backlog(path)
        assert tasks[0].status == "READY"

    def test_wmf_legacy_status_raises(self, tmp_path: Path) -> None:
        bad = {**MINIMAL_WMF_TASK, "status": "pending"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([bad]))
        with pytest.raises(BacklogValidationError, match="status"):
            load_backlog(path)

    def test_wmf_all_statuses_valid(self, tmp_path: Path) -> None:
        statuses = [
            "INTAKE",
            "TRIAGED",
            "READY",
            "DISPATCHED",
            "REVIEW",
            "CLOSED",
            "BLOCKED",
            "DEFERRED",
            "REJECTED",
            "DUPLICATE",
            "SUPERSEDED",
        ]
        for status in statuses:
            task = {**MINIMAL_WMF_TASK, "status": status}
            path = tmp_path / f"backlog_{status}.yaml"
            path.write_text(_make_backlog_yaml([task]))
            tasks = load_backlog(path)
            assert tasks[0].status == status


class TestGithubIssueCoercion:
    """github_issue field coercion: int accepted, string digits accepted, bad strings rejected."""

    def test_int_github_issue_loads(self, tmp_path: Path) -> None:
        task = {**MINIMAL_WMF_TASK, "github_issue": 48}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([task]))
        tasks = load_backlog(path)
        assert tasks[0].github_issue == 48

    def test_string_github_issue_coerced(self, tmp_path: Path) -> None:
        task = {**MINIMAL_WMF_TASK, "github_issue": "48"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([task]))
        tasks = load_backlog(path)
        assert tasks[0].github_issue == 48

    def test_invalid_github_issue_raises(self, tmp_path: Path) -> None:
        task = {**MINIMAL_WMF_TASK, "github_issue": "abc"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([task]))
        with pytest.raises(BacklogValidationError, match="github_issue"):
            load_backlog(path)

    def test_absent_github_issue_loads_as_none(self, tmp_path: Path) -> None:
        task = {k: v for k, v in MINIMAL_WMF_TASK.items() if k != "github_issue"}
        path = tmp_path / "backlog.yaml"
        path.write_text(_make_backlog_yaml([task]))
        tasks = load_backlog(path)
        assert tasks[0].github_issue is None


def _make_wmf_task_entry() -> TaskEntry:
    return TaskEntry(
        id="WI-2026-001",
        title="WMF test item",
        description="A WMF test work item",
        dod="Tests pass",
        priority="P1",
        risk="low",
        scope_paths=["docs/"],
        status="READY",
        requires_approval=False,
        owner="claude-code",
        evidence="",
        task_type="build",
        tags=["wmf"],
        objective_ref="work-management",
        created_at="2026-04-27T00:00:00Z",
        completed_at=None,
        decision_support_required=False,
        github_issue=48,
        workstream="mission_registry",
        acceptance_criteria=["Framework doc exists", "Validator passes"],
        plan_mode="none",
    )


class TestLegacyMarkHelpersRejectWMF:
    """mark_in_progress/blocked/completed must raise for WI-* items."""

    def test_mark_in_progress_rejects_wmf(self) -> None:
        tasks = [_make_wmf_task_entry()]
        with pytest.raises(BacklogValidationError, match="WMF item"):
            mark_in_progress(tasks, "WI-2026-001")

    def test_mark_blocked_rejects_wmf(self) -> None:
        tasks = [_make_wmf_task_entry()]
        with pytest.raises(BacklogValidationError, match="WMF item"):
            mark_blocked(tasks, "WI-2026-001")

    def test_mark_completed_rejects_wmf(self) -> None:
        tasks = [_make_wmf_task_entry()]
        with pytest.raises(BacklogValidationError, match="WMF item"):
            mark_completed(tasks, "WI-2026-001")

    def test_mark_in_progress_legacy_still_works(self) -> None:
        tasks = [_make_task("T-001", "pending")]
        result = mark_in_progress(tasks, "T-001")
        assert result[0].status == "in_progress"


class TestWMFRoundTrip:
    """WMF items with optional fields survive save_backlog → load_backlog without field loss."""

    def test_wmf_fields_preserved_on_roundtrip(self, tmp_path: Path) -> None:
        original = [
            TaskEntry(
                id="WI-2026-001",
                title="WMF roundtrip item",
                description="Round-trip test",
                dod="Fields preserved",
                priority="P0",
                risk="low",
                scope_paths=["docs/02_protocols/"],
                status="DISPATCHED",
                requires_approval=False,
                owner="claude-code",
                evidence="",
                task_type="build",
                tags=["wmf", "roundtrip"],
                objective_ref="work-management",
                created_at="2026-04-27T00:00:00Z",
                completed_at=None,
                decision_support_required=False,
                github_issue=48,
                workstream="mission_registry",
                acceptance_criteria=["Validator passes", "Framework doc exists"],
                acceptance_ref=None,
                plan_mode="plan_lite",
                plan_path=None,
                plan_followup_required=True,
                followup_backlog_item="WI-2026-002",
                closure_evidence=None,
            )
        ]
        path = tmp_path / "backlog.yaml"
        save_backlog(path, original)
        loaded = load_backlog(path)
        assert len(loaded) == 1
        t = loaded[0]
        assert t.id == "WI-2026-001"
        assert t.status == "DISPATCHED"
        assert t.github_issue == 48
        assert t.workstream == "mission_registry"
        assert t.acceptance_criteria == ["Validator passes", "Framework doc exists"]
        assert t.plan_mode == "plan_lite"
        assert t.plan_followup_required is True
        assert t.followup_backlog_item == "WI-2026-002"
        assert t.closure_evidence is None

    def test_legacy_task_unaffected_by_wmf_fields(self, tmp_path: Path) -> None:
        original = [_make_task("T-001", "pending")]
        path = tmp_path / "backlog.yaml"
        save_backlog(path, original)
        loaded = load_backlog(path)
        assert loaded[0].id == "T-001"
        assert loaded[0].github_issue is None
        assert loaded[0].workstream is None
        assert loaded[0].plan_mode is None
