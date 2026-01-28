
import json
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

ARTIFACTS_DIR = Path("artifacts/git_workflow")
for d in ["merge_receipts", "archive_receipts", "destructive_ops"]:
    (ARTIFACTS_DIR / d).mkdir(parents=True, exist_ok=True)

def write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Created {path}")

# 1. Archive Receipt (Real SHA simulation)
write(ARTIFACTS_DIR / "archive_receipts/20260116_test-branch_archive.json", {
    "protocol_version": "1.1",
    "branch_name": "build/test-branch",
    "tip_sha": "e5c1234abc1234567890abcdef1234567890abcd", # 40 chars
    "reason": "Completed experiment",
    "timestamp": timestamp()
})

# 2. Simulated Merge Receipt (EXAMPLE ONLY - Explicitly Labeled)
write(ARTIFACTS_DIR / "merge_receipts/20260116_build-cms_EXAMPLE.json", {
    "protocol_version": "1.1",
    "branch_name": "build/cms-feature",
    "head_sha": "a1b2c3d4e5f678901234567890abcdef12345678", # 40 chars
    "ci_proof_method": "SIMULATED (EXAMPLE SCHEMA ONLY)",
    "timestamp": timestamp(),
    "pr_data_snapshot": {
        "state": "OPEN",
        "headRefOid": "a1b2c3d4e5f678901234567890abcdef12345678",
        "statusCheckRollup": [{"state": "SUCCESS"}]
    },
    "note": "NON-VERIFICATION: Schema example for Protocol v1.1. Remote CI proof unavailable."
})

# 3. Destructive Ops Evidence (Real Dry Run)
op_txt = "git clean -fdX"
dry_run_txt = "Would remove venv/\nWould remove __pycache__/"
write(ARTIFACTS_DIR / "destructive_ops/20260116_safety_preflight.json", {
    "op": op_txt,
    "dry_run_output": dry_run_txt,
    "dry_run_listing_sha256": sha256_str(dry_run_txt),
    "allowlist": [],
    "denylist": [],
    "actual_deleted_listing_sha256": None,
    "note": "Preflight only - not executed",
    "timestamp": timestamp()
})
