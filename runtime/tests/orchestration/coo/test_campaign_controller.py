from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from scripts.campaign.coo_promotion_controller import run_campaign, run_scenario
from scripts.campaign.coo_rollback import run_rollback
from scripts.campaign.coo_stability_checker import check_stability


def test_run_scenario_mock(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "config" / "tasks").mkdir(parents=True)
    (tmp_path / "config" / "tasks" / "backlog.yaml").write_text(
        yaml.safe_dump({"schema_version": "backlog.v1", "tasks": []}, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "scripts.campaign.coo_promotion_controller.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="schema_version: nothing_to_propose.v1\nreason: idle\nrecommended_follow_up: wait\n",  # noqa: E501
            returncode=0,
        ),
    )
    row = run_scenario(
        {
            "scenario_id": "s1",
            "mode": "propose",
            "expected_packet_family": "nothing_to_propose",
        },
        tmp_path,
        tmp_path / "captures",
        "gate1",
    )
    assert row["scenario_id"] == "s1"
    assert row["actual_packet_family"] == "nothing_to_propose"


def test_stability_pass_5_identical(tmp_path: Path) -> None:
    log = tmp_path / "campaign.jsonl"
    rows = [
        {"scenario_id": "s1", "actual_packet_family": "task_proposal", "side_effect_class": "none"}
        for _ in range(5)
    ]
    log.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    assert check_stability(log)["all_stable"] is True


def test_stability_fail_family_drift(tmp_path: Path) -> None:
    log = tmp_path / "campaign.jsonl"
    rows = [
        {"scenario_id": "s1", "actual_packet_family": fam, "side_effect_class": "none"}
        for fam in [
            "task_proposal",
            "task_proposal",
            "nothing_to_propose",
            "task_proposal",
            "task_proposal",
        ]
    ]
    log.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    assert check_stability(log)["all_stable"] is False


def test_stability_insufficient_runs(tmp_path: Path) -> None:
    log = tmp_path / "campaign.jsonl"
    rows = [
        {"scenario_id": "s1", "actual_packet_family": "task_proposal", "side_effect_class": "none"}
        for _ in range(4)
    ]
    log.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    assert check_stability(log)["all_stable"] is False


def test_run_campaign_rejects_invalid_gate(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("scenarios: []\n", encoding="utf-8")
    import pytest

    with pytest.raises(ValueError, match="gate must match"):
        run_campaign(manifest, tmp_path, "../evil")


def test_run_campaign_rejects_path_traversal_gate(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("scenarios: []\n", encoding="utf-8")
    import pytest

    with pytest.raises(ValueError, match="gate must match"):
        run_campaign(manifest, tmp_path, "gate/../../etc/passwd")


def test_rollback_restores_profile(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "config" / "openclaw" / "instance_profiles").mkdir(parents=True)
    (tmp_path / "config" / "openclaw" / "profile_approvals").mkdir(parents=True)
    (tmp_path / "config" / "governance").mkdir(parents=True)
    (
        tmp_path / "config" / "openclaw" / "instance_profiles" / "coo_shared_ingress_burnin.json"
    ).write_text('{"name":"burnin"}', encoding="utf-8")
    (tmp_path / "config" / "openclaw" / "instance_profiles" / "coo.json").write_text(
        '{"name":"prod"}', encoding="utf-8"
    )
    (
        tmp_path / "config" / "openclaw" / "profile_approvals" / "coo_unsandboxed_prod_l3.yaml"
    ).write_text("status: approved\n", encoding="utf-8")
    (tmp_path / "config" / "governance" / "delegation_envelope.yaml").write_text(
        yaml.safe_dump(
            {"active_levels": ["L0", "L3", "L4"], "trust_tier": "burn-in"}, sort_keys=False
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "scripts.campaign.coo_rollback.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    run_rollback(tmp_path, dry_run=False)
    assert (tmp_path / "config" / "openclaw" / "instance_profiles" / "coo.json").read_text(
        encoding="utf-8"
    ) == '{"name":"burnin"}'
