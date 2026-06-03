"""Tests for entrypoint freshness sweep adapter."""

from __future__ import annotations

from typing import Any, cast

from doc_steward.entrypoint_freshness_sweep import (
    CHECK_ID,
    SWEEP_ID,
    TARGET,
    issue_body,
    normalize_error,
    process_findings,
    run,
    validate_repo_labels,
)


class FakeDB:
    def __init__(self, action: str = "created") -> None:
        self.action = action
        self.calls = []
        self.closed = False

    def upsert_finding(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {"action": self.action}

    def close(self) -> None:
        self.closed = True


def finding(identifier: str = "entrypoint-read-order-missing-links") -> dict[str, object]:
    return {
        "id": identifier,
        "severity": "warning",
        "paths": ["README.md"],
        "evidence": "README operator read-order is missing: docs/INDEX.md",
        "recommended_recovery": "Add the missing canonical read-order links to README.md.",
        "authority_class": "canonical",
    }


def fake_lib(db: FakeDB):
    return {
        "FindingsDB": lambda: db,
        "make_fingerprint": lambda sweep_id, target, check_id, normalized_error, severity: (
            f"fp:{sweep_id}:{target}:{check_id}:{severity}:{len(normalized_error)}"
        ),
        "validate_issue_payload": lambda title, body, labels: True,
        "record_sweep_run": lambda *args, **kwargs: "/tmp/receipt.json",
    }


def test_normalize_error_is_stable_by_finding_id():
    first = [finding("b"), finding("a")]
    second = [finding("a"), finding("b")]

    assert normalize_error(first) == normalize_error(second)


def test_issue_body_contains_sweep_lib_required_sections():
    body = issue_body([finding()])

    assert "**Finding:**" in body
    assert f"**Target:** {TARGET}" in body
    assert "**Evidence:**" in body
    assert "**Next action:**" in body
    assert SWEEP_ID in body
    assert CHECK_ID in body


def test_process_findings_dry_run_does_not_touch_db():
    db = FakeDB()

    result = process_findings([finding()], dry_run=True, sweep_lib=fake_lib(db))

    assert result["findings"] == 1
    assert result["findings_created"] == 0
    assert result["findings_updated"] == 0
    rows = cast(list[dict[str, Any]], result["rows"])
    assert rows[0]["action"] == "dry-run"
    assert db.calls == []


def test_process_findings_created_records_one_finding_without_issue_creation():
    db = FakeDB(action="created")

    result = process_findings(
        [finding()], dry_run=False, create_issue=False, sweep_lib=fake_lib(db)
    )

    assert result["findings_created"] == 1
    assert result["findings_updated"] == 0
    rows = cast(list[dict[str, Any]], result["rows"])
    assert rows[0]["action"] == "created"
    assert db.calls[0][0][0].startswith("fp:inventory-hygiene-sweep:lifeos-doc-entrypoint")
    assert db.closed is True


def test_process_findings_create_issue_validates_labels_before_issue_creation(monkeypatch):
    db = FakeDB(action="created")
    import doc_steward.entrypoint_freshness_sweep as sweep

    monkeypatch.setattr(
        sweep,
        "validate_repo_labels",
        lambda repo, labels: {
            "repo": repo,
            "labels": labels,
            "missing_labels": ["severity:warning"],
            "valid": False,
        },
    )

    import pytest

    with pytest.raises(RuntimeError, match="missing GitHub labels"):
        process_findings([finding()], dry_run=False, create_issue=True, sweep_lib=fake_lib(db))

    assert len(db.calls) == 1
    assert db.calls[0][0][0].startswith("fp:inventory-hygiene-sweep:lifeos-doc-entrypoint")


def test_process_findings_updated_skips_duplicate_creation():
    db = FakeDB(action="updated")

    result = process_findings([finding()], dry_run=False, create_issue=True, sweep_lib=fake_lib(db))

    assert result["findings_created"] == 0
    assert result["findings_updated"] == 1
    rows = cast(list[dict[str, Any]], result["rows"])
    assert rows[0]["action"] == "updated"
    assert db.closed is True


def test_validate_repo_labels_reports_missing_without_mutation():
    result = validate_repo_labels(
        "marcusglee11/lifeos-operational-bus",
        ["sweep:inventory-hygiene", "severity:warning"],
        existing_labels={"sweep:inventory-hygiene"},
    )

    assert result == {
        "repo": "marcusglee11/lifeos-operational-bus",
        "labels": ["sweep:inventory-hygiene", "severity:warning"],
        "missing_labels": ["severity:warning"],
        "valid": False,
    }


def test_validate_repo_labels_accepts_configured_labels():
    result = validate_repo_labels(
        "marcusglee11/lifeos-operational-bus",
        ["sweep:inventory-hygiene", "severity:warning"],
        existing_labels={"sweep:inventory-hygiene", "severity:warning"},
    )

    assert result["valid"] is True
    assert result["missing_labels"] == []


def test_process_findings_clean_state_has_no_rows():
    result = process_findings([], dry_run=False, sweep_lib=fake_lib(FakeDB()))

    assert result == {"findings": 0, "findings_created": 0, "findings_updated": 0, "rows": []}


def test_process_findings_dirty_dry_run_does_not_require_sweep_lib():
    result = process_findings([finding()], dry_run=True, sweep_lib=None)

    assert result["findings_created"] == 0
    assert result["findings_updated"] == 0
    rows = cast(list[dict[str, Any]], result["rows"])
    assert rows[0]["action"] == "dry-run"
    assert isinstance(rows[0]["fingerprint"], str)


def test_run_dirty_dry_run_does_not_load_sweep_lib(monkeypatch, tmp_path):
    import doc_steward.entrypoint_freshness_sweep as sweep

    monkeypatch.setattr(sweep, "check_entrypoint_freshness", lambda repo_root: [finding()])
    monkeypatch.setattr(
        sweep,
        "_load_sweep_lib",
        lambda: (_ for _ in ()).throw(AssertionError("sweep_lib should not load")),
    )

    result = run(tmp_path, dry_run=True, json_output=False, record_run=False)

    assert result["findings"] == 1
    rows = cast(list[dict[str, Any]], result["rows"])
    assert rows[0]["action"] == "dry-run"


def test_run_clean_dry_run_is_quiet_and_does_not_record_receipt(monkeypatch, tmp_path, capsys):
    import doc_steward.entrypoint_freshness_sweep as sweep

    monkeypatch.setattr(sweep, "check_entrypoint_freshness", lambda repo_root: [])
    result = run(tmp_path, dry_run=True, json_output=False, record_run=False)
    captured = capsys.readouterr()

    assert captured.out.strip() == "[SILENT]"
    assert result["findings"] == 0
    assert result["rows"] == []
    assert result["receipt"] is None


def test_cli_rejects_dry_run_record_run(tmp_path):
    import pytest

    from doc_steward.entrypoint_freshness_sweep import main

    with pytest.raises(SystemExit) as excinfo:
        main([str(tmp_path), "--dry-run", "--record-run"])

    assert excinfo.value.code == 2


def test_run_rejects_dry_run_record_run_before_loading_sweep_lib(monkeypatch, tmp_path):
    import pytest

    import doc_steward.entrypoint_freshness_sweep as sweep

    monkeypatch.setattr(
        sweep,
        "_load_sweep_lib",
        lambda: (_ for _ in ()).throw(AssertionError("sweep_lib should not load")),
    )

    with pytest.raises(ValueError):
        run(tmp_path, dry_run=True, record_run=True)


def test_doc_steward_cli_rejects_dry_run_record_run(monkeypatch, tmp_path):
    import pytest

    import doc_steward.entrypoint_freshness_sweep as sweep
    from doc_steward import cli

    monkeypatch.setattr(
        sweep,
        "_load_sweep_lib",
        lambda: (_ for _ in ()).throw(AssertionError("sweep_lib should not load")),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "doc_steward.cli",
            "entrypoint-freshness-sweep",
            str(tmp_path),
            "--dry-run",
            "--record-run",
        ],
    )

    with pytest.raises(ValueError):
        cli.main()
