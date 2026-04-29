from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools" / "memory"
sys.path.insert(0, str(TOOLS))

from new_record import build_payload  # noqa: E402
from retrieve import retrieve  # noqa: E402
from validate import validate_path  # noqa: E402


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "docs").mkdir()
    shutil.copytree(REPO_ROOT / "schemas", repo / "schemas")
    return repo


def _front(path: Path, payload: dict, body: str = "synthetic fixture\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + yaml.safe_dump(payload, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )


def _durable(**overrides: object) -> dict:
    payload = {
        "id": "MEM-SYN-0001",
        "title": "Synthetic durable record",
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


def _errors(path: Path, repo: Path) -> list[str]:
    return [finding["error"] for finding in validate_path(path, repo)]


def test_schema_required_fields_and_enum_enforcement(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    bad = _durable(record_kind="memory_blob")
    bad.pop("title")
    path = repo / "memory" / "workflows" / "bad.md"
    _front(path, bad)
    errors = _errors(path, repo)
    assert any("missing required field: title" in err for err in errors)
    assert any("invalid enum record_kind" in err for err in errors)


def test_durable_records_use_json_schema_validation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "memory" / "workflows" / "bad-schema.md"
    _front(path, _durable(sources=[]))
    errors = _errors(path, repo)
    assert any(err.startswith("sources:") for err in errors)
    assert "sources must be a non-empty list" in errors


def test_state_record_special_rules(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "memory" / "projects" / "state.md"
    _front(path, _durable(record_kind="state", scope="project"))
    errors = _errors(path, repo)
    assert "missing required field: state_observed_utc" in errors
    assert "missing required field: state_subject" in errors


def test_agent_scope_path_enforcement(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    wrong = repo / "memory" / "workflows" / "agent.md"
    _front(wrong, _durable(scope="agent", agent="Hermes"))
    assert any("memory/agents/<agent_name>" in err for err in _errors(wrong, repo))

    right = repo / "memory" / "agents" / "Hermes" / "agent.md"
    _front(right, _durable(scope="agent", agent="Hermes"))
    assert _errors(right, repo) == []


def test_candidate_derived_records_require_receipts(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "memory" / "workflows" / "candidate-derived.md"
    _front(path, _durable(derived_from_candidate=True, write_receipts=[]))
    assert "candidate-derived durable records require write_receipts" in _errors(path, repo)


def test_non_coo_durable_memory_writes_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "memory" / "workflows" / "bad-writer.md"
    _front(path, _durable(writer="Hermes"))
    errors = _errors(path, repo)
    assert any("writer == COO" in err for err in errors)
    assert any("direct non-COO durable write" in err for err in errors)


def test_repo_evidence_requires_commit_stable_provenance(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "memory" / "workflows" / "repo-evidence.md"
    source = {
        "source_type": "repo_file",
        "locator": "memory/workflows/example.md@main",
        "quoted_evidence": "synthetic fixture",
        "captured_utc": "2026-04-28T00:00:00Z",
        "content_hash": "",
        "commit_sha": "",
    }
    _front(path, _durable(sources=[source]))
    assert any("commit-stable provenance" in err for err in _errors(path, repo))


def test_conflict_and_supersession_fixtures_validate() -> None:
    fixtures = REPO_ROOT / "tests" / "memory" / "fixtures" / "synthetic"
    assert _errors(fixtures / "conflict_record.md", REPO_ROOT) == []
    assert _errors(fixtures / "supersession_edge.md", REPO_ROOT) == []


def test_synthetic_examples_and_hermes_openclaw_candidates_validate() -> None:
    fixtures = REPO_ROOT / "tests" / "memory" / "fixtures" / "synthetic"
    assert _errors(fixtures, REPO_ROOT) == []


def test_retrieval_ordering_and_hard_filters(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _front(
        repo / "memory" / "workflows" / "agent.md",
        _durable(
            id="MEM-AGENT",
            title="shared synthetic retrieval topic",
            authority_class="agent_memory",
        ),
    )
    _front(
        repo / "memory" / "workflows" / "shared.md",
        _durable(
            id="MEM-SHARED",
            title="shared synthetic retrieval topic",
            authority_class="shared_knowledge",
        ),
    )
    _front(
        repo / "memory" / "workflows" / "secret.md",
        _durable(id="MEM-SECRET", title="shared synthetic retrieval topic", sensitivity="secret"),
    )
    _front(
        repo / "memory" / "workflows" / "archived.md",
        _durable(
            id="MEM-ARCHIVED", title="shared synthetic retrieval topic", lifecycle_state="archived"
        ),
    )
    _front(
        repo / "memory" / "workflows" / "conflict.md",
        _durable(
            id="MEM-CONFLICT",
            title="shared synthetic retrieval topic",
            lifecycle_state="conflicted",
            conflicts=[{"id": "CONFLICT-SYN", "status": "open", "materiality": "high"}],
        ),
    )

    results = retrieve(
        repo,
        query="retrieval topic",
        scope="workflow",
        authority_floor="agent_memory",
        include_sensitive=False,
    )
    ids = [item["record_id"] for item in results]
    assert ids[:2] == ["MEM-SHARED", "MEM-AGENT"]
    assert "MEM-SECRET" not in ids
    assert "MEM-ARCHIVED" not in ids
    conflict = next(item for item in results if item["record_id"] == "MEM-CONFLICT")
    assert conflict["has_medium_high_conflict"] is True
    assert conflict["excluded_reason"] == "medium_high_conflict"


def test_retrieval_does_not_return_unmatched_conflicted_records(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _front(
        repo / "memory" / "workflows" / "unmatched-conflict.md",
        _durable(
            id="MEM-UNMATCHED-CONFLICT",
            title="unmatched synthetic conflict topic",
            lifecycle_state="conflicted",
            conflicts=[{"id": "CONFLICT-SYN", "status": "open", "materiality": "high"}],
        ),
    )

    results = retrieve(
        repo,
        query="absent retrieval term",
        scope="workflow",
        authority_floor="agent_memory",
        include_sensitive=False,
    )
    assert results == []


def test_generator_output_validity(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = repo / "knowledge-staging" / "generated.md"
    args = argparse.Namespace(
        mode="candidate",
        title="Generated Synthetic Candidate",
        record_id="CAND-GENERATED",
        record_kind="lesson",
        scope="workflow",
        agent=None,
        sensitivity="internal",
        retention_class="medium",
        classification="agent_memory_candidate",
        authority_class="agent_memory",
        authority_impact="low",
        proposed_action="create",
        source_agent="synthetic-fixture",
        source_packet_id="packet-generated",
        output=str(output),
    )
    payload, body, path = build_payload(args, interactive=False)
    _front(path, payload, body)
    assert _errors(output, repo) == []
