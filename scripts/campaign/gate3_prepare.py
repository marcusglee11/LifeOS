"""Prepare approval-manifest hashes after Council ratification."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import yaml

from runtime.util.atomic_write import atomic_write_text
from runtime.util.canonical import sha256_file


def prepare_gate3(repo_root: Path, ruling_ref: str, dry_run: bool = False) -> dict:
    repo_root = Path(repo_root)
    manifest_path = repo_root / "config" / "openclaw" / "profile_approvals" / "coo_unsandboxed_prod_l3.yaml"
    profile_path = repo_root / "config" / "openclaw" / "instance_profiles" / "coo_unsandboxed_prod_l3.json"
    envelope_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    manifest["profile_sha256"] = sha256_file(profile_path)
    manifest["delegation_envelope_sha256"] = sha256_file(envelope_path)
    manifest.setdefault("approval", {})
    manifest["approval"]["council_ruling_ref"] = ruling_ref
    manifest["approval"]["approved_at"] = datetime.now(timezone.utc).isoformat()
    manifest["status"] = "approved"
    if not dry_run:
        atomic_write_text(manifest_path, yaml.safe_dump(manifest, sort_keys=False))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare gate 3 approval manifest.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ruling-ref", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    prepare_gate3(Path(args.repo_root), args.ruling_ref, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
