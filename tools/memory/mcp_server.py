#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from memory_lib import (  # noqa: E402
    AUTHORITY_CLASSES,
    AUTHORITY_IMPACTS,
    PROPOSED_ACTIONS,
    RECORD_KINDS,
    RETENTION_CLASSES,
    SCOPES,
    SENSITIVITIES,
    is_under,
    iso_now,
    relpath,
    repo_root,
    write_front_matter,
)
from retrieve import retrieve as phase1_retrieve  # noqa: E402
from validate import validate_candidate  # noqa: E402

TOOL_RETRIEVE = "memory.retrieve"
TOOL_CAPTURE = "memory.capture_candidate"
EXPOSED_TOOL_NAMES = (TOOL_RETRIEVE, TOOL_CAPTURE)

GATEWAY_AUTHORITY_FLOORS = (
    "observation",
    "agent_memory",
    "shared_knowledge",
    "canonical_doctrine",
)
GATEWAY_CAPTURE_AUTHORITY = AUTHORITY_CLASSES - {"canonical_doctrine"}
RETRIEVE_EXCLUDED_LIFECYCLE = {"archived", "superseded", "stale", "conflicted"}
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
TOKEN_RE = re.compile(r"[^a-z0-9]+")
DATE_RE = re.compile(r"^(\d{4})-?(\d{2})-?(\d{2})")
SECRET_FIELD_RE = re.compile(
    r"(?i)(api[_-]?key|auth(?:orization)?|cookie|oauth|password|passwd|pwd|"
    r"refresh[_-]?token|access[_-]?token|id[_-]?token|secret|connection[_-]?string)"
)
SECRET_VALUE_PATTERNS = (
    (
        "secret_field",
        re.compile(
            r"(?i)(api[_-]?key|auth(?:orization)?|cookie|oauth|password|passwd|pwd|"
            r"refresh[_-]?token|access[_-]?token|id[_-]?token|secret|"
            r"connection[_-]?string)\s*=\s*<redacted>"
        ),
    ),
    (
        "authorization_header",
        re.compile(r"(?i)\bauthorization\s*:\s*(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    ),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "named_secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token|refresh[_-]?token|"
            r"id[_-]?token|oauth[_-]?token|cookie|password|passwd|pwd)\b\s*[:=]\s*"
            r"['\"]?[^\s'\"]{8,}"
        ),
    ),
    (
        "private_connection_string",
        re.compile(
            r"(?i)\b(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"
            r"[^/\s:@]+:[^@\s]+@"
        ),
    ),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": TOOL_RETRIEVE,
        "description": "Retrieve governed LifeOS Phase 1 memory through local gateway rules.",
        "inputSchema": {
            "type": "object",
            "required": ["session_id", "query", "scope", "authority_floor"],
            "properties": {
                "session_id": {"type": "string"},
                "query": {"type": "string"},
                "scope": {"enum": sorted(SCOPES)},
                "authority_floor": {"enum": list(GATEWAY_AUTHORITY_FLOORS)},
                "include_sensitive": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "default": 10, "minimum": 1},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": TOOL_CAPTURE,
        "description": "Capture a local memory candidate packet for human review.",
        "inputSchema": {
            "type": "object",
            "required": [
                "session_id",
                "agent",
                "iso_timestamp",
                "summary",
                "proposed_action",
                "proposed_record_kind",
                "proposed_authority_class",
                "scope",
                "sensitivity",
                "personal_inference",
                "promotion_basis",
                "sources",
                "payload",
            ],
            "properties": {
                "session_id": {"type": "string"},
                "agent": {"type": "string"},
                "iso_timestamp": {"type": "string"},
                "summary": {"type": "string"},
                "proposed_action": {"enum": sorted(PROPOSED_ACTIONS)},
                "proposed_record_kind": {"enum": sorted(RECORD_KINDS)},
                "proposed_authority_class": {"enum": sorted(GATEWAY_CAPTURE_AUTHORITY)},
                "scope": {"enum": sorted(SCOPES)},
                "sensitivity": {"enum": sorted(SENSITIVITIES)},
                "personal_inference": {"type": "boolean"},
                "promotion_basis": {"type": "string"},
                "sources": {"type": "array"},
                "payload": {"type": "object"},
                "authority_impact": {"enum": sorted(AUTHORITY_IMPACTS), "default": "low"},
                "retention_class": {"enum": sorted(RETENTION_CLASSES), "default": "medium"},
            },
            "additionalProperties": True,
        },
    },
)


def exposed_tool_names() -> list[str]:
    return list(EXPOSED_TOOL_NAMES)


def tool_definitions() -> list[dict[str, Any]]:
    return [dict(definition) for definition in TOOL_DEFINITIONS]


def _finding(code: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def _as_rel(path: Path | None, repo: Path) -> str:
    if path is None:
        return ""
    return relpath(path, repo)


def _slug(value: str, fallback: str) -> str:
    slug = TOKEN_RE.sub("-", value.lower()).strip("-")
    return slug[:64] or fallback


def _date_token(iso_timestamp: str) -> str:
    match = DATE_RE.match(iso_timestamp)
    if not match:
        return "undated"
    return "".join(match.groups())


def _candidate_id(agent: str, iso_timestamp: str, summary: str) -> str:
    digest = hashlib.sha256(f"{agent}{iso_timestamp}{summary}".encode("utf-8")).hexdigest()
    return f"CAND-{digest[:16]}"


def _session_file_token(session_id: str) -> str:
    if SESSION_ID_RE.fullmatch(session_id):
        return session_id
    slug = _slug(session_id, "invalid-session")
    return slug[:128] or "invalid-session"


def _sessions_dir(repo: Path) -> Path:
    return repo / "knowledge-staging" / "_sessions"


def _failed_dir(repo: Path) -> Path:
    return repo / "knowledge-staging" / "_failed"


def _candidate_root(repo: Path) -> Path:
    return repo / "knowledge-staging"


def _assert_allowed_write(path: Path, repo: Path) -> None:
    staging = (repo / "knowledge-staging").resolve()
    resolved = path.resolve()
    if not is_under(resolved, staging):
        raise RuntimeError(f"gateway write outside knowledge-staging rejected: {resolved}")
    if is_under(resolved, repo / "memory"):
        raise RuntimeError(f"gateway durable write rejected: {resolved}")
    relative = resolved.relative_to(staging)
    allowed_root_candidate = (
        len(relative.parts) == 1 and resolved.name.startswith("cand-") and resolved.suffix == ".md"
    )
    allowed_session_log = (
        len(relative.parts) == 2
        and relative.parts[0] == "_sessions"
        and resolved.suffix == ".jsonl"
    )
    allowed_failed_candidate = (
        len(relative.parts) == 2
        and relative.parts[0] == "_failed"
        and resolved.name.startswith("CAND-")
        and resolved.suffix == ".md"
    )
    if not (allowed_root_candidate or allowed_session_log or allowed_failed_candidate):
        raise RuntimeError(f"gateway write target rejected: {resolved}")


def _append_session_log(
    repo: Path,
    *,
    session_id: str,
    tool: str,
    agent_claim: str | None,
    transport_identity: str | None,
    query_or_summary: str,
    candidate_id: str | None,
    candidate_path: Path | None,
    result_ok: bool,
    findings: list[dict[str, Any]],
    redacted_session: bool = False,
) -> Path:
    safe_session_id = "redacted-session" if redacted_session else _session_file_token(session_id)
    session_path = _sessions_dir(repo) / f"{safe_session_id}.jsonl"
    _assert_allowed_write(session_path, repo)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp_utc": iso_now(),
        "session_id": "[REDACTED_SECRET]" if redacted_session else session_id,
        "tool": tool,
        "agent_claim": agent_claim,
        "transport_identity": transport_identity,
        "query_or_summary": query_or_summary,
        "candidate_id": candidate_id,
        "candidate_path": _as_rel(candidate_path, repo) or None,
        "result_ok": result_ok,
        "findings": findings,
    }
    with session_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return session_path


def _walk_strings(value: Any, path: str = "<root>") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, dict):
        items: list[tuple[str, str]] = []
        for key, item in value.items():
            child_path = f"{path}.{key}" if path != "<root>" else str(key)
            if isinstance(item, str) and SECRET_FIELD_RE.search(str(key)) and item:
                items.append((child_path, f"{key}=<redacted>"))
            items.extend(_walk_strings(item, child_path))
        return items
    if isinstance(value, list):
        items = []
        for index, item in enumerate(value):
            items.extend(_walk_strings(item, f"{path}[{index}]"))
        return items
    return []


def _secret_findings(value: Any) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for path, text in _walk_strings(value):
        for name, pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(text):
                key = (path, name)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    _finding(
                        "secret_material_rejected",
                        (
                            f"secret-like material detected at {path} ({name}); "
                            "raw material not stored"
                        ),
                    )
                )
    return findings


def _has_secret_at(findings: list[dict[str, str]], path: str) -> bool:
    needle = f"detected at {path} ("
    return any(needle in item.get("message", "") for item in findings)


def _capabilities(repo: Path) -> dict[str, Any]:
    path = repo / "tools" / "memory" / "gateway_capabilities.yaml"
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


def _sensitive_allowed(repo: Path, transport_identity: str | None) -> bool:
    allowlist = _capabilities(repo).get("sensitive_retrieval_allowlist", [])
    if not isinstance(allowlist, list) or not allowlist:
        return False
    return bool(transport_identity and transport_identity in allowlist)


def _validate_session_id(session_id: Any) -> list[dict[str, str]]:
    if not isinstance(session_id, str) or not session_id:
        return [_finding("invalid_session_id", "session_id must be a non-empty string")]
    if not SESSION_ID_RE.fullmatch(session_id):
        return [
            _finding(
                "invalid_session_id",
                "session_id must contain only letters, numbers, dot, underscore, or hyphen",
            )
        ]
    return []


def _filter_retrieve_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for item in results:
        if item.get("lifecycle_state") in RETRIEVE_EXCLUDED_LIFECYCLE:
            continue
        if item.get("has_medium_high_conflict") or item.get("excluded_reason"):
            continue
        filtered.append(item)
    return filtered


def memory_retrieve(
    args: dict[str, Any], *, repo: Path | None = None, transport_identity: str | None = None
) -> dict[str, Any]:
    repo_path = repo_root(repo or Path.cwd())
    session_id = str(args.get("session_id") or "")
    query = args.get("query")
    findings = _validate_session_id(session_id)
    if not isinstance(query, str):
        findings.append(_finding("invalid_query", "query must be a string"))
        query = ""
    secret_probe = {"session_id": session_id, "query": query}
    if transport_identity is not None:
        secret_probe["transport_identity"] = transport_identity
    secret_findings = _secret_findings(secret_probe)
    redacted_session = _has_secret_at(secret_findings, "session_id")
    redacted_transport = (
        "[REDACTED_SECRET]"
        if _has_secret_at(secret_findings, "transport_identity")
        else transport_identity
    )
    if secret_findings:
        findings.extend(secret_findings)
        session_path = _append_session_log(
            repo_path,
            session_id=session_id,
            tool=TOOL_RETRIEVE,
            agent_claim=None,
            transport_identity=redacted_transport,
            query_or_summary="[REDACTED_SECRET]",
            candidate_id=None,
            candidate_path=None,
            result_ok=False,
            findings=findings,
            redacted_session=redacted_session,
        )
        return {
            "ok": False,
            "results": [],
            "findings": findings,
            "session_log_path": relpath(session_path, repo_path),
        }

    scope = args.get("scope")
    authority_floor = args.get("authority_floor")
    include_sensitive = args.get("include_sensitive", False)
    limit = args.get("limit", 10)
    if scope not in SCOPES:
        findings.append(_finding("invalid_scope", f"scope must be one of {sorted(SCOPES)}"))
    if authority_floor not in GATEWAY_AUTHORITY_FLOORS:
        findings.append(
            _finding(
                "invalid_authority_floor",
                f"authority_floor must be one of {list(GATEWAY_AUTHORITY_FLOORS)}",
            )
        )
    if not isinstance(include_sensitive, bool):
        findings.append(_finding("invalid_include_sensitive", "include_sensitive must be boolean"))
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        findings.append(_finding("invalid_limit", "limit must be integer >= 1"))
        limit = 10
    if include_sensitive is True and not _sensitive_allowed(repo_path, transport_identity):
        findings.append(
            _finding(
                "sensitive_retrieval_denied",
                "include_sensitive denied by empty v0.1 sensitive retrieval allow-list",
            )
        )
    if findings:
        session_path = _append_session_log(
            repo_path,
            session_id=session_id,
            tool=TOOL_RETRIEVE,
            agent_claim=None,
            transport_identity=transport_identity,
            query_or_summary=query,
            candidate_id=None,
            candidate_path=None,
            result_ok=False,
            findings=findings,
        )
        return {
            "ok": False,
            "results": [],
            "findings": findings,
            "session_log_path": relpath(session_path, repo_path),
        }

    raw_results = phase1_retrieve(
        repo_path,
        query=query,
        scope=scope,
        authority_floor=authority_floor,
        include_sensitive=False,
    )
    results = _filter_retrieve_results(raw_results)[:limit]
    session_path = _append_session_log(
        repo_path,
        session_id=session_id,
        tool=TOOL_RETRIEVE,
        agent_claim=None,
        transport_identity=transport_identity,
        query_or_summary=query,
        candidate_id=None,
        candidate_path=None,
        result_ok=True,
        findings=[],
    )
    return {
        "ok": True,
        "results": results,
        "findings": [],
        "session_log_path": relpath(session_path, repo_path),
    }


def _classification(proposed_action: str, proposed_authority_class: str) -> str:
    if proposed_action == "conflict_open":
        return "conflict_candidate"
    if proposed_action == "archive":
        return "archive_candidate"
    if proposed_authority_class == "observation":
        return "observation"
    if proposed_authority_class == "shared_knowledge":
        return "shared_knowledge_candidate"
    return "agent_memory_candidate"


def _staging_status(classification: str) -> str:
    return "conflict_candidate" if classification == "conflict_candidate" else "candidate_packet"


def _candidate_payload(args: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    classification = _classification(
        str(args.get("proposed_action") or ""),
        str(args.get("proposed_authority_class") or ""),
    )
    return {
        "candidate_id": candidate_id,
        "source_agent": args.get("agent"),
        "source_packet_type": "memory_gateway_capture",
        "source_packet_id": f"gateway-{candidate_id}",
        "generated_utc": args.get("iso_timestamp"),
        "proposed_action": args.get("proposed_action"),
        "proposed_record_kind": args.get("proposed_record_kind"),
        "proposed_authority_class": args.get("proposed_authority_class"),
        "scope": args.get("scope"),
        "requires_human_review": True,
        "authority_impact": args.get("authority_impact", "low"),
        "personal_inference": args.get("personal_inference"),
        "sensitivity": args.get("sensitivity"),
        "retention_class": args.get("retention_class", "medium"),
        "classification": classification,
        "staging_status": _staging_status(classification),
        "promotion_basis": args.get("promotion_basis"),
        "sources": args.get("sources"),
        "summary": args.get("summary"),
        "payload": args.get("payload"),
    }


def _candidate_path(repo: Path, agent: str, iso_timestamp: str, candidate_id: str) -> Path:
    digest = candidate_id.removeprefix("CAND-")
    filename = f"cand-{_date_token(iso_timestamp)}-{_slug(agent, 'agent')}-{digest}.md"
    return _candidate_root(repo) / filename


def _write_packet(path: Path, repo: Path, payload: dict[str, Any], body: str) -> None:
    _assert_allowed_write(path, repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_front_matter(path, payload, body)


def _validation_findings(errors: list[str]) -> list[dict[str, str]]:
    return [_finding("candidate_validation_failed", error) for error in errors]


def _required_capture_findings(args: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    required = (
        "session_id",
        "agent",
        "iso_timestamp",
        "summary",
        "proposed_action",
        "proposed_record_kind",
        "proposed_authority_class",
        "scope",
        "sensitivity",
        "personal_inference",
        "promotion_basis",
        "sources",
        "payload",
    )
    for key in required:
        if key not in args or args[key] in (None, "", []):
            findings.append(_finding("missing_capture_field", f"{key} is required"))
    if "personal_inference" in args and not isinstance(args.get("personal_inference"), bool):
        findings.append(
            _finding("invalid_personal_inference", "personal_inference must be boolean")
        )
    if "payload" in args and not isinstance(args.get("payload"), dict):
        findings.append(_finding("invalid_payload", "payload must be object"))
    return findings


def memory_capture_candidate(
    args: dict[str, Any], *, repo: Path | None = None, transport_identity: str | None = None
) -> dict[str, Any]:
    repo_path = repo_root(repo or Path.cwd())
    session_id = str(args.get("session_id") or "")
    summary = str(args.get("summary") or "")
    agent = str(args.get("agent") or "")
    iso_timestamp = str(args.get("iso_timestamp") or "")
    candidate_id = _candidate_id(agent, iso_timestamp, summary)
    candidate_path: Path | None = None
    findings = _validate_session_id(session_id)

    secret_probe = dict(args)
    if transport_identity is not None:
        secret_probe["transport_identity"] = transport_identity
    secret_findings = _secret_findings(secret_probe)
    redacted_session = _has_secret_at(secret_findings, "session_id")
    redacted_agent = "[REDACTED_SECRET]" if _has_secret_at(secret_findings, "agent") else agent
    redacted_transport = (
        "[REDACTED_SECRET]"
        if _has_secret_at(secret_findings, "transport_identity")
        else transport_identity
    )
    if secret_findings:
        findings.extend(secret_findings)
        session_path = _append_session_log(
            repo_path,
            session_id=session_id,
            tool=TOOL_CAPTURE,
            agent_claim=redacted_agent or None,
            transport_identity=redacted_transport,
            query_or_summary="[REDACTED_SECRET]",
            candidate_id=candidate_id,
            candidate_path=None,
            result_ok=False,
            findings=findings,
            redacted_session=redacted_session,
        )
        return {
            "ok": False,
            "candidate_id": candidate_id,
            "candidate_path": "",
            "session_log_path": relpath(session_path, repo_path),
            "findings": findings,
        }

    if args.get("proposed_authority_class") == "canonical_doctrine":
        findings.append(
            _finding(
                "canonical_doctrine_rejected",
                "canonical_doctrine capture is rejected at input in gateway v0.1",
            )
        )
        session_path = _append_session_log(
            repo_path,
            session_id=session_id,
            tool=TOOL_CAPTURE,
            agent_claim=agent or None,
            transport_identity=transport_identity,
            query_or_summary=summary,
            candidate_id=candidate_id,
            candidate_path=None,
            result_ok=False,
            findings=findings,
        )
        return {
            "ok": False,
            "candidate_id": candidate_id,
            "candidate_path": "",
            "session_log_path": relpath(session_path, repo_path),
            "findings": findings,
        }

    findings.extend(_required_capture_findings(args))
    personal_sensitive = args.get("personal_inference") is True and args.get("sensitivity") in {
        "sensitive",
        "secret",
    }
    if personal_sensitive:
        findings.append(
            _finding(
                "personal_inference_sensitivity_rejected",
                (
                    "personal inference with sensitive or secret sensitivity is rejected "
                    "in gateway v0.1"
                ),
            )
        )

    payload = _candidate_payload(args, candidate_id)
    validation_errors = validate_candidate(payload, repo_path)
    if validation_errors:
        findings.extend(_validation_findings(validation_errors))

    if findings:
        failed_path = _failed_dir(repo_path) / f"{candidate_id}.md"
        failed_payload = dict(payload)
        failed_payload["gateway_findings"] = findings
        body = "Candidate packet failed gateway validation. Human review required before reuse.\n"
        _write_packet(failed_path, repo_path, failed_payload, body)
        session_path = _append_session_log(
            repo_path,
            session_id=session_id,
            tool=TOOL_CAPTURE,
            agent_claim=agent or None,
            transport_identity=transport_identity,
            query_or_summary=summary,
            candidate_id=candidate_id,
            candidate_path=failed_path,
            result_ok=False,
            findings=findings,
        )
        return {
            "ok": False,
            "candidate_id": candidate_id,
            "candidate_path": relpath(failed_path, repo_path),
            "session_log_path": relpath(session_path, repo_path),
            "findings": findings,
        }

    candidate_path = _candidate_path(repo_path, agent, iso_timestamp, candidate_id)
    body = "Gateway candidate packet. Requires human review before durable memory disposition.\n"
    _write_packet(candidate_path, repo_path, payload, body)
    session_path = _append_session_log(
        repo_path,
        session_id=session_id,
        tool=TOOL_CAPTURE,
        agent_claim=agent,
        transport_identity=transport_identity,
        query_or_summary=summary,
        candidate_id=candidate_id,
        candidate_path=candidate_path,
        result_ok=True,
        findings=[],
    )
    return {
        "ok": True,
        "candidate_id": candidate_id,
        "candidate_path": relpath(candidate_path, repo_path),
        "session_log_path": relpath(session_path, repo_path),
        "findings": [],
    }


def call_tool(
    name: str,
    args: dict[str, Any],
    *,
    repo: Path | None = None,
    transport_identity: str | None = None,
) -> dict[str, Any]:
    if name == TOOL_RETRIEVE:
        return memory_retrieve(args, repo=repo, transport_identity=transport_identity)
    if name == TOOL_CAPTURE:
        return memory_capture_candidate(args, repo=repo, transport_identity=transport_identity)
    return {
        "ok": False,
        "results": [],
        "findings": [_finding("unknown_tool", f"unsupported tool: {name}")],
        "session_log_path": "",
    }


def _run_jsonl_stdio() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            name = request.get("tool") or request.get("name")
            args = request.get("arguments") or request.get("args") or {}
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
            response = call_tool(str(name), args)
        except Exception as exc:
            response = {
                "ok": False,
                "findings": [_finding("request_failed", str(exc))],
                "session_log_path": "",
            }
        sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
        sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LifeOS Memory Gateway v0.1 local tool server.")
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--call", choices=list(EXPOSED_TOOL_NAMES))
    parser.add_argument("--arguments", default="{}")
    args = parser.parse_args(argv)
    if args.list_tools:
        print(json.dumps({"tools": tool_definitions()}, indent=2, sort_keys=True))
        return 0
    if args.call:
        payload = json.loads(args.arguments)
        if not isinstance(payload, dict):
            raise SystemExit("--arguments must decode to an object")
        print(json.dumps(call_tool(args.call, payload), indent=2, sort_keys=True))
        return 0
    return _run_jsonl_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
