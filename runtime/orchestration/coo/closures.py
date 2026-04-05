"""Validation and I/O helpers for file-based COO coordination artifacts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.util.atomic_write import atomic_write_text

SPRINT_CLOSE_SCHEMA_VERSION = "sprint_close_packet.v1"
SESSION_CONTEXT_SCHEMA_VERSION = "session_context_packet.v1"
COUNCIL_REQUEST_SCHEMA_VERSION = "council_request.v1"

_VALID_AGENTS = {"codex", "claude_code", "gemini", "opencode"}
_VALID_OUTCOMES = {"success", "partial", "blocked"}


class ClosureValidationError(ValueError):
    """Raised when a closure artifact fails validation."""


def _require_string(payload: dict[str, Any], field: str) -> str:
    value = str(payload.get(field, "")).strip()
    if not value:
        raise ClosureValidationError(f"Missing required field {field!r}")
    return value


def _require_string_list(payload: dict[str, Any], field: str) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ClosureValidationError(f"Field {field!r} must be a list")
    return [str(item) for item in value]


def _require_bool(payload: dict[str, Any], field: str) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        raise ClosureValidationError(f"Field {field!r} must be a bool")
    return value


def _parse_iso8601(value: str, field: str) -> datetime:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ClosureValidationError(f"Field {field!r} must be an ISO-8601 timestamp") from exc


def _dump_yaml(payload: dict[str, Any]) -> str:
    return yaml.dump(payload, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _closures_dir(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "dispatch" / "closures"


def _session_context_dir(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "for_ceo"


def validate_sprint_close_packet(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ClosureValidationError("Sprint-close payload must be a mapping")
    if payload.get("schema_version") != SPRINT_CLOSE_SCHEMA_VERSION:
        raise ClosureValidationError(
            f"Unsupported schema_version {payload.get('schema_version')!r} for sprint-close packet"
        )
    _require_string(payload, "order_id")
    _require_string(payload, "task_ref")
    agent = _require_string(payload, "agent")
    if agent not in _VALID_AGENTS:
        raise ClosureValidationError(f"agent must be one of {sorted(_VALID_AGENTS)}")
    outcome = _require_string(payload, "outcome")
    if outcome not in _VALID_OUTCOMES:
        raise ClosureValidationError(f"outcome must be one of {sorted(_VALID_OUTCOMES)}")
    _parse_iso8601(_require_string(payload, "closed_at"), "closed_at")
    _require_string_list(payload, "evidence_paths")
    _require_string_list(payload, "open_items")
    _require_string_list(payload, "suggested_next_task_ids")
    _require_string_list(payload, "state_mutations")
    _require_string(payload, "sync_check_result")


def validate_session_context_packet(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ClosureValidationError("Session-context payload must be a mapping")
    if payload.get("schema_version") != SESSION_CONTEXT_SCHEMA_VERSION:
        raise ClosureValidationError(
            f"Unsupported schema_version {payload.get('schema_version')!r}"
            " for session-context packet"
        )
    _require_string(payload, "author")
    written_at = _parse_iso8601(_require_string(payload, "written_at"), "written_at")
    _require_string(payload, "subject")
    _require_string(payload, "context")
    _require_string_list(payload, "decisions_needed")
    _require_string_list(payload, "related_tasks")
    expires_at = _parse_iso8601(_require_string(payload, "expires_at"), "expires_at")
    if expires_at < written_at:
        raise ClosureValidationError("expires_at must not be earlier than written_at")


def validate_council_request_packet(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ClosureValidationError("Council-request payload must be a mapping")
    if payload.get("schema_version") != COUNCIL_REQUEST_SCHEMA_VERSION:
        raise ClosureValidationError(
            f"Unsupported schema_version {payload.get('schema_version')!r} for council request"
        )
    _require_string(payload, "request_id")
    _parse_iso8601(_require_string(payload, "requested_at"), "requested_at")
    _require_string(payload, "trigger")
    _require_string(payload, "question")
    _require_string(payload, "context_summary")
    _require_string_list(payload, "suggested_respondents")
    options = payload.get("options")
    if not isinstance(options, list) or not options:
        raise ClosureValidationError("Field 'options' must be a non-empty list")
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            raise ClosureValidationError(f"options[{index}] must be a mapping")
        _require_string(option, "label")
        _require_string(option, "description")
    _require_bool(payload, "requires_quorum")
    _require_string_list(payload, "related_tasks")
    resolved = _require_bool(payload, "resolved")
    resolved_at = str(payload.get("resolved_at", "") or "").strip()
    if resolved:
        if not resolved_at:
            raise ClosureValidationError("resolved_at is required when resolved is true")
        _parse_iso8601(resolved_at, "resolved_at")
    elif resolved_at:
        _parse_iso8601(resolved_at, "resolved_at")


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ClosureValidationError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ClosureValidationError(f"{path} must contain a YAML mapping")
    return payload


def load_closures(repo_root: Path) -> list[dict[str, Any]]:
    closures_dir = _closures_dir(repo_root)
    if not closures_dir.exists():
        return []

    packets: list[dict[str, Any]] = []
    for path in sorted(list(closures_dir.glob("SC-*.yaml")) + list(closures_dir.glob("CR-*.yaml"))):
        payload = _load_yaml(path)
        schema_version = str(payload.get("schema_version", "")).strip()
        if path.name.startswith("SC-"):
            if schema_version != SPRINT_CLOSE_SCHEMA_VERSION:
                raise ClosureValidationError(
                    f"{path} has filename SC-* but schema_version {schema_version!r}"
                )
            validate_sprint_close_packet(payload)
        elif path.name.startswith("CR-"):
            if schema_version != COUNCIL_REQUEST_SCHEMA_VERSION:
                raise ClosureValidationError(
                    f"{path} has filename CR-* but schema_version {schema_version!r}"
                )
            validate_council_request_packet(payload)
        packets.append(payload)
    return packets


def load_session_context_packets(repo_root: Path) -> list[dict[str, Any]]:
    context_dir = _session_context_dir(repo_root)
    if not context_dir.exists():
        return []

    packets: list[dict[str, Any]] = []
    for path in sorted(context_dir.glob("SCP-*.yaml")):
        payload = _load_yaml(path)
        schema_version = str(payload.get("schema_version", "")).strip()
        if schema_version != SESSION_CONTEXT_SCHEMA_VERSION:
            raise ClosureValidationError(
                f"{path} has filename SCP-* but schema_version {schema_version!r}"
            )
        validate_session_context_packet(payload)
        packets.append(payload)
    return packets


def write_sprint_close_packet(
    *,
    repo_root: Path,
    order_id: str,
    task_ref: str,
    agent: str,
    outcome: str,
    evidence_paths: list[str],
    open_items: list[str],
    suggested_next_task_ids: list[str],
    state_mutations: list[str],
    sync_check_result: str,
    closed_at: str | None = None,
) -> Path:
    payload = {
        "schema_version": SPRINT_CLOSE_SCHEMA_VERSION,
        "order_id": order_id,
        "task_ref": task_ref,
        "agent": agent,
        "closed_at": closed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "outcome": outcome,
        "evidence_paths": evidence_paths,
        "open_items": open_items,
        "suggested_next_task_ids": suggested_next_task_ids,
        "state_mutations": state_mutations,
        "sync_check_result": sync_check_result,
    }
    validate_sprint_close_packet(payload)
    out_dir = _closures_dir(repo_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"SC-{order_id}.yaml"
    atomic_write_text(path, _dump_yaml(payload))
    return path


def write_council_request_packet(
    *,
    repo_root: Path,
    request_id: str,
    trigger: str,
    question: str,
    context_summary: str,
    suggested_respondents: list[str],
    options: list[dict[str, str]],
    requires_quorum: bool,
    related_tasks: list[str],
    resolved: bool = False,
    resolved_at: str | None = None,
    requested_at: str | None = None,
) -> Path:
    payload = {
        "schema_version": COUNCIL_REQUEST_SCHEMA_VERSION,
        "request_id": request_id,
        "requested_at": requested_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "trigger": trigger,
        "question": question,
        "context_summary": context_summary,
        "suggested_respondents": suggested_respondents,
        "options": options,
        "requires_quorum": requires_quorum,
        "related_tasks": related_tasks,
        "resolved": resolved,
        "resolved_at": resolved_at,
    }
    validate_council_request_packet(payload)
    out_dir = _closures_dir(repo_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"CR-{request_id}.yaml"
    atomic_write_text(path, _dump_yaml(payload))
    return path


def default_session_context_expiry(written_at: str) -> str:
    """Return the default Build Handoff TTL of written_at + 72h."""
    expires_at = _parse_iso8601(written_at, "written_at") + timedelta(hours=72)
    return expires_at.isoformat().replace("+00:00", "Z")
