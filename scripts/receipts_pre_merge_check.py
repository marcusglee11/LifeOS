#!/usr/bin/env python3
"""
Phase B pre-merge enforcement gate.

Usage:
    python scripts/receipts_pre_merge_check.py \
        --workspace-sha <sha> --plan-sha <sha256> --store <path>

Exit codes: 0 = allow, 1 = blocked, 2 = usage error
Output: JSON to stdout {"allowed", "reason_code", "receipt_id", "detail"}

Env:
    LIFEOS_MOCK_TREE_OID: Override tree OID resolution (for testing only).
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from runtime.receipts.pre_merge import run_pre_merge_check
from runtime.receipts import plan_core as _pc


def main() -> int:
    p = argparse.ArgumentParser(description="Pre-merge receipt enforcement check")
    p.add_argument("--workspace-sha", required=True)
    p.add_argument("--plan-sha", required=True)
    p.add_argument("--store", required=True)
    p.add_argument("--repo-root", default=None)
    args = p.parse_args()

    mock_oid = os.environ.get("LIFEOS_MOCK_TREE_OID")
    if mock_oid:
        _pc.resolve_tree_oid = lambda sha, **kw: mock_oid  # type: ignore[assignment]

    result = run_pre_merge_check(
        workspace_sha=args.workspace_sha,
        plan_core_sha256=args.plan_sha,
        store_root=Path(args.store),
        repo_root=Path(args.repo_root) if args.repo_root else None,
    )
    print(json.dumps({
        "allowed": result.allowed,
        "reason_code": result.reason_code,
        "receipt_id": result.receipt.get("receipt_id") if result.receipt else None,
        "detail": result.detail,
    }, sort_keys=True))
    return 0 if result.allowed else 1


if __name__ == "__main__":
    sys.exit(main())
