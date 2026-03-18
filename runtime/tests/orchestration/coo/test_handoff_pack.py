from __future__ import annotations

import json
from pathlib import Path

from runtime.util.canonical import sha256_file
from scripts.campaign.gate6_handoff import build_handoff


def test_handoff_creates_all_files(tmp_path: Path) -> None:
    (tmp_path / "config" / "openclaw" / "instance_profiles").mkdir(parents=True)
    for name in ["coo.json", "coo_unsandboxed_prod_l3.json", "coo_shared_ingress_burnin.json"]:
        (tmp_path / "config" / "openclaw" / "instance_profiles" / name).write_text("{}", encoding="utf-8")
    build_handoff(tmp_path)
    handoff_dir = tmp_path / "artifacts" / "coo" / "promotion_campaign" / "handoff_pack"
    for name in [
        "profile_hashes.json",
        "ruling_ref.txt",
        "campaign_summary.json",
        "soak_results.json",
        "corrective_batches.txt",
        "uat_prompts.md",
        "rollback_procedure.md",
        "cutover_checklist.md",
        "residual_risks.md",
    ]:
        assert (handoff_dir / name).exists()


def test_profile_hashes_correct(tmp_path: Path) -> None:
    profile_dir = tmp_path / "config" / "openclaw" / "instance_profiles"
    profile_dir.mkdir(parents=True)
    for name in ["coo.json", "coo_unsandboxed_prod_l3.json", "coo_shared_ingress_burnin.json"]:
        (profile_dir / name).write_text(name, encoding="utf-8")
    build_handoff(tmp_path)
    hashes = json.loads(
        (tmp_path / "artifacts" / "coo" / "promotion_campaign" / "handoff_pack" / "profile_hashes.json").read_text(encoding="utf-8")
    )
    assert hashes["coo.json"] == sha256_file(profile_dir / "coo.json")
