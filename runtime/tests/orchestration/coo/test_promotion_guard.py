from __future__ import annotations

import json
from pathlib import Path

import yaml

from runtime.orchestration.coo.promotion_guard import (
    full_promotion_guard,
    verify_approval_manifest,
    verify_delegation_ceiling,
)


def _envelope(levels=None, tier="burn-in"):
    return {"active_levels": levels or ["L0", "L3", "L4"], "trust_tier": tier}


def test_verify_delegation_ceiling_pass() -> None:
    assert verify_delegation_ceiling(_envelope()) == []


def test_verify_delegation_ceiling_wrong_levels() -> None:
    violations = verify_delegation_ceiling(_envelope(["L0", "L1", "L3", "L4"]))
    assert violations


def test_verify_delegation_ceiling_wrong_tier() -> None:
    violations = verify_delegation_ceiling(_envelope(tier="established"))
    assert violations


def test_verify_approval_manifest_pass(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    from runtime.util.canonical import sha256_file

    manifest = {
        "status": "approved",
        "profile_sha256": sha256_file(profile),
        "autonomy_ceiling": {"active_levels": ["L0", "L3", "L4"], "trust_tier": "burn-in"},
        "approval": {"council_ruling_ref": "docs/01_governance/ruling.md"},
    }
    assert verify_approval_manifest(manifest, profile, _envelope()) == []


def test_verify_approval_manifest_pending_fails(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    manifest = {"status": "pending", "profile_sha256": "x", "autonomy_ceiling": {}, "approval": {}}
    assert verify_approval_manifest(manifest, profile, _envelope())


def test_verify_approval_manifest_sha_mismatch(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    manifest = {
        "status": "approved",
        "profile_sha256": "wrong",
        "autonomy_ceiling": {"active_levels": ["L0", "L3", "L4"], "trust_tier": "burn-in"},
        "approval": {"council_ruling_ref": "x"},
    }
    assert verify_approval_manifest(manifest, profile, _envelope())


def test_verify_approval_manifest_missing_ruling_ref(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    from runtime.util.canonical import sha256_file

    manifest = {
        "status": "approved",
        "profile_sha256": sha256_file(profile),
        "autonomy_ceiling": {"active_levels": ["L0", "L3", "L4"], "trust_tier": "burn-in"},
        "approval": {"council_ruling_ref": ""},
    }
    assert verify_approval_manifest(manifest, profile, _envelope())


def test_full_promotion_guard_all_missing(tmp_path: Path) -> None:
    result = full_promotion_guard(tmp_path)
    assert result["pass"] is False
    assert result["violations"]


def test_full_promotion_guard_pass(tmp_path: Path) -> None:
    (tmp_path / "config" / "governance").mkdir(parents=True)
    (tmp_path / "config" / "openclaw" / "instance_profiles").mkdir(parents=True)
    (tmp_path / "config" / "openclaw" / "profile_approvals").mkdir(parents=True)
    envelope_path = tmp_path / "config" / "governance" / "delegation_envelope.yaml"
    envelope_path.write_text(yaml.safe_dump(_envelope(), sort_keys=False), encoding="utf-8")
    profile_path = tmp_path / "config" / "openclaw" / "instance_profiles" / "coo_unsandboxed_prod_l3.json"
    profile_path.write_text("{}", encoding="utf-8")
    from runtime.util.canonical import sha256_file

    manifest = {
        "status": "approved",
        "profile_sha256": sha256_file(profile_path),
        "autonomy_ceiling": {"active_levels": ["L0", "L3", "L4"], "trust_tier": "burn-in"},
        "approval": {"council_ruling_ref": "docs/01_governance/ruling.md"},
    }
    (tmp_path / "config" / "openclaw" / "profile_approvals" / "coo_unsandboxed_prod_l3.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    result = full_promotion_guard(tmp_path)
    assert result["pass"] is True


def test_profiles_on_disk_valid_json() -> None:
    root = Path(__file__).resolve().parents[4]
    for name in [
        "coo.json",
        "coo_shared_ingress_burnin.json",
        "coo_unsandboxed_prod_l3.json",
    ]:
        path = root / "config" / "openclaw" / "instance_profiles" / name
        json.loads(path.read_text(encoding="utf-8"))
