from __future__ import annotations

import json
from pathlib import Path

import pytest
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
    (tmp_path / "docs" / "01_governance").mkdir(parents=True)
    envelope_path = tmp_path / "config" / "governance" / "delegation_envelope.yaml"
    envelope_path.write_text(yaml.safe_dump(_envelope(), sort_keys=False), encoding="utf-8")
    profile_path = (
        tmp_path / "config" / "openclaw" / "instance_profiles" / "coo_unsandboxed_prod_l3.json"
    )
    profile_path.write_text("{}", encoding="utf-8")
    ruling_path = tmp_path / "docs" / "01_governance" / "ruling.md"
    ruling_path.write_text("**Decision**: RATIFIED\n", encoding="utf-8")
    from runtime.util.canonical import sha256_file

    manifest = {
        "status": "approved",
        "profile_sha256": sha256_file(profile_path),
        "autonomy_ceiling": {"active_levels": ["L0", "L3", "L4"], "trust_tier": "burn-in"},
        "approval": {"council_ruling_ref": "docs/01_governance/ruling.md"},
    }
    (
        tmp_path / "config" / "openclaw" / "profile_approvals" / "coo_unsandboxed_prod_l3.yaml"
    ).write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    result = full_promotion_guard(tmp_path)
    assert result["pass"] is True


def test_verify_delegation_ceiling_order_independent(tmp_path: Path) -> None:
    """sorted() normalization: [L3, L0, L4] should still pass."""
    assert (
        verify_delegation_ceiling({"active_levels": ["L3", "L0", "L4"], "trust_tier": "burn-in"})
        == []
    )


def test_verify_approval_manifest_ruling_ref_missing_file(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    from runtime.util.canonical import sha256_file

    manifest = {
        "status": "approved",
        "profile_sha256": sha256_file(profile),
        "autonomy_ceiling": {"active_levels": ["L0", "L3", "L4"], "trust_tier": "burn-in"},
        "approval": {"council_ruling_ref": "docs/01_governance/nonexistent.md"},
    }
    violations = verify_approval_manifest(manifest, profile, _envelope(), repo_root=tmp_path)
    assert any("ruling_ref_missing" in v for v in violations)


def test_verify_approval_manifest_ruling_ref_outside_governance(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    from runtime.util.canonical import sha256_file

    manifest = {
        "status": "approved",
        "profile_sha256": sha256_file(profile),
        "autonomy_ceiling": {"active_levels": ["L0", "L3", "L4"], "trust_tier": "burn-in"},
        "approval": {"council_ruling_ref": "docs/00_foundations/some.md"},
    }
    violations = verify_approval_manifest(manifest, profile, _envelope(), repo_root=tmp_path)
    assert any("outside_governance" in v for v in violations)


def test_verify_surface_profile_name_consistency() -> None:
    """Regression: empty PROFILE_NAME for sandboxed posture is vacuously OK;
    for unsandboxed posture it must block (fail-closed, no governance bypass).
    Invalid-format PROFILE_NAME must also block.
    """
    script = (
        Path(__file__).resolve().parents[4] / "runtime" / "tools" / "openclaw_verify_surface.sh"
    )
    text = script.read_text(encoding="utf-8")
    # Must extract target_posture alongside profile_name
    assert "PROFILE_TARGET_POSTURE" in text, "missing posture-aware PROFILE_TARGET_POSTURE variable"
    # Unsandboxed posture with empty profile_name must add a blocking reason
    assert "approval_manifest_missing_profile_name_for_unsandboxed_posture" in text, (
        "missing blocking reason for unsandboxed+empty profile_name"
    )
    # Invalid format must add a blocking reason (no silent skip)
    assert "approval_manifest_profile_name_invalid_format" in text, (
        "missing blocking reason for invalid PROFILE_NAME format"
    )
    # CHECK_APPROVAL_MANIFEST must be false for unsandboxed without profile_name
    assert '"unsandboxed"' in text, (
        "missing unsandboxed posture guard in CHECK_APPROVAL_MANIFEST block"
    )


def test_gate3_ruling_requires_structured_marker(tmp_path: Path) -> None:
    """Regression: gate3_prepare must require **Decision**: RATIFIED/APPROVED, not bare substring.

    Old code accepted any file containing 'RATIFIED' anywhere — a document referencing
    a prior RATIFIED ruling would falsely pass. New code requires a structural marker.
    """
    from scripts.campaign.gate3_prepare import _validate_ruling_ref

    gov_dir = tmp_path / "docs" / "01_governance"
    gov_dir.mkdir(parents=True)

    # Bare substring alone must fail
    bad = gov_dir / "weak_ruling.md"
    bad.write_text("This ruling is NOT RATIFIED, see previous APPROVED decision.", encoding="utf-8")
    with pytest.raises(ValueError, match="structured approval marker"):
        _validate_ruling_ref(tmp_path, "docs/01_governance/weak_ruling.md")

    # Structural marker must pass
    good = gov_dir / "good_ruling.md"
    good.write_text("**Decision**: RATIFIED\n", encoding="utf-8")
    _validate_ruling_ref(tmp_path, "docs/01_governance/good_ruling.md")  # no exception


def test_profiles_on_disk_valid_json() -> None:
    root = Path(__file__).resolve().parents[4]
    for name in [
        "coo.json",
        "coo_shared_ingress_burnin.json",
        "coo_unsandboxed_prod_l3.json",
    ]:
        path = root / "config" / "openclaw" / "instance_profiles" / name
        json.loads(path.read_text(encoding="utf-8"))
