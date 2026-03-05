from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from runtime.tools.workflow_pack import (
    build_active_work_payload,
    check_doc_stewardship,
    cleanup_after_merge,
    merge_to_main,
    read_active_work,
    run_closure_tests,
    route_targeted_tests,
    update_structured_backlog,
    write_active_work,
)


def test_active_work_roundtrip(tmp_path: Path) -> None:
    payload = build_active_work_payload(
        branch="feature/workflow-pack",
        latest_commits=["abc123 add router", "def456 add skills"],
        focus=["W4-T01", "W5-T04"],
        tests_targeted=["pytest -q runtime/tests/test_workflow_pack.py"],
        findings_open=[{"id": "M1", "severity": "moderate", "status": "open"}],
    )

    output = write_active_work(tmp_path, payload)
    assert output == tmp_path / ".context" / "active_work.yaml"

    loaded = read_active_work(tmp_path)
    assert loaded["version"] == "1.0"
    assert loaded["branch"] == "feature/workflow-pack"
    assert loaded["focus"] == ["W4-T01", "W5-T04"]
    assert loaded["findings_open"] == [{"id": "M1", "severity": "moderate", "status": "open"}]


def test_route_targeted_tests_routes_known_files() -> None:
    changed = [
        "runtime/orchestration/openclaw_bridge.py",
        "runtime/orchestration/missions/autonomous_build_cycle.py",
    ]
    commands = route_targeted_tests(changed)
    assert commands == [
        "pytest -q runtime/tests/orchestration/test_openclaw_bridge.py",
        "pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py",
    ]


def test_route_targeted_tests_deduplicates() -> None:
    changed = [
        "runtime/agents/api.py",
        "tests/test_agent_api.py",
        "runtime/agents/opencode_client.py",
    ]
    commands = route_targeted_tests(changed)
    assert commands == [
        "pytest -q runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py",
    ]


def test_route_targeted_tests_routes_openclaw_model_preflight() -> None:
    commands = route_targeted_tests(["runtime/tools/openclaw_models_preflight.sh"])
    assert commands == [
        "pytest -q runtime/tests/test_openclaw_model_policy_assert.py "
        "runtime/tests/test_openclaw_policy_assert.py "
        "runtime/tests/test_openclaw_memory_policy_assert.py"
    ]


def test_route_targeted_tests_routes_openclaw_policy_bundle() -> None:
    commands = route_targeted_tests(["runtime/tools/openclaw_policy_assert.py"])
    assert commands == [
        "pytest -q runtime/tests/test_openclaw_model_policy_assert.py "
        "runtime/tests/test_openclaw_policy_assert.py "
        "runtime/tests/test_openclaw_memory_policy_assert.py"
    ]


def test_route_targeted_tests_fallback() -> None:
    # Unknown file → falls back to full suite
    commands = route_targeted_tests(["some/unknown/module.py"])
    assert commands == ["pytest -q runtime/tests"]


def test_route_targeted_tests_docs_admin() -> None:
    # docs/11_admin changes route to targeted doc tests, not full suite
    commands = route_targeted_tests(["docs/11_admin/BACKLOG.md"])
    assert commands == [
        "pytest -q runtime/tests/test_doc_hygiene.py runtime/tests/test_backlog_parser.py"
    ]


def test_route_targeted_tests_docs_general() -> None:
    # Any docs/ change routes to targeted doc tests
    commands = route_targeted_tests(["docs/02_protocols/some_spec.md"])
    assert commands == [
        "pytest -q runtime/tests/test_doc_hygiene.py runtime/tests/test_backlog_parser.py"
    ]


def test_route_targeted_tests_spine() -> None:
    # spine.py routes to loop spine + shadow runner tests
    commands = route_targeted_tests(["runtime/orchestration/loop/spine.py"])
    assert commands == [
        "pytest -q runtime/tests/test_loop_spine.py "
        "runtime/tests/orchestration/council/test_shadow_runner.py"
    ]


def test_route_targeted_tests_pyproject() -> None:
    # pyproject.toml routes to config/hygiene tests
    commands = route_targeted_tests(["pyproject.toml"])
    assert commands == [
        "pytest -q runtime/tests/test_known_failures_gate.py runtime/tests/test_state_hygiene.py"
    ]


def test_route_targeted_tests_artifacts_status() -> None:
    # Regenerated status artifacts route to workflow_pack tests
    commands = route_targeted_tests(["artifacts/status/runtime_status.json"])
    assert commands == ["pytest -q runtime/tests/test_workflow_pack.py"]


def test_route_targeted_tests_coo_module() -> None:
    commands = route_targeted_tests(["runtime/orchestration/coo/backlog.py"])
    assert commands == ["pytest -q runtime/tests/orchestration/coo/"]


def test_route_targeted_tests_coo_tests() -> None:
    commands = route_targeted_tests(["runtime/tests/orchestration/coo/test_backlog.py"])
    assert commands == ["pytest -q runtime/tests/orchestration/coo/"]


def test_route_targeted_tests_config_tasks() -> None:
    commands = route_targeted_tests(["config/tasks/backlog.yaml"])
    assert commands == ["pytest -q runtime/tests/orchestration/coo/test_backlog.py"]


def test_route_targeted_tests_config_governance() -> None:
    commands = route_targeted_tests(["config/governance/delegation_envelope.yaml"])
    assert commands == ["pytest -q runtime/tests/test_doc_hygiene.py"]


def test_route_targeted_tests_artifacts_plans() -> None:
    commands = route_targeted_tests(["artifacts/plans/2026-03-05-coo-bootstrap-plan.md"])
    assert commands == ["pytest -q runtime/tests/test_workflow_pack.py"]


def test_route_targeted_tests_artifacts_handoffs() -> None:
    commands = route_targeted_tests(["artifacts/handoffs/some-handoff.md"])
    assert commands == ["pytest -q runtime/tests/test_workflow_pack.py"]


def test_route_targeted_tests_coo_and_config_deduplicates() -> None:
    # Mixed coo + config/tasks change should not repeat the coo suite
    commands = route_targeted_tests([
        "runtime/orchestration/coo/backlog.py",
        "config/tasks/backlog.yaml",
    ])
    assert "pytest -q runtime/tests/orchestration/coo/" in commands
    assert "pytest -q runtime/tests/orchestration/coo/test_backlog.py" in commands
    assert len(commands) == 2  # no duplicates


def test_run_closure_tests_passes_on_zero_returncode(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_closure_tests(Path("."), ["runtime/tools/workflow_pack.py"])
    assert result["passed"] is True
    assert result["commands_run"] == ["pytest -q runtime/tests/test_workflow_pack.py"]


def test_run_closure_tests_fails_on_nonzero(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="failed",
        )

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_closure_tests(Path("."), ["runtime/tools/workflow_pack.py"])
    assert result["passed"] is False
    assert result["failures"]


def test_check_doc_stewardship_skips_when_no_docs(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess should not be called")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fail_if_called)
    result = check_doc_stewardship(Path("."), ["runtime/tools/workflow_pack.py"])
    assert result["required"] is False
    assert result["passed"] is True


def test_check_doc_stewardship_runs_when_docs_changed(monkeypatch) -> None:
    payload = {
        "passed": True,
        "docs_modified": True,
        "docs_files": ["docs/INDEX.md"],
        "errors": [],
    }

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = check_doc_stewardship(Path("."), ["docs/INDEX.md"])
    assert result["required"] is True
    assert result["passed"] is True
    assert result["docs_files"] == ["docs/INDEX.md"]


def test_cleanup_after_merge_clears_context(tmp_path: Path, monkeypatch) -> None:
    context_path = tmp_path / ".context" / "active_work.yaml"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text("{}", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = cleanup_after_merge(tmp_path, "build/feature", clear_context=True)
    assert result["branch_deleted"] is True
    assert result["context_cleared"] is True
    assert not context_path.exists()


def test_cleanup_after_merge_removes_worktree_before_branch(tmp_path: Path, monkeypatch) -> None:
    primary = tmp_path / "primary"
    repo = tmp_path / ".worktrees" / "feature"
    primary.mkdir(parents=True, exist_ok=True)
    repo.mkdir(parents=True, exist_ok=True)
    commands: list[list[str]] = []

    worktree_list = (
        f"worktree {primary}\n"
        "branch refs/heads/main\n\n"
        f"worktree {repo}\n"
        "branch refs/heads/build/feature\n"
    )

    def fake_run(*args, **kwargs):
        cmd = args[0]
        commands.append(cmd)
        if cmd[-3:] == ["worktree", "list", "--porcelain"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=worktree_list, stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)

    result = cleanup_after_merge(repo, "build/feature", clear_context=False)

    worktree_remove_idx = next(
        i for i, c in enumerate(commands) if "worktree" in c and "remove" in c and "--force" in c
    )
    branch_delete_idx = next(i for i, c in enumerate(commands) if c[-2:] == ["-d", "build/feature"])
    branch_delete_cmd = commands[branch_delete_idx]
    assert worktree_remove_idx < branch_delete_idx
    assert branch_delete_cmd[2] == str(primary)
    assert result["worktree_removed"] is True
    assert result["branch_deleted"] is True


def test_cleanup_after_merge_skips_remove_when_branch_maps_to_primary(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path
    commands: list[list[str]] = []

    worktree_list = (
        f"worktree {repo}\n"
        "branch refs/heads/main\n"
        "branch refs/heads/build/feature\n"
    )

    def fake_run(*args, **kwargs):
        cmd = args[0]
        commands.append(cmd)
        if cmd[-3:] == ["worktree", "list", "--porcelain"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=worktree_list, stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)

    result = cleanup_after_merge(repo, "build/feature", clear_context=False)

    assert result["worktree_removed"] is False
    assert result["branch_deleted"] is True
    assert not any(c[-3:] == ["worktree", "remove", "--force"] for c in commands)


def test_merge_to_main_includes_primary_repo(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path
    primary = repo / "primary"
    primary.mkdir(parents=True, exist_ok=True)

    worktree_list = f"worktree {primary}\nbranch refs/heads/main\n"

    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd == [sys.executable, "scripts/repo_safety_gate.py", "--operation", "merge"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        if cmd[-3:] == ["worktree", "list", "--porcelain"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=worktree_list, stderr="")
        if cmd[-2:] == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="main\n", stderr="")
        if cmd[-1:] == ["HEAD"] and "rev-parse" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="abc123\n", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = merge_to_main(repo, "build/feature")

    assert result["success"] is True
    assert result["primary_repo"] == str(primary)


def test_merge_to_main_empty_branch_returns_primary_none() -> None:
    from runtime.tools.workflow_pack import merge_to_main

    result = merge_to_main(Path("."), "")
    assert result["success"] is False
    assert result["primary_repo"] is None


# --- Tests for STATE/BACKLOG update functions ---


def test_extract_win_details_from_branch(monkeypatch) -> None:
    """Test extraction of win details from branch name and commits."""
    from runtime.tools.workflow_pack import _extract_win_details

    fake_commits = "feat: fix test debt\nchore: update docs\ntest: add coverage"

    def fake_run(*args, **kwargs):
        if "git" in args[0] and "log" in args[0]:
            return subprocess.CompletedProcess(
                args=args[0], returncode=0, stdout=fake_commits, stderr=""
            )
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)

    result = _extract_win_details(
        repo_root=Path("/fake/repo"),
        branch="build/doc-refresh-and-test-debt",
        merge_sha="abc123def456",
        test_summary="3/3 targeted test command(s) passed.",
    )

    assert result["title"] == "Doc Refresh And Test Debt"
    assert "fix test debt" in result["details"].lower()
    assert result["merge_sha_short"] == "abc123d"


def test_update_lifeos_state_adds_recent_win(tmp_path: Path) -> None:
    """Test that STATE update adds Recent Win and updates timestamp."""
    from runtime.tools.workflow_pack import _update_lifeos_state

    state_path = tmp_path / "docs" / "11_admin" / "LIFEOS_STATE.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# LifeOS State

**Last Updated:** 2026-02-12 (rev3)

## 🟩 Recent Wins

- **2026-02-12:** Old win entry
- **2026-02-11:** Another old win
""",
        encoding="utf-8",
    )

    result = _update_lifeos_state(
        state_path=state_path,
        title="Doc Refresh And Test Debt",
        details="Fixed test debt; Updated docs; Added coverage",
        merge_sha_short="abc123d",
        skip_on_error=True,
    )

    assert result["success"] is True
    assert result["errors"] == []

    content = state_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    # Should have new win at the top
    assert f"**{today}:** Doc Refresh And Test Debt — Fixed test debt" in content
    assert "(merge commit abc123d)" in content
    # Should have updated timestamp with rev4
    assert f"**Last Updated:** {today} (rev4)" in content


def test_update_lifeos_state_increments_revision(tmp_path: Path) -> None:
    """Test that revision number increments correctly."""
    from runtime.tools.workflow_pack import _update_lifeos_state

    state_path = tmp_path / "docs" / "11_admin" / "LIFEOS_STATE.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# LifeOS State

**Last Updated:** 2026-01-15 (rev10)

## 🟩 Recent Wins

- **2026-01-15:** Some win
""",
        encoding="utf-8",
    )

    result = _update_lifeos_state(
        state_path=state_path,
        title="Test",
        details="Test details",
        merge_sha_short="xyz789a",
        skip_on_error=True,
    )

    assert result["success"] is True
    content = state_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    # Should increment from rev10 to rev11
    assert f"**Last Updated:** {today} (rev11)" in content


def test_match_backlog_item_finds_match() -> None:
    """Test that BACKLOG item matching works with fuzzy similarity."""
    from runtime.tools.workflow_pack import _match_backlog_item
    from recursive_kernel.backlog_parser import BacklogItem, ItemStatus, Priority

    # Create mock backlog items
    items = [
        BacklogItem(
            item_key="abc123",
            item_key_full="abc123full",
            priority=Priority.P1,
            title="Fix test_steward_runner.py (25/27 failing)",
            dod="Tests pass",
            owner="antigravity",
            status=ItemStatus.TODO,
            context="Import/fixture issues",
            line_number=26,
            original_line="- [ ] **Fix test_steward_runner.py (25/27 failing)**",
        ),
        BacklogItem(
            item_key="def456",
            item_key_full="def456full",
            priority=Priority.P1,
            title="Fix test_e2e_smoke_timeout.py (import error)",
            dod="Import fixed",
            owner="antigravity",
            status=ItemStatus.TODO,
            context="",
            line_number=27,
            original_line="- [ ] **Fix test_e2e_smoke_timeout.py (import error)**",
        ),
    ]

    # Branch name with "test debt" should match first item
    result = _match_backlog_item(
        branch="build/doc-refresh-and-test-debt",
        commit_messages=["fix test_steward_runner", "update docs"],
        backlog_items=items,
        threshold=0.3,  # Lower threshold for testing
    )

    assert result is not None
    assert "test" in result.title.lower()


def test_match_backlog_item_no_match_below_threshold() -> None:
    """Test that no match is returned if similarity is below threshold."""
    from runtime.tools.workflow_pack import _match_backlog_item
    from recursive_kernel.backlog_parser import BacklogItem, ItemStatus, Priority

    items = [
        BacklogItem(
            item_key="abc123",
            item_key_full="abc123full",
            priority=Priority.P0,
            title="OpenClaw installation",
            dod="Installed",
            owner="antigravity",
            status=ItemStatus.TODO,
            context="",
            line_number=10,
            original_line="- [ ] **OpenClaw installation**",
        ),
    ]

    # Completely different branch should not match
    result = _match_backlog_item(
        branch="build/ui-theme-colors",
        commit_messages=["change button colors"],
        backlog_items=items,
        threshold=0.7,
    )

    assert result is None


def test_update_backlog_marks_item_done(tmp_path: Path) -> None:
    """Test that BACKLOG update marks matched items as done."""
    from runtime.tools.workflow_pack import _update_backlog_state

    backlog_path = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        """# BACKLOG

**Last Updated:** 2026-02-12

## Now

### P1 (High)

- [ ] **Fix test_steward_runner.py (25/27 failing)** — DoD: Tests pass — Owner: antigravity
- [ ] **Fix test_e2e_smoke_timeout.py** — DoD: Import fixed — Owner: antigravity
""",
        encoding="utf-8",
    )

    result = _update_backlog_state(
        backlog_path=backlog_path,
        branch="build/test-debt-stabilization",
        commit_messages=["fix test_steward_runner", "add tests"],
        skip_on_error=True,
    )

    assert result["success"] is True
    content = backlog_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    # Should update timestamp
    assert f"**Last Updated:** {today}" in content
    # Should mark matching item as done
    assert "[x] **Fix test_steward_runner.py" in content


def test_update_backlog_updates_timestamp_only_if_no_match(tmp_path: Path) -> None:
    """Test that BACKLOG timestamp updates even if no item matches."""
    from runtime.tools.workflow_pack import _update_backlog_state

    backlog_path = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        """# BACKLOG

**Last Updated:** 2026-02-10

## Now

- [ ] **Some unrelated task** — DoD: Done — Owner: antigravity
""",
        encoding="utf-8",
    )

    result = _update_backlog_state(
        backlog_path=backlog_path,
        branch="build/ui-improvements",
        commit_messages=["change colors"],
        skip_on_error=True,
    )

    assert result["success"] is True
    content = backlog_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    # Should update timestamp
    assert f"**Last Updated:** {today}" in content
    # Should NOT mark item as done
    assert "[ ] **Some unrelated task**" in content


def test_update_state_and_backlog_integration(tmp_path: Path, monkeypatch) -> None:
    """Test integration of STATE and BACKLOG updates."""
    from runtime.tools.workflow_pack import update_state_and_backlog

    # Create STATE file
    state_path = tmp_path / "docs" / "11_admin" / "LIFEOS_STATE.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# LifeOS State

**Last Updated:** 2026-02-12 (rev3)

## 🟩 Recent Wins

- **2026-02-12:** Old win
""",
        encoding="utf-8",
    )

    # Create BACKLOG file
    backlog_path = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
    backlog_path.write_text(
        """# BACKLOG

**Last Updated:** 2026-02-10

## Now

### P1 (High)

- [ ] **Fix test debt** — DoD: Tests pass — Owner: antigravity
""",
        encoding="utf-8",
    )

    # Mock git log
    def fake_run(*args, **kwargs):
        if "git" in args[0] and "log" in args[0]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout="fix: stabilize test suite",
                stderr="",
            )
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)

    result = update_state_and_backlog(
        repo_root=tmp_path,
        branch="build/test-debt-stabilization",
        merge_sha="abc123def456",
        test_summary="5/5 tests passed.",
        skip_on_error=True,
    )

    assert result["state_updated"] is True
    assert result["backlog_updated"] is True
    assert result["items_marked"] == 1
    assert result["errors"] == []

    # Verify STATE was updated
    state_content = state_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    assert f"**{today}:** Test Debt Stabilization" in state_content
    assert "(merge commit abc123d)" in state_content
    assert f"**Last Updated:** {today} (rev4)" in state_content

    # Verify BACKLOG was updated
    backlog_content = backlog_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    assert "[x] **Fix test debt**" in backlog_content
    assert f"**Last Updated:** {today}" in backlog_content


def test_update_graceful_on_missing_files(tmp_path: Path) -> None:
    """Test that updates gracefully handle missing files."""
    from runtime.tools.workflow_pack import update_state_and_backlog

    result = update_state_and_backlog(
        repo_root=tmp_path,
        branch="build/test",
        merge_sha="abc123",
        test_summary="",
        skip_on_error=True,
    )

    assert result["state_updated"] is False
    assert result["backlog_updated"] is False
    assert len(result["errors"]) > 0
    assert any("not found" in err.lower() for err in result["errors"])


def _write_minimal_structured_backlog(tmp_path: Path, status: str = "in_progress") -> Path:
    backlog_path = tmp_path / "config" / "tasks" / "backlog.yaml"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        f"""schema_version: "backlog.v1"
tasks:
  - id: "T-001"
    title: "Test task"
    description: ""
    dod: ""
    priority: "P1"
    risk: "low"
    scope_paths: []
    status: "{status}"
    requires_approval: false
    owner: ""
    evidence: ""
    task_type: "build"
    tags: []
    objective_ref: "bootstrap"
    created_at: "2026-03-05T00:00:00Z"
""",
        encoding="utf-8",
    )
    return backlog_path


def _write_completed_order(tmp_path: Path, name: str, content: str) -> None:
    completed_dir = tmp_path / "artifacts" / "dispatch" / "completed"
    completed_dir.mkdir(parents=True, exist_ok=True)
    (completed_dir / name).write_text(content, encoding="utf-8")


def test_update_structured_backlog_no_completed_dir_returns_not_updated(tmp_path: Path) -> None:
    _write_minimal_structured_backlog(tmp_path, status="in_progress")

    result = update_structured_backlog(
        repo_root=tmp_path,
        merge_sha="abc123",
        skip_on_error=True,
    )

    assert result["updated"] is False
    assert result["tasks_completed"] == []


def test_update_structured_backlog_no_matching_task_ref(tmp_path: Path) -> None:
    _write_minimal_structured_backlog(tmp_path, status="pending")
    _write_completed_order(
        tmp_path,
        "order-success.yaml",
        """schema_version: "execution_order.v1"
order_id: "ORD-T-999-20260305120000"
task_ref: "T-999"
created_at: "2026-03-05T12:00:00Z"
outcome: "SUCCESS"
steps:
  - name: "implementation"
    role: "builder"
""",
    )

    result = update_structured_backlog(
        repo_root=tmp_path,
        merge_sha="abc123",
        skip_on_error=True,
    )

    assert result["updated"] is False
    assert result["tasks_completed"] == []


def test_update_structured_backlog_marks_matching_task(tmp_path: Path) -> None:
    from runtime.orchestration.coo.backlog import load_backlog

    backlog_path = _write_minimal_structured_backlog(tmp_path, status="in_progress")
    _write_completed_order(
        tmp_path,
        "order-success.yaml",
        """schema_version: "execution_order.v1"
order_id: "ORD-T-001-20260305120000"
task_ref: "T-001"
created_at: "2026-03-05T12:00:00Z"
outcome: "SUCCESS"
steps:
  - name: "implementation"
    role: "builder"
""",
    )

    result = update_structured_backlog(
        repo_root=tmp_path,
        merge_sha="abc123",
        skip_on_error=True,
    )

    assert result["updated"] is True
    assert result["tasks_completed"] == ["T-001"]

    tasks = load_backlog(backlog_path)
    assert next(task for task in tasks if task.id == "T-001").status == "completed"


def test_update_structured_backlog_failed_outcome_not_marked_complete(tmp_path: Path) -> None:
    _write_minimal_structured_backlog(tmp_path, status="in_progress")
    _write_completed_order(
        tmp_path,
        "order-failed.yaml",
        """schema_version: "execution_order.v1"
order_id: "ORD-T-001-20260305130000"
task_ref: "T-001"
created_at: "2026-03-05T13:00:00Z"
outcome: "FAILED"
steps:
  - name: "implementation"
    role: "builder"
""",
    )

    result = update_structured_backlog(
        repo_root=tmp_path,
        merge_sha="abc123",
        skip_on_error=True,
    )

    assert result["updated"] is False
    assert result["tasks_completed"] == []


def test_update_structured_backlog_missing_outcome_skipped_with_warning(tmp_path: Path) -> None:
    _write_minimal_structured_backlog(tmp_path, status="in_progress")
    _write_completed_order(
        tmp_path,
        "order-missing-outcome.yaml",
        """schema_version: "execution_order.v1"
order_id: "ORD-T-001-20260305120000"
task_ref: "T-001"
created_at: "2026-03-05T12:00:00Z"
steps:
  - name: "implementation"
    role: "builder"
""",
    )

    result = update_structured_backlog(
        repo_root=tmp_path,
        merge_sha="abc123",
        skip_on_error=True,
    )

    assert result["updated"] is False
    assert result["errors"]
    assert any("outcome" in err.lower() for err in result["errors"])


def test_update_structured_backlog_missing_backlog_returns_error(tmp_path: Path) -> None:
    result = update_structured_backlog(
        repo_root=tmp_path,
        merge_sha="abc123",
        skip_on_error=True,
    )

    assert result["updated"] is False
    assert any("backlog.yaml not found" in err for err in result["errors"])
