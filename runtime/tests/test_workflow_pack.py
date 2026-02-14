from __future__ import annotations

import json
import subprocess
from pathlib import Path

from runtime.tools.workflow_pack import (
    build_active_work_payload,
    check_doc_stewardship,
    cleanup_after_merge,
    read_active_work,
    run_closure_tests,
    route_targeted_tests,
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


def test_route_targeted_tests_fallback() -> None:
    commands = route_targeted_tests(["docs/11_admin/BACKLOG.md"])
    assert commands == ["pytest -q runtime/tests"]


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
    # Should have new win at the top
    assert "**2026-02-14:** Doc Refresh And Test Debt — Fixed test debt" in content
    assert "(merge commit abc123d)" in content
    # Should have updated timestamp with rev4
    assert "**Last Updated:** 2026-02-14 (rev4)" in content


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
    # Should increment from rev10 to rev11
    assert "**Last Updated:** 2026-02-14 (rev11)" in content


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
    # Should update timestamp
    assert "**Last Updated:** 2026-02-14" in content
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
    # Should update timestamp
    assert "**Last Updated:** 2026-02-14" in content
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
    assert "**2026-02-14:** Test Debt Stabilization" in state_content
    assert "(merge commit abc123d)" in state_content
    assert "**Last Updated:** 2026-02-14 (rev4)" in state_content

    # Verify BACKLOG was updated
    backlog_content = backlog_path.read_text(encoding="utf-8")
    assert "[x] **Fix test debt**" in backlog_content
    assert "**Last Updated:** 2026-02-14" in backlog_content


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
