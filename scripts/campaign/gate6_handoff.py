"""Assemble the gate 6 UAT handoff pack."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from runtime.util.atomic_write import atomic_write_text
from runtime.util.canonical import sha256_file


def build_handoff(repo_root: Path) -> dict[str, Any]:
    repo_root = Path(repo_root)
    handoff_dir = repo_root / "artifacts" / "coo" / "promotion_campaign" / "handoff_pack"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = repo_root / "config" / "openclaw" / "instance_profiles"

    profile_hashes = {
        "coo.json": sha256_file(profile_dir / "coo.json"),
        "coo_unsandboxed_prod_l3.json": sha256_file(profile_dir / "coo_unsandboxed_prod_l3.json"),
        "coo_shared_ingress_burnin.json": sha256_file(profile_dir / "coo_shared_ingress_burnin.json"),
    }
    atomic_write_text(handoff_dir / "profile_hashes.json", json.dumps(profile_hashes, indent=2, sort_keys=True) + "\n")

    manifest_path = repo_root / "config" / "openclaw" / "profile_approvals" / "coo_unsandboxed_prod_l3.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    ruling_ref = str(((manifest.get("approval") or {}).get("council_ruling_ref")) or "").strip()
    if not ruling_ref:
        raise RuntimeError("gate6_handoff: approval manifest is not sealed; ruling_ref is missing")
    atomic_write_text(handoff_dir / "ruling_ref.txt", ruling_ref + "\n")

    summary = {"gates": ["gate1", "gate4", "gate5"], "status": "prepared"}
    atomic_write_text(handoff_dir / "campaign_summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")

    soak = {"status": "pending_gate5_execution"}
    atomic_write_text(handoff_dir / "soak_results.json", json.dumps(soak, indent=2, sort_keys=True) + "\n")

    atomic_write_text(handoff_dir / "corrective_batches.txt", "No corrective batches recorded yet.\n")
    atomic_write_text(
        handoff_dir / "uat_prompts.md",
        "\n".join(
            [
                "1. `lifeos coo propose --yaml`",
                "2. `lifeos coo direct \"modify docs/00_foundations/LifeOS_Constitution_v2.0.md\"`",
                "3. `lifeos coo direct \"do something useful\"`",
                "4. `bash runtime/tools/openclaw_verify_surface.sh`",
                "5. `python3 scripts/campaign/coo_rollback.py --dry-run --json`",
            ]
        )
        + "\n",
    )
    atomic_write_text(
        handoff_dir / "rollback_procedure.md",
        "1. Copy `coo_shared_ingress_burnin.json` over `coo.json`.\n2. Rerun verify surface.\n",
    )
    atomic_write_text(
        handoff_dir / "cutover_checklist.md",
        "\n".join(
            [
                "- All 6 gates PASS",
                "- Council ruling verdict PASS or PASS_WITH_CONDITIONS",
                "- Soak: 16 clean runs, 4 sessions, 2 calendar days",
                "- CEO completes 5/5 UAT prompts",
                "- Profile SHA matches manifest",
                "- Delegation ceiling confirmed [L0, L3, L4]",
                "- Rollback verified (dry-run)",
            ]
        )
        + "\n",
    )
    atomic_write_text(handoff_dir / "residual_risks.md", "- Step 5 governance ruling remains pending.\n")
    return {"handoff_dir": str(handoff_dir), "profile_hashes": profile_hashes}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the gate 6 handoff pack.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = build_handoff(Path(args.repo_root))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
