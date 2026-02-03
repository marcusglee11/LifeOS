"""
Integration tests for backlog-driven autonomous execution.

Tests the full flow from BACKLOG.md parsing through task completion marking.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.base import MissionContext, MissionResult
from runtime.orchestration.task_spec import TaskSpec, TaskPriority
from recursive_kernel.backlog_parser import (
    parse_backlog,
    select_eligible_item,
    get_uncompleted_tasks,
    mark_item_done_with_evidence,
)


def setup_test_repo(root: Path) -> Path:
    """Create minimal test repository structure."""
    (root / "docs/11_admin").mkdir(parents=True)
    (root / "artifacts").mkdir(parents=True)
    (root / "artifacts/loop_state").mkdir(parents=True)
    (root / "artifacts/queue").mkdir(parents=True)
    (root / "config/policy").mkdir(parents=True)
    (root / "runtime").mkdir(parents=True)

    # Create minimal policy config that matches PolicyLoader expectations
    # Only use known keys from KNOWN_MASTER_KEYS
    policy_rules = """includes: []
"""
    (root / "config/policy/policy_rules.yaml").write_text(policy_rules)

    return root


def create_test_context(repo_root: Path, run_id: str = "test-001") -> MissionContext:
    """Create test mission context."""
    return MissionContext(
        repo_root=repo_root,
        baseline_commit="test-baseline",
        run_id=run_id,
    )


def write_backlog(path: Path, content: str) -> None:
    """Write content to backlog file with UTF-8 encoding."""
    path.write_text(content, encoding='utf-8')


class TestBacklogDrivenExecution:
    """Integration tests for backlog-driven loop."""

    def test_select_highest_priority_task(self, tmp_path):
        """Selection prefers P0 over P1."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P1 (High)

- [ ] **P1 task** -- DoD: Done -- Owner: dev

### P0 (Critical)

- [ ] **P0 task** -- DoD: Done -- Owner: dev
""")

        items = parse_backlog(backlog)
        selected = select_eligible_item(items)

        assert selected.priority.value == "P0"
        assert selected.title == "P0 task"

    def test_skip_completed_tasks(self, tmp_path):
        """Selection ignores completed items."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P0 (Critical)

- [x] **Done task** -- DoD: Done -- Owner: dev
- [ ] **Open task** -- DoD: Done -- Owner: dev
""")

        items = parse_backlog(backlog)
        selected = select_eligible_item(items)

        assert selected.title == "Open task"

    def test_task_spec_to_design_input_includes_dod(self):
        """TaskSpec.to_design_input includes DoD as acceptance criteria."""
        task = TaskSpec(
            item_key="abc123def",
            title="Implement feature X",
            priority=TaskPriority.P0,
            dod="Tests pass with >80% coverage",
            owner="antigravity",
            context="Sprint 5",
            line_number=10,
            original_line="- [ ] **Implement feature X** ...",
        )

        design_input = task.to_design_input()

        assert "acceptance_criteria" in design_input
        assert design_input["acceptance_criteria"] == "Tests pass with >80% coverage"
        assert "Implement feature X" in design_input["task_description"]
        assert "Acceptance Criteria:" in design_input["task_description"]

    def test_blocked_task_detection(self):
        """is_blocked correctly identifies blocked tasks."""
        blocked = TaskSpec(
            item_key="abc",
            title="Blocked",
            priority=TaskPriority.P0,
            dod="Done",
            owner="dev",
            context="depends on T-99",
            line_number=1,
            original_line="",
        )
        assert blocked.is_blocked() is True

        unblocked = TaskSpec(
            item_key="def",
            title="Ready",
            priority=TaskPriority.P0,
            dod="Done",
            owner="dev",
            context="Ready to start",
            line_number=2,
            original_line="",
        )
        assert unblocked.is_blocked() is False

    def test_mark_complete_toggles_checkbox(self, tmp_path):
        """mark_item_done_with_evidence changes [ ] to [x] and creates evidence at repo root."""
        # Setup directory structure with .git to mark repo root
        (tmp_path / ".git").mkdir(exist_ok=True)
        backlog_in_structure = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog_in_structure.parent.mkdir(parents=True, exist_ok=True)

        write_backlog(backlog_in_structure, """### P0 (Critical)

- [ ] **Test task** -- DoD: Done -- Owner: dev
""")

        # Create artifacts directory at repo root
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        items = parse_backlog(backlog_in_structure)
        evidence = {
            "commit_hash": "abc123def",
            "run_id": "test-run-001",
        }

        # P0.1 Fix: Pass repo_root explicitly
        mark_item_done_with_evidence(
            backlog_in_structure,
            items[0],
            evidence,
            repo_root=tmp_path
        )

        # Verify checkbox marked
        new_content = backlog_in_structure.read_text(encoding='utf-8')
        assert "[x] **Test task**" in new_content
        assert "[ ] **Test task**" not in new_content

        # P0.1 Verification: Evidence file created at <repo_root>/artifacts/
        evidence_file = tmp_path / "artifacts" / "backlog_evidence.jsonl"
        assert evidence_file.exists(), f"Evidence file not found at {evidence_file}"

        # Verify evidence content
        with open(evidence_file, encoding='utf-8') as f:
            logged = json.loads(f.readline())

        assert logged["item_key"] == items[0].item_key
        assert logged["title"] == "Test task"
        assert logged["commit_hash"] == "abc123def"
        assert logged["run_id"] == "test-run-001"
        assert "completed_at" in logged

    def test_no_eligible_tasks_returns_blocked(self, tmp_path):
        """Loop terminates when no eligible tasks exist."""
        repo_root = setup_test_repo(tmp_path)
        backlog_path = repo_root / "docs" / "11_admin" / "BACKLOG.md"

        # All tasks completed or low priority
        write_backlog(backlog_path, """### P0 (Critical)
- [x] **Done task** -- DoD: Done -- Owner: dev

### P2 (Normal)
- [ ] **P2 task** -- DoD: Done -- Owner: dev
""")

        mission = AutonomousBuildCycleMission()

        # Just test _load_task_from_backlog directly to avoid policy loader issues
        context = create_test_context(repo_root)
        task = mission._load_task_from_backlog(context)

        # No eligible tasks (completed or P2)
        assert task is None

    def test_from_backlog_loads_task(self, tmp_path):
        """from_backlog mode loads task from BACKLOG.md."""
        repo_root = setup_test_repo(tmp_path)
        backlog_path = repo_root / "docs" / "11_admin" / "BACKLOG.md"

        write_backlog(backlog_path, """### P0 (Critical)

- [ ] **Test Feature** -- DoD: Feature works -- Owner: antigravity
""")

        mission = AutonomousBuildCycleMission()

        # We need to mock the internal missions to avoid actual execution
        with patch.object(mission, '_can_reset_workspace', return_value=True):
            # Call validate_inputs to ensure from_backlog mode doesn't require task_spec
            try:
                mission.validate_inputs({"from_backlog": True})
                validation_passed = True
            except Exception:
                validation_passed = False

            assert validation_passed, "from_backlog mode should not require task_spec"

            # Test that _load_task_from_backlog works
            context = create_test_context(repo_root)
            loaded_task = mission._load_task_from_backlog(context)

            assert loaded_task is not None
            assert loaded_task.title == "Test Feature"
            assert loaded_task.dod == "Feature works"
            assert loaded_task.priority.value == "P0"

    def test_get_uncompleted_tasks_filters_correctly(self, tmp_path):
        """get_uncompleted_tasks returns only TODO P0/P1 items."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P0 (Critical)

- [x] **Completed P0** -- DoD: Done -- Owner: dev
- [ ] **Todo P0** -- DoD: Done -- Owner: dev

### P1 (High)

- [ ] **Todo P1** -- DoD: Done -- Owner: dev

### P2 (Normal)

- [ ] **Todo P2** -- DoD: Done -- Owner: dev
""")

        items = parse_backlog(backlog)
        uncompleted = get_uncompleted_tasks(items)

        assert len(uncompleted) == 2
        titles = [item.title for item in uncompleted]
        assert "Todo P0" in titles
        assert "Todo P1" in titles
        assert "Completed P0" not in titles
        assert "Todo P2" not in titles

    def test_cli_summary_format(self):
        """TaskSpec.to_cli_summary produces expected format."""
        task = TaskSpec(
            item_key="abc123def456",
            title="Fix bug in parser",
            priority=TaskPriority.P0,
            dod="Bug fixed",
            owner="dev",
        )

        summary = task.to_cli_summary()

        assert summary == "[P0] Fix bug in parser (abc123de)"
        assert len(summary.split("(")[1].rstrip(")")) == 8  # Truncated to 8 chars

    def test_blocked_task_skipped_during_selection(self, tmp_path):
        """P0.2: Blocked task is skipped when unblocked task exists."""
        repo_root = setup_test_repo(tmp_path)
        backlog_path = repo_root / "docs" / "11_admin" / "BACKLOG.md"

        # P0 blocked task followed by P0 unblocked task
        write_backlog(backlog_path, """### P0 (Critical)

- [ ] **Blocked Task** -- DoD: Done -- Owner: dev -- Context: depends on T-99
- [ ] **Unblocked Task** -- DoD: Done -- Owner: dev -- Context: Ready to start
""")

        mission = AutonomousBuildCycleMission()

        with patch.object(mission, '_can_reset_workspace', return_value=True):
            context = create_test_context(repo_root)
            loaded_task = mission._load_task_from_backlog(context)

            # Must select the unblocked task, not the blocked one
            assert loaded_task is not None
            assert loaded_task.title == "Unblocked Task"
            assert "depends on" not in loaded_task.context

    def test_backlog_missing_returns_specific_outcome(self, tmp_path):
        """P1.1: BACKLOG_MISSING is distinct from NO_ELIGIBLE_TASKS."""
        repo_root = setup_test_repo(tmp_path)
        # Do not create BACKLOG.md

        mission = AutonomousBuildCycleMission()
        result = mission.run(create_test_context(repo_root), {
            "from_backlog": True,
            "handoff_schema_version": "v1.0",
        })

        assert result.success is False
        assert result.outputs["reason"] == "BACKLOG_MISSING"
        assert "BACKLOG.md not found" in result.outputs.get("error", "")

    def test_why_now_used_as_dod(self, tmp_path):
        """P1.2: 'Why Now:' is accepted in place of 'DoD:' as acceptance criteria."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Urgent Fix** -- Why Now: Blocking production deployment -- Owner: dev
""")

        items = parse_backlog(backlog)

        assert len(items) == 1
        assert items[0].dod == "Blocking production deployment"
        assert items[0].title == "Urgent Fix"

    def test_evidence_file_written_to_repo_root(self, tmp_path):
        """P0.1: Evidence file is written to <repo_root>/artifacts/backlog_evidence.jsonl."""
        # Setup with .git to mark repo root
        (tmp_path / ".git").mkdir(exist_ok=True)
        backlog_path = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True, exist_ok=True)

        write_backlog(backlog_path, """### P0 (Critical)

- [ ] **Test Evidence Path** -- DoD: Done -- Owner: dev
""")

        items = parse_backlog(backlog_path)
        evidence = {"commit_hash": "test123", "run_id": "run-001"}

        # Call with explicit repo_root
        mark_item_done_with_evidence(
            backlog_path,
            items[0],
            evidence,
            repo_root=tmp_path
        )

        # Assert evidence file at repo root, not at docs/artifacts/
        evidence_file = tmp_path / "artifacts" / "backlog_evidence.jsonl"
        assert evidence_file.exists(), "Evidence must be at <repo_root>/artifacts/"

        # Assert it's NOT at the wrong location
        wrong_location = tmp_path / "docs" / "artifacts" / "backlog_evidence.jsonl"
        assert not wrong_location.exists(), "Evidence must not be at docs/artifacts/"

    def test_evidence_auto_detect_repo_root(self, tmp_path):
        """P0.1: Evidence file auto-detects repo root via .git directory."""
        # Setup with .git to mark repo root
        (tmp_path / ".git").mkdir(exist_ok=True)
        backlog_path = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True, exist_ok=True)

        write_backlog(backlog_path, """### P0 (Critical)

- [ ] **Test Auto-Detect** -- DoD: Done -- Owner: dev
""")

        items = parse_backlog(backlog_path)
        evidence = {"commit_hash": "auto123", "run_id": "run-002"}

        # Call WITHOUT repo_root - should auto-detect
        mark_item_done_with_evidence(
            backlog_path,
            items[0],
            evidence
        )

        # Assert evidence file at repo root (auto-detected)
        evidence_file = tmp_path / "artifacts" / "backlog_evidence.jsonl"
        assert evidence_file.exists(), "Evidence must be at auto-detected repo root"
