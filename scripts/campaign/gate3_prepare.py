"""Prepare approval-manifest hashes after Council ratification."""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from runtime.util.atomic_write import atomic_write_text
from runtime.util.canonical import sha256_file


def _validate_ruling_ref(repo_root: Path, ruling_ref: str) -> None:
    """Fail closed: ruling must exist under docs/01_governance/ before sealing."""
    ruling_path = (repo_root / ruling_ref).resolve()
    gov_root = (repo_root / "docs" / "01_governance").resolve()
    if not str(ruling_path).startswith(str(gov_root) + "/"):
        raise ValueError(
            f"gate3_prepare: ruling_ref {ruling_ref!r} is outside docs/01_governance/"
        )
    if not ruling_path.is_file():
        raise FileNotFoundError(
            f"gate3_prepare: ruling_ref {ruling_ref!r} does not exist"
        )
    text = ruling_path.read_text(encoding="utf-8")
    # Require a structural approval marker on its own line — bare substring rejected (Governance R2).
    if not re.search(r"^\*\*Decision\*\*:\s*(RATIFIED|APPROVED)\b", text, re.MULTILINE):
        raise ValueError(
            f"gate3_prepare: ruling_ref {ruling_ref!r} does not contain a structured"
            " approval marker (**Decision**: RATIFIED or **Decision**: APPROVED)"
        )


def prepare_gate3(repo_root: Path, ruling_ref: str, dry_run: bool = False) -> dict:
    repo_root = Path(repo_root)
    manifest_path = repo_root / "config" / "openclaw" / "profile_approvals" / "coo_unsandboxed_prod_l3.yaml"
    profile_path = repo_root / "config" / "openclaw" / "instance_profiles" / "coo_unsandboxed_prod_l3.json"
    envelope_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if manifest.get("status") == "approved":
        raise RuntimeError(
            "gate3_prepare: manifest is already sealed (status=approved); re-sealing is not allowed"
        )
    _validate_ruling_ref(repo_root, ruling_ref)
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
