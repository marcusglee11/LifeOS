#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import mcp_server  # noqa: E402
from memory_lib import read_record, relpath, repo_root  # noqa: E402
from retrieve import retrieve  # noqa: E402
from validate import validate_path  # noqa: E402

WARNING = "warning"
FAILURE = "failure"
NONACTIVE_LIFECYCLE = {"archived", "conflicted", "stale", "superseded"}
EXPOSED_GATEWAY_TOOLS = {"memory.retrieve", "memory.capture_candidate"}
REPORT_JSON = "memory_health_report.json"
REPORT_MD = "memory_health_report.md"


@dataclass
class HealthContext:
    repo: Path
    issues: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)

    def add_issue(
        self,
        *,
        check: str,
        severity: str,
        code: str,
        message: str,
        path: str = "",
        record_id: str = "",
        command: str = "",
        details: list[str] | None = None,
        recommended_action: str,
        needs_marcus_approval: bool,
        safe_for_codex_local_implementation: bool,
    ) -> None:
        self.issues.append(
            {
                "id": f"MH{len(self.issues) + 1:04d}",
                "check": check,
                "severity": severity,
                "code": code,
                "message": message,
                "path": path,
                "record_id": record_id,
                "command": command,
                "details": details or [],
                "recommended_action": recommended_action,
                "needs_marcus_approval": needs_marcus_approval,
                "safe_for_codex_local_implementation": safe_for_codex_local_implementation,
            }
        )


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _finish_check(
    ctx: HealthContext,
    *,
    name: str,
    start_issue_index: int,
    summary: str,
    paths: list[str] | None = None,
    commands: list[str] | None = None,
    skipped: bool = False,
    skip_reason: str = "",
) -> None:
    new_issues = ctx.issues[start_issue_index:]
    if skipped:
        status = "skipped"
    elif any(issue["severity"] == FAILURE for issue in new_issues):
        status = "fail"
    elif any(issue["severity"] == WARNING for issue in new_issues):
        status = "warn"
    else:
        status = "pass"
    ctx.checks.append(
        {
            "name": name,
            "status": status,
            "summary": summary,
            "issue_count": len(new_issues),
            "paths": paths or [],
            "commands": commands or [],
            "skipped": skipped,
            "skip_reason": skip_reason,
        }
    )


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_record(path: Path) -> tuple[dict[str, Any], str] | None:
    try:
        loaded = read_record(path)
    except Exception:
        return None
    return loaded.front_matter, loaded.body


def _iter_markdown_records(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file() and path.name != "README.md" and path.name != ".gitkeep"
    )


def _run_command(
    ctx: HealthContext,
    args: list[str],
    *,
    input_text: str | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    command = shlex.join(args)
    try:
        completed = subprocess.run(
            args,
            cwd=ctx.repo,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        result = {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    except (OSError, subprocess.SubprocessError) as exc:
        result = {
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(exc),
        }
    ctx.commands.append(result)
    return result


def _issue_for_validation(
    ctx: HealthContext,
    *,
    check: str,
    finding: dict[str, Any],
    severity: str,
    code: str,
    recommended_action: str,
    needs_marcus_approval: bool,
    safe_for_codex_local_implementation: bool,
) -> None:
    ctx.add_issue(
        check=check,
        severity=severity,
        code=code,
        message=str(finding.get("error", "validation failed")),
        path=str(finding.get("path", "")),
        recommended_action=recommended_action,
        needs_marcus_approval=needs_marcus_approval,
        safe_for_codex_local_implementation=safe_for_codex_local_implementation,
    )


def _secret_scan(
    ctx: HealthContext,
    *,
    check: str,
    path: Path,
    payload: dict[str, Any],
    body: str,
    severity: str,
) -> None:
    findings = mcp_server._secret_findings({"front_matter": payload, "body": body})
    for finding in findings:
        ctx.add_issue(
            check=check,
            severity=severity,
            code=finding.get("code", "secret_like_material"),
            message=finding.get("message", "secret-like material detected"),
            path=relpath(path, ctx.repo),
            record_id=str(payload.get("id") or payload.get("candidate_id") or ""),
            recommended_action="Remove or redact raw secret-like material before memory review.",
            needs_marcus_approval=True,
            safe_for_codex_local_implementation=False,
        )


def _receipt_index(repo: Path) -> dict[str, list[dict[str, Any]]]:
    receipts: dict[str, list[dict[str, Any]]] = {}
    for path in _iter_markdown_records(repo / "memory" / "receipts"):
        loaded = _load_record(path)
        if loaded is None:
            continue
        payload, _ = loaded
        candidate_id = payload.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id:
            receipts.setdefault(candidate_id, []).append(
                {
                    "path": relpath(path, repo),
                    "disposition": payload.get("disposition"),
                    "target_record_id": payload.get("target_record_id"),
                    "target_record_path": payload.get("target_record_path"),
                }
            )
    return receipts


def _durable_records(repo: Path) -> list[tuple[Path, dict[str, Any], str]]:
    records: list[tuple[Path, dict[str, Any], str]] = []
    memory = repo / "memory"
    for path in _iter_markdown_records(memory):
        if relpath(path, repo).startswith("memory/receipts/"):
            continue
        loaded = _load_record(path)
        if loaded is None:
            continue
        payload, body = loaded
        if payload.get("id") or payload.get("record_kind") or payload.get("authority_class"):
            records.append((path, payload, body))
    return records


def _candidate_records(repo: Path) -> list[tuple[Path, dict[str, Any], str]]:
    records: list[tuple[Path, dict[str, Any], str]] = []
    staging = repo / "knowledge-staging"
    for path in sorted(staging.glob("*.md")) if staging.exists() else []:
        if path.name == "README.md":
            continue
        loaded = _load_record(path)
        if loaded is None:
            continue
        payload, body = loaded
        records.append((path, payload, body))
    return records


def check_durable_memory(ctx: HealthContext) -> list[tuple[Path, dict[str, Any], str]]:
    check = "durable_memory_records"
    start = len(ctx.issues)
    memory = ctx.repo / "memory"
    if not memory.exists():
        ctx.add_issue(
            check=check,
            severity=FAILURE,
            code="memory_dir_missing",
            message="memory/ directory is missing.",
            path="memory/",
            recommended_action=(
                "Restore memory/ durable memory surface before running health sweep."
            ),
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )
        _finish_check(
            ctx,
            name=check,
            start_issue_index=start,
            summary="memory/ missing",
            paths=["memory/"],
        )
        return []

    for finding in validate_path(memory, ctx.repo):
        path = str(finding.get("path", ""))
        code = (
            "memory_receipt_validation_failed"
            if path.startswith("memory/receipts/")
            else "durable_record_validation_failed"
        )
        _issue_for_validation(
            ctx,
            check=check,
            finding=finding,
            severity=FAILURE,
            code=code,
            recommended_action=(
                "Fix malformed durable memory metadata or receipt before relying on retrieval."
            ),
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )

    records = _durable_records(ctx.repo)
    ids: dict[str, list[str]] = {}
    for path, payload, body in records:
        record_id = str(payload.get("id") or "")
        if record_id:
            ids.setdefault(record_id, []).append(relpath(path, ctx.repo))
        _secret_scan(ctx, check=check, path=path, payload=payload, body=body, severity=FAILURE)
        for receipt in payload.get("write_receipts") or []:
            if not isinstance(receipt, str):
                continue
            if not (ctx.repo / receipt).exists():
                ctx.add_issue(
                    check=check,
                    severity=FAILURE,
                    code="missing_write_receipt",
                    message=f"write_receipts entry does not exist: {receipt}",
                    path=relpath(path, ctx.repo),
                    record_id=record_id,
                    recommended_action=(
                        "Restore receipt or correct durable record write_receipts metadata."
                    ),
                    needs_marcus_approval=False,
                    safe_for_codex_local_implementation=True,
                )

    for record_id, paths in sorted(ids.items()):
        if len(paths) > 1:
            ctx.add_issue(
                check=check,
                severity=FAILURE,
                code="duplicate_durable_record_id",
                message=f"duplicate durable record id: {record_id}",
                record_id=record_id,
                details=paths,
                recommended_action="Deduplicate durable records or assign unique ids.",
                needs_marcus_approval=True,
                safe_for_codex_local_implementation=False,
            )

    _finish_check(
        ctx,
        name=check,
        start_issue_index=start,
        summary=f"scanned {len(records)} durable record(s) plus receipt metadata",
        paths=["memory/"],
    )
    return records


def check_knowledge_staging(ctx: HealthContext) -> list[tuple[Path, dict[str, Any], str]]:
    check = "knowledge_staging_candidates"
    start = len(ctx.issues)
    staging = ctx.repo / "knowledge-staging"
    if not staging.exists():
        ctx.add_issue(
            check=check,
            severity=WARNING,
            code="knowledge_staging_missing",
            message="knowledge-staging/ directory is missing.",
            path="knowledge-staging/",
            recommended_action="Restore staging surface before accepting candidate packets.",
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )
        _finish_check(
            ctx,
            name=check,
            start_issue_index=start,
            summary="knowledge-staging/ missing",
            paths=["knowledge-staging/"],
        )
        return []

    for finding in validate_path(staging, ctx.repo):
        _issue_for_validation(
            ctx,
            check=check,
            finding=finding,
            severity=WARNING,
            code="staging_candidate_validation_failed",
            recommended_action="Repair or quarantine malformed staging candidate before review.",
            needs_marcus_approval=True,
            safe_for_codex_local_implementation=False,
        )

    receipts = _receipt_index(ctx.repo)
    candidates = _candidate_records(ctx.repo)
    candidate_ids: dict[str, list[str]] = {}
    for path, payload, body in candidates:
        candidate_id = str(payload.get("candidate_id") or "")
        if candidate_id:
            candidate_ids.setdefault(candidate_id, []).append(relpath(path, ctx.repo))
        _secret_scan(ctx, check=check, path=path, payload=payload, body=body, severity=FAILURE)
        if payload.get("requires_human_review") is not True:
            ctx.add_issue(
                check=check,
                severity=FAILURE,
                code="candidate_human_review_not_required",
                message="candidate does not require human review.",
                path=relpath(path, ctx.repo),
                record_id=candidate_id,
                recommended_action="Set requires_human_review true or reject the candidate.",
                needs_marcus_approval=True,
                safe_for_codex_local_implementation=False,
            )
        if payload.get("proposed_authority_class") == "canonical_doctrine":
            ctx.add_issue(
                check=check,
                severity=FAILURE,
                code="canonical_doctrine_candidate_boundary",
                message="candidate proposes canonical_doctrine through staging gateway boundary.",
                path=relpath(path, ctx.repo),
                record_id=candidate_id,
                recommended_action=(
                    "Route canonical doctrine changes through governance/docs review, "
                    "not memory gateway capture."
                ),
                needs_marcus_approval=True,
                safe_for_codex_local_implementation=False,
            )
        accepted_receipts = [
            receipt
            for receipt in receipts.get(candidate_id, [])
            if receipt["disposition"] == "accepted"
        ]
        if accepted_receipts:
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="accepted_candidate_still_staged",
                message="accepted candidate still exists in root knowledge-staging/.",
                path=relpath(path, ctx.repo),
                record_id=candidate_id,
                details=[receipt["path"] for receipt in accepted_receipts],
                recommended_action=(
                    "COO should decide whether accepted candidate remains as audit evidence "
                    "or moves out of active staging."
                ),
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=False,
            )

    for candidate_id, paths in sorted(candidate_ids.items()):
        if len(paths) > 1:
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="duplicate_candidate_id",
                message=f"duplicate staging candidate id: {candidate_id}",
                record_id=candidate_id,
                details=paths,
                recommended_action="Deduplicate staging candidates before COO review.",
                needs_marcus_approval=True,
                safe_for_codex_local_implementation=False,
            )

    _finish_check(
        ctx,
        name=check,
        start_issue_index=start,
        summary=f"scanned {len(candidates)} root candidate packet(s)",
        paths=["knowledge-staging/"],
    )
    return candidates


def check_failed_quarantine(ctx: HealthContext) -> None:
    check = "failed_quarantine"
    start = len(ctx.issues)
    failed_dir = ctx.repo / "knowledge-staging" / "_failed"
    if not failed_dir.exists():
        ctx.add_issue(
            check=check,
            severity=WARNING,
            code="failed_quarantine_missing",
            message="knowledge-staging/_failed/ directory is missing.",
            path="knowledge-staging/_failed/",
            recommended_action=(
                "Restore _failed quarantine directory for rejected candidate packets."
            ),
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )
        _finish_check(
            ctx,
            name=check,
            start_issue_index=start,
            summary="_failed quarantine missing",
            paths=["knowledge-staging/_failed/"],
        )
        return

    failed_files = sorted(path for path in failed_dir.glob("*.md") if path.is_file())
    if failed_files:
        ctx.add_issue(
            check=check,
            severity=WARNING,
            code="failed_quarantine_nonempty",
            message=f"_failed quarantine contains {len(failed_files)} failed candidate(s).",
            path="knowledge-staging/_failed/",
            recommended_action="Review quarantine backlog and repeated validation failures.",
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=False,
        )

    finding_codes: Counter[str] = Counter()
    for path in failed_files:
        loaded = _load_record(path)
        if loaded is None:
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="failed_candidate_unparseable",
                message="failed candidate packet is not parseable YAML front matter.",
                path=relpath(path, ctx.repo),
                recommended_action="Repair or remove unparseable quarantine item after review.",
                needs_marcus_approval=True,
                safe_for_codex_local_implementation=False,
            )
            continue
        payload, _ = loaded
        for finding in payload.get("gateway_findings") or []:
            if isinstance(finding, dict):
                code = str(finding.get("code") or "")
                if code:
                    finding_codes[code] += 1

    repeated = [f"{code}={count}" for code, count in sorted(finding_codes.items()) if count > 1]
    if repeated:
        ctx.add_issue(
            check=check,
            severity=WARNING,
            code="repeated_failed_candidate_pattern",
            message="repeated failed candidate pattern(s): " + ", ".join(repeated),
            path="knowledge-staging/_failed/",
            recommended_action=(
                "Fix upstream gateway caller or candidate template causing repeated failures."
            ),
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )

    _finish_check(
        ctx,
        name=check,
        start_issue_index=start,
        summary=f"scanned {len(failed_files)} failed candidate(s)",
        paths=["knowledge-staging/_failed/"],
    )


def check_session_logs(ctx: HealthContext) -> None:
    check = "session_logs"
    start = len(ctx.issues)
    sessions_dir = ctx.repo / "knowledge-staging" / "_sessions"
    if not sessions_dir.exists():
        ctx.add_issue(
            check=check,
            severity=WARNING,
            code="session_log_dir_missing",
            message="knowledge-staging/_sessions/ directory is missing.",
            path="knowledge-staging/_sessions/",
            recommended_action="Restore _sessions directory so gateway calls can be audited.",
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )
        _finish_check(
            ctx,
            name=check,
            start_issue_index=start,
            summary="_sessions directory missing",
            paths=["knowledge-staging/_sessions/"],
        )
        return

    log_files = sorted(path for path in sessions_dir.glob("*.jsonl") if path.is_file())
    required = {"timestamp_utc", "tool", "result_ok", "findings"}
    parsed_lines = 0
    for path in log_files:
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="empty_session_log",
                message="session log is empty.",
                path=relpath(path, ctx.repo),
                recommended_action=(
                    "Remove empty session log or investigate interrupted gateway write."
                ),
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )
            continue
        for number, line in enumerate(lines, start=1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                ctx.add_issue(
                    check=check,
                    severity=WARNING,
                    code="session_log_json_parse_failed",
                    message=f"session log line {number} is invalid JSON: {exc}",
                    path=relpath(path, ctx.repo),
                    recommended_action="Repair malformed JSONL session log entry.",
                    needs_marcus_approval=False,
                    safe_for_codex_local_implementation=True,
                )
                continue
            parsed_lines += 1
            if not isinstance(entry, dict):
                missing = sorted(required)
            else:
                missing = sorted(required - set(entry))
            if missing:
                ctx.add_issue(
                    check=check,
                    severity=WARNING,
                    code="session_log_missing_fields",
                    message="session log entry missing required fields: " + ", ".join(missing),
                    path=relpath(path, ctx.repo),
                    recommended_action=(
                        "Repair gateway session log format before relying on audit trail."
                    ),
                    needs_marcus_approval=False,
                    safe_for_codex_local_implementation=True,
                )

    _finish_check(
        ctx,
        name=check,
        start_issue_index=start,
        summary=f"scanned {len(log_files)} session log file(s), {parsed_lines} parseable line(s)",
        paths=["knowledge-staging/_sessions/"],
    )


def _query_terms(payload: dict[str, Any]) -> str:
    text = str(payload.get("title") or payload.get("id") or "")
    words = [
        "".join(ch for ch in word.lower() if ch.isalnum()) for word in text.split() if len(word) > 2
    ]
    words = [word for word in words if word]
    return " ".join(words[:4]) or str(payload.get("id") or "")


def _choose_retrieval_fixture(
    records: list[tuple[Path, dict[str, Any], str]],
) -> tuple[Path, dict[str, Any], str] | None:
    for path, payload, body in records:
        if payload.get("lifecycle_state") != "active":
            continue
        if payload.get("sensitivity") in {"sensitive", "secret"}:
            continue
        if not payload.get("id") or not payload.get("scope"):
            continue
        return path, payload, body
    return None


def check_retrieval_health(
    ctx: HealthContext,
    records: list[tuple[Path, dict[str, Any], str]],
) -> None:
    check = "retrieval_health"
    start = len(ctx.issues)
    commands: list[str] = []
    retrieve_script = ctx.repo / "tools" / "memory" / "retrieve.py"
    if not retrieve_script.exists():
        ctx.add_issue(
            check=check,
            severity=FAILURE,
            code="retrieve_script_missing",
            message="tools/memory/retrieve.py is missing.",
            path="tools/memory/retrieve.py",
            recommended_action="Restore retrieval command before using memory health sweep.",
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )
    else:
        fixture = _choose_retrieval_fixture(records)
        if fixture is None:
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="retrieval_fixture_missing",
                message=(
                    "no active non-sensitive durable record available for retrieval fixture smoke."
                ),
                recommended_action=(
                    "Add or preserve at least one active non-sensitive durable memory fixture."
                ),
                needs_marcus_approval=True,
                safe_for_codex_local_implementation=False,
            )
        else:
            path, payload, _ = fixture
            query = _query_terms(payload)
            args = [
                sys.executable,
                "tools/memory/retrieve.py",
                "--query",
                query,
                "--scope",
                str(payload.get("scope")),
                "--authority-floor",
                "observation",
                "--json",
            ]
            result = _run_command(ctx, args)
            commands.append(result["command"])
            record_id = str(payload.get("id"))
            if result["exit_code"] != 0:
                ctx.add_issue(
                    check=check,
                    severity=FAILURE,
                    code="retrieval_command_failed",
                    message="retrieval command exited non-zero.",
                    path=relpath(path, ctx.repo),
                    record_id=record_id,
                    command=result["command"],
                    details=[result["stderr"]],
                    recommended_action=(
                        "Fix tools/memory/retrieve.py command path or retrieval runtime error."
                    ),
                    needs_marcus_approval=False,
                    safe_for_codex_local_implementation=True,
                )
            else:
                try:
                    payload_json = json.loads(result["stdout"])
                    results = payload_json.get("results", [])
                except json.JSONDecodeError as exc:
                    results = []
                    ctx.add_issue(
                        check=check,
                        severity=FAILURE,
                        code="retrieval_json_parse_failed",
                        message=f"retrieval command did not emit parseable JSON: {exc}",
                        path=relpath(path, ctx.repo),
                        record_id=record_id,
                        command=result["command"],
                        recommended_action="Fix retrieval --json output contract.",
                        needs_marcus_approval=False,
                        safe_for_codex_local_implementation=True,
                    )
                if not any(item.get("record_id") == record_id for item in results):
                    ctx.add_issue(
                        check=check,
                        severity=FAILURE,
                        code="retrieval_fixture_empty",
                        message=(
                            "known active durable fixture was not returned by retrieval command."
                        ),
                        path=relpath(path, ctx.repo),
                        record_id=record_id,
                        command=result["command"],
                        recommended_action=(
                            "Fix retrieval matching/filtering for active durable records."
                        ),
                        needs_marcus_approval=False,
                        safe_for_codex_local_implementation=True,
                    )

    for path, payload, _ in records:
        lifecycle = payload.get("lifecycle_state")
        if lifecycle not in NONACTIVE_LIFECYCLE:
            continue
        if payload.get("sensitivity") in {"sensitive", "secret"}:
            continue
        query = str(payload.get("id") or _query_terms(payload))
        scope = str(payload.get("scope") or "any")
        try:
            results = retrieve(
                ctx.repo,
                query=query,
                scope=scope,
                authority_floor="observation",
                include_sensitive=False,
            )
        except Exception as exc:
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="retrieval_lifecycle_probe_failed",
                message=f"nonactive lifecycle retrieval probe failed: {exc}",
                path=relpath(path, ctx.repo),
                record_id=str(payload.get("id") or ""),
                recommended_action="Inspect lifecycle filtering after durable validation is clean.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )
            continue
        matches = [item for item in results if item.get("record_id") == payload.get("id")]
        if matches:
            detail = [
                (
                    f"source_path={item.get('source_path')} "
                    f"excluded_reason={item.get('excluded_reason', '')}"
                )
                for item in matches
            ]
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="nonactive_record_retrievable_by_default",
                message=f"{lifecycle} durable record is still returned by default retrieval path.",
                path=relpath(path, ctx.repo),
                record_id=str(payload.get("id") or ""),
                details=detail,
                recommended_action="Tighten retrieval filtering or update lifecycle metadata.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )

    _finish_check(
        ctx,
        name=check,
        start_issue_index=start,
        summary="ran retrieval command smoke and nonactive lifecycle probes",
        paths=["tools/memory/retrieve.py", "memory/"],
        commands=commands,
    )


def _mcp_smoke_input() -> str:
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "memory-health", "version": "0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "memory.unknown_health_smoke", "arguments": {}},
        },
    ]
    return "\n".join(json.dumps(message, sort_keys=True) for message in messages) + "\n"


def check_gateway_smoke(ctx: HealthContext) -> None:
    check = "gateway_smoke"
    start = len(ctx.issues)
    commands: list[str] = []
    gateway = ctx.repo / "tools" / "memory" / "mcp_server.py"
    if not gateway.exists():
        ctx.add_issue(
            check=check,
            severity=FAILURE,
            code="gateway_script_missing",
            message="tools/memory/mcp_server.py is missing.",
            path="tools/memory/mcp_server.py",
            recommended_action="Restore memory gateway script before using health sweep.",
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )
        _finish_check(
            ctx,
            name=check,
            start_issue_index=start,
            summary="gateway script missing",
            paths=["tools/memory/mcp_server.py"],
        )
        return

    list_result = _run_command(ctx, [sys.executable, "tools/memory/mcp_server.py", "--list-tools"])
    commands.append(list_result["command"])
    if list_result["exit_code"] != 0:
        ctx.add_issue(
            check=check,
            severity=FAILURE,
            code="gateway_tool_list_failed",
            message="gateway --list-tools exited non-zero.",
            path="tools/memory/mcp_server.py",
            command=list_result["command"],
            details=[list_result["stderr"]],
            recommended_action="Fix MCP gateway list-tools path.",
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )
    else:
        try:
            payload = json.loads(list_result["stdout"])
            tool_names = {tool.get("name") for tool in payload.get("tools", [])}
        except json.JSONDecodeError as exc:
            tool_names = set()
            ctx.add_issue(
                check=check,
                severity=FAILURE,
                code="gateway_tool_list_json_failed",
                message=f"gateway tool list was not parseable JSON: {exc}",
                path="tools/memory/mcp_server.py",
                command=list_result["command"],
                recommended_action="Fix gateway --list-tools JSON output.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )
        missing = sorted(EXPOSED_GATEWAY_TOOLS - tool_names)
        if missing:
            ctx.add_issue(
                check=check,
                severity=FAILURE,
                code="gateway_expected_tools_missing",
                message="gateway tool list missing expected tools: " + ", ".join(missing),
                path="tools/memory/mcp_server.py",
                command=list_result["command"],
                recommended_action="Restore v0.1 memory gateway exposed tool list.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )

    call_result = _run_command(
        ctx,
        [sys.executable, "tools/memory/mcp_server.py"],
        input_text=_mcp_smoke_input(),
    )
    commands.append(call_result["command"])
    if call_result["exit_code"] != 0:
        ctx.add_issue(
            check=check,
            severity=FAILURE,
            code="gateway_tool_call_failed",
            message="gateway JSON-RPC tool-call smoke exited non-zero.",
            path="tools/memory/mcp_server.py",
            command=call_result["command"],
            details=[call_result["stderr"]],
            recommended_action="Fix MCP stdio tool-call handling.",
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=True,
        )
    else:
        lines = [line for line in call_result["stdout"].splitlines() if line.strip()]
        try:
            responses = [json.loads(line) for line in lines]
        except json.JSONDecodeError as exc:
            responses = []
            ctx.add_issue(
                check=check,
                severity=FAILURE,
                code="gateway_tool_call_json_failed",
                message=f"gateway tool-call smoke output was not parseable JSON: {exc}",
                path="tools/memory/mcp_server.py",
                command=call_result["command"],
                recommended_action="Fix MCP stdio JSON-RPC output.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )
        if len(responses) != 2:
            ctx.add_issue(
                check=check,
                severity=FAILURE,
                code="gateway_tool_call_response_count",
                message=f"expected 2 JSON-RPC responses, got {len(responses)}.",
                path="tools/memory/mcp_server.py",
                command=call_result["command"],
                recommended_action="Fix MCP initialize/tools-call response flow.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )
        elif not any("unknown_tool" in json.dumps(response) for response in responses):
            ctx.add_issue(
                check=check,
                severity=FAILURE,
                code="gateway_tool_call_fail_closed_missing",
                message="tool-call smoke did not fail closed on unknown tool.",
                path="tools/memory/mcp_server.py",
                command=call_result["command"],
                recommended_action="Fix gateway call_tool fail-closed behavior.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )

    _finish_check(
        ctx,
        name=check,
        start_issue_index=start,
        summary="ran gateway tool-list and read-only fail-closed tool-call smoke",
        paths=["tools/memory/mcp_server.py"],
        commands=commands,
    )


def _git_commit_epoch(repo: Path, path: Path) -> int | None:
    try:
        rel = relpath(path, repo)
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", rel],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return int(value) if value.isdigit() else None


def _configured_corpora(repo: Path) -> list[str]:
    config = repo / "config" / "steward_runner.yaml"
    outputs: list[str] = []
    if config.exists():
        try:
            loaded = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            loaded = {}
        corpus = loaded.get("corpus") if isinstance(loaded, dict) else {}
        configured = corpus.get("outputs_expected", []) if isinstance(corpus, dict) else []
        if isinstance(configured, list):
            outputs.extend(str(path) for path in configured if path)
    for default in ("docs/LifeOS_Strategic_Corpus.md", "docs/LifeOS_Universal_Corpus.md"):
        if (repo / default).exists() and default not in outputs:
            outputs.append(default)
    return sorted(outputs)


def _check_index_mentions(
    ctx: HealthContext,
    *,
    check: str,
    index_path: Path,
    required_files: list[Path],
) -> None:
    text = _safe_read(index_path)
    for required in required_files:
        rel = relpath(required, ctx.repo)
        if rel not in text and required.name not in text:
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="index_missing_canonical_memory_doc",
                message=f"docs/INDEX.md does not mention canonical memory doc: {rel}",
                path="docs/INDEX.md",
                details=[rel],
                recommended_action=(
                    "Update docs/INDEX.md through doc stewardship if memory docs changed."
                ),
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=False,
            )


def _check_git_freshness(
    ctx: HealthContext,
    *,
    check: str,
    target: Path,
    sources: list[Path],
    code: str,
    message: str,
    recommended_action: str,
) -> None:
    target_epoch = _git_commit_epoch(ctx.repo, target)
    source_epochs = [epoch for source in sources if (epoch := _git_commit_epoch(ctx.repo, source))]
    if target_epoch is None or not source_epochs:
        return
    newest_source = max(source_epochs)
    if newest_source > target_epoch:
        ctx.add_issue(
            check=check,
            severity=WARNING,
            code=code,
            message=message,
            path=relpath(target, ctx.repo),
            recommended_action=recommended_action,
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=False,
        )


def check_indexes_wiki_corpus(ctx: HealthContext) -> None:
    check = "indexes_wiki_corpus"
    start = len(ctx.issues)
    paths = [
        "memory/README.md",
        "knowledge-staging/README.md",
        "docs/INDEX.md",
        "docs/03_runtime/memory/",
        ".context/wiki/",
    ]

    for required in ("memory/README.md", "knowledge-staging/README.md"):
        if not (ctx.repo / required).exists():
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="memory_surface_readme_missing",
                message=f"{required} is missing.",
                path=required,
                recommended_action="Restore memory surface README for operator discovery.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )

    memory_doc_dir = ctx.repo / "docs" / "03_runtime" / "memory"
    memory_docs = (
        sorted(path for path in memory_doc_dir.glob("*.md") if path.name != "README.md")
        if memory_doc_dir.exists()
        else []
    )
    index_path = ctx.repo / "docs" / "INDEX.md"
    if index_path.exists():
        _check_index_mentions(ctx, check=check, index_path=index_path, required_files=memory_docs)
        _check_git_freshness(
            ctx,
            check=check,
            target=index_path,
            sources=memory_docs,
            code="index_older_than_memory_docs",
            message="docs/INDEX.md is older than one or more canonical memory docs.",
            recommended_action="Run doc stewardship index update if canonical memory docs changed.",
        )
    elif memory_docs:
        ctx.add_issue(
            check=check,
            severity=WARNING,
            code="docs_index_missing",
            message="docs/INDEX.md missing while canonical memory docs exist.",
            path="docs/INDEX.md",
            recommended_action="Restore docs/INDEX.md through doc stewardship.",
            needs_marcus_approval=False,
            safe_for_codex_local_implementation=False,
        )

    corpus_paths = _configured_corpora(ctx.repo)
    corpus_sources = [index_path, *memory_docs]
    for corpus_rel in corpus_paths:
        corpus = ctx.repo / corpus_rel
        if not corpus.exists():
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="configured_corpus_missing",
                message=f"configured corpus output is missing: {corpus_rel}",
                path=corpus_rel,
                recommended_action="Regenerate configured corpus through doc stewardship.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=False,
            )
            continue
        text = _safe_read(corpus)
        for memory_doc in memory_docs:
            rel = relpath(memory_doc, ctx.repo)
            if rel not in text and memory_doc.name not in text:
                ctx.add_issue(
                    check=check,
                    severity=WARNING,
                    code="corpus_missing_memory_doc",
                    message=f"{corpus_rel} does not mention canonical memory doc: {rel}",
                    path=corpus_rel,
                    details=[rel],
                    recommended_action=(
                        "Regenerate corpus through doc stewardship if canonical docs changed."
                    ),
                    needs_marcus_approval=False,
                    safe_for_codex_local_implementation=False,
                )
        _check_git_freshness(
            ctx,
            check=check,
            target=corpus,
            sources=[source for source in corpus_sources if source.exists()],
            code="corpus_older_than_memory_sources",
            message=f"{corpus_rel} is older than memory/index source files.",
            recommended_action="Regenerate corpus through doc stewardship.",
        )

    wiki_dir = ctx.repo / ".context" / "wiki"
    if wiki_dir.exists():
        try:
            from doc_steward.wiki_lint_validator import check_wiki_lint
        except ImportError as exc:
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="wiki_lint_unavailable",
                message=f"wiki lint validator unavailable: {exc}",
                path=".context/wiki/",
                recommended_action="Run wiki lint manually after ensuring doc_steward import path.",
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=True,
            )
        else:
            for error in check_wiki_lint(str(ctx.repo)):
                ctx.add_issue(
                    check=check,
                    severity=WARNING,
                    code="wiki_lint_failed",
                    message=error,
                    path=".context/wiki/",
                    recommended_action="Refresh or repair wiki layer through wiki stewardship.",
                    needs_marcus_approval=False,
                    safe_for_codex_local_implementation=False,
                )
        marker = wiki_dir / "_refresh_needed"
        marker_text = _safe_read(marker).strip() if marker.exists() else ""
        if marker_text:
            ctx.add_issue(
                check=check,
                severity=WARNING,
                code="wiki_refresh_pending",
                message=".context/wiki/_refresh_needed contains pending source paths.",
                path=".context/wiki/_refresh_needed",
                details=marker_text.splitlines(),
                recommended_action=(
                    "Run reviewed wiki refresh flow; do not auto-commit wiki updates."
                ),
                needs_marcus_approval=False,
                safe_for_codex_local_implementation=False,
            )

    _finish_check(
        ctx,
        name=check,
        start_issue_index=start,
        summary="checked memory discovery readmes, docs index, corpora, and wiki freshness",
        paths=paths,
    )


def _overall_status(issues: list[dict[str, Any]]) -> str:
    if any(issue["severity"] == FAILURE for issue in issues):
        return "fail"
    if any(issue["severity"] == WARNING for issue in issues):
        return "warn"
    return "pass"


def _report_payload(ctx: HealthContext, report_dir: Path) -> dict[str, Any]:
    status = _overall_status(ctx.issues)
    failures = sum(1 for issue in ctx.issues if issue["severity"] == FAILURE)
    warnings = sum(1 for issue in ctx.issues if issue["severity"] == WARNING)
    return {
        "generated_utc": _iso_now(),
        "repo_root": str(ctx.repo),
        "report_dir": relpath(report_dir, ctx.repo),
        "overall_status": status,
        "summary": {
            "failures": failures,
            "warnings": warnings,
            "issues": len(ctx.issues),
            "checks": len(ctx.checks),
        },
        "checks_run": ctx.checks,
        "issues_found": ctx.issues,
        "commands": ctx.commands,
        "hard_constraints": {
            "schedules_created_or_enabled": False,
            "durable_memory_mutated": False,
            "candidates_promoted": False,
            "external_sends": False,
        },
    }


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Memory Health Report",
        "",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Overall status: `{payload['overall_status']}`",
        f"- Report dir: `{payload['report_dir']}`",
        f"- Failures: `{payload['summary']['failures']}`",
        f"- Warnings: `{payload['summary']['warnings']}`",
        "",
        "## Checks Run",
        "",
        "| Check | Status | Issues | Summary |",
        "|---|---:|---:|---|",
    ]
    for check in payload["checks_run"]:
        summary = str(check["summary"]).replace("|", "\\|")
        lines.append(
            f"| `{check['name']}` | `{check['status']}` | {check['issue_count']} | {summary} |"
        )

    lines.extend(["", "## Issues Found", ""])
    if not payload["issues_found"]:
        lines.append("No issues found.")
    for issue in payload["issues_found"]:
        lines.extend(
            [
                f"### {issue['id']} `{issue['severity']}` `{issue['code']}`",
                "",
                f"- Check: `{issue['check']}`",
                f"- Path: `{issue['path'] or 'n/a'}`",
                f"- Record: `{issue['record_id'] or 'n/a'}`",
                f"- Command: `{issue['command'] or 'n/a'}`",
                f"- Message: {issue['message']}",
                f"- Recommended action: {issue['recommended_action']}",
                f"- Needs Marcus approval: `{issue['needs_marcus_approval']}`",
                (
                    "- Safe for Codex/local implementation: "
                    f"`{issue['safe_for_codex_local_implementation']}`"
                ),
            ]
        )
        if issue["details"]:
            lines.append("- Details:")
            lines.extend(f"  - `{detail}`" for detail in issue["details"])
        lines.append("")

    lines.extend(["## Commands", ""])
    if not payload["commands"]:
        lines.append("No subprocess commands run.")
    for command in payload["commands"]:
        lines.extend(
            [
                f"- `{command['command']}`",
                f"  - exit: `{command['exit_code']}`",
            ]
        )
        stderr = str(command.get("stderr") or "").strip()
        if stderr:
            lines.append(f"  - stderr tail: `{stderr}`")

    lines.extend(
        [
            "",
            "## Hard Constraints",
            "",
            "| Constraint | Result |",
            "|---|---:|",
        ]
    )
    for key, value in payload["hard_constraints"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.append("")
    return "\n".join(lines)


def run_health_check(
    repo: Path,
    *,
    report_root: Path | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    ctx = HealthContext(repo=repo.resolve())
    if str(ctx.repo) not in sys.path:
        sys.path.insert(0, str(ctx.repo))
    durable_records = check_durable_memory(ctx)
    check_knowledge_staging(ctx)
    check_failed_quarantine(ctx)
    check_session_logs(ctx)
    check_retrieval_health(ctx, durable_records)
    check_gateway_smoke(ctx)
    check_indexes_wiki_corpus(ctx)

    base = report_root or ctx.repo / "artifacts" / "reports" / "memory_health"
    report_dir = base / (timestamp or _utc_timestamp())
    report_dir.mkdir(parents=True, exist_ok=False)
    payload = _report_payload(ctx, report_dir)
    (report_dir / REPORT_JSON).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (report_dir / REPORT_MD).write_text(_markdown_report(payload), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manual LifeOS memory/wiki health sweep. Writes reports only."
    )
    parser.add_argument("--repo-root", default=None, help="Repo root; defaults to detected root.")
    parser.add_argument(
        "--report-root",
        default=None,
        help="Directory that receives timestamped report directories.",
    )
    parser.add_argument("--timestamp", default=None, help="Optional report timestamp override.")
    args = parser.parse_args(argv)

    detected = repo_root(Path.cwd()) if args.repo_root is None else Path(args.repo_root)
    report_root = Path(args.report_root).resolve() if args.report_root else None
    payload = run_health_check(detected, report_root=report_root, timestamp=args.timestamp)
    print(
        json.dumps(
            {
                "overall_status": payload["overall_status"],
                "report_dir": payload["report_dir"],
                "json": f"{payload['report_dir']}/{REPORT_JSON}",
                "markdown": f"{payload['report_dir']}/{REPORT_MD}",
                "failures": payload["summary"]["failures"],
                "warnings": payload["summary"]["warnings"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if payload["overall_status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
