#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import mcp_server
from memory_lib import is_under, iso_now, relpath, repo_root

TOOL_RETRIEVE = mcp_server.TOOL_RETRIEVE
TOOL_CAPTURE = mcp_server.TOOL_CAPTURE
AUDIT_SCHEMA = "hermes_native_audit.v1"
DEFAULT_SESSION_ID = "hermes-native-audit"
DEFAULT_AGENT = "Hermes"
DEFAULT_SCOPE = "workflow"
VALID_CAPTURE_CLASSES = ("agent_memory", "observation", "shared_knowledge")
DISPOSITIONS = (
    "archive_observation",
    "candidate_handoff",
    "discard",
    "keep_native",
    "pointer_only",
)
GATEWAY_TRANSPORT_IDENTITY = "hermes-native-audit"

DISPOSITION_RE = re.compile(
    r"(?i)(?:\[|disposition\s*[:=]\s*)"
    r"(keep_native|pointer_only|discard|archive_observation|candidate_handoff)"
    r"(?:\]|$|\s)"
)
AUTHORITY_RE = re.compile(
    r"(?i)(?:authority(?:_class)?|class)\s*[:=]\s*"
    r"(canonical_doctrine|shared_knowledge|agent_memory|observation)"
)
BRACKET_AUTHORITY_RE = re.compile(
    r"(?i)\[(canonical_doctrine|shared_knowledge|agent_memory|observation)\]"
)
SCOPE_RE = re.compile(r"(?i)\bscope\s*[:=]\s*(global|project|agent|workflow|infrastructure)\b")
ENTRY_PREFIX_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?(.+?)\s*$")
CANONICAL_RE = re.compile(r"(?i)\bcanonical_doctrine\b")
POINTER_RE = re.compile(r"(?i)\b(pointer|see|refer|already captured)\b|(?:^|\s)(memory|docs)/\S+")
ARCHIVE_RE = re.compile(r"(?i)\b(archive|archived|obsolete|superseded|stale)\b")
CANDIDATE_RE = re.compile(
    r"(?i)\b(candidate|remember|learned|lesson|decision|rule|shared_knowledge|"
    r"agent_memory|observation|handoff)\b"
)
RECORD_KIND_RE = re.compile(
    r"(?i)\b(record_kind|kind)\s*[:=]\s*(fact|preference|rule|decision|state|lesson|pattern)\b"
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("authorization_header", re.compile(r"(?i)\bauthorization\s*:\s*(bearer|basic)\s+\S+"), ""),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), ""),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), ""),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), ""),
    (
        "named_secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token|refresh[_-]?token|"
            r"id[_-]?token|oauth[_-]?token|cookie|password|passwd|pwd)\b\s*[:=]\s*"
            r"['\"]?[^\s'\"]{8,}"
        ),
        "",
    ),
    (
        "private_connection_string",
        re.compile(r"(?i)\b(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^/\s:@]+:[^@\s]+@"),
        "",
    ),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), ""),
)


@dataclass(frozen=True)
class NativeEntry:
    index: int
    source_label: str
    line_start: int
    text: str


@dataclass(frozen=True)
class Classification:
    disposition: str
    proposed_authority_class: str | None
    proposed_record_kind: str
    scope: str
    reasons: tuple[str, ...]
    secret_rejected: bool = False


GatewayCall = Callable[..., dict[str, Any]]


def _entry_id(index: int) -> str:
    return f"HNA-{index:04d}"


def _content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_label(path: Path, repo: Path) -> str:
    try:
        resolved = path.resolve()
    except OSError:
        return path.name
    if is_under(resolved, repo):
        return relpath(resolved, repo)
    return path.name


def _strip_entry_prefix(line: str) -> str:
    match = ENTRY_PREFIX_RE.match(line.strip())
    if not match:
        return line.strip()
    return match.group(1).strip()


def parse_snapshot_text(text: str, *, source_label: str, start_index: int = 1) -> list[NativeEntry]:
    entries: list[NativeEntry] = []
    next_index = start_index
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped == "---" or stripped.startswith("#"):
            continue
        entry_text = _strip_entry_prefix(stripped)
        if not entry_text:
            continue
        entries.append(
            NativeEntry(
                index=next_index,
                source_label=source_label,
                line_start=line_number,
                text=entry_text,
            )
        )
        next_index += 1
    return entries


def load_entries(
    snapshot_paths: Sequence[Path], explicit_entries: Sequence[str], *, repo: Path
) -> list[NativeEntry]:
    entries: list[NativeEntry] = []
    next_index = 1
    for path in snapshot_paths:
        text = path.read_text(encoding="utf-8")
        parsed = parse_snapshot_text(
            text,
            source_label=_source_label(path, repo),
            start_index=next_index,
        )
        entries.extend(parsed)
        next_index += len(parsed)
    for entry_text in explicit_entries:
        stripped = entry_text.strip()
        if not stripped:
            continue
        entries.append(
            NativeEntry(
                index=next_index,
                source_label="<explicit>",
                line_start=next_index,
                text=stripped,
            )
        )
        next_index += 1
    return entries


def redact_secrets(text: str) -> tuple[str, tuple[str, ...]]:
    redacted = text
    findings: list[str] = []
    for name, pattern, _replacement in SECRET_PATTERNS:
        if not pattern.search(redacted):
            continue
        findings.append(f"secret_material_rejected:{name}")
        if name == "authorization_header":
            redacted = pattern.sub("Authorization: [REDACTED_SECRET]", redacted)
        elif name == "named_secret":
            redacted = pattern.sub(_redact_named_secret, redacted)
        elif name == "private_connection_string":
            redacted = pattern.sub(_redact_connection_secret, redacted)
        else:
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted, tuple(dict.fromkeys(findings))


def _redact_named_secret(match: re.Match[str]) -> str:
    raw = match.group(0)
    separator = "=" if "=" in raw else ":"
    key = raw.split(separator, 1)[0].strip()
    return f"{key}{separator}[REDACTED_SECRET]"


def _redact_connection_secret(match: re.Match[str]) -> str:
    scheme = match.group(1)
    return f"{scheme}://[REDACTED_SECRET]@"


def _explicit_disposition(text: str) -> str | None:
    match = DISPOSITION_RE.search(text)
    if not match:
        return None
    disposition = match.group(1).lower()
    return disposition if disposition in DISPOSITIONS else None


def _proposed_authority_class(text: str) -> str | None:
    for pattern in (AUTHORITY_RE, BRACKET_AUTHORITY_RE):
        match = pattern.search(text)
        if match:
            return match.group(1).lower()
    lowered = text.lower()
    for authority_class in VALID_CAPTURE_CLASSES:
        if authority_class in lowered:
            return authority_class
    return None


def _record_kind(text: str) -> str:
    match = RECORD_KIND_RE.search(text)
    if match:
        return match.group(2).lower()
    lowered = text.lower()
    if "preference" in lowered or "prefers" in lowered:
        return "preference"
    if "must" in lowered or "never" in lowered or "always" in lowered or "rule" in lowered:
        return "rule"
    if "decision" in lowered:
        return "decision"
    if "pattern" in lowered:
        return "pattern"
    if "state" in lowered or "status" in lowered:
        return "state"
    if "fact" in lowered:
        return "fact"
    return "lesson"


def _scope(text: str, default_scope: str) -> str:
    match = SCOPE_RE.search(text)
    if match:
        return match.group(1).lower()
    return default_scope


def classify_entry(
    entry: NativeEntry, *, default_scope: str = DEFAULT_SCOPE, redacted_text: str | None = None
) -> Classification:
    text = redacted_text if redacted_text is not None else entry.text
    redacted, secret_findings = redact_secrets(text)
    if secret_findings:
        return Classification(
            disposition="discard",
            proposed_authority_class=None,
            proposed_record_kind=_record_kind(redacted),
            scope=_scope(redacted, default_scope),
            reasons=(*secret_findings, "gateway_handoff_not_attempted"),
            secret_rejected=True,
        )

    if CANONICAL_RE.search(redacted):
        return Classification(
            disposition="discard",
            proposed_authority_class=None,
            proposed_record_kind=_record_kind(redacted),
            scope=_scope(redacted, default_scope),
            reasons=("canonical_doctrine_capture_rejected", "gateway_handoff_not_attempted"),
        )

    explicit = _explicit_disposition(redacted)
    proposed_class = _proposed_authority_class(redacted)
    record_kind = _record_kind(redacted)
    scope = _scope(redacted, default_scope)
    if explicit:
        if explicit == "candidate_handoff":
            return Classification(
                disposition=explicit,
                proposed_authority_class=proposed_class or "agent_memory",
                proposed_record_kind=record_kind,
                scope=scope,
                reasons=("explicit_disposition",),
            )
        return Classification(
            disposition=explicit,
            proposed_authority_class=proposed_class,
            proposed_record_kind=record_kind,
            scope=scope,
            reasons=("explicit_disposition",),
        )

    if POINTER_RE.search(redacted):
        return Classification(
            disposition="pointer_only",
            proposed_authority_class=proposed_class,
            proposed_record_kind=record_kind,
            scope=scope,
            reasons=("native_entry_points_to_existing_context",),
        )
    if ARCHIVE_RE.search(redacted):
        return Classification(
            disposition="archive_observation",
            proposed_authority_class=proposed_class or "observation",
            proposed_record_kind=record_kind,
            scope=scope,
            reasons=("archive_signal",),
        )
    if proposed_class or CANDIDATE_RE.search(redacted):
        return Classification(
            disposition="candidate_handoff",
            proposed_authority_class=proposed_class or "agent_memory",
            proposed_record_kind=record_kind,
            scope=scope,
            reasons=("candidate_signal",),
        )
    return Classification(
        disposition="keep_native",
        proposed_authority_class=None,
        proposed_record_kind=record_kind,
        scope=scope,
        reasons=("no_lifeos_handoff_signal",),
    )


def _retrieval_args(
    *,
    session_id: str,
    query: str,
    scope: str,
    limit: int,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "query": query,
        "scope": scope,
        "authority_floor": "observation",
        "include_sensitive": False,
        "limit": limit,
    }


def _candidate_args(
    *,
    entry: NativeEntry,
    classification: Classification,
    redacted_text: str,
    session_id: str,
    agent: str,
    iso_timestamp: str,
) -> dict[str, Any]:
    summary = f"Hermes native memory candidate: {redacted_text}"
    if len(summary) > 180:
        summary = summary[:177].rstrip() + "..."
    locator = f"{entry.source_label}:{entry.line_start}"
    proposed_authority_class = classification.proposed_authority_class or "agent_memory"
    return {
        "session_id": session_id,
        "agent": agent,
        "iso_timestamp": iso_timestamp,
        "summary": summary,
        "proposed_action": "create",
        "proposed_record_kind": classification.proposed_record_kind,
        "proposed_authority_class": proposed_authority_class,
        "scope": classification.scope,
        "sensitivity": "internal",
        "personal_inference": False,
        "promotion_basis": (
            "Hermes native memory is non-canonical; this handoff is review input through "
            "LifeOS Memory Gateway only."
        ),
        "sources": [
            {
                "source_type": "manual_note",
                "locator": locator,
                "quoted_evidence": redacted_text,
                "captured_utc": iso_timestamp,
                "content_hash": _content_hash(redacted_text),
                "commit_sha": "",
            }
        ],
        "payload": {
            "title": summary,
            "record_kind": classification.proposed_record_kind,
            "scope": classification.scope,
            "source_agent": agent,
            "native_entry_id": _entry_id(entry.index),
            "native_memory_disposition": classification.disposition,
            "text": redacted_text,
        },
        "authority_impact": "low",
        "retention_class": "medium",
    }


def _call_gateway(
    gateway_call: GatewayCall,
    name: str,
    args: dict[str, Any],
    *,
    repo: Path,
) -> dict[str, Any]:
    return gateway_call(
        name,
        args,
        repo=repo,
        transport_identity=GATEWAY_TRANSPORT_IDENTITY,
    )


def _gateway_boundary() -> dict[str, Any]:
    return {
        "allowed_candidate_authority_classes": list(VALID_CAPTURE_CLASSES),
        "capture_tool": TOOL_CAPTURE,
        "compaction_mutates_native": False,
        "direct_candidate_emission": False,
        "durable_memory_write": False,
        "retrieval_tool": TOOL_RETRIEVE,
    }


def _entry_report(
    *,
    entry: NativeEntry,
    classification: Classification,
    redacted_text: str,
    retrieval: dict[str, Any],
    handoff: dict[str, Any],
) -> dict[str, Any]:
    return {
        "compaction_recommendation": _recommendation_for(classification.disposition),
        "disposition": classification.disposition,
        "entry_id": _entry_id(entry.index),
        "handoff": handoff,
        "line_start": entry.line_start,
        "proposed_authority_class": classification.proposed_authority_class,
        "proposed_record_kind": classification.proposed_record_kind,
        "reasons": list(classification.reasons),
        "redacted_text": redacted_text,
        "retrieval": retrieval,
        "scope": classification.scope,
        "source": entry.source_label,
    }


def _recommendation_for(disposition: str) -> str:
    if disposition == "candidate_handoff":
        return "candidate staged through gateway; review before any durable memory promotion"
    if disposition == "archive_observation":
        return "operator may archive native entry after review; no native file mutation performed"
    if disposition == "pointer_only":
        return "replace native detail with pointer only after operator review"
    if disposition == "discard":
        return "operator may discard native entry after review; no native file mutation performed"
    return "retain native entry; no LifeOS memory handoff recommended"


def _summarize(entries: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {disposition: 0 for disposition in DISPOSITIONS}
    handoff_attempted = 0
    handoff_succeeded = 0
    for entry in entries:
        counts[str(entry["disposition"])] += 1
        handoff = entry["handoff"]
        if handoff.get("attempted"):
            handoff_attempted += 1
        if handoff.get("ok") is True:
            handoff_succeeded += 1
    return {
        "by_disposition": counts,
        "candidate_handoff_attempted": handoff_attempted,
        "candidate_handoff_succeeded": handoff_succeeded,
        "entries": len(entries),
    }


def run_audit(
    *,
    snapshot_paths: Sequence[Path] = (),
    explicit_entries: Sequence[str] = (),
    repo: Path | None = None,
    session_id: str = DEFAULT_SESSION_ID,
    agent: str = DEFAULT_AGENT,
    scope: str = DEFAULT_SCOPE,
    iso_timestamp: str | None = None,
    retrieve_context: bool = True,
    capture_candidates: bool = True,
    retrieval_limit: int = 3,
    gateway_call: GatewayCall = mcp_server.call_tool,
) -> dict[str, Any]:
    repo_path = repo_root(repo or Path.cwd())
    timestamp = iso_timestamp or iso_now()
    native_entries = load_entries(snapshot_paths, explicit_entries, repo=repo_path)
    entry_reports: list[dict[str, Any]] = []
    for entry in native_entries:
        redacted_text, secret_findings = redact_secrets(entry.text)
        classification = classify_entry(entry, default_scope=scope, redacted_text=redacted_text)
        if secret_findings and not classification.secret_rejected:
            classification = Classification(
                disposition="discard",
                proposed_authority_class=None,
                proposed_record_kind=classification.proposed_record_kind,
                scope=classification.scope,
                reasons=(*secret_findings, "gateway_handoff_not_attempted"),
                secret_rejected=True,
            )
        retrieval = {"called": False, "ok": None, "result_count": 0, "tool": TOOL_RETRIEVE}
        if retrieve_context and not classification.secret_rejected:
            retrieval_result = _call_gateway(
                gateway_call,
                TOOL_RETRIEVE,
                _retrieval_args(
                    session_id=session_id,
                    query=redacted_text,
                    scope=classification.scope,
                    limit=retrieval_limit,
                ),
                repo=repo_path,
            )
            retrieval = {
                "called": True,
                "ok": retrieval_result.get("ok"),
                "result_count": len(retrieval_result.get("results") or []),
                "session_log_path": retrieval_result.get("session_log_path", ""),
                "tool": TOOL_RETRIEVE,
            }
        handoff = {"attempted": False, "ok": None, "tool": TOOL_CAPTURE}
        if (
            capture_candidates
            and classification.disposition == "candidate_handoff"
            and classification.proposed_authority_class in VALID_CAPTURE_CLASSES
            and not classification.secret_rejected
        ):
            capture_result = _call_gateway(
                gateway_call,
                TOOL_CAPTURE,
                _candidate_args(
                    entry=entry,
                    classification=classification,
                    redacted_text=redacted_text,
                    session_id=session_id,
                    agent=agent,
                    iso_timestamp=timestamp,
                ),
                repo=repo_path,
            )
            handoff = {
                "attempted": True,
                "candidate_id": capture_result.get("candidate_id", ""),
                "candidate_path": capture_result.get("candidate_path", ""),
                "findings": capture_result.get("findings", []),
                "ok": capture_result.get("ok"),
                "session_log_path": capture_result.get("session_log_path", ""),
                "tool": TOOL_CAPTURE,
            }
        entry_reports.append(
            _entry_report(
                entry=entry,
                classification=classification,
                redacted_text=redacted_text,
                retrieval=retrieval,
                handoff=handoff,
            )
        )
    return {
        "agent": agent,
        "compaction": {
            "mutated_native_files": False,
            "recommendation_only": True,
        },
        "entries": entry_reports,
        "gateway_boundary": _gateway_boundary(),
        "schema": AUDIT_SCHEMA,
        "session_id": session_id,
        "summary": _summarize(entry_reports),
        "timestamp_utc": timestamp,
    }


def render_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def _assert_report_path_allowed(path: Path, repo: Path) -> None:
    resolved = path.resolve()
    if is_under(resolved, repo / "memory"):
        raise ValueError("report path under durable memory/ is rejected")


def write_report(report: dict[str, Any], path: Path, *, repo: Path) -> None:
    _assert_report_path_allowed(path, repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(report), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit Hermes native-memory snapshots through LifeOS Memory Gateway."
    )
    parser.add_argument(
        "--snapshot",
        action="append",
        default=[],
        help="Hermes MEMORY.md/USER.md path",
    )
    parser.add_argument("--entry", action="append", default=[], help="Explicit snapshot entry text")
    parser.add_argument("--report", help="Write JSON report path outside durable memory/")
    parser.add_argument("--session-id", default=DEFAULT_SESSION_ID)
    parser.add_argument("--agent", default=DEFAULT_AGENT)
    parser.add_argument("--scope", default=DEFAULT_SCOPE)
    parser.add_argument("--iso-timestamp")
    parser.add_argument("--retrieval-limit", type=int, default=3)
    parser.add_argument("--no-retrieve-context", action="store_true")
    parser.add_argument("--no-capture-candidates", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    snapshot_paths = [Path(item) for item in args.snapshot]
    if not snapshot_paths and not args.entry:
        parser.error("at least one --snapshot or --entry is required")
    repo = repo_root(Path.cwd())
    report = run_audit(
        snapshot_paths=snapshot_paths,
        explicit_entries=args.entry,
        repo=repo,
        session_id=args.session_id,
        agent=args.agent,
        scope=args.scope,
        iso_timestamp=args.iso_timestamp,
        retrieve_context=not args.no_retrieve_context,
        capture_candidates=not args.no_capture_candidates,
        retrieval_limit=args.retrieval_limit,
    )
    rendered = render_report(report)
    if args.report:
        write_report(report, Path(args.report), repo=repo)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
