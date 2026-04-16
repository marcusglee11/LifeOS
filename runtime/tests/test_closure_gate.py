"""Tests for scripts/workflow/closure_gate.py run_gate function."""

from __future__ import annotations

from pathlib import Path

from scripts.workflow.closure_gate import run_gate


def test_gate_no_changes_includes_policy_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.resolve_closure_tier",
        lambda *_args, **_kwargs: {
            "outcome": "no_changes",
            "closure_tier": "no_changes",
            "classification_reason": "none",
            "changed_paths": [],
        },
    )
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.get_tier_execution_policy",
        lambda *_args, **_kwargs: {
            "selected_checks": [],
            "skipped_checks": ["targeted_pytest"],
            "post_merge_updates_suppressed": True,
        },
    )

    verdict = run_gate(Path("."))
    assert verdict["passed"] is True
    assert verdict["gate"] == "no_changes"
    assert verdict["closure_policy_version"] == "v1"
    assert verdict["closure_tier"] == "no_changes"
    assert verdict["post_merge_updates_suppressed"] is True


def test_gate_structured_docs_reports_selected_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.resolve_closure_tier",
        lambda *_args, **_kwargs: {
            "outcome": "classified",
            "closure_tier": "structured_docs",
            "classification_reason": "structured docs",
            "changed_paths": ["docs/02_protocols/example.md"],
        },
    )
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.get_tier_execution_policy",
        lambda *_args, **_kwargs: {
            "selected_checks": ["doc_stewardship", "markdownlint", "targeted_pytest"],
            "skipped_checks": ["quality_gate"],
            "post_merge_updates_suppressed": True,
            "run_doc_stewardship": True,
            "quality_tools": ["markdownlint"],
            "run_general_quality_gate": False,
        },
    )
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.check_doc_stewardship",
        lambda *_args, **_kwargs: {"passed": True, "required": True, "errors": []},
    )
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.run_quality_gates",
        lambda *_args, **_kwargs: {"passed": True, "summary": "markdown ok", "results": []},
    )
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.run_closure_tests",
        lambda *_args, **_kwargs: {"passed": True, "summary": "doc pytest ok"},
    )

    verdict = run_gate(Path("."))
    assert verdict["passed"] is True
    assert verdict["gate"] == "all"
    assert verdict["closure_tier"] == "structured_docs"
    assert verdict["selected_checks"] == ["doc_stewardship", "markdownlint", "targeted_pytest"]
    assert verdict["skipped_checks"] == ["quality_gate"]
    assert verdict["post_merge_updates_suppressed"] is True


def test_gate_quality_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.resolve_closure_tier",
        lambda *_args, **_kwargs: {
            "outcome": "classified",
            "closure_tier": "full",
            "classification_reason": "full",
            "changed_paths": ["runtime/tools/workflow_pack.py"],
        },
    )
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.get_tier_execution_policy",
        lambda *_args, **_kwargs: {
            "selected_checks": ["targeted_pytest", "quality_gate"],
            "skipped_checks": [],
            "post_merge_updates_suppressed": False,
            "run_doc_stewardship": False,
            "quality_tools": [],
            "run_general_quality_gate": True,
        },
    )
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.run_quality_gates",
        lambda *_args, **_kwargs: {
            "passed": False,
            "summary": "quality failed",
            "results": [{"passed": False, "mode": "blocking", "details": "unused import"}],
        },
    )

    verdict = run_gate(Path("."))
    assert verdict["passed"] is False
    assert verdict["gate"] == "quality"


def test_gate_full_fallback_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.resolve_closure_tier",
        lambda *_args, **_kwargs: {
            "outcome": "full_fallback",
            "closure_tier": "full",
            "classification_reason": "Unsupported diff status line: X",
            "changed_paths": [],
        },
    )
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.get_tier_execution_policy",
        lambda *_args, **_kwargs: {
            "selected_checks": ["targeted_pytest", "quality_gate"],
            "skipped_checks": [],
            "post_merge_updates_suppressed": False,
            "run_doc_stewardship": False,
            "quality_tools": [],
            "run_general_quality_gate": False,
        },
    )
    monkeypatch.setattr(
        "scripts.workflow.closure_gate.run_closure_tests",
        lambda *_args, **_kwargs: {"passed": True, "summary": "test ok"},
    )

    verdict = run_gate(Path("."))
    assert verdict["passed"] is True
    assert "fell back to full" in verdict["summary"]
