from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools" / "memory"
sys.path.insert(0, str(TOOLS))

import hermes_native_audit as audit  # noqa: E402


class GatewaySpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], Path, str | None]] = []

    def __call__(
        self,
        name: str,
        args: dict[str, Any],
        *,
        repo: Path,
        transport_identity: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append((name, args, repo, transport_identity))
        assert transport_identity == "hermes-native-audit"
        if name == "memory.retrieve":
            return {
                "ok": True,
                "results": [{"record_id": "MEM-GATEWAY-CONTEXT"}],
                "session_log_path": "knowledge-staging/_sessions/hermes-native-audit.jsonl",
            }
        if name == "memory.capture_candidate":
            assert args["proposed_authority_class"] != "canonical_doctrine"
            return {
                "ok": True,
                "candidate_id": "CAND-SPY",
                "candidate_path": "knowledge-staging/cand-spy.md",
                "session_log_path": "knowledge-staging/_sessions/hermes-native-audit.jsonl",
                "findings": [],
            }
        raise AssertionError(f"unexpected tool: {name}")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "docs").mkdir()
    (repo / "memory" / "workflows").mkdir(parents=True)
    (repo / "knowledge-staging" / "_sessions").mkdir(parents=True)
    (repo / "knowledge-staging" / "_failed").mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "schemas", repo / "schemas")
    return repo


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(repo: Path, snapshot: Path, gateway: GatewaySpy) -> dict[str, Any]:
    return audit.run_audit(
        snapshot_paths=[snapshot],
        repo=repo,
        session_id="sess-hermes-audit",
        iso_timestamp="2026-04-29T00:00:00Z",
        gateway_call=gateway,
    )


def test_deterministic_classification_and_report_output(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot = repo / "MEMORY.md"
    _write(
        snapshot,
        "\n".join(
            [
                "# Hermes memory",
                "- [candidate_handoff] class=shared_knowledge kind=lesson gateway stays generic",
                "- [pointer_only] See memory/workflows/gateway.md for boundary",
                "- [archive_observation] stale direct write note",
                "- Native-only scratch note",
                "- [discard] obsolete temporary note",
            ]
        ),
    )

    first = _run(repo, snapshot, GatewaySpy())
    second = _run(repo, snapshot, GatewaySpy())

    assert audit.render_report(first) == audit.render_report(second)
    assert [entry["disposition"] for entry in first["entries"]] == [
        "candidate_handoff",
        "pointer_only",
        "archive_observation",
        "keep_native",
        "discard",
    ]
    assert first["summary"]["by_disposition"] == {
        "archive_observation": 1,
        "candidate_handoff": 1,
        "discard": 1,
        "keep_native": 1,
        "pointer_only": 1,
    }
    assert first["gateway_boundary"]["capture_tool"] == "memory.capture_candidate"
    assert first["gateway_boundary"]["retrieval_tool"] == "memory.retrieve"


def test_candidate_handoff_delegates_to_gateway_without_direct_candidate_file(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    snapshot = repo / "USER.md"
    _write(snapshot, "- remember: class=agent_memory kind=lesson Hermes should use gateway handoff")
    gateway = GatewaySpy()

    report = _run(repo, snapshot, gateway)

    assert [call[0] for call in gateway.calls] == ["memory.retrieve", "memory.capture_candidate"]
    capture_args = gateway.calls[1][1]
    assert capture_args["agent"] == "Hermes"
    assert capture_args["proposed_authority_class"] == "agent_memory"
    assert capture_args["sources"][0]["locator"] == "USER.md:1"
    assert not list((repo / "knowledge-staging").glob("cand-*.md"))
    assert report["entries"][0]["handoff"]["candidate_path"] == "knowledge-staging/cand-spy.md"


def test_retrieval_context_uses_gateway_call_tool(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot = repo / "MEMORY.md"
    _write(snapshot, "- learned lesson: class=observation kind=fact workflow boundary")
    gateway = GatewaySpy()

    report = _run(repo, snapshot, gateway)

    assert gateway.calls[0][0] == "memory.retrieve"
    assert gateway.calls[0][1]["authority_floor"] == "observation"
    assert report["entries"][0]["retrieval"] == {
        "called": True,
        "ok": True,
        "result_count": 1,
        "session_log_path": "knowledge-staging/_sessions/hermes-native-audit.jsonl",
        "tool": "memory.retrieve",
    }


def test_compaction_report_only_no_durable_or_native_mutation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    memory_record = repo / "memory" / "workflows" / "existing.md"
    memory_md = repo / "MEMORY.md"
    user_md = repo / "USER.md"
    _write(memory_record, "durable marker\n")
    _write(memory_md, "- [archive_observation] stale Hermes native entry\n")
    _write(user_md, "- Native user note\n")
    durable_before = {
        path.relative_to(repo).as_posix(): path.read_text(encoding="utf-8")
        for path in (repo / "memory").rglob("*")
        if path.is_file()
    }
    memory_before = memory_md.read_text(encoding="utf-8")
    user_before = user_md.read_text(encoding="utf-8")
    report_path = tmp_path / "hermes-audit.json"

    report = audit.run_audit(
        snapshot_paths=[memory_md, user_md],
        repo=repo,
        session_id="sess-hermes-audit",
        iso_timestamp="2026-04-29T00:00:00Z",
        gateway_call=GatewaySpy(),
    )
    audit.write_report(report, report_path, repo=repo)

    durable_after = {
        path.relative_to(repo).as_posix(): path.read_text(encoding="utf-8")
        for path in (repo / "memory").rglob("*")
        if path.is_file()
    }
    assert durable_after == durable_before
    assert memory_md.read_text(encoding="utf-8") == memory_before
    assert user_md.read_text(encoding="utf-8") == user_before
    assert json.loads(report_path.read_text(encoding="utf-8"))["compaction"] == {
        "mutated_native_files": False,
        "recommendation_only": True,
    }
    with pytest.raises(ValueError, match="durable memory"):
        audit.write_report(report, repo / "memory" / "audit.json", repo=repo)


def test_canonical_doctrine_capture_not_attempted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot = repo / "MEMORY.md"
    _write(snapshot, "- [candidate_handoff] class=canonical_doctrine kind=rule forbidden capture")
    gateway = GatewaySpy()

    report = _run(repo, snapshot, gateway)

    assert [call[0] for call in gateway.calls] == ["memory.retrieve"]
    entry = report["entries"][0]
    assert entry["disposition"] == "discard"
    assert entry["handoff"] == {"attempted": False, "ok": None, "tool": "memory.capture_candidate"}
    assert "canonical_doctrine_capture_rejected" in entry["reasons"]


def test_secret_entries_are_redacted_and_rejected_before_gateway_or_report(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    snapshot = repo / "MEMORY.md"
    raw_secret = "password=" + "fixturevalue123"
    _write(snapshot, f"- remember: class=agent_memory do not persist {raw_secret}\n")
    gateway = GatewaySpy()
    report_path = tmp_path / "hermes-secret-audit.json"

    report = _run(repo, snapshot, gateway)
    audit.write_report(report, report_path, repo=repo)
    persisted_report = report_path.read_text(encoding="utf-8")

    assert gateway.calls == []
    assert raw_secret not in persisted_report
    assert "[REDACTED_SECRET]" in persisted_report
    entry = json.loads(persisted_report)["entries"][0]
    assert entry["disposition"] == "discard"
    assert entry["retrieval"]["called"] is False
    assert entry["handoff"]["attempted"] is False
    assert any(reason.startswith("secret_material_rejected") for reason in entry["reasons"])


def test_audit_source_has_no_process_or_vcs_invocation() -> None:
    source = (TOOLS / "hermes_native_audit.py").read_text(encoding="utf-8")

    assert "subprocess" not in source
    assert re.search(r"\b(?:git|gh)\b", source) is None
