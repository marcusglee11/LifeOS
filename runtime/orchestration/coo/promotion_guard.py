"""Approval and delegation checks for COO production-profile promotion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from runtime.util.canonical import sha256_file


def verify_delegation_ceiling(
    envelope: dict[str, Any],
    expected_levels: list[str] | None = None,
    expected_trust_tier: str = "burn-in",
) -> list[str]:
    expected_levels = expected_levels or ["L0", "L3", "L4"]
    violations: list[str] = []

    active_levels = envelope.get("active_levels")
    if sorted(active_levels or []) != sorted(expected_levels):
        violations.append(
            f"delegation_active_levels_mismatch: expected {expected_levels}, got {active_levels!r}"
        )

    trust_tier = str(envelope.get("trust_tier", "")).strip()
    if trust_tier != expected_trust_tier:
        violations.append(
            f"delegation_trust_tier_mismatch: expected {expected_trust_tier!r}, got {trust_tier!r}"
        )

    return violations


def verify_approval_manifest(
    manifest: dict[str, Any],
    profile_path: Path,
    envelope: dict[str, Any],
    repo_root: Path | None = None,
) -> list[str]:
    violations: list[str] = []

    status = str(manifest.get("status", "")).strip()
    if status not in {"approved", "active"}:
        violations.append(f"approval_manifest_status_invalid: {status!r}")

    try:
        actual_profile_sha = sha256_file(profile_path)
    except FileNotFoundError:
        violations.append(f"profile_missing: {profile_path}")
        actual_profile_sha = None

    manifest_profile_sha = str(manifest.get("profile_sha256", "")).strip()
    if actual_profile_sha and manifest_profile_sha != actual_profile_sha:
        violations.append("approval_manifest_profile_sha_mismatch")

    ruling_ref = str(
        ((manifest.get("approval") or {}).get("council_ruling_ref")) or ""
    ).strip()
    if not ruling_ref:
        violations.append("approval_manifest_missing_ruling_ref")
    elif repo_root is not None:
        ruling_path = (Path(repo_root) / ruling_ref).resolve()
        gov_root = (Path(repo_root) / "docs" / "01_governance").resolve()
        if not str(ruling_path).startswith(str(gov_root) + "/"):
            violations.append(
                f"approval_manifest_ruling_ref_outside_governance: {ruling_ref!r}"
            )
        elif not ruling_path.is_file():
            violations.append(
                f"approval_manifest_ruling_ref_missing: {ruling_ref!r}"
            )

    approval_levels = ((manifest.get("autonomy_ceiling") or {}).get("active_levels")) or []
    approval_tier = str(
        ((manifest.get("autonomy_ceiling") or {}).get("trust_tier")) or ""
    ).strip()
    violations.extend(
        verify_delegation_ceiling(
            {
                "active_levels": approval_levels,
                "trust_tier": approval_tier,
            },
            expected_levels=list(envelope.get("active_levels") or []),
            expected_trust_tier=str(envelope.get("trust_tier") or ""),
        )
    )

    return violations


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def full_promotion_guard(
    repo_root: Path,
    profile_name: str = "coo_unsandboxed_prod_l3",
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    violations: list[str] = []

    envelope_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    manifest_path = repo_root / "config" / "openclaw" / "profile_approvals" / f"{profile_name}.yaml"
    profile_path = repo_root / "config" / "openclaw" / "instance_profiles" / f"{profile_name}.json"

    envelope: dict[str, Any] = {}
    manifest: dict[str, Any] = {}

    if not envelope_path.exists():
        violations.append(f"delegation_envelope_missing: {envelope_path}")
    else:
        envelope = _load_yaml(envelope_path)
        violations.extend(verify_delegation_ceiling(envelope))

    if not manifest_path.exists():
        violations.append(f"approval_manifest_missing: {manifest_path}")
    else:
        manifest = _load_yaml(manifest_path)

    if not profile_path.exists():
        violations.append(f"profile_missing: {profile_path}")

    if envelope and manifest and profile_path.exists():
        violations.extend(verify_approval_manifest(manifest, profile_path, envelope, repo_root=repo_root))
        manifest_envelope_sha = str(manifest.get("delegation_envelope_sha256", "")).strip()
        if manifest_envelope_sha:
            actual_envelope_sha = sha256_file(envelope_path)
            if manifest_envelope_sha != actual_envelope_sha:
                violations.append("approval_manifest_delegation_envelope_sha_mismatch")

    return {"pass": not violations, "violations": violations}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate COO promotion approval state.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile-name", default="coo_unsandboxed_prod_l3")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = full_promotion_guard(Path(args.repo_root), profile_name=args.profile_name)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for violation in result["violations"]:
            print(f"violation={violation}")
        print(f"pass={'true' if result['pass'] else 'false'}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
