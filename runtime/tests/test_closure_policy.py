from __future__ import annotations

from pathlib import Path

from runtime.tools import closure_policy as cp


def test_classify_paths_general_docs() -> None:
    assert cp.classify_paths(["docs/04_project_builder/example.md"])["closure_tier"] == "general_docs"


def test_classify_paths_structured_docs() -> None:
    assert cp.classify_paths(["docs/02_protocols/example.md"])["closure_tier"] == "structured_docs"


def test_classify_paths_docs_admin_is_full() -> None:
    assert cp.classify_paths(["docs/11_admin/BACKLOG.md"])["closure_tier"] == "full"


def test_classify_paths_config_is_full() -> None:
    assert cp.classify_paths(["config/tasks/backlog.yaml"])["closure_tier"] == "full"


def test_classify_paths_mixed_docs_and_artifacts_is_full() -> None:
    assert (
        cp.classify_paths(["artifacts/plans/x.md", "docs/04_project_builder/example.md"])["closure_tier"]
        == "full"
    )


def test_classify_paths_unknown_root_markdown_is_full() -> None:
    assert cp.classify_paths(["README.md"])["closure_tier"] == "full"


def test_discover_normalized_change_set_rename_semantics(monkeypatch) -> None:
    def fake_git_stdout(_repo_root: Path, args: list[str]):
        if args[:2] == ["merge-base", cp.BASE_BRANCH]:
            return True, "abc123"
        if args[:3] == ["diff", "--name-status", "-M"]:
            return True, "R100\tdocs/04_project_builder/a.md\tconfig/tasks/a.yaml"
        raise AssertionError(args)

    monkeypatch.setattr(cp, "_git_stdout", fake_git_stdout)
    result = cp.discover_normalized_change_set(Path("."))
    assert result["ok"] is True
    assert result["changed_paths"] == ["docs/04_project_builder/a.md", "config/tasks/a.yaml"]


def test_resolve_closure_tier_valid_empty_diff_is_no_changes(monkeypatch) -> None:
    def fake_git_stdout(_repo_root: Path, args: list[str]):
        if args[:2] == ["merge-base", cp.BASE_BRANCH]:
            return True, "abc123"
        if args[:3] == ["diff", "--name-status", "-M"]:
            return True, ""
        raise AssertionError(args)

    monkeypatch.setattr(cp, "_git_stdout", fake_git_stdout)
    result = cp.resolve_closure_tier(Path("."))
    assert result["outcome"] == "no_changes"
    assert result["closure_tier"] == "no_changes"


def test_resolve_closure_tier_parse_failure_falls_back_to_full(monkeypatch) -> None:
    def fake_git_stdout(_repo_root: Path, args: list[str]):
        if args[:2] == ["merge-base", cp.BASE_BRANCH]:
            return True, "abc123"
        if args[:3] == ["diff", "--name-status", "-M"]:
            return True, "X\tmystery.txt"
        raise AssertionError(args)

    monkeypatch.setattr(cp, "_git_stdout", fake_git_stdout)
    result = cp.resolve_closure_tier(Path("."))
    assert result["outcome"] == "full_fallback"
    assert result["closure_tier"] == "full"


def test_base_branch_is_centralized() -> None:
    assert cp.BASE_BRANCH == "main"


def test_review_checkpoint_uses_central_base_branch() -> None:
    assert cp.BASE_BRANCH == "main"


def test_structured_doc_commands_are_centralized() -> None:
    policy = cp.get_tier_execution_policy("structured_docs")
    assert policy["targeted_pytest_commands"] == list(cp.STRUCTURED_DOC_PYTEST_COMMANDS)
