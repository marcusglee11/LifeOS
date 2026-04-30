from __future__ import annotations

import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from runtime.tools.workflow_pack import route_quality_tools, run_quality_gates
from scripts.workflow import workstream_context as wc

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "runtime/tests/fixtures/workstreams/context_v1/state.yaml"
STATE_SCHEMA = REPO_ROOT / "schemas/workstreams/workstream_state.schema.json"
REVIEWER_SCHEMA = REPO_ROOT / "schemas/workstreams/reviewer_result.schema.json"


def _load_fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _write_state(tmp_path: Path, state: dict) -> Path:
    path = tmp_path / "state.yaml"
    path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
    return path


def _validate_payload(
    tmp_path: Path,
    state: dict,
    *,
    now: datetime | None = None,
    relative_path: Path | None = None,
) -> wc.ValidationResult:
    original_repo_root = wc.REPO_ROOT
    original_schema_path = wc.SCHEMA_PATH
    original_workstreams_path = wc.WORKSTREAMS_PATH
    repo_root = tmp_path / "repo"
    schema_path = repo_root / "schemas/workstreams/workstream_state.schema.json"
    workstreams_path = repo_root / "artifacts/workstreams.yaml"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    workstreams_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(STATE_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")
    workstreams_path.write_text(
        (REPO_ROOT / "artifacts/workstreams.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    state_relative_path = relative_path or (
        Path("artifacts/workstreams") / state.get("slug", "missing") / "state.yaml"
    )
    state_path = repo_root / state_relative_path
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
    wc.REPO_ROOT = repo_root
    wc.SCHEMA_PATH = schema_path
    wc.WORKSTREAMS_PATH = workstreams_path
    try:
        return wc.validate_state(state_path, now=now)
    finally:
        wc.REPO_ROOT = original_repo_root
        wc.SCHEMA_PATH = original_schema_path
        wc.WORKSTREAMS_PATH = original_workstreams_path


def test_valid_fixture_passes_validation() -> None:
    result = wc.validate_state(FIXTURE, now=datetime(2026, 4, 30, 13, tzinfo=timezone.utc))
    assert result.ok, result.errors


def test_missing_required_fields_fail_validation(tmp_path: Path) -> None:
    state = _load_fixture()
    del state["completion_truth"]

    result = _validate_payload(tmp_path, state)

    assert not result.ok
    assert any("completion_truth" in error for error in result.errors)


def test_slug_validates_against_artifacts_workstreams_yaml(tmp_path: Path) -> None:
    state = _load_fixture()
    state["slug"] = "not_registered"

    result = _validate_payload(tmp_path, state)

    assert not result.ok
    assert any("not registered" in error for error in result.errors)


def test_current_yaml_alias_is_rejected(tmp_path: Path) -> None:
    state = _load_fixture()

    result = _validate_payload(
        tmp_path,
        state,
        relative_path=Path("artifacts/workstreams/current.yaml"),
    )

    assert not result.ok
    assert any("current.yaml alias is forbidden" in error for error in result.errors)


def test_non_canonical_state_path_is_rejected(tmp_path: Path) -> None:
    state = _load_fixture()

    result = _validate_payload(tmp_path, state, relative_path=Path("tmp/state.yaml"))

    assert not result.ok
    assert any("must be canonical" in error for error in result.errors)


def test_head_sha_required_once_implementation_phase_starts(tmp_path: Path) -> None:
    state = _load_fixture()
    state["lifecycle_state"] = "PAUSED"
    state["active_issue"]["phase"] = "implementation"
    state.pop("current_head_sha", None)
    state.pop("observed_main_sha", None)

    result = _validate_payload(tmp_path, state)

    assert not result.ok
    assert any("current_head_sha or observed_main_sha" in error for error in result.errors)


def test_stale_required_preflight_is_detected(tmp_path: Path) -> None:
    state = _load_fixture()
    state["tool_preflight"][0]["checked_at"] = "2026-04-28T12:00:00Z"
    state["tool_preflight"][0].pop("valid_until", None)
    state["tool_preflight"][0]["stale_after"] = "24h"

    result = _validate_payload(
        tmp_path,
        state,
        now=datetime(2026, 4, 30, 13, tzinfo=timezone.utc),
    )

    assert not result.ok
    assert any("stale" in error for error in result.errors)


def test_required_preflight_pass_without_evidence_fails_validation(tmp_path: Path) -> None:
    state = _load_fixture()
    state["tool_preflight"][0]["evidence_ref"] = ""

    result = _validate_payload(tmp_path, state)

    assert not result.ok
    assert any("PASS lacks evidence_ref" in error for error in result.errors)


def test_duration_parsing_for_24h_is_deterministic() -> None:
    assert wc.parse_duration("24h").total_seconds() == 24 * 60 * 60
    with pytest.raises(wc.WorkstreamContextError):
        wc.parse_duration("1.5h")


def test_unknown_required_preflight_allowed_only_before_relevant_phase(tmp_path: Path) -> None:
    state = _load_fixture()
    state["active_issue"]["phase"] = "implementation"
    premerge = state["tool_preflight"][1]
    premerge["status"] = "UNKNOWN"
    assert _validate_payload(tmp_path, state).ok

    state["active_issue"]["phase"] = "pre-merge"
    blocked = _validate_payload(tmp_path, state)
    assert not blocked.ok
    assert any("UNKNOWN" in error for error in blocked.errors)


def test_reviewer_result_accepts_pass_revise_block() -> None:
    schema = json.loads(REVIEWER_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    base = {
        "schema_version": "reviewer-result-v1",
        "slug": "context_v1",
        "reviewer": "AA",
        "created_at": "2026-04-30T12:00:00Z",
    }
    for verdict in ("PASS", "REVISE", "BLOCK"):
        payload = {**base, "verdict": verdict}
        assert list(validator.iter_errors(payload)) == []
    invalid = {**base, "verdict": "APPROVE"}
    assert list(validator.iter_errors(invalid))


def test_resume_prompt_contains_required_operational_fields() -> None:
    prompt = wc.emit_resume_prompt(FIXTURE)

    assert "Active issue: #102" in prompt
    assert "Phase: implementation" in prompt
    assert "Next action:" in prompt
    assert "Blockers:" in prompt
    assert "Do not start:" in prompt
    assert "chained_jobs" in prompt
    assert "Evidence refs and summaries only:" in prompt
    assert "claude_code_auth" in prompt
    assert "Completion truth requirements:" in prompt
    assert "State file alone never proves done/merged/closed." in prompt


def test_resume_prompt_does_not_inline_full_evidence_bodies() -> None:
    prompt = wc.emit_resume_prompt(FIXTURE)

    assert "issue-102-aa-approval" in prompt
    assert "AA approved revised spec" in prompt
    assert "FULL_EVIDENCE_BODY_SHOULD_NOT_APPEAR" not in prompt


def test_active_work_is_documented_as_non_canonical_advisory_generated() -> None:
    doc = (REPO_ROOT / "docs/02_protocols/workstream_context_v1.md").read_text(encoding="utf-8")
    lowered = doc.lower()
    assert ".context/active_work.yaml" in doc
    for required_word in ("advisory", "generated", "non-canonical", "never compete"):
        assert required_word in lowered


def test_state_schema_requires_tool_preflight_evidence_and_expiry() -> None:
    schema = json.loads(STATE_SCHEMA.read_text(encoding="utf-8"))
    state = _load_fixture()
    entry = copy.deepcopy(state["tool_preflight"][0])
    del entry["evidence_ref"]
    state["tool_preflight"] = [entry]
    errors = list(Draft202012Validator(schema).iter_errors(state))
    assert errors


def test_changed_scope_quality_routing_invokes_workstream_context_validation(monkeypatch) -> None:
    changed = [
        "artifacts/workstreams/context_v1/state.yaml",
        "schemas/workstreams/workstream_state.schema.json",
        "docs/02_protocols/workstream_context_v1.md",
        "scripts/workflow/workstream_context.py",
        "runtime/tests/fixtures/workstreams/context_v1/state.yaml",
    ]
    routed = route_quality_tools(REPO_ROOT, changed, scope="changed")
    assert routed["workstream_context"] == changed

    commands: list[list[str]] = []

    def fake_run(*args, **kwargs):
        command = args[0]
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="OK", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_quality_gates(REPO_ROOT, changed, scope="changed")

    assert result["passed"] is True
    assert any(row["tool"] == "workstream_context" for row in result["results"])
    assert any("scripts/workflow/workstream_context.py" in command for command in commands)


def test_changed_scope_quality_validates_current_yaml_alias_instead_of_fixture(monkeypatch) -> None:
    changed = ["artifacts/workstreams/current.yaml"]
    commands: list[list[str]] = []

    def fake_run(*args, **kwargs):
        command = args[0]
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="OK", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_quality_gates(
        REPO_ROOT,
        changed,
        scope="changed",
        tool_names=["workstream_context"],
    )

    assert result["passed"] is True
    assert any("artifacts/workstreams/current.yaml" in command for command in commands)
    assert not any(
        "runtime/tests/fixtures/workstreams/context_v1/state.yaml" in command
        for command in commands
    )


def test_changed_scope_quality_validates_every_changed_workstream_state(monkeypatch) -> None:
    changed = [
        "artifacts/workstreams/context_v1/state.yaml",
        "artifacts/workstreams/other_v1/state.yaml",
    ]
    commands: list[list[str]] = []

    def fake_run(*args, **kwargs):
        command = args[0]
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="OK", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_quality_gates(
        REPO_ROOT,
        changed,
        scope="changed",
        tool_names=["workstream_context"],
    )

    assert result["passed"] is True
    workstream_commands = [
        command for command in commands if "scripts/workflow/workstream_context.py" in command
    ]
    assert len(workstream_commands) == 1
    command = workstream_commands[0]
    assert "artifacts/workstreams/context_v1/state.yaml" in command
    assert "artifacts/workstreams/other_v1/state.yaml" in command


def test_cli_validate_and_emit_resume_prompt() -> None:
    validate = subprocess.run(
        [
            sys.executable,
            "scripts/workflow/workstream_context.py",
            "validate",
            "--state",
            str(FIXTURE.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert validate.returncode == 0, validate.stderr + validate.stdout
    assert '"ok": true' in validate.stdout

    resume = subprocess.run(
        [
            sys.executable,
            "scripts/workflow/workstream_context.py",
            "emit-resume-prompt",
            "--state",
            str(FIXTURE.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert resume.returncode == 0, resume.stderr
    assert "Active issue: #102" in resume.stdout
