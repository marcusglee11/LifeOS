"""OpenClaw <-> Spine mapping helpers.

This module centralizes payload conversions between OpenClaw orchestration
inputs and LoopSpine execution/result contracts.
"""

from __future__ import annotations

from typing import Any, Mapping


OPENCLAW_JOB_KIND = "lifeos.job.v0.1"
OPENCLAW_RESULT_KIND = "lifeos.result.v0.2"


class OpenClawBridgeError(ValueError):
    """Raised when bridge payload mapping fails validation."""


def _require_non_empty_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OpenClawBridgeError(f"missing or invalid '{key}'")
    return value.strip()


def _normalize_string_list(value: Any, *, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise OpenClawBridgeError(f"'{key}' must be a list[str]")
    return [item.strip() for item in value if item.strip()]


def map_openclaw_job_to_spine_invocation(job_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map an OpenClaw job payload into a LoopSpine invocation payload."""
    kind = _require_non_empty_str(job_payload, "kind")
    if kind != OPENCLAW_JOB_KIND:
        raise OpenClawBridgeError(f"unsupported job kind: {kind}")

    job_id = _require_non_empty_str(job_payload, "job_id")
    objective = _require_non_empty_str(job_payload, "objective")
    workdir = _require_non_empty_str(job_payload, "workdir")
    command = _normalize_string_list(job_payload.get("command"), key="command")
    if not command:
        raise OpenClawBridgeError("'command' must include at least one token")

    timeout_s = job_payload.get("timeout_s")
    if not isinstance(timeout_s, int) or timeout_s <= 0:
        raise OpenClawBridgeError("missing or invalid 'timeout_s'")

    scope = _normalize_string_list(job_payload.get("scope"), key="scope")
    non_goals = _normalize_string_list(job_payload.get("non_goals"), key="non_goals")
    expected_artifacts = _normalize_string_list(
        job_payload.get("expected_artifacts"),
        key="expected_artifacts",
    )
    context_refs = _normalize_string_list(job_payload.get("context_refs"), key="context_refs")

    run_id = (
        str(job_payload["run_id"]).strip()
        if isinstance(job_payload.get("run_id"), str) and str(job_payload["run_id"]).strip()
        else f"openclaw:{job_id}"
    )

    task_spec = {
        "source": "openclaw",
        "job_id": job_id,
        "job_type": _require_non_empty_str(job_payload, "job_type"),
        "objective": objective,
        "workdir": workdir,
        "command": command,
        "constraints": {
            "scope": scope,
            "non_goals": non_goals,
            "timeout_s": timeout_s,
        },
        "expected_artifacts": expected_artifacts,
        "context_refs": context_refs,
    }

    return {
        "job_id": job_id,
        "run_id": run_id,
        "task_spec": task_spec,
    }


def map_spine_artifacts_to_openclaw_result(
    *,
    job_id: str,
    terminal_packet: Mapping[str, Any] | None = None,
    checkpoint_packet: Mapping[str, Any] | None = None,
    terminal_packet_ref: str | None = None,
    checkpoint_packet_ref: str | None = None,
) -> dict[str, Any]:
    """Map LoopSpine terminal/checkpoint packets into an OpenClaw result payload."""
    if bool(terminal_packet) == bool(checkpoint_packet):
        raise OpenClawBridgeError("provide exactly one of terminal_packet or checkpoint_packet")

    if terminal_packet is not None:
        run_id = _require_non_empty_str(terminal_packet, "run_id")
        result: dict[str, Any] = {
            "kind": OPENCLAW_RESULT_KIND,
            "job_id": job_id,
            "run_id": run_id,
            "state": "terminal",
            "outcome": _require_non_empty_str(terminal_packet, "outcome"),
            "reason": _require_non_empty_str(terminal_packet, "reason"),
            "terminal_at": _require_non_empty_str(terminal_packet, "timestamp"),
        }
        if terminal_packet_ref:
            result["terminal_packet_ref"] = terminal_packet_ref
        return result

    run_id = _require_non_empty_str(checkpoint_packet or {}, "run_id")
    result = {
        "kind": OPENCLAW_RESULT_KIND,
        "job_id": job_id,
        "run_id": run_id,
        "state": "checkpoint",
        "trigger": _require_non_empty_str(checkpoint_packet or {}, "trigger"),
        "checkpoint_id": _require_non_empty_str(checkpoint_packet or {}, "checkpoint_id"),
        "checkpoint_at": _require_non_empty_str(checkpoint_packet or {}, "timestamp"),
    }
    if checkpoint_packet_ref:
        result["checkpoint_packet_ref"] = checkpoint_packet_ref
    return result

