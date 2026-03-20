"""Gate 4 candidate runner for COO promotion."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from runtime.orchestration.coo.promotion_guard import full_promotion_guard
from runtime.util.atomic_write import atomic_write_text
from scripts.campaign.coo_promotion_controller import run_campaign
from scripts.campaign.coo_rollback import run_rollback
from scripts.campaign.gate4_host_probes import run_all_probes


def run_gate4(repo_root: Path) -> dict[str, Any]:
    repo_root = Path(repo_root)
    profile_dir = repo_root / "config" / "openclaw" / "instance_profiles"
    active_profile = profile_dir / "coo.json"
    backup_profile = profile_dir / "coo.json.gate4_backup"
    candidate = profile_dir / "coo_unsandboxed_prod_l3.json"
    result_path = repo_root / "artifacts" / "coo" / "promotion_campaign" / "gate4_result.json"


    # Run promotion guard BEFORE activating the candidate profile (Gov F1: pre-activation guard).
    guard = full_promotion_guard(repo_root)
    if not guard["pass"]:
        return {
            "pass": False,
            "guard": guard,
            "abort_reason": "promotion_guard_failed_before_activation",
        }

    shutil.copyfile(active_profile, backup_profile)
    verify_proc = None
    probes = None
    campaign = None
    passed = False
    rollback = None
    try:
        # Profile swap: wrapped in try/finally so exceptions always restore the safe profile (Gov F2).
        shutil.copyfile(candidate, active_profile)
        verify_proc = subprocess.run(
            ["bash", "runtime/tools/openclaw_verify_surface.sh"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        probes = run_all_probes(repo_root)
        campaign = run_campaign(
            repo_root / "artifacts" / "coo" / "promotion_campaign" / "manifests" / "gate4_candidate.yaml",
            repo_root,
            "gate4",
        )

        passed = verify_proc.returncode == 0 and probes["all_pass"] and guard["pass"]
    finally:
        if not passed:
            shutil.copyfile(backup_profile, active_profile)
            rollback = run_rollback(repo_root, dry_run=False)

    payload: dict[str, Any] = {
        "pass": passed,
        "verify_exit_code": verify_proc.returncode if verify_proc is not None else None,
        "probes": probes,
        "campaign": campaign,
        "guard": guard,
    }
    if rollback is not None:
        payload["rollback"] = rollback
    result_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(result_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run gate 4 candidate checks.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_gate4(Path(args.repo_root))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
