#!/usr/bin/env python3
"""Validate and resume LifeOS workstream context v1 state."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "workstreams" / "workstream_state.schema.json"
WORKSTREAMS_PATH = REPO_ROOT / "artifacts" / "workstreams.yaml"
PHASE_ORDER = {
    "pre-implementation": 10,
    "spec-approved": 15,
    "implementation": 20,
    "review": 30,
    "pre-merge": 40,
    "merge": 50,
    "post-merge": 60,
    "closed": 70,
}
DURATION_RE = re.compile(r"^(?P<count>[1-9][0-9]*)(?P<unit>[smhd])$")


class WorkstreamContextError(ValueError):
    """Raised when workstream context validation fails."""


class ValidationResult:
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise WorkstreamContextError(f"{field_name} must be a non-empty ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkstreamContextError(f"{field_name} is not valid ISO-8601: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_duration(value: str) -> timedelta:
    """Parse deterministic compact durations such as 24h."""
    match = DURATION_RE.match(value)
    if not match:
        raise WorkstreamContextError(
            f"duration must use positive integer plus unit s/m/h/d: {value}"
        )
    count = int(match.group("count"))
    unit = match.group("unit")
    if unit == "s":
        return timedelta(seconds=count)
    if unit == "m":
        return timedelta(minutes=count)
    if unit == "h":
        return timedelta(hours=count)
    if unit == "d":
        return timedelta(days=count)
    raise WorkstreamContextError(f"unsupported duration unit: {unit}")


def _phase_rank(phase: str) -> int:
    normalized = str(phase or "").strip().lower()
    if not normalized:
        return 0
    return PHASE_ORDER.get(normalized, 10_000)


def _check_schema(state: dict[str, Any]) -> list[str]:
    schema = _load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"schema:{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(state), key=lambda item: list(item.path))
    ]


def _registered_workstream_slugs() -> set[str]:
    loaded = _load_yaml(WORKSTREAMS_PATH) or {}
    if not isinstance(loaded, dict):
        raise WorkstreamContextError("artifacts/workstreams.yaml must be a mapping")
    return {str(key) for key in loaded}


def _check_slug(state: dict[str, Any]) -> list[str]:
    slug = str(state.get("slug", "")).strip()
    if not slug:
        return ["slug is required"]
    if slug not in _registered_workstream_slugs():
        return [f"slug {slug!r} is not registered in artifacts/workstreams.yaml"]
    return []


def _repo_relative_path(state_path: Path) -> Path | None:
    try:
        return state_path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return None


def _check_state_path(state_path: Path, state: dict[str, Any]) -> list[str]:
    slug = str(state.get("slug", "")).strip()
    rel = _repo_relative_path(state_path)
    if rel is None:
        return ["state path must live under the LifeOS repo"]
    parts = rel.parts
    canonical = Path("artifacts") / "workstreams" / slug / "state.yaml"
    fixture = Path("runtime") / "tests" / "fixtures" / "workstreams" / slug / "state.yaml"
    if rel == canonical or rel == fixture:
        return []
    if parts[:2] == ("artifacts", "workstreams"):
        if rel.name == "current.yaml":
            return ["artifacts/workstreams/current.yaml alias is forbidden in v1"]
        return [f"workstream state path must be {canonical.as_posix()}"]
    return [
        "state path must be canonical artifacts/workstreams/<slug>/state.yaml "
        "or a runtime/tests fixture"
    ]


def _check_head_fields(state: dict[str, Any]) -> list[str]:
    lifecycle = str(state.get("lifecycle_state", "")).strip().upper()
    active_issue = state.get("active_issue") or {}
    phase = str(active_issue.get("phase", "")).strip()
    implementation_started = lifecycle in {
        "ACTIVE",
        "BLOCKED",
        "COMPLETE",
        "CLOSED",
    } or _phase_rank(phase) >= _phase_rank("implementation")
    if not implementation_started:
        return []
    if state.get("current_head_sha") or state.get("observed_main_sha"):
        return []
    return ["current_head_sha or observed_main_sha is required once implementation starts"]


def _is_phase_required(current_phase: str, entry_phase: str) -> bool:
    return _phase_rank(current_phase) >= _phase_rank(entry_phase)


def _expiry_for_entry(entry: dict[str, Any]) -> datetime | None:
    if entry.get("valid_until"):
        return _parse_datetime(entry.get("valid_until"), "tool_preflight.valid_until")
    if entry.get("stale_after"):
        checked_at = _parse_datetime(entry.get("checked_at"), "tool_preflight.checked_at")
        return checked_at + parse_duration(str(entry["stale_after"]))
    return None


def _check_tool_preflight(state: dict[str, Any], *, now: datetime) -> list[str]:
    errors: list[str] = []
    current_phase = str((state.get("active_issue") or {}).get("phase", "")).strip()
    entries = state.get("tool_preflight") or []
    if not isinstance(entries, list):
        return ["tool_preflight must be a list"]
    required_fields = {
        "status",
        "checked_at",
        "evidence_ref",
        "required",
        "scope",
        "phase",
        "failure_reason",
    }
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"tool_preflight[{index}] must be a mapping")
            continue
        name = str(entry.get("name") or f"#{index}")
        missing = sorted(field for field in required_fields if field not in entry)
        if missing:
            errors.append(f"tool_preflight[{name}] missing fields: {', '.join(missing)}")
        if not (entry.get("stale_after") or entry.get("valid_until")):
            errors.append(f"tool_preflight[{name}] must include stale_after or valid_until")
        required_now = bool(entry.get("required")) and _is_phase_required(
            current_phase,
            str(entry.get("phase", "")),
        )
        status = str(entry.get("status", "")).strip().upper()
        evidence_ref = str(entry.get("evidence_ref") or "").strip()
        if bool(entry.get("required")) and status == "PASS" and not evidence_ref:
            errors.append(f"tool_preflight[{name}] required PASS lacks evidence_ref")
        if required_now and status in {"FAIL", "SKIPPED"}:
            reason = str(entry.get("failure_reason") or "").strip()
            suffix = f": {reason}" if reason else ""
            errors.append(f"tool_preflight[{name}] required check is {status}{suffix}")
        if required_now and status == "UNKNOWN":
            errors.append(
                f"tool_preflight[{name}] required check is UNKNOWN for phase {current_phase}"
            )
        try:
            expiry = _expiry_for_entry(entry)
        except WorkstreamContextError as exc:
            errors.append(f"tool_preflight[{name}] {exc}")
            continue
        if required_now and expiry is not None and expiry < now:
            errors.append(f"tool_preflight[{name}] required check is stale")
    return errors


def _check_completion_truth(state: dict[str, Any]) -> list[str]:
    completion_truth = state.get("completion_truth") or {}
    required = completion_truth.get("required") or []
    refs = completion_truth.get("refs") or []
    errors = []
    if not required:
        errors.append("completion_truth.required must name external completion proof")
    if not refs:
        errors.append("completion_truth.refs must name authoritative external refs")
    joined = "\n".join(str(item) for item in required + refs).lower()
    if "state.yaml alone" not in joined and "not state.yaml" not in joined:
        errors.append("completion_truth must state that state.yaml alone never proves done")
    return errors


def validate_state(state_path: Path, *, now: datetime | None = None) -> ValidationResult:
    state = _load_yaml(state_path)
    errors: list[str] = []
    if not isinstance(state, dict):
        return ValidationResult(["state document must be a mapping"])
    now_utc = now or datetime.now(timezone.utc)
    errors.extend(_check_schema(state))
    errors.extend(_check_slug(state))
    errors.extend(_check_state_path(state_path, state))
    errors.extend(_check_head_fields(state))
    errors.extend(_check_completion_truth(state))
    errors.extend(_check_tool_preflight(state, now=now_utc))
    return ValidationResult(errors)


def emit_resume_prompt(state_path: Path) -> str:
    state = _load_yaml(state_path)
    if not isinstance(state, dict):
        raise WorkstreamContextError("state document must be a mapping")
    issue = state.get("active_issue") or {}
    blockers = state.get("blockers") or []
    do_not_start = state.get("do_not_start") or []
    preflight = state.get("tool_preflight") or []
    completion_truth = state.get("completion_truth") or {}
    evidence_packets = state.get("evidence_packets") or []

    lines = [
        "Resume LifeOS workstream from canonical state.",
        "",
        f"Canonical state: artifacts/workstreams/{state.get('slug')}/state.yaml",
        ".context/active_work.yaml is advisory/generated only; never treat it as truth.",
        "Local paths are hints only, not authority.",
        "",
        f"Active issue: #{issue.get('number')} {issue.get('title', '')}".rstrip(),
        f"Issue URL: {issue.get('url', '')}".rstrip(),
        f"Phase: {issue.get('phase', '')}".rstrip(),
        f"Next action: {issue.get('next_action', '')}".rstrip(),
        "",
        "Blockers:",
    ]
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker.get('description', '')} ({blocker.get('ref', 'no ref')})")
    else:
        lines.append("- none recorded")
    lines.extend(["", "Do not start:"])
    for entry in do_not_start:
        lines.append(f"- {entry.get('type')}: {entry.get('description')}")
    lines.extend(["", "Evidence refs and summaries only:"])
    for entry in preflight:
        evidence_ref = entry.get("evidence_ref") or "no evidence ref"
        lines.append(f"- {entry.get('name')}: {entry.get('status')} — {evidence_ref}")
    for packet in evidence_packets:
        ref = packet.get("ref", "no ref")
        summary = packet.get("summary", "no summary")
        lines.append(f"- evidence packet {ref}: {summary}")
    lines.extend(["", "Completion truth requirements:"])
    for required in completion_truth.get("required") or []:
        lines.append(f"- {required}")
    lines.append("Refs:")
    for ref in completion_truth.get("refs") or []:
        lines.append(f"- {ref}")
    lines.append("State file alone never proves done/merged/closed.")
    return "\n".join(lines) + "\n"


def _cmd_validate(args: argparse.Namespace) -> int:
    now = None
    if args.now:
        now = _parse_datetime(args.now, "--now")
    state_paths = [Path(state) for state in args.state]
    per_state = []
    ok = True
    for state_path in state_paths:
        result = validate_state(state_path, now=now)
        ok = ok and result.ok
        per_state.append({"state": str(state_path), "ok": result.ok, "errors": result.errors})
    payload: dict[str, Any] = {"ok": ok}
    if len(per_state) == 1:
        payload.update(per_state[0])
    else:
        payload["states"] = per_state
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


def _cmd_emit_resume_prompt(args: argparse.Namespace) -> int:
    result = validate_state(Path(args.state))
    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1
    print(emit_resume_prompt(Path(args.state)), end="")
    return 0


def _cmd_deferred(_args: argparse.Namespace) -> int:
    print("Mutating workstream_context.py subcommands are deferred in v1", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="Validate one or more workstream state.yaml files")
    validate.add_argument(
        "--state",
        required=True,
        action="append",
        help="Path to state.yaml; repeat to validate multiple states",
    )
    validate.add_argument("--now", help="Deterministic ISO timestamp for tests")
    validate.set_defaults(func=_cmd_validate)
    resume = sub.add_parser("emit-resume-prompt", help="Emit a resume prompt from state.yaml")
    resume.add_argument("--state", required=True, help="Path to state.yaml")
    resume.set_defaults(func=_cmd_emit_resume_prompt)
    for name in ("init", "update", "complete", "generate-active-work"):
        deferred = sub.add_parser(name, help="Deferred mutating command")
        deferred.set_defaults(func=_cmd_deferred)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, WorkstreamContextError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"workstream_context error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
