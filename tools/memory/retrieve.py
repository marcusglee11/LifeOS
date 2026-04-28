#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from memory_lib import AUTHORITY_ORDER, listify, read_record, relpath, repo_root

EXCLUDED_LIFECYCLE = {"archived", "superseded"}
BLOCKING_MATERIALITY = {"medium", "high"}
DEFAULT_SENSITIVE_EXCLUDE = {"sensitive", "secret"}


def _text_match(query_terms: list[str], payload: dict[str, Any], body: str) -> bool:
    haystack = " ".join(
        str(payload.get(key, ""))
        for key in ("id", "title", "record_kind", "scope", "project", "agent", "tags", "summary")
    )
    haystack = f"{haystack} {body}".lower()
    return all(term in haystack for term in query_terms)


def _conflict_state(payload: dict[str, Any]) -> dict[str, Any]:
    conflicts = listify(payload.get("conflicts"))
    material = [
        item
        for item in conflicts
        if isinstance(item, dict)
        and item.get("status", "open") in {"open", "acknowledged", "blocked"}
        and item.get("materiality") in BLOCKING_MATERIALITY
    ]
    return {
        "has_medium_high_conflict": bool(material),
        "conflicts": conflicts,
    }


def _record_result(path: Path, repo: Path, payload: dict[str, Any]) -> dict[str, Any]:
    conflict_state = _conflict_state(payload)
    return {
        "source_path": relpath(path, repo),
        "record_id": payload.get("id"),
        "record_kind": payload.get("record_kind"),
        "authority_class": payload.get("authority_class"),
        "scope": payload.get("scope"),
        "lifecycle_state": payload.get("lifecycle_state"),
        "review_after": payload.get("review_after"),
        "superseded_by": payload.get("superseded_by"),
        "conflicts": conflict_state["conflicts"],
        "has_medium_high_conflict": conflict_state["has_medium_high_conflict"],
        "sensitivity": payload.get("sensitivity"),
        "last_updated": payload.get("updated_utc"),
        "write_receipts": listify(payload.get("write_receipts")),
    }


def retrieve(
    repo: Path,
    *,
    query: str,
    scope: str,
    authority_floor: str,
    include_sensitive: bool,
) -> list[dict[str, Any]]:
    terms = [term.lower() for term in query.split() if term.strip()]
    floor = AUTHORITY_ORDER[authority_floor]
    results: list[dict[str, Any]] = []
    for root in (repo / "docs", repo / "memory", repo / "knowledge-staging"):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            try:
                record = read_record(path)
            except Exception:
                continue
            payload = record.front_matter
            if "authority_class" not in payload or "record_kind" not in payload:
                continue
            authority = AUTHORITY_ORDER.get(str(payload.get("authority_class")), -1)
            if authority < floor:
                continue
            if payload.get("lifecycle_state") in EXCLUDED_LIFECYCLE:
                continue
            if not include_sensitive and payload.get("sensitivity") in DEFAULT_SENSITIVE_EXCLUDE:
                continue
            if scope != "any" and payload.get("scope") not in {scope, "global"}:
                continue
            if terms and not _text_match(terms, payload, record.body):
                continue
            conflict_state = _conflict_state(payload)
            if conflict_state["has_medium_high_conflict"]:
                result = _record_result(path, repo, payload)
                result["excluded_reason"] = "medium_high_conflict"
                results.append(result)
                continue
            results.append(_record_result(path, repo, payload))

    def sort_key(item: dict[str, Any]) -> tuple[int, int, int, str, str]:
        authority = AUTHORITY_ORDER.get(str(item.get("authority_class")), -1)
        pass_order = (
            0 if item.get("authority_class") in {"canonical_doctrine", "shared_knowledge"} else 1
        )
        exact_scope = 0 if item.get("scope") == scope else 1
        updated = str(item.get("last_updated") or "")
        return (pass_order, -authority, exact_scope, updated, str(item.get("source_path")))

    return sorted(results, key=sort_key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Retrieve Phase 1 memory without vectors or embeddings."
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument(
        "--authority-floor",
        required=True,
        choices=sorted(AUTHORITY_ORDER.keys()),
    )
    parser.add_argument("--include-sensitive", default="false", choices=["true", "false"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    repo = repo_root(Path.cwd())
    results = retrieve(
        repo,
        query=args.query,
        scope=args.scope,
        authority_floor=args.authority_floor,
        include_sensitive=args.include_sensitive == "true",
    )
    if args.json:
        print(json.dumps({"results": results}, indent=2, sort_keys=True))
    else:
        for item in results:
            print(
                f"{item['source_path']} | {item['record_id']} | {item['record_kind']} | "
                f"{item['authority_class']} | {item['scope']} | {item['lifecycle_state']} | "
                f"sensitivity={item['sensitivity']} | conflicts={item['has_medium_high_conflict']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
