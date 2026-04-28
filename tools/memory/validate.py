#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from memory_lib import (
    AUTHORITY_CLASSES,
    AUTHORITY_IMPACTS,
    CLASSIFICATIONS,
    CONFLICT_STATUSES,
    CONFLICT_TYPES,
    DISPOSITIONS,
    LIFECYCLE_STATES,
    MATERIALITIES,
    PROPOSED_ACTIONS,
    RECORD_KINDS,
    RETENTION_CLASSES,
    SCOPES,
    SENSITIVITIES,
    SOURCE_TYPES,
    STAGING_STATUSES,
    SUPERSESSION_TYPES,
    WRITER_ALLOWED,
    has_commit_stable_provenance,
    is_under,
    iter_yaml_markdown_files,
    listify,
    read_record,
    relpath,
    repo_root,
    validate_json_schema,
)

DURABLE_REQUIRED = {
    "id",
    "title",
    "record_kind",
    "authority_class",
    "scope",
    "sensitivity",
    "retention_class",
    "lifecycle_state",
    "created_utc",
    "updated_utc",
    "owner",
    "writer",
    "sources",
}


def _kind(path: Path, payload: dict[str, Any], repo: Path) -> str:
    rel = relpath(path, repo)
    if payload.get("receipt_id"):
        return "receipt"
    if payload.get("staging_status") == "conflict_candidate" or payload.get("conflict_id"):
        return "conflict"
    if payload.get("distillation_id") or payload.get("workorder_id"):
        return "distillation"
    if payload.get("from_record") and payload.get("to_record"):
        return "supersession"
    if payload.get("candidate_id") or rel.startswith("knowledge-staging/"):
        return "candidate"
    if rel.startswith("memory/") and not rel.startswith("memory/receipts/"):
        return "durable"
    return "unknown"


def _require(
    errors: list[str], payload: dict[str, Any], fields: set[str], prefix: str = ""
) -> None:
    for field in sorted(fields):
        if field not in payload or payload[field] in (None, "", []):
            errors.append(f"{prefix}missing required field: {field}")


def _enum(
    errors: list[str], payload: dict[str, Any], field: str, allowed: set[str], prefix: str = ""
) -> None:
    if field in payload and payload[field] not in allowed:
        errors.append(f"{prefix}invalid enum {field}: {payload[field]!r}")


def _validate_sources(errors: list[str], payload: dict[str, Any], prefix: str = "") -> None:
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{prefix}sources must be a non-empty list")
        return
    for idx, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"{prefix}sources[{idx}] must be object")
            continue
        for field in ("source_type", "locator", "captured_utc"):
            if not source.get(field):
                errors.append(f"{prefix}sources[{idx}] missing {field}")
        if source.get("source_type") not in SOURCE_TYPES:
            errors.append(
                f"{prefix}sources[{idx}] invalid source_type: {source.get('source_type')!r}"
            )
        if not has_commit_stable_provenance(source):
            errors.append(f"{prefix}sources[{idx}] repo evidence missing commit-stable provenance")


def validate_durable(path: Path, payload: dict[str, Any], repo: Path) -> list[str]:
    errors: list[str] = []
    _require(errors, payload, DURABLE_REQUIRED)
    for field, allowed in (
        ("record_kind", RECORD_KINDS),
        ("authority_class", AUTHORITY_CLASSES),
        ("scope", SCOPES),
        ("sensitivity", SENSITIVITIES),
        ("retention_class", RETENTION_CLASSES),
        ("lifecycle_state", LIFECYCLE_STATES),
        ("authority_impact", AUTHORITY_IMPACTS),
    ):
        _enum(errors, payload, field, allowed)
    if payload.get("writer") != WRITER_ALLOWED:
        errors.append("durable records require writer == COO")
    _validate_sources(errors, payload)
    if payload.get("record_kind") == "state":
        _require(errors, payload, {"state_subject", "state_observed_utc"})
    if (
        payload.get("lifecycle_state") == "active"
        and payload.get("authority_class") != "canonical_doctrine"
    ):
        if not payload.get("review_after"):
            errors.append("active non-canon durable records require review_after")
    if payload.get("derived_from_candidate") is True and not listify(payload.get("write_receipts")):
        errors.append("candidate-derived durable records require write_receipts")
    if payload.get("superseded_by") and payload.get("lifecycle_state") != "superseded":
        errors.append("superseded_by requires lifecycle_state superseded")
    open_material = [
        item
        for item in listify(payload.get("conflicts"))
        if isinstance(item, dict)
        and item.get("status", "open") in {"open", "acknowledged", "blocked"}
        and item.get("materiality") in {"medium", "high"}
    ]
    if open_material and payload.get("lifecycle_state") != "conflicted":
        errors.append("open medium/high conflicts require lifecycle_state conflicted")

    rel = relpath(path, repo)
    if payload.get("scope") == "agent":
        agent = payload.get("agent")
        if not agent:
            errors.append("scope agent requires agent")
        elif not rel.startswith(f"memory/agents/{agent}/"):
            errors.append("scope agent records must live under memory/agents/<agent_name>/")
    elif rel.startswith("memory/agents/"):
        errors.append("records under memory/agents/<agent_name>/ must have scope agent")
    return errors


def validate_candidate(payload: dict[str, Any], repo: Path) -> list[str]:
    errors = validate_json_schema(repo, "candidate_packet.schema.json", payload)
    for field, allowed in (
        ("proposed_action", PROPOSED_ACTIONS),
        ("proposed_record_kind", RECORD_KINDS),
        ("proposed_authority_class", AUTHORITY_CLASSES),
        ("scope", SCOPES),
        ("authority_impact", AUTHORITY_IMPACTS),
        ("sensitivity", SENSITIVITIES),
        ("classification", CLASSIFICATIONS),
        ("staging_status", STAGING_STATUSES),
    ):
        _enum(errors, payload, field, allowed)
    _validate_sources(errors, payload)
    return errors


def validate_receipt(payload: dict[str, Any], repo: Path) -> list[str]:
    schema = (
        "batched_durable_write_receipt.schema.json"
        if payload.get("receipt_type") == "batch"
        else "durable_write_receipt.schema.json"
    )
    errors = validate_json_schema(repo, schema, payload)
    if payload.get("decided_by") != WRITER_ALLOWED:
        errors.append("receipt decided_by must be COO")
    entries = payload.get("entries") if payload.get("receipt_type") == "batch" else [payload]
    if isinstance(entries, list):
        for idx, entry in enumerate(entries):
            if isinstance(entry, dict) and entry.get("disposition") not in DISPOSITIONS:
                errors.append(f"entries[{idx}] invalid disposition: {entry.get('disposition')!r}")
    return errors


def validate_conflict(payload: dict[str, Any], repo: Path) -> list[str]:
    errors = validate_json_schema(repo, "conflict_record.schema.json", payload)
    for field, allowed in (
        ("status", CONFLICT_STATUSES),
        ("conflict_type", CONFLICT_TYPES),
        ("materiality", MATERIALITIES),
    ):
        _enum(errors, payload, field, allowed)
    if payload.get("owner") != WRITER_ALLOWED:
        errors.append("conflict owner must be COO")
    return errors


def validate_supersession(payload: dict[str, Any], repo: Path) -> list[str]:
    errors = validate_json_schema(repo, "supersession_edge.schema.json", payload)
    _enum(errors, payload, "supersession_type", SUPERSESSION_TYPES)
    if payload.get("decided_by") != WRITER_ALLOWED:
        errors.append("supersession decided_by must be COO")
    return errors


def validate_distillation(payload: dict[str, Any], repo: Path) -> list[str]:
    return validate_json_schema(repo, "distillation_packet.schema.json", payload)


def validate_path(path: Path, repo: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for file_path in iter_yaml_markdown_files(path):
        rel = relpath(file_path, repo)
        if file_path.name == ".gitkeep" or file_path.name == "README.md":
            continue
        try:
            if file_path.suffix == ".json":
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            else:
                payload = read_record(file_path).front_matter
        except Exception as exc:
            findings.append({"path": rel, "error": str(exc)})
            continue
        if not isinstance(payload, dict):
            findings.append({"path": rel, "error": "payload must be object"})
            continue
        kind = _kind(file_path, payload, repo)
        if kind == "durable":
            errors = validate_durable(file_path, payload, repo)
        elif kind == "candidate":
            errors = validate_candidate(payload, repo)
        elif kind == "receipt":
            errors = validate_receipt(payload, repo)
        elif kind == "conflict":
            errors = validate_conflict(payload, repo)
        elif kind == "supersession":
            errors = validate_supersession(payload, repo)
        elif kind == "distillation":
            errors = validate_distillation(payload, repo)
        else:
            errors = []
        for error in errors:
            findings.append({"path": rel, "error": error})

        if is_under(file_path, repo / "memory") and not is_under(
            file_path, repo / "memory" / "receipts"
        ):
            if kind != "durable":
                findings.append(
                    {"path": rel, "error": "direct non-durable write under memory/ rejected"}
                )
            elif payload.get("writer") != WRITER_ALLOWED:
                findings.append(
                    {"path": rel, "error": "direct non-COO durable write to memory/ rejected"}
                )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate LifeOS Phase 1 memory records.")
    parser.add_argument("path", help="file or directory to validate")
    parser.add_argument("--json", action="store_true", help="emit JSON findings")
    args = parser.parse_args(argv)
    repo = repo_root(Path.cwd())
    findings = validate_path((Path.cwd() / args.path).resolve(), repo)
    if args.json:
        print(json.dumps({"ok": not findings, "findings": findings}, indent=2, sort_keys=True))
    else:
        if not findings:
            print("OK")
        for finding in findings:
            print(f"{finding['path']}: {finding['error']}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
