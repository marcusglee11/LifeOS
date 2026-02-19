#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ALLOWED_KEYS = {"status", "summary", "sources", "counts"}
ALLOWED_STATUS = {"ok", "warn", "fail", "error", "degraded"}
SOURCE_PTR_RE = re.compile(r"^[A-Za-z0-9_./:#@+\-]{1,220}$")
MAX_SUMMARY_CHARS = 280
MAX_SOURCES = 16
MAX_COUNTS = 32


def _metadata_schema_checks(payload: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    keys = set(payload.keys())
    extra = sorted(keys - ALLOWED_KEYS)
    if extra:
        reasons.append(f"extra_keys:{','.join(extra)}")

    status = payload.get("status")
    if not isinstance(status, str) or status.strip().lower() not in ALLOWED_STATUS:
        reasons.append("invalid_status")

    summary = payload.get("summary")
    if not isinstance(summary, str):
        reasons.append("summary_not_string")
    else:
        stripped = summary.strip()
        if not stripped:
            reasons.append("summary_empty")
        if len(stripped) > MAX_SUMMARY_CHARS:
            reasons.append("summary_too_long")
        if "\n" in stripped or "```" in stripped:
            reasons.append("summary_not_single_line")

    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        reasons.append("sources_not_list")
    else:
        if len(sources) > MAX_SOURCES:
            reasons.append("sources_too_many")
        for item in sources:
            if not isinstance(item, str) or not SOURCE_PTR_RE.match(item.strip()):
                reasons.append("invalid_source_pointer")
                break

    counts = payload.get("counts", {})
    if not isinstance(counts, dict):
        reasons.append("counts_not_object")
    else:
        if len(counts) > MAX_COUNTS:
            reasons.append("counts_too_many_keys")
        for key, value in counts.items():
            if not isinstance(key, str) or not key.strip():
                reasons.append("invalid_count_key")
                break
            if not isinstance(value, (int, float)):
                reasons.append("invalid_count_value")
                break
            if value < 0:
                reasons.append("invalid_count_negative")
                break

    return reasons


def classify_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "classification": "contentful",
            "allowed_for_scheduled": False,
            "reasons": ["payload_not_object"],
        }

    reasons = _metadata_schema_checks(payload)
    metadata_only = len(reasons) == 0
    return {
        "classification": "metadata_only" if metadata_only else "contentful",
        "allowed_for_scheduled": metadata_only,
        "reasons": reasons,
    }


def classify_payload_text(payload_text: str) -> Dict[str, Any]:
    raw = payload_text.strip()
    if not raw:
        return {
            "classification": "contentful",
            "allowed_for_scheduled": False,
            "reasons": ["payload_empty"],
        }
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "classification": "contentful",
            "allowed_for_scheduled": False,
            "reasons": ["payload_not_json"],
        }
    return classify_payload(parsed)


def _load_payload(args: argparse.Namespace) -> Tuple[str, str]:
    if args.payload_file:
        return Path(args.payload_file).read_text(encoding="utf-8"), args.payload_file
    if args.payload is not None:
        return args.payload, "inline"
    return sys.stdin.read(), "stdin"


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify outbound payloads for OpenClaw scheduled egress policy.")
    parser.add_argument("--payload", default=None, help="Raw payload text.")
    parser.add_argument("--payload-file", default="", help="Path to payload text file.")
    parser.add_argument("--scheduled", action="store_true", help="Fail closed unless payload is metadata_only.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload_text, payload_source = _load_payload(args)
    result = classify_payload_text(payload_text)
    result["payload_source"] = payload_source

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(
            f"classification={result['classification']} "
            f"allowed_for_scheduled={'true' if result['allowed_for_scheduled'] else 'false'} "
            f"reasons={','.join(result['reasons']) if result['reasons'] else 'none'} "
            f"payload_source={payload_source}"
        )

    if args.scheduled and not result["allowed_for_scheduled"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
