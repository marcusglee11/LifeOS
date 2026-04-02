from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts import run_ops_certification


def _write_lanes(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "lanes.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_load_lanes_requires_mapping(tmp_path: Path) -> None:
    path = tmp_path / "lanes.yaml"
    path.write_text("- bad\n", encoding="utf-8")

    try:
        run_ops_certification.load_lanes(path)
    except ValueError as exc:
        assert "mapping" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_validate_lane_manifest_rejects_unknown_action() -> None:
    payload = {
        "schema_version": "ops_lanes.v1",
        "lanes": [
            {
                "lane_id": "bad_lane",
                "approval_class": "explicit_human_approval",
                "allowed_actions": ["workspace.file.write", "unknown.action"],
                "excluded_actions": [],
                "profiles": {"local": {"required_suites": []}},
            }
        ],
    }

    leaks = run_ops_certification.validate_lane_manifest(payload)

    assert any(leak["id"] == "lane_unknown_action" for leak in leaks)


def test_validate_lane_manifest_rejects_non_explicit_approval_and_overlap() -> None:
    payload = {
        "schema_version": "ops_lanes.v1",
        "lanes": [
            {
                "lane_id": "bad_lane",
                "approval_class": "auto",
                "allowed_actions": ["workspace.file.write"],
                "excluded_actions": ["workspace.file.write"],
                "profiles": {"local": {"required_suites": []}},
            }
        ],
    }

    leaks = run_ops_certification.validate_lane_manifest(payload)

    assert any(leak["id"] == "lane_approval_class" for leak in leaks)
    assert any(leak["id"] == "lane_action_overlap" for leak in leaks)


def test_determine_state_transitions() -> None:
    assert run_ops_certification.determine_state("local", blocking=True) == "red"
    assert run_ops_certification.determine_state("local", blocking=False) == "prod_local"
    assert run_ops_certification.determine_state("ci", blocking=False) == "prod_ci"
    assert (
        run_ops_certification.determine_state(
            "live", blocking=False, previous_state="prod_ci"
        )
        == "prod_ci"
    )


def test_certify_writes_ops_readiness_artifact(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_lanes(
        tmp_path,
        {
            "schema_version": "ops_lanes.v1",
            "lanes": [
                {
                    "lane_id": "workspace_mutation_v1",
                    "status": "ratification_pending",
                    "approval_class": "explicit_human_approval",
                    "allowed_actions": ["workspace.file.write"],
                    "excluded_actions": [],
                    "profiles": {"local": {"required_suites": []}},
                }
            ],
        },
    )
    output_path = tmp_path / "ops_readiness.json"
    monkeypatch.setattr(run_ops_certification, "CONFIG_PATH", config_path)
    monkeypatch.setattr(run_ops_certification, "OUTPUT_PATH", output_path)
    monkeypatch.setattr(run_ops_certification, "current_worktree_clean", lambda: True)

    payload = run_ops_certification.certify("local")

    assert payload["state"] == "prod_local"
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == "ops_readiness.v1"
    assert saved["profile"] == "local"
