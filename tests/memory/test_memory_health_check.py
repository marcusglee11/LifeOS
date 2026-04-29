from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools" / "memory"
sys.path.insert(0, str(TOOLS))

import health_check  # noqa: E402


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "docs").mkdir()
    (repo / "memory" / "workflows").mkdir(parents=True)
    (repo / "memory" / "receipts").mkdir(parents=True)
    (repo / "knowledge-staging" / "_failed").mkdir(parents=True)
    (repo / "knowledge-staging" / "_sessions").mkdir(parents=True)
    (repo / "memory" / "README.md").write_text("# Memory\n", encoding="utf-8")
    (repo / "knowledge-staging" / "README.md").write_text("# Knowledge Staging\n", encoding="utf-8")
    shutil.copytree(REPO_ROOT / "schemas", repo / "schemas")
    (repo / "tools").mkdir()
    shutil.copytree(
        TOOLS,
        repo / "tools" / "memory",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    return repo


def _front(path: Path, payload: dict, body: str = "synthetic fixture\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + yaml.safe_dump(payload, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )


def _durable(**overrides: object) -> dict:
    payload = {
        "id": "MEM-HEALTH-0001",
        "title": "health retrieval topic",
        "record_kind": "lesson",
        "authority_class": "agent_memory",
        "scope": "workflow",
        "sensitivity": "internal",
        "retention_class": "long",
        "lifecycle_state": "active",
        "created_utc": "2026-04-28T00:00:00Z",
        "updated_utc": "2026-04-28T00:00:00Z",
        "review_after": "2026-07-28",
        "owner": "COO",
        "writer": "COO",
        "derived_from_candidate": False,
        "sources": [
            {
                "source_type": "manual_note",
                "locator": "synthetic fixture",
                "quoted_evidence": "synthetic fixture",
                "captured_utc": "2026-04-28T00:00:00Z",
                "content_hash": "",
                "commit_sha": "",
            }
        ],
        "conflicts": [],
        "write_receipts": [],
    }
    payload.update(overrides)
    return payload


def _candidate(**overrides: object) -> dict:
    payload = {
        "candidate_id": "CAND-HEALTH-0001",
        "source_agent": "Hermes",
        "source_packet_type": "health_test",
        "source_packet_id": "packet-health",
        "generated_utc": "2026-04-28T00:00:00Z",
        "proposed_action": "create",
        "proposed_record_kind": "lesson",
        "proposed_authority_class": "agent_memory",
        "scope": "workflow",
        "requires_human_review": True,
        "authority_impact": "low",
        "personal_inference": False,
        "sensitivity": "internal",
        "retention_class": "medium",
        "classification": "agent_memory_candidate",
        "staging_status": "candidate_packet",
        "promotion_basis": "synthetic health test candidate",
        "sources": [
            {
                "source_type": "manual_note",
                "locator": "synthetic fixture",
                "quoted_evidence": "synthetic fixture",
                "captured_utc": "2026-04-28T00:00:00Z",
                "content_hash": "",
                "commit_sha": "",
            }
        ],
        "summary": "Synthetic candidate remains staged for health test.",
        "payload": {"title": "Synthetic candidate", "record_kind": "lesson"},
    }
    payload.update(overrides)
    return payload


def _hash_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    hashes: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        hashes[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def test_memory_health_pass_case_writes_json_and_markdown(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _front(repo / "memory" / "workflows" / "record.md", _durable())

    payload = health_check.run_health_check(repo, timestamp="pass")

    assert payload["overall_status"] == "pass"
    report_dir = repo / payload["report_dir"]
    assert (report_dir / "memory_health_report.json").exists()
    assert (report_dir / "memory_health_report.md").exists()
    assert {check["status"] for check in payload["checks_run"]} == {"pass"}


def test_memory_health_warn_case_exits_zero(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _front(repo / "memory" / "workflows" / "record.md", _durable())
    _front(
        repo / "memory" / "workflows" / "stale.md",
        _durable(
            id="MEM-HEALTH-STALE",
            title="stale health retrieval topic",
            lifecycle_state="stale",
        ),
    )
    _front(repo / "knowledge-staging" / "cand-health.md", _candidate())
    _front(
        repo / "memory" / "receipts" / "receipt.md",
        {
            "receipt_id": "RCP-HEALTH-0001",
            "candidate_id": "CAND-HEALTH-0001",
            "disposition": "accepted",
            "target_record_id": "MEM-HEALTH-0001",
            "target_record_path": "memory/workflows/record.md",
            "decided_by": "COO",
            "decided_utc": "2026-04-28T00:00:00Z",
            "rationale": "synthetic accepted candidate",
            "source_agent": "Hermes",
            "source_packet_id": "packet-health",
        },
    )
    for suffix in ("one", "two"):
        _front(
            repo / "knowledge-staging" / "_failed" / f"CAND-FAILED-{suffix}.md",
            _candidate(
                candidate_id=f"CAND-FAILED-{suffix}",
                sources=[],
                gateway_findings=[{"severity": "error", "code": "candidate_validation_failed"}],
            ),
        )

    exit_code = health_check.main(["--repo-root", str(repo), "--timestamp", "warn"])
    payload = health_check.run_health_check(repo, timestamp="warn-second")
    codes = {issue["code"] for issue in payload["issues_found"]}

    assert exit_code == 0
    assert payload["overall_status"] == "warn"
    assert "nonactive_record_retrievable_by_default" in codes
    assert "accepted_candidate_still_staged" in codes
    assert "repeated_failed_candidate_pattern" in codes


def test_memory_health_fail_case_exits_nonzero(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    bad = _durable()
    bad.pop("title")
    _front(repo / "memory" / "workflows" / "bad.md", bad)

    exit_code = health_check.main(["--repo-root", str(repo), "--timestamp", "fail"])
    payload = health_check.run_health_check(repo, timestamp="fail-second")

    assert exit_code == 1
    assert payload["overall_status"] == "fail"
    assert any(
        issue["code"] == "durable_record_validation_failed" for issue in payload["issues_found"]
    )


def test_memory_health_does_not_write_memory_or_promote_candidates(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _front(repo / "memory" / "workflows" / "record.md", _durable())
    _front(repo / "knowledge-staging" / "cand-health.md", _candidate())
    memory_before = _hash_tree(repo / "memory")
    staging_candidates_before = _hash_tree(repo / "knowledge-staging")

    payload = health_check.run_health_check(repo, timestamp="no-mutation")

    assert payload["overall_status"] == "pass"
    assert _hash_tree(repo / "memory") == memory_before
    staging_after = _hash_tree(repo / "knowledge-staging")
    for path, digest in staging_candidates_before.items():
        assert staging_after[path] == digest
    assert not list((repo / "memory" / "receipts").glob("*.md"))
