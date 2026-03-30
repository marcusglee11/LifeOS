from __future__ import annotations

import json
from pathlib import Path

from runtime.tools import openclaw_distill_lane as lane


def _write_health_receipt(
    tmp_path: Path, *, fingerprint: str, effective_mode: str = "active"
) -> Path:
    path = lane.health_path_for_state(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "effective_mode": effective_mode,
                "compatibility_fingerprint": fingerprint,
                "last_successful_preflight_fingerprint": fingerprint,
                "preflight_ok": True,
                "last_preflight_ts_utc": lane._utc_now(),  # noqa: SLF001
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_active_gate_receipts(tmp_path: Path, *, fingerprint: str) -> None:
    lane.shadow_success_receipt_path_for_state(tmp_path).write_text(
        json.dumps(
            {
                "compatibility_fingerprint": fingerprint,
                "ceo_approved": True,
            }
        ),
        encoding="utf-8",
    )
    lane.forced_failure_receipt_path_for_state(tmp_path).write_text(
        json.dumps(
            {
                "compatibility_fingerprint": fingerprint,
                "drill_passed": True,
            }
        ),
        encoding="utf-8",
    )


def test_classify_denies_protected_path_before_allow(tmp_path: Path) -> None:
    result = lane.classify_payload(
        source_path="artifacts/evidence/openclaw/receipts/example.txt",
        source_executable="openclaw",
        argv=["openclaw", "models", "status"],
        wrapper_command="coo openclaw -- models status",
        traffic_class="repo_scans",
        raw_payload_sha256="abc123",
        payload_bytes=16384,
        text_like=True,
        state_dir=tmp_path,
    )
    assert result["decision"] == "bypass"
    assert result["reason"] == "protected_path"


def test_classify_allows_models_status_active(tmp_path: Path) -> None:
    result = lane.classify_payload(
        source_path="",
        source_executable="openclaw",
        argv=["openclaw", "models", "status"],
        wrapper_command="coo openclaw -- models status",
        traffic_class="repo_scans",
        raw_payload_sha256="abc123",
        payload_bytes=16384,
        text_like=True,
        state_dir=tmp_path,
    )
    assert result["decision"] == "eligible_active"
    assert result["replacement_allowed"] is True


def test_classify_status_all_usage_shadow_only(tmp_path: Path) -> None:
    result = lane.classify_payload(
        source_path="",
        source_executable="openclaw",
        argv=["openclaw", "status", "--all", "--usage"],
        wrapper_command="coo openclaw -- status --all --usage",
        traffic_class="repo_scans",
        raw_payload_sha256="abc123",
        payload_bytes=16384,
        text_like=True,
        state_dir=tmp_path,
    )
    assert result["decision"] == "eligible_shadow"
    assert result["replacement_allowed"] is False


def test_classify_duplicate_hash_bypasses(tmp_path: Path) -> None:
    seen_path = tmp_path / "runtime" / "gates" / "distill" / lane.SEEN_HASHES_FILENAME
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps({"dup": "2026-03-07T00:00:00Z"}), encoding="utf-8")
    result = lane.classify_payload(
        source_path="",
        source_executable="openclaw",
        argv=["openclaw", "models", "status"],
        wrapper_command="coo openclaw -- models status",
        traffic_class="repo_scans",
        raw_payload_sha256="dup",
        payload_bytes=16384,
        text_like=True,
        state_dir=tmp_path,
    )
    assert result["reason"] == "duplicate_raw_hash"


def test_validate_output_schema_requires_template_id() -> None:
    ok, reason = lane._validate_output_schema(  # noqa: SLF001
        {
            "status": "ok",
            "summary": ["a"],
            "key_entities": ["x"],
            "raw_payload_sha256": "hash",
            "traffic_class": "repo_scans",
            "source_command": "openclaw models status",
        },
        template_id="actionable_faults",
        raw_payload_sha256="hash",
    )
    assert ok is False
    assert reason == "schema_failure"


def test_preflight_quick_lane_success(monkeypatch) -> None:
    def fake_run(cmd, *, env, timeout_s=30):  # type: ignore[no-untyped-def]
        assert "--agent" in cmd
        assert "quick" in cmd
        return 0, json.dumps({"payloads": [{"text": "READY"}]}), ""

    monkeypatch.setattr(lane, "_run", fake_run)
    result = lane.preflight_quick_lane(openclaw_bin="openclaw", profile="", env={})
    assert result["ok"] is True


def test_build_compatibility_fingerprint_normalizes_unknowns() -> None:
    fingerprint, payload = lane.build_compatibility_fingerprint(
        {
            "openclaw_version": "",
            "channel_if_known": None,  # type: ignore[arg-type]
            "cheap_lane_id": "Quick",
            "cheap_model_target": "",
            "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
        }
    )
    assert fingerprint
    assert payload["openclaw_version"] == lane.UNKNOWN_SENTINEL
    assert payload["channel_if_known"] == lane.UNKNOWN_SENTINEL
    assert payload["cheap_lane_id"] == "quick"
    assert payload["cheap_model_target"] == lane.UNKNOWN_SENTINEL


def test_resolve_effective_mode_requested_off_dominates(tmp_path: Path) -> None:
    effective_mode, cause, receipt = lane.resolve_effective_mode(
        requested_mode="off",
        state_dir=tmp_path,
        runtime_context={
            "openclaw_version": "v1",
            "channel_if_known": "stable",
            "cheap_lane_id": "quick",
            "cheap_model_target": "github-copilot/gpt-5-mini",
            "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
        },
    )
    assert effective_mode == "off"
    assert cause == lane.HEALTH_EVENT_CAUSE_REQUESTED_OFF
    assert receipt is None


def test_resolve_effective_mode_missing_health_receipt_forces_shadow(tmp_path: Path) -> None:
    effective_mode, cause, _receipt = lane.resolve_effective_mode(
        requested_mode="active",
        state_dir=tmp_path,
        runtime_context={
            "openclaw_version": "v1",
            "channel_if_known": "stable",
            "cheap_lane_id": "quick",
            "cheap_model_target": "github-copilot/gpt-5-mini",
            "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
        },
    )
    assert effective_mode == "shadow"
    assert cause == lane.HEALTH_EVENT_CAUSE_HEALTH_INVALID


def test_resolve_effective_mode_corrupt_health_receipt_forces_shadow(tmp_path: Path) -> None:
    path = lane.health_path_for_state(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")
    effective_mode, cause, _receipt = lane.resolve_effective_mode(
        requested_mode="active",
        state_dir=tmp_path,
        runtime_context={
            "openclaw_version": "v1",
            "channel_if_known": "stable",
            "cheap_lane_id": "quick",
            "cheap_model_target": "github-copilot/gpt-5-mini",
            "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
        },
    )
    assert effective_mode == "shadow"
    assert cause == lane.HEALTH_EVENT_CAUSE_HEALTH_INVALID


def test_health_path_uses_health_state_filename_and_reads_legacy_receipt(tmp_path: Path) -> None:
    assert lane.health_path_for_state(tmp_path).name == "health_state.json"
    legacy_path = lane.legacy_health_path_for_state(tmp_path)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(
        json.dumps(
            {
                "effective_mode": "shadow",
                "compatibility_fingerprint": "legacy-fingerprint",
                "last_successful_preflight_fingerprint": "legacy-fingerprint",
                "preflight_ok": True,
                "last_preflight_ts_utc": lane._utc_now(),  # noqa: SLF001
            }
        ),
        encoding="utf-8",
    )
    receipt, valid = lane._read_health_receipt(tmp_path)  # noqa: SLF001
    assert valid is True
    assert receipt is not None
    assert receipt["compatibility_fingerprint"] == "legacy-fingerprint"


def test_process_payload_active_without_health_receipt_bypasses_raw(
    monkeypatch, tmp_path: Path
) -> None:
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text("x" * 9000, encoding="utf-8")
    monkeypatch.setattr(
        lane,
        "build_runtime_context",
        lambda **_: {
            "openclaw_version": "v1",
            "channel_if_known": "stable",
            "cheap_lane_id": "quick",
            "cheap_model_target": "github-copilot/gpt-5-mini",
            "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
        },
    )
    args = lane.build_parser().parse_args(
        [
            "process",
            "--enabled",
            "--payload-file",
            str(payload_path),
            "--source-executable",
            "openclaw",
            "--argv-json",
            json.dumps(["openclaw", "models", "status"]),
            "--wrapper-command",
            "coo openclaw -- models status",
            "--traffic-class",
            "repo_scans",
            "--source-command",
            "openclaw models status",
            "--template-id",
            "actionable_faults",
            "--mode",
            "active",
            "--state-dir",
            str(tmp_path),
            "--openclaw-bin",
            "openclaw",
        ]
    )
    result = lane.process_payload(args)
    assert result["effective_mode"] == "shadow"
    assert result["replacement_allowed"] is False
    assert result["status"] == "bypass"
    assert result["bypass_reason"] == "health_state_invalid"


def test_process_payload_active_with_current_health_receipt_allows_replacement(
    monkeypatch, tmp_path: Path
) -> None:
    payload = "x" * 9000
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text(payload, encoding="utf-8")
    context = {
        "openclaw_version": "v1",
        "channel_if_known": "stable",
        "cheap_lane_id": "quick",
        "cheap_model_target": "github-copilot/gpt-5-mini",
        "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
    }
    fingerprint, _payload = lane.build_compatibility_fingerprint(context)
    _write_health_receipt(tmp_path, fingerprint=fingerprint)
    _write_active_gate_receipts(tmp_path, fingerprint=fingerprint)
    monkeypatch.setattr(lane, "build_runtime_context", lambda **_: context)
    monkeypatch.setattr(
        lane,
        "run_distill",
        lambda **_: (
            0,
            {
                "status": "ok",
                "template_id": "actionable_faults",
                "summary": ["fault"],
                "key_entities": ["openclaw"],
                "raw_payload_sha256": lane._compute_sha256(payload),  # noqa: SLF001
                "traffic_class": "repo_scans",
                "source_command": "openclaw models status",
                "bypass_reason": None,
            },
            "",
        ),
    )
    args = lane.build_parser().parse_args(
        [
            "process",
            "--enabled",
            "--payload-file",
            str(payload_path),
            "--source-executable",
            "openclaw",
            "--argv-json",
            json.dumps(["openclaw", "models", "status"]),
            "--wrapper-command",
            "coo openclaw -- models status",
            "--traffic-class",
            "repo_scans",
            "--source-command",
            "openclaw models status",
            "--template-id",
            "actionable_faults",
            "--mode",
            "active",
            "--state-dir",
            str(tmp_path),
            "--openclaw-bin",
            "openclaw",
        ]
    )
    result = lane.process_payload(args)
    assert result["effective_mode"] == "active"
    assert result["replacement_allowed"] is True
    assert result["status"] == "ok"


def test_process_payload_active_requires_shadow_receipt_and_forced_failure_drill(
    monkeypatch, tmp_path: Path
) -> None:
    payload = "x" * 9000
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text(payload, encoding="utf-8")
    context = {
        "openclaw_version": "v1",
        "channel_if_known": "stable",
        "cheap_lane_id": "quick",
        "cheap_model_target": "github-copilot/gpt-5-mini",
        "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
    }
    fingerprint, _payload = lane.build_compatibility_fingerprint(context)
    _write_health_receipt(tmp_path, fingerprint=fingerprint)
    monkeypatch.setattr(lane, "build_runtime_context", lambda **_: context)
    args = lane.build_parser().parse_args(
        [
            "process",
            "--enabled",
            "--payload-file",
            str(payload_path),
            "--source-executable",
            "openclaw",
            "--argv-json",
            json.dumps(["openclaw", "models", "status"]),
            "--wrapper-command",
            "coo openclaw -- models status",
            "--traffic-class",
            "repo_scans",
            "--source-command",
            "openclaw models status",
            "--template-id",
            "actionable_faults",
            "--mode",
            "active",
            "--state-dir",
            str(tmp_path),
            "--openclaw-bin",
            "openclaw",
        ]
    )
    result = lane.process_payload(args)
    assert result["effective_mode"] == "shadow"
    assert result["bypass_reason"] == "health_state_invalid"


def test_process_payload_active_requires_fresh_preflight(monkeypatch, tmp_path: Path) -> None:
    payload = "x" * 9000
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text(payload, encoding="utf-8")
    context = {
        "openclaw_version": "v1",
        "channel_if_known": "stable",
        "cheap_lane_id": "quick",
        "cheap_model_target": "github-copilot/gpt-5-mini",
        "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
    }
    fingerprint, _payload = lane.build_compatibility_fingerprint(context)
    health_path = _write_health_receipt(tmp_path, fingerprint=fingerprint)
    stale_receipt = json.loads(health_path.read_text(encoding="utf-8"))
    stale_receipt["last_preflight_ts_utc"] = "2000-01-01T00:00:00Z"
    health_path.write_text(json.dumps(stale_receipt), encoding="utf-8")
    _write_active_gate_receipts(tmp_path, fingerprint=fingerprint)
    monkeypatch.setattr(lane, "build_runtime_context", lambda **_: context)
    args = lane.build_parser().parse_args(
        [
            "process",
            "--enabled",
            "--payload-file",
            str(payload_path),
            "--source-executable",
            "openclaw",
            "--argv-json",
            json.dumps(["openclaw", "models", "status"]),
            "--wrapper-command",
            "coo openclaw -- models status",
            "--traffic-class",
            "repo_scans",
            "--source-command",
            "openclaw models status",
            "--template-id",
            "actionable_faults",
            "--mode",
            "active",
            "--state-dir",
            str(tmp_path),
            "--openclaw-bin",
            "openclaw",
        ]
    )
    result = lane.process_payload(args)
    assert result["effective_mode"] == "shadow"
    assert result["bypass_reason"] == "health_state_invalid"


def test_run_health_preflight_writes_health_receipt(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        lane,
        "build_runtime_context",
        lambda **_: {
            "openclaw_version": "v1",
            "channel_if_known": "stable",
            "cheap_lane_id": "quick",
            "cheap_model_target": "github-copilot/gpt-5-mini",
            "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
        },
    )
    monkeypatch.setattr(
        lane,
        "preflight_quick_lane",
        lambda **_: {"ok": True, "rc": 0, "stderr": "", "stdout": "READY"},
    )
    monkeypatch.setattr(
        lane,
        "probe_usage_visibility",
        lambda **_: {"ok": True, "rc": 0, "stderr": "", "stdout": "usage ok"},
    )
    monkeypatch.setattr(
        lane,
        "run_distill",
        lambda **_: (
            0,
            {
                "status": "ok",
                "template_id": lane.CANONICAL_PREFLIGHT_TEMPLATE_ID,
                "summary": ["preflight_fixture.py::test_smoke failed on auth token"],
                "key_entities": [lane.CANONICAL_PREFLIGHT_REQUIRED_ENTITY],
                "raw_payload_sha256": lane._compute_sha256(lane.CANONICAL_PREFLIGHT_PAYLOAD),  # noqa: SLF001
                "traffic_class": "repo_scans",
                "source_command": lane.CANONICAL_PREFLIGHT_FIXTURE_NAME,
                "bypass_reason": None,
            },
            "",
        ),
    )
    result = lane.run_health_preflight(
        state_dir=tmp_path,
        openclaw_bin="openclaw",
        profile="",
        env={},
        requested_mode="active",
    )
    assert result["ok"] is True
    receipt = json.loads(lane.health_path_for_state(tmp_path).read_text(encoding="utf-8"))
    assert receipt["preflight_ok"] is True
    assert receipt["last_successful_preflight_fingerprint"] == receipt["compatibility_fingerprint"]


def test_preflight_requires_distill_success_not_bypass(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        lane,
        "build_runtime_context",
        lambda **_: {
            "openclaw_version": "v1",
            "channel_if_known": "stable",
            "cheap_lane_id": "quick",
            "cheap_model_target": "github-copilot/gpt-5-mini",
            "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
        },
    )
    monkeypatch.setattr(
        lane,
        "preflight_quick_lane",
        lambda **_: {"ok": True, "rc": 0, "stderr": "", "stdout": "READY"},
    )
    monkeypatch.setattr(
        lane,
        "probe_usage_visibility",
        lambda **_: {"ok": True, "rc": 0, "stderr": "", "stdout": "usage ok"},
    )
    monkeypatch.setattr(
        lane,
        "run_distill",
        lambda **_: (
            0,
            {
                "status": "bypass",
                "template_id": lane.CANONICAL_PREFLIGHT_TEMPLATE_ID,
                "summary": [],
                "key_entities": [],
                "raw_payload_sha256": lane._compute_sha256(lane.CANONICAL_PREFLIGHT_PAYLOAD),  # noqa: SLF001
                "traffic_class": "repo_scans",
                "source_command": lane.CANONICAL_PREFLIGHT_FIXTURE_NAME,
                "bypass_reason": "distill_call_failed",
            },
            "",
        ),
    )
    result = lane.run_health_preflight(
        state_dir=tmp_path,
        openclaw_bin="openclaw",
        profile="",
        env={},
        requested_mode="active",
    )
    assert result["ok"] is False


def test_process_payload_emits_mode_transition_audit(monkeypatch, tmp_path: Path) -> None:
    payload = "x" * 9000
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text(payload, encoding="utf-8")
    context = {
        "openclaw_version": "v1",
        "channel_if_known": "stable",
        "cheap_lane_id": "quick",
        "cheap_model_target": "github-copilot/gpt-5-mini",
        "wrapper_schema_version": lane.WRAPPER_SCHEMA_VERSION,
    }
    fingerprint, _payload = lane.build_compatibility_fingerprint(context)
    _write_health_receipt(tmp_path, fingerprint=fingerprint, effective_mode="shadow")
    _write_active_gate_receipts(tmp_path, fingerprint=fingerprint)
    monkeypatch.setattr(lane, "build_runtime_context", lambda **_: context)
    monkeypatch.setattr(
        lane,
        "run_distill",
        lambda **_: (
            0,
            {
                "status": "ok",
                "template_id": "actionable_faults",
                "summary": ["fault"],
                "key_entities": ["openclaw"],
                "raw_payload_sha256": lane._compute_sha256(payload),  # noqa: SLF001
                "traffic_class": "repo_scans",
                "source_command": "openclaw models status",
                "bypass_reason": None,
            },
            "",
        ),
    )
    args = lane.build_parser().parse_args(
        [
            "process",
            "--enabled",
            "--payload-file",
            str(payload_path),
            "--source-executable",
            "openclaw",
            "--argv-json",
            json.dumps(["openclaw", "models", "status"]),
            "--wrapper-command",
            "coo openclaw -- models status",
            "--traffic-class",
            "repo_scans",
            "--source-command",
            "openclaw models status",
            "--template-id",
            "actionable_faults",
            "--mode",
            "active",
            "--state-dir",
            str(tmp_path),
            "--openclaw-bin",
            "openclaw",
        ]
    )
    lane.process_payload(args)
    audit_entries = [
        json.loads(line)
        for line in (tmp_path / "runtime" / "gates" / "distill" / lane.AUDIT_FILENAME)
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    transitions = [entry for entry in audit_entries if entry["event_type"] == "mode_transition"]
    assert transitions[-1]["from_mode"] == "shadow"
    assert transitions[-1]["to_mode"] == "active"
    assert transitions[-1]["cause"] == lane.HEALTH_EVENT_CAUSE_HEALTHY
