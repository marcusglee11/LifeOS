#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

DEFAULT_CATALOG_PATH = Path("config/openclaw/gate_reason_catalog.json")


class CatalogError(RuntimeError):
    pass


def load_catalog(path: Path) -> Dict[str, dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CatalogError(f"catalog_read_failed:{type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise CatalogError("catalog_not_object")
    reasons = payload.get("reasons")
    if not isinstance(reasons, dict):
        raise CatalogError("catalog_reasons_not_object")
    normalized: Dict[str, dict] = {}
    for code, meta in reasons.items():
        if not isinstance(code, str) or not code.strip():
            continue
        if not isinstance(meta, dict):
            continue
        normalized[code.strip()] = {
            "severity": str(meta.get("severity") or "hard").strip().lower() or "hard",
            "drift_bypassable": bool(meta.get("drift_bypassable", False)),
            "owner_system": str(meta.get("owner_system") or "unknown").strip() or "unknown",
        }
    if not normalized:
        raise CatalogError("catalog_empty")
    return normalized


def classify_reasons(codes: Iterable[str], catalog: Dict[str, dict]) -> Tuple[List[str], List[str], List[str]]:
    bypassable: List[str] = []
    hard: List[str] = []
    unknown: List[str] = []

    for raw in codes:
        code = str(raw or "").strip()
        if not code:
            continue
        meta = catalog.get(code)
        if meta is None:
            unknown.append(code)
            hard.append(code)
            continue
        if bool(meta.get("drift_bypassable", False)):
            bypassable.append(code)
        else:
            hard.append(code)

    return bypassable, hard, unknown


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify OpenClaw gate reasons against the canonical catalog.")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH))
    parser.add_argument("--reasons", nargs="*", default=[])
    parser.add_argument("--reasons-file", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    reasons = [str(r).strip() for r in args.reasons if str(r).strip()]
    if args.reasons_file:
        rf = Path(args.reasons_file)
        if rf.exists():
            reasons.extend([line.strip() for line in rf.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()])

    try:
        catalog = load_catalog(Path(args.catalog))
        bypassable, hard, unknown = classify_reasons(reasons, catalog)
        payload = {
            "catalog_ok": True,
            "can_bypass": bool(bypassable) and not hard,
            "bypassable": bypassable,
            "hard": hard,
            "unknown": unknown,
        }
    except CatalogError as exc:
        payload = {
            "catalog_ok": False,
            "can_bypass": False,
            "bypassable": [],
            "hard": ["gate_reason_catalog_failed"],
            "unknown": [],
            "error": str(exc),
        }

    if args.json:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(f"catalog_ok={'true' if payload['catalog_ok'] else 'false'}")
        print(f"can_bypass={'true' if payload['can_bypass'] else 'false'}")
        print("bypassable=" + ",".join(payload["bypassable"]))
        print("hard=" + ",".join(payload["hard"]))
        print("unknown=" + ",".join(payload["unknown"]))

    return 0 if payload["catalog_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
