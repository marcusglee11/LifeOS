import pytest
import yaml
from pathlib import Path

from runtime.orchestration.ops.registry import (
    OperationValidationError,
    get_action_spec,
    normalize_artifact_path,
)


def _load_lanes(repo_root: Path) -> list[dict]:
    raw = (repo_root / "config" / "ops" / "lanes.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(raw)["lanes"]


def test_repo_artifact_lane_exists_in_config():
    from runtime.config.repo_root import detect_repo_root
    lanes = _load_lanes(detect_repo_root())
    assert "repo_artifact_v1" in [l["lane_id"] for l in lanes]


def test_repo_artifact_lane_is_ratification_pending():
    from runtime.config.repo_root import detect_repo_root
    lanes = _load_lanes(detect_repo_root())
    lane = next(l for l in lanes if l["lane_id"] == "repo_artifact_v1")
    assert lane["status"] == "ratification_pending"
    assert lane["approval_ref"] == ""
    assert lane["approval_class"] == "explicit_human_approval"


def test_repo_artifact_lane_has_correct_actions():
    from runtime.config.repo_root import detect_repo_root
    lanes = _load_lanes(detect_repo_root())
    lane = next(l for l in lanes if l["lane_id"] == "repo_artifact_v1")
    assert set(lane["allowed_actions"]) == {
        "artifact.file.write",
        "artifact.dir.ensure",
        "artifact.file.archive",
    }


# --- ActionSpec tests ---

def test_artifact_action_specs_are_mutation_and_require_approval():
    for action_id in ("artifact.file.write", "artifact.dir.ensure", "artifact.file.archive"):
        spec = get_action_spec(action_id)
        assert spec.operation_kind == "mutation", action_id
        assert spec.requires_approval is True, action_id


# --- normalize_artifact_path: path resolution ---

def test_normalize_artifact_path_relative_in_plans(tmp_path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    result = normalize_artifact_path("plans/my-plan.md", artifacts_root=artifacts_root)
    assert result == (artifacts_root / "plans" / "my-plan.md").resolve()


def test_normalize_artifact_path_alias_in_review_packets(tmp_path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    result = normalize_artifact_path("/artifacts/review_packets/rp.md", artifacts_root=artifacts_root)
    assert result == (artifacts_root / "review_packets" / "rp.md").resolve()


def test_normalize_artifact_path_traversal_escape_rejected(tmp_path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    with pytest.raises(OperationValidationError, match="escapes"):
        normalize_artifact_path("../outside.txt", artifacts_root=artifacts_root)


def test_normalize_artifact_path_non_artifacts_absolute_rejected(tmp_path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    with pytest.raises(OperationValidationError):
        normalize_artifact_path("/etc/passwd", artifacts_root=artifacts_root)


# --- Subpath allowlist tests ---

def test_normalize_artifact_path_rejects_coo_operations_subpath(tmp_path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    with pytest.raises(OperationValidationError, match="not in the allowed"):
        normalize_artifact_path("coo/operations/proposals/OP-abc.yaml", artifacts_root=artifacts_root)


def test_normalize_artifact_path_rejects_status_subpath(tmp_path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    with pytest.raises(OperationValidationError, match="not in the allowed"):
        normalize_artifact_path("status/ops_readiness.json", artifacts_root=artifacts_root)


def test_normalize_artifact_path_rejects_packets_subpath(tmp_path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    with pytest.raises(OperationValidationError, match="not in the allowed"):
        normalize_artifact_path("packets/status/report.zip", artifacts_root=artifacts_root)


def test_normalize_artifact_path_allows_99_archive(tmp_path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    result = normalize_artifact_path("99_archive/old-plan.md", artifacts_root=artifacts_root)
    assert result == (artifacts_root / "99_archive" / "old-plan.md").resolve()


from runtime.orchestration.ops.executor import (
    OperationExecutionError,
    execute_operation_proposal,
)
from runtime.orchestration.ops.queue import persist_operation_proposal


def _proposal(
    *,
    proposal_id: str = "OP-a1b2c3d4",
    action_id: str = "artifact.file.write",
    args: dict | None = None,
) -> dict:
    return {
        "schema_version": "operation_proposal.v1",
        "proposal_id": proposal_id,
        "operation_kind": "mutation",
        "action_id": action_id,
        "args": args or {"path": "plans/test-plan.md", "content": "# Test"},
        "requires_approval": True,
        "suggested_owner": "lifeos",
    }


def test_execute_artifact_file_write_round_trip(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    (artifacts_root / "plans").mkdir(parents=True)
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-wr1te001",
        args={"path": "plans/hello.md", "content": "# Hello"},
    ))
    receipt = execute_operation_proposal(repo_root, "OP-wr1te001")
    assert receipt["status"] == "executed"
    assert receipt["details"]["bytes_written"] == len("# Hello".encode())
    assert (artifacts_root / "plans" / "hello.md").read_text(encoding="utf-8") == "# Hello"


def test_execute_artifact_file_write_creates_parent_dirs(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    (artifacts_root / "plans").mkdir(parents=True)
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-wr1te002",
        args={"path": "plans/deep/subdir/file.md", "content": "deep"},
    ))
    receipt = execute_operation_proposal(repo_root, "OP-wr1te002")
    assert receipt["status"] == "executed"
    assert (artifacts_root / "plans" / "deep" / "subdir" / "file.md").exists()


def test_execute_artifact_file_write_rejects_directory_target(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    (artifacts_root / "plans").mkdir(parents=True)
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-wr1te003",
        args={"path": "plans", "content": "writing to dir"},
    ))
    with pytest.raises(OperationExecutionError, match="directory"):
        execute_operation_proposal(repo_root, "OP-wr1te003")


def test_execute_artifact_dir_ensure_creates_new_dir(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    (artifacts_root / "evidence").mkdir(parents=True)
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-dir00001",
        action_id="artifact.dir.ensure",
        args={"path": "evidence/batch2"},
    ))
    receipt = execute_operation_proposal(repo_root, "OP-dir00001")
    assert receipt["status"] == "executed"
    assert receipt["details"]["created"] is True
    assert (artifacts_root / "evidence" / "batch2").is_dir()


def test_execute_artifact_dir_ensure_idempotent(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    (artifacts_root / "evidence").mkdir(parents=True)
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-dir00002",
        action_id="artifact.dir.ensure",
        args={"path": "evidence"},
    ))
    receipt = execute_operation_proposal(repo_root, "OP-dir00002")
    assert receipt["status"] == "executed"
    assert receipt["details"]["created"] is False


def test_execute_artifact_dir_ensure_rejects_existing_file(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    (artifacts_root / "plans").mkdir(parents=True)
    (artifacts_root / "plans" / "clash.md").write_text("file")
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-dir00003",
        action_id="artifact.dir.ensure",
        args={"path": "plans/clash.md"},
    ))
    with pytest.raises(OperationExecutionError, match="file"):
        execute_operation_proposal(repo_root, "OP-dir00003")


def test_execute_artifact_file_archive_moves_file(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    source_file = artifacts_root / "plans" / "old-plan.md"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("old plan content")
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-arc00001",
        action_id="artifact.file.archive",
        args={"path": "plans/old-plan.md", "archive_dir": "99_archive"},
    ))
    receipt = execute_operation_proposal(repo_root, "OP-arc00001")
    assert receipt["status"] == "executed"
    assert not source_file.exists()
    archive_path = Path(receipt["details"]["archive_path"])
    assert archive_path.exists()
    assert archive_path.read_text(encoding="utf-8") == "old plan content"


def test_execute_artifact_file_archive_missing_source_raises(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    (artifacts_root / "plans").mkdir(parents=True)
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-arc00002",
        action_id="artifact.file.archive",
        args={"path": "plans/missing.md", "archive_dir": "99_archive"},
    ))
    with pytest.raises(OperationExecutionError, match="missing"):
        execute_operation_proposal(repo_root, "OP-arc00002")


def test_execute_artifact_file_archive_destination_collision_raises(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    source_file = artifacts_root / "plans" / "plan.md"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("source")
    archive_dir = artifacts_root / "99_archive"
    archive_dir.mkdir(parents=True)
    (archive_dir / "plan.md").write_text("existing archived file")
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-arc00003",
        action_id="artifact.file.archive",
        args={"path": "plans/plan.md", "archive_dir": "99_archive"},
    ))
    with pytest.raises(OperationExecutionError, match="already exists"):
        execute_operation_proposal(repo_root, "OP-arc00003")


def test_coo_parser_accepts_artifact_file_write_proposal():
    from runtime.orchestration.coo.parser import parse_operation_proposal
    yaml_text = (
        "```yaml\n"
        "schema_version: operation_proposal.v1\n"
        "proposal_id: OP-coo00001\n"
        "title: Write batch2 summary\n"
        "rationale: Document batch2 completion\n"
        "operation_kind: mutation\n"
        "action_id: artifact.file.write\n"
        "args:\n"
        "  path: plans/batch2-summary.md\n"
        '  content: "# Batch 2 Summary"\n'
        "requires_approval: true\n"
        "suggested_owner: lifeos\n"
        "```"
    )
    proposal = parse_operation_proposal(yaml_text)
    assert proposal["action_id"] == "artifact.file.write"


def test_receipt_emission_through_execute_operation_proposal(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    (artifacts_root / "plans").mkdir(parents=True)
    monkeypatch.setenv("LIFEOS_REPO_ROOT", str(tmp_path))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    from runtime.orchestration.ops.queue import find_receipt_by_proposal_id

    persist_operation_proposal(repo_root, _proposal(
        proposal_id="OP-rcpt0001",
        args={"path": "plans/receipt-test.md", "content": "receipt"},
    ))
    receipt = execute_operation_proposal(repo_root, "OP-rcpt0001")
    stored = find_receipt_by_proposal_id(repo_root, "OP-rcpt0001")
    assert stored is not None
    assert stored["schema_version"] == "operational_receipt.v1"
    assert stored["status"] == "executed"
