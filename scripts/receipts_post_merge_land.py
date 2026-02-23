#!/usr/bin/env python3
"""
Phase C post-merge land receipt gate.

Usage:
    python scripts/receipts_post_merge_land.py \
        --landed-sha <sha> --land-target <ref> --merge-method <method> \
        --acceptance-receipt-id <ulid> --store <path> \
        --agent-id <id> --run-id <id>

Exit codes: 0 = emitted, 1 = error/not emitted
Output: JSON to stdout {"emitted", "receipt_id", "tree_match", "error_code", "detail"}

Env:
    LIFEOS_MOCK_TREE_OID: Override tree OID resolution (testing only).
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from runtime.receipts.post_merge import run_post_merge_land_gate
from runtime.receipts import plan_core as _pc


def main() -> int:
    p = argparse.ArgumentParser(description="Post-merge land receipt gate")
    p.add_argument("--landed-sha", required=True)
    p.add_argument("--land-target", required=True)
    p.add_argument("--merge-method", required=True)
    p.add_argument("--acceptance-receipt-id", required=True)
    p.add_argument("--store", required=True)
    p.add_argument("--agent-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--repo-root", default=None)
    args = p.parse_args()

    mock_oid = os.environ.get("LIFEOS_MOCK_TREE_OID")
    if mock_oid:
        _pc.resolve_tree_oid = lambda sha, **kw: mock_oid  # type: ignore[assignment]

    result = run_post_merge_land_gate(
        landed_sha=args.landed_sha,
        land_target=args.land_target,
        merge_method=args.merge_method,
        acceptance_receipt_id=args.acceptance_receipt_id,
        store_root=Path(args.store),
        agent_id=args.agent_id,
        run_id=args.run_id,
        repo_root=Path(args.repo_root) if args.repo_root else None,
    )
    tree_match = (
        result.land_receipt.get("tree_equivalence", {}).get("match")
        if result.land_receipt else None
    )
    print(json.dumps({
        "emitted": result.emitted,
        "receipt_id": result.land_receipt.get("receipt_id") if result.land_receipt else None,
        "tree_match": tree_match,
        "error_code": result.error_code,
        "detail": result.detail,
    }, sort_keys=True))
    return 0 if result.emitted else 1


if __name__ == "__main__":
    sys.exit(main())
