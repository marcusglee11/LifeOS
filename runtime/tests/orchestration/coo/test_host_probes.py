from __future__ import annotations

from pathlib import Path

import yaml

from scripts.campaign.gate4_host_probes import delegation_ceiling, protected_path_block, run_all_probes


def _write_envelope(tmp_path: Path, active_levels=None) -> None:
    (tmp_path / "config" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "governance" / "delegation_envelope.yaml").write_text(
        yaml.safe_dump(
            {
                "active_levels": active_levels or ["L0", "L3", "L4"],
                "autonomy": {"L4": {"actions": ["unknown_action_category"]}},
                "escalation": {"fail_closed": True},
                "protected_paths": ["docs/00_foundations/", "docs/01_governance/", "config/governance/protected_artefacts.json"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_probe_benign_read_pass(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("hello", encoding="utf-8")
    _write_envelope(tmp_path)
    assert run_all_probes(tmp_path)["probes"][0]["pass"] is True


def test_probe_protected_path_present(tmp_path: Path) -> None:
    _write_envelope(tmp_path)
    assert protected_path_block(tmp_path)["pass"] is True


def test_probe_delegation_ceiling_pass(tmp_path: Path) -> None:
    _write_envelope(tmp_path)
    assert delegation_ceiling(tmp_path)["pass"] is True


def test_probe_delegation_ceiling_fail(tmp_path: Path) -> None:
    _write_envelope(tmp_path, ["L0", "L1", "L3", "L4"])
    assert delegation_ceiling(tmp_path)["pass"] is False


def test_run_all_probes(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "CLAUDE.md").write_text("hello", encoding="utf-8")
    _write_envelope(tmp_path)
    monkeypatch.setattr(
        "scripts.campaign.gate4_host_probes.subprocess.run",
        lambda *args, **kwargs: type("P", (), {"returncode": 0})(),
    )
    assert run_all_probes(tmp_path)["all_pass"] is True
