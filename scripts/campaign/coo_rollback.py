"""Rollback helper for COO promotion experiments."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.coo.promotion_guard import verify_delegation_ceiling
from runtime.util.atomic_write import atomic_write_text


def run_rollback(repo_root: Path, dry_run: bool = False) -> dict[str, Any]:
    repo_root = Path(repo_root)
    profile_dir = repo_root / "config" / "openclaw" / "instance_profiles"
    source = profile_dir / "coo_shared_ingress_burnin.json"
    target = profile_dir / "coo.json"
    manifest_path = repo_root / "config" / "openclaw" / "profile_approvals" / "coo_unsandboxed_prod_l3.yaml"
    envelope_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"

    if not dry_run:
        atomic_write_text(target, source.read_text(encoding="utf-8"))

    verify_proc = subprocess.run(
        ["bash", "runtime/tools/openclaw_verify_surface.sh"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    envelope = yaml.safe_load(envelope_path.read_text(encoding="utf-8")) or {}
    violations = verify_delegation_ceiling(envelope)

    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        manifest["status"] = "rolled_back"
        if not dry_run:
            atomic_write_text(manifest_path, yaml.safe_dump(manifest, sort_keys=False))

    return {
        "verify_exit_code": verify_proc.returncode,
        "delegation_violations": violations,
        "next_step": "Open corrective worktree",
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback COO promotion profile.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run_rollback(Path(args.repo_root), dry_run=args.dry_run)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result)
    return 0 if (not result["delegation_violations"] and result["verify_exit_code"] == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
