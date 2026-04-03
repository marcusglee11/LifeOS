from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts import run_ops_certification


def _write_lanes(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "lanes.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _lane(
    *,
    status: str = "ratification_pending",
    approval_ref: str | None = None,
    approval_class: str = "explicit_human_approval",
    allowed_actions: list[str] | None = None,
    excluded_actions: list[str] | None = None,
) -> dict:
    return {
        "lane_id": "workspace_mutation_v1",
        "status": status,
        "approval_ref": approval_ref,
        "approval_class": approval_class,
        "allowed_actions": allowed_actions or ["workspace.file.write"],
        "excluded_actions": excluded_actions or [],
        "profiles": {
            "local": {"required_suites": []},
            "ci": {"required_suites": []},
            "live": {"required_suites": []},
        },
    }


def _payload(*lanes: dict) -> dict:
    return {"schema_version": "ops_lanes.v1", "lanes": list(lanes)}


def _write_ruling(tmp_path: Path, name: str = "Council_Ruling_Ops_Autonomy_v1.0.md") -> str:
    path = tmp_path / "docs" / "01_governance" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Council Ruling: Ops Autonomy\n\n**Decision**: RATIFIED\n",
        encoding="utf-8",
    )
    return str(path.relative_to(tmp_path)).replace("\\", "/")


def _write_non_ruling_doc(tmp_path: Path, name: str = "Ops_Autonomy_Draft.md") -> str:
    path = tmp_path / "docs" / "01_governance" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Draft\n\nNo decision marker here.\n", encoding="utf-8")
    return str(path.relative_to(tmp_path)).replace("\\", "/")


def _write_outside_governance_doc(tmp_path: Path, name: str = "Ops_Autonomy_Note.md") -> str:
    path = tmp_path / "docs" / "11_admin" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Note\n\nOutside governance.\n", encoding="utf-8")
    return str(path.relative_to(tmp_path)).replace("\\", "/")


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
    payload = _payload(
        _lane(
            allowed_actions=["workspace.file.write", "unknown.action"],
        )
    )

    leaks = run_ops_certification.validate_lane_manifest(payload, "local")

    assert any(leak["id"] == "lane_unknown_action" for leak in leaks)


def test_validate_lane_manifest_rejects_non_explicit_approval_and_overlap() -> None:
    payload = _payload(
        _lane(
            approval_class="auto",
            excluded_actions=["workspace.file.write"],
        )
    )

    leaks = run_ops_certification.validate_lane_manifest(payload, "local")

    assert any(leak["id"] == "lane_approval_class" for leak in leaks)
    assert any(leak["id"] == "lane_action_overlap" for leak in leaks)


def test_ratification_pending_blocks_ci() -> None:
    leaks = run_ops_certification.validate_lane_manifest(_payload(_lane()), "ci")
    leak = next(leak for leak in leaks if leak["id"] == "lane_ratification_pending")

    assert leak["blocker_kind"] == "ratification"


def test_ratification_pending_blocks_live() -> None:
    leaks = run_ops_certification.validate_lane_manifest(_payload(_lane()), "live")

    assert any(leak["id"] == "lane_ratification_pending" for leak in leaks)


def test_ratification_pending_local_is_allowed() -> None:
    leaks = run_ops_certification.validate_lane_manifest(_payload(_lane()), "local")

    assert not any(leak["id"] == "lane_ratification_pending" for leak in leaks)


def test_ratified_with_approval_ref_allows_ci(monkeypatch, tmp_path: Path) -> None:
    approval_ref = _write_ruling(tmp_path)
    monkeypatch.setattr(run_ops_certification, "REPO_ROOT", tmp_path)

    leaks = run_ops_certification.validate_lane_manifest(
        _payload(_lane(status="ratified", approval_ref=approval_ref)),
        "ci",
    )

    assert not any(leak["id"] in {"lane_ratification_pending", "lane_missing_approval_ref", "lane_invalid_approval_ref"} for leak in leaks)


def test_ratified_with_approval_ref_allows_live(monkeypatch, tmp_path: Path) -> None:
    approval_ref = _write_ruling(tmp_path)
    monkeypatch.setattr(run_ops_certification, "REPO_ROOT", tmp_path)

    leaks = run_ops_certification.validate_lane_manifest(
        _payload(_lane(status="ratified", approval_ref=approval_ref)),
        "live",
    )

    assert not any(leak["id"] in {"lane_ratification_pending", "lane_missing_approval_ref", "lane_invalid_approval_ref"} for leak in leaks)


def test_ratified_missing_approval_ref_blocks() -> None:
    leaks = run_ops_certification.validate_lane_manifest(
        _payload(_lane(status="ratified", approval_ref=None)),
        "ci",
    )
    leak = next(leak for leak in leaks if leak["id"] == "lane_missing_approval_ref")

    assert leak["blocker_kind"] == "policy"


def test_ratified_invalid_approval_ref_blocks(monkeypatch, tmp_path: Path) -> None:
    approval_ref = _write_non_ruling_doc(tmp_path)
    monkeypatch.setattr(run_ops_certification, "REPO_ROOT", tmp_path)

    leaks = run_ops_certification.validate_lane_manifest(
        _payload(_lane(status="ratified", approval_ref=approval_ref)),
        "ci",
    )

    assert any(leak["id"] == "lane_invalid_approval_ref" for leak in leaks)


def test_ratified_approval_ref_outside_governance_blocks(
    monkeypatch, tmp_path: Path
) -> None:
    approval_ref = _write_outside_governance_doc(tmp_path)
    monkeypatch.setattr(run_ops_certification, "REPO_ROOT", tmp_path)

    leaks = run_ops_certification.validate_lane_manifest(
        _payload(_lane(status="ratified", approval_ref=approval_ref)),
        "ci",
    )
    leak = next(leak for leak in leaks if leak["id"] == "lane_invalid_approval_ref")

    assert leak["blocker_kind"] == "policy"


def test_invalid_status_blocks() -> None:
    leaks = run_ops_certification.validate_lane_manifest(
        _payload(_lane(status="pending_review")),
        "ci",
    )

    assert any(leak["id"] == "lane_invalid_status" for leak in leaks)


def test_leak_records_carry_blocker_kind() -> None:
    leaks = run_ops_certification.validate_lane_manifest(
        _payload(
            _lane(
                status="ratified",
                approval_ref=None,
                approval_class="auto",
                allowed_actions=["workspace.file.write", "unknown.action"],
                excluded_actions=["workspace.file.write"],
            )
        ),
        "ci",
    )

    assert leaks
    assert all("blocker_kind" in leak for leak in leaks)


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
                    "approval_ref": None,
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
