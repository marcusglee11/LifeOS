from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools" / "memory"
sys.path.insert(0, str(TOOLS))

import mcp_server  # noqa: E402


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "docs").mkdir()
    (repo / "knowledge-staging").mkdir()
    shutil.copytree(REPO_ROOT / "schemas", repo / "schemas")
    shutil.copytree(REPO_ROOT / "tools", repo / "tools")
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
        "title": "gateway retrieval topic",
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


def _capture_args(**overrides: object) -> dict:
    payload = {
        "session_id": "sess-capture",
        "agent": "Codex Lane",
        "iso_timestamp": "2026-04-29T01:23:45Z",
        "summary": "Gateway captures candidate packets only",
        "proposed_action": "create",
        "proposed_record_kind": "lesson",
        "proposed_authority_class": "agent_memory",
        "scope": "workflow",
        "sensitivity": "internal",
        "personal_inference": False,
        "promotion_basis": "synthetic gateway test candidate; human review required",
        "sources": [
            {
                "source_type": "manual_note",
                "locator": "gateway test",
                "quoted_evidence": "synthetic non-secret evidence",
                "captured_utc": "2026-04-29T01:23:45Z",
                "content_hash": "",
                "commit_sha": "",
            }
        ],
        "payload": {"title": "Gateway capture", "record_kind": "lesson", "scope": "workflow"},
    }
    payload.update(overrides)
    return payload


def _session_lines(repo: Path, session_id: str) -> list[dict]:
    path = repo / "knowledge-staging" / "_sessions" / f"{session_id}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _mcp_request(request_id: int, method: str, params: dict | None = None) -> dict:
    request = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        request["params"] = params
    return request


def _mcp_exchange(repo: Path, messages: list[dict]) -> list[dict]:
    input_text = "\n".join(json.dumps(message) for message in messages) + "\n"
    process = subprocess.Popen(
        [sys.executable, str(repo / "tools" / "memory" / "mcp_server.py")],
        cwd=repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(input_text, timeout=10)
    assert process.returncode == 0, stderr
    return [json.loads(line) for line in stdout.splitlines()]


def _mcp_session_prefix() -> list[dict]:
    return [
        _mcp_request(
            1,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        ),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    ]


def _structured_tool_result(response: dict) -> dict:
    result = response["result"]
    assert result["content"][0]["type"] == "text"
    return result["structuredContent"]


def test_exposes_only_v01_memory_tools() -> None:
    assert mcp_server.exposed_tool_names() == [
        "memory.retrieve",
        "memory.capture_candidate",
    ]
    assert [tool["name"] for tool in mcp_server.tool_definitions()] == [
        "memory.retrieve",
        "memory.capture_candidate",
    ]


def test_mcp_stdio_lists_exact_v01_memory_tools(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    responses = _mcp_exchange(
        repo,
        [
            *_mcp_session_prefix(),
            _mcp_request(2, "tools/list"),
        ],
    )

    assert responses[0]["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert [tool["name"] for tool in responses[1]["result"]["tools"]] == [
        "memory.retrieve",
        "memory.capture_candidate",
    ]


def test_mcp_stdio_retrieve_appends_session_log(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _front(
        repo / "memory" / "workflows" / "agent.md",
        _durable(id="MEM-MCP-RETRIEVE", authority_class="agent_memory"),
    )

    responses = _mcp_exchange(
        repo,
        [
            *_mcp_session_prefix(),
            _mcp_request(
                2,
                "tools/call",
                {
                    "name": "memory.retrieve",
                    "arguments": {
                        "session_id": "sess-mcp-retrieve",
                        "query": "gateway retrieval topic",
                        "scope": "workflow",
                        "authority_floor": "observation",
                        "limit": 5,
                    },
                },
            ),
        ],
    )

    payload = _structured_tool_result(responses[1])
    assert payload["ok"] is True
    assert [item["record_id"] for item in payload["results"]] == ["MEM-MCP-RETRIEVE"]
    log = _session_lines(repo, "sess-mcp-retrieve")[-1]
    assert log["tool"] == "memory.retrieve"
    assert log["result_ok"] is True


def test_mcp_stdio_capture_candidate_writes_candidate_and_session(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    responses = _mcp_exchange(
        repo,
        [
            *_mcp_session_prefix(),
            _mcp_request(
                2,
                "tools/call",
                {"name": "memory.capture_candidate", "arguments": _capture_args()},
            ),
        ],
    )

    payload = _structured_tool_result(responses[1])
    assert payload["ok"] is True
    assert (repo / payload["candidate_path"]).exists()
    log = _session_lines(repo, "sess-capture")[-1]
    assert log["tool"] == "memory.capture_candidate"
    assert log["candidate_path"] == payload["candidate_path"]


def test_mcp_stdio_unknown_tool_fails_closed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    responses = _mcp_exchange(
        repo,
        [
            *_mcp_session_prefix(),
            _mcp_request(
                2,
                "tools/call",
                {
                    "name": "memory.promote",
                    "arguments": {
                        "session_id": "sess-unknown",
                        "query": "gateway",
                    },
                },
            ),
        ],
    )

    assert responses[1]["result"]["isError"] is True
    payload = _structured_tool_result(responses[1])
    assert payload["ok"] is False
    assert any(item["code"] == "unknown_tool" for item in payload["findings"])


def test_gateway_calls_do_not_invoke_subprocess(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    calls: list[tuple] = []

    def fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
        calls.append((args, kwargs))
        raise AssertionError("subprocess.run must not be called")

    def fake_popen(*args, **kwargs):  # noqa: ANN002, ANN003
        calls.append((args, kwargs))
        raise AssertionError("subprocess.Popen must not be called")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    mcp_server.memory_retrieve(
        {
            "session_id": "sess-no-process",
            "query": "absent",
            "scope": "workflow",
            "authority_floor": "observation",
        },
        repo=repo,
    )
    mcp_server.memory_capture_candidate(_capture_args(session_id="sess-no-process"), repo=repo)
    assert calls == []
    source = (REPO_ROOT / "tools" / "memory" / "mcp_server.py").read_text(encoding="utf-8")
    assert "subprocess" not in source


def test_capture_writes_only_knowledge_staging_and_session_log(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    durable_marker = repo / "memory" / "workflows" / ".gitkeep"
    durable_marker.parent.mkdir(parents=True)
    durable_marker.write_text("", encoding="utf-8")
    durable_before = sorted(path.relative_to(repo) for path in (repo / "memory").rglob("*"))

    result = mcp_server.memory_capture_candidate(_capture_args(), repo=repo)

    assert result["ok"] is True
    assert result["candidate_path"].startswith("knowledge-staging/cand-20260429-codex-lane-")
    assert (repo / result["candidate_path"]).exists()
    assert sorted(path.relative_to(repo) for path in (repo / "memory").rglob("*")) == durable_before
    assert _session_lines(repo, "sess-capture")[-1]["candidate_path"] == result["candidate_path"]


def test_capture_candidate_collision_fails_closed_without_overwrite(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    args = _capture_args(session_id="sess-collision")
    first = mcp_server.memory_capture_candidate(args, repo=repo)
    candidate_path = repo / first["candidate_path"]
    before = candidate_path.read_text(encoding="utf-8")

    second = mcp_server.memory_capture_candidate(args, repo=repo)

    assert second["ok"] is False
    assert second["candidate_path"] == ""
    assert candidate_path.read_text(encoding="utf-8") == before
    assert any(item["code"] == "candidate_collision" for item in second["findings"])
    assert len(_session_lines(repo, "sess-collision")) == 2


def test_failed_candidate_collision_fails_closed_without_overwrite(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    args = _capture_args(session_id="sess-failed-collision", sources=[])
    first = mcp_server.memory_capture_candidate(args, repo=repo)
    failed_path = repo / first["candidate_path"]
    before = failed_path.read_text(encoding="utf-8")

    second = mcp_server.memory_capture_candidate(args, repo=repo)

    assert second["ok"] is False
    assert second["candidate_path"] == ""
    assert failed_path.read_text(encoding="utf-8") == before
    assert any(item["code"] == "candidate_collision" for item in second["findings"])
    assert len(_session_lines(repo, "sess-failed-collision")) == 2


def test_retrieve_denies_sensitive_with_empty_allowlist_and_logs(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = mcp_server.memory_retrieve(
        {
            "session_id": "sess-sensitive",
            "query": "gateway",
            "scope": "workflow",
            "authority_floor": "observation",
            "include_sensitive": True,
        },
        repo=repo,
    )
    assert result["ok"] is False
    assert result["results"] == []
    assert any(item["code"] == "sensitive_retrieval_denied" for item in result["findings"])
    log = _session_lines(repo, "sess-sensitive")[-1]
    assert log["tool"] == "memory.retrieve"
    assert log["result_ok"] is False


def test_canonical_doctrine_capture_rejected_before_candidate_persistence(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = mcp_server.memory_capture_candidate(
        _capture_args(
            session_id="sess-canon",
            proposed_authority_class="canonical_doctrine",
        ),
        repo=repo,
    )
    assert result["ok"] is False
    assert result["candidate_path"] == ""
    assert not list((repo / "knowledge-staging").glob("cand-*.md"))
    assert not list((repo / "knowledge-staging" / "_failed").glob("*.md"))
    assert any(item["code"] == "canonical_doctrine_rejected" for item in result["findings"])
    assert _session_lines(repo, "sess-canon")[-1]["candidate_id"] == result["candidate_id"]


def test_invalid_non_secret_candidate_quarantined_and_logged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = mcp_server.memory_capture_candidate(
        _capture_args(session_id="sess-invalid", sources=[]),
        repo=repo,
    )
    assert result["ok"] is False
    assert result["candidate_path"].startswith("knowledge-staging/_failed/CAND-")
    failed = repo / result["candidate_path"]
    assert failed.exists()
    assert "gateway_findings:" in failed.read_text(encoding="utf-8")
    assert any(item["code"] == "candidate_validation_failed" for item in result["findings"])
    assert _session_lines(repo, "sess-invalid")[-1]["candidate_path"] == result["candidate_path"]


def test_secret_failure_persists_no_raw_secret_material(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    raw_secret = "password=supersecret12345"
    result = mcp_server.memory_capture_candidate(
        _capture_args(
            session_id="sess-secret",
            summary=f"do not persist {raw_secret}",
            sources=[
                {
                    "source_type": "manual_note",
                    "locator": "gateway test",
                    "quoted_evidence": f"contains {raw_secret}",
                    "captured_utc": "2026-04-29T01:23:45Z",
                }
            ],
        ),
        repo=repo,
    )
    assert result["ok"] is False
    assert result["candidate_path"] == ""
    assert any(item["code"] == "secret_material_rejected" for item in result["findings"])
    persisted_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (repo / "knowledge-staging").rglob("*")
        if path.is_file()
    )
    assert raw_secret not in persisted_text
    assert "[REDACTED_SECRET]" in persisted_text


def test_secret_failure_redacts_agent_and_keyed_secret_fields(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    raw_agent_secret = "password=supersecret12345"
    raw_auth_secret = "Bearer abcdefghijklmnop"

    result = mcp_server.memory_capture_candidate(
        _capture_args(
            session_id="sess-keyed-secret",
            agent=f"Codex {raw_agent_secret}",
            payload={
                "title": "Gateway capture",
                "record_kind": "lesson",
                "scope": "workflow",
                "authorization": raw_auth_secret,
            },
        ),
        repo=repo,
    )

    assert result["ok"] is False
    assert result["candidate_path"] == ""
    assert any("detected at agent" in item["message"] for item in result["findings"])
    assert any(
        "detected at payload.authorization" in item["message"] for item in result["findings"]
    )
    persisted_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (repo / "knowledge-staging").rglob("*")
        if path.is_file()
    )
    assert raw_agent_secret not in persisted_text
    assert raw_auth_secret not in persisted_text
    assert _session_lines(repo, "sess-keyed-secret")[-1]["agent_claim"] == "[REDACTED_SECRET]"


def test_retrieve_preserves_phase1_ordering_metadata_and_gateway_filters(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _front(
        repo / "memory" / "workflows" / "agent.md",
        _durable(id="MEM-AGENT", authority_class="agent_memory"),
    )
    _front(
        repo / "memory" / "workflows" / "shared.md",
        _durable(id="MEM-SHARED", authority_class="shared_knowledge"),
    )
    _front(
        repo / "memory" / "workflows" / "canon.md",
        _durable(id="MEM-CANON", authority_class="canonical_doctrine"),
    )
    _front(
        repo / "memory" / "workflows" / "stale.md",
        _durable(id="MEM-STALE", lifecycle_state="stale"),
    )
    _front(
        repo / "memory" / "workflows" / "conflict.md",
        _durable(
            id="MEM-CONFLICT",
            lifecycle_state="conflicted",
            conflicts=[{"id": "CONFLICT-SYN", "status": "open", "materiality": "high"}],
        ),
    )
    result = mcp_server.memory_retrieve(
        {
            "session_id": "sess-retrieve",
            "query": "gateway retrieval topic",
            "scope": "workflow",
            "authority_floor": "observation",
            "limit": 10,
        },
        repo=repo,
    )
    assert result["ok"] is True
    ids = [item["record_id"] for item in result["results"]]
    assert ids == ["MEM-CANON", "MEM-SHARED", "MEM-AGENT"]
    assert result["results"][0]["authority_class"] == "canonical_doctrine"
    assert result["results"][0]["source_path"].startswith("memory/workflows/")
    assert _session_lines(repo, "sess-retrieve")[-1]["result_ok"] is True
