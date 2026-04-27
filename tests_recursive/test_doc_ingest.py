#!/usr/bin/env python3
"""
Acceptance Tests for doc_ingest stage (AT-DI-01 through AT-DI-18).

Tests use tmp_path for isolation — no git worktrees required (WSL-safe).

Run with:
    python3 -m pytest tests_recursive/test_doc_ingest.py -v
"""

import json
import sys
from pathlib import Path
from typing import Any

# Allow importing runtime.stewardship.doc_ingest
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from runtime.stewardship.doc_ingest import (  # noqa: E402
    SCHEMA_ID,
    SCHEMA_VERSION,
    DocIngestResult,
    _compute_fingerprint,
    _detect_index_shape,
    _has_artefact_key_collision,
    _update_index,
    emit_result_packet,
    run,
)

# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_source_doc(path: Path, title: str = "Test Doc") -> None:
    """Write a minimal DSP-compliant source document."""
    path.write_text(
        f"# {title}\n\n**Status**: Draft\n**Authority**: Test\n\nContent.\n",
        encoding="utf-8",
    )


def _make_manifest(
    source_path: str,
    dest_path: str,
    target_index_path: str,
    artefact_key: str = "test_key",
    commit_enabled: bool = False,
    supersedes: list[str] | None = None,
    binding_class: str = "PROTOCOL",
    canonicality: str = "draft",
) -> dict:
    return {
        "schema": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "source_path": source_path,
        "dest_path": dest_path,
        "title": "Test Protocol v1.0",
        "description": "A test protocol document.",
        "artefact_key": artefact_key,
        "target_index_path": target_index_path,
        "binding_class": binding_class,
        "canonicality": canonicality,
        "supersedes": supersedes or [],
        "related": {"issues": [], "prs": [], "adrs": []},
        "commit": {"enabled": commit_enabled, "message": "test: ingest test doc"},
    }


def _make_array_index() -> dict:
    return {
        "meta": {"version": "1.0.0"},
        "artefacts": [
            {"_comment": "Active Protocols"},
        ],
    }


def _make_dict_index() -> dict:
    return {
        "meta": {"version": "1.0.0", "binding_classes": {"PROTOCOL": "Active protocols"}},
        "artefacts": {
            "_comment_protocols": "=== 02_protocols: Active Protocols ===",
        },
    }


_DEFAULT_PERMITTED_INDEX_PATHS = [
    "docs/02_protocols/ARTEFACT_INDEX.json",
    "docs/03_runtime/ARTEFACT_INDEX.json",
]


def _make_runner_ctx(
    repo_root: Path,
    run_id: str = "test-run-001",
    actually_commit: bool = False,
    allowed_dest_roots: list[str] | None = None,
    permitted_index_paths: list[str] | None = None,
) -> dict:
    """
    Build a runner context dict.
    permitted_index_paths=None  → use v1 defaults (02_protocols, 03_runtime only)
    permitted_index_paths=[]    → explicitly empty → fails closed for all index paths
    """
    config: dict[str, Any] = {
        "doc_ingest": {
            "allowed_dest_roots": allowed_dest_roots or ["docs/02_protocols/"],
            "permitted_target_index_paths": (
                _DEFAULT_PERMITTED_INDEX_PATHS
                if permitted_index_paths is None
                else permitted_index_paths
            ),
        },
        "git": {"commit_enabled": False},
    }
    return {
        "run_id": run_id,
        "repo_root": repo_root,
        "actually_commit": actually_commit,
        "config": config,
    }


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


def _scaffold_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    """
    Create a minimal repo-like layout in tmp_path.
    Returns (repo_root, source_path, index_path).
    """
    repo_root = tmp_path / "repo"
    src_dir = repo_root / "staging"
    dest_dir = repo_root / "docs" / "02_protocols"
    index_dir = repo_root / "docs" / "02_protocols"
    logs_dir = repo_root / "logs"

    for d in [src_dir, dest_dir, logs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    source_path = src_dir / "Test_Protocol_v1.0.md"
    _make_source_doc(source_path)

    index_path = index_dir / "ARTEFACT_INDEX.json"
    index_path.write_text(json.dumps(_make_array_index(), indent=2), encoding="utf-8")

    return repo_root, source_path, index_path


# ─── AT-DI-01: dry-run emits preview, no mutation ────────────────────────────


def test_AT_DI_01_dry_run_no_mutation(tmp_path):
    """Valid dry-run emits preview logs/diffs and performs no repo-tree mutation."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)
    dest_rel = "docs/02_protocols/Test_Protocol_v1.0.md"

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        commit_enabled=False,
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, actually_commit=False)

    result = run(manifest_path, ctx)

    assert result.success, f"Expected success, got: {result.failure_reason}"
    assert not result.is_idempotent_noop

    # No file was written to dest
    assert not (repo_root / dest_rel).exists(), "dest_path must not exist after dry-run"

    # Index was NOT mutated
    index_after = json.loads(index_path.read_bytes())
    assert index_after == _make_array_index(), "ARTEFACT_INDEX must not be mutated in dry-run"

    # Preview logs were emitted
    log_dir = repo_root / "logs" / "steward_runner" / "doc_ingest" / ctx["run_id"]
    assert (log_dir / "trace.jsonl").exists()
    assert (log_dir / "index_diff.md").exists()


# ─── AT-DI-02: valid commit copies, updates index, emits result ───────────────


def test_AT_DI_02_commit_run(tmp_path):
    """Valid commit run copies source to dest, updates target ARTEFACT_INDEX."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)
    dest_rel = "docs/02_protocols/Test_Protocol_v1.0.md"

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        commit_enabled=True,
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, actually_commit=True)

    result = run(manifest_path, ctx)

    assert result.success, f"Expected success, got: {result.failure_reason}"
    assert not result.is_idempotent_noop
    assert result.commit_enabled_for_runner

    # File was copied
    dest_path = repo_root / dest_rel
    assert dest_path.exists(), "dest_path must exist after commit run"
    assert dest_path.read_text() == source_path.read_text()

    # Index was updated with new path entry
    index_after = json.loads(index_path.read_bytes())
    paths = [e.get("path") for e in index_after["artefacts"] if isinstance(e, dict) and "path" in e]
    assert dest_rel in paths, f"dest_rel must be in updated index, got: {paths}"


# ─── AT-DI-03: CLI --commit without manifest.commit.enabled fails ─────────────


def test_AT_DI_03_cli_commit_manifest_disabled(tmp_path):
    """CLI --commit without manifest.commit.enabled=true fails closed."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path="docs/02_protocols/Test_Protocol_v1.0.md",
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        commit_enabled=False,  # disabled
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, actually_commit=True)  # CLI says commit

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-4"
    assert "manifest_commit_disabled" in result.failure_reason


# ─── AT-DI-04: manifest.commit.enabled without CLI --commit does not commit ───


def test_AT_DI_04_manifest_enabled_no_cli_commit(tmp_path):
    """manifest.commit.enabled=true without CLI --commit does not commit."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)
    dest_rel = "docs/02_protocols/Test_Protocol_v1.0.md"

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        commit_enabled=True,  # manifest says yes
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, actually_commit=False)  # CLI says no

    result = run(manifest_path, ctx)

    assert result.success
    # No file copied
    assert not (repo_root / dest_rel).exists()
    # commit_enabled_for_runner must be False (no CLI commit)
    assert not result.commit_enabled_for_runner


# ─── AT-DI-05: existing dest_path fails closed ───────────────────────────────


def test_AT_DI_05_dest_already_exists(tmp_path):
    """Existing dest_path fails closed."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)
    dest_rel = "docs/02_protocols/Test_Protocol_v1.0.md"

    # Pre-create the destination
    (repo_root / dest_rel).write_text("already here", encoding="utf-8")

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, actually_commit=False)

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-8"


# ─── AT-DI-06: missing source_path fails closed ──────────────────────────────


def test_AT_DI_06_missing_source_path(tmp_path):
    """Missing source_path fails closed."""
    repo_root, _source, index_path = _scaffold_repo(tmp_path)

    manifest = _make_manifest(
        source_path="nonexistent/Source_Doc_v1.0.md",
        dest_path="docs/02_protocols/Test_Protocol_v1.0.md",
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root)

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-5"


# ─── AT-DI-07: dest_path outside allowed_dest_roots fails closed ─────────────


def test_AT_DI_07_dest_outside_allowed_roots(tmp_path):
    """dest_path outside allowed_dest_roots fails closed."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)

    # dest goes to 01_governance — not in allowed roots
    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path="docs/01_governance/Test_Protocol_v1.0.md",
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, allowed_dest_roots=["docs/02_protocols/"])

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-7"


# ─── AT-DI-08: filename violating protocol naming fails closed ───────────────


def test_AT_DI_08_filename_convention_violation(tmp_path):
    """Filename violating protocol naming pattern fails closed."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path="docs/02_protocols/bad_name.md",  # no version suffix
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root)

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-9"


# ─── AT-DI-09: missing required metadata header fails closed ─────────────────


def test_AT_DI_09_missing_metadata_header(tmp_path):
    """Missing required metadata header in source fails closed."""
    repo_root, _, index_path = _scaffold_repo(tmp_path)

    # Source without required headers
    bad_source = repo_root / "staging" / "Bad_Protocol_v1.0.md"
    bad_source.write_text("# Bad Doc\n\nNo status header here.\n", encoding="utf-8")

    manifest = _make_manifest(
        source_path=str(bad_source),
        dest_path="docs/02_protocols/Bad_Protocol_v1.0.md",
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root)

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-10"


# ─── AT-DI-10: artefact_key collision fails closed ───────────────────────────


def test_AT_DI_10_artefact_key_collision_array(tmp_path):
    """artefact_key (path) collision in array-shaped index fails closed."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)
    dest_rel = "docs/02_protocols/Test_Protocol_v1.0.md"

    # Pre-populate index with the same path
    existing = _make_array_index()
    existing["artefacts"].append({"path": dest_rel})
    index_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root)

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-13"


# ─── AT-DI-11: unknown target_index_path shape fails closed ─────────────────


def test_AT_DI_11_unknown_index_shape(tmp_path):
    """Unknown ARTEFACT_INDEX shape fails closed."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)

    # Write index with artefacts as a string (unknown shape)
    index_path.write_text(
        json.dumps({"meta": {}, "artefacts": "bad_shape"}),
        encoding="utf-8",
    )

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path="docs/02_protocols/Test_Protocol_v1.0.md",
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root)

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-12"


# ─── AT-DI-12: dict-shaped index update works ────────────────────────────────


def test_AT_DI_12_dict_shaped_index_update(tmp_path):
    """dict-shaped target-index update works."""
    repo_root, source_path, _ = _scaffold_repo(tmp_path)

    # Create a dict-shaped ARTEFACT_INDEX (like 01_governance, but in 02_protocols for test)
    index_path = repo_root / "docs" / "02_protocols" / "ARTEFACT_INDEX.json"
    index_path.write_text(json.dumps(_make_dict_index(), indent=2), encoding="utf-8")

    dest_rel = "docs/02_protocols/Test_Protocol_v1.0.md"
    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        artefact_key="test_protocol",
        commit_enabled=True,
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, actually_commit=True)

    result = run(manifest_path, ctx)

    assert result.success, f"Expected success, got: {result.failure_reason}"
    index_after = json.loads(index_path.read_bytes())
    assert index_after["artefacts"]["test_protocol"] == dest_rel


# ─── AT-DI-13: array-shaped index update preserves schema shape ─────────────


def test_AT_DI_13_array_shaped_index_update(tmp_path):
    """array-shaped target-index update works without destroying schema shape."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)
    dest_rel = "docs/02_protocols/Test_Protocol_v1.0.md"

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        commit_enabled=True,
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, actually_commit=True)

    result = run(manifest_path, ctx)

    assert result.success
    index_after = json.loads(index_path.read_bytes())
    assert isinstance(index_after["artefacts"], list), "artefacts must remain a list"
    paths = [e.get("path") for e in index_after["artefacts"] if isinstance(e, dict)]
    assert dest_rel in paths


# ─── AT-DI-14: supersedes target missing fails closed ────────────────────────


def test_AT_DI_14_supersedes_missing(tmp_path):
    """supersedes target missing fails closed with no partial update."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path="docs/02_protocols/Test_Protocol_v1.0.md",
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        supersedes=["docs/02_protocols/OldDoc_v1.0.md"],  # does not exist
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root)

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-14"
    # Index must be unmodified
    assert json.loads(index_path.read_bytes()) == _make_array_index()


# ─── AT-DI-15: supersedes metadata update in array index ────────────────────


def test_AT_DI_15_supersedes_metadata_update(tmp_path):
    """supersedes metadata update works where schema supports superseded_by."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)
    old_rel = "docs/02_protocols/Old_Protocol_v1.0.md"
    old_path = repo_root / old_rel
    old_path.write_text("# Old\n**Status**: Superseded\n**Authority**: Test\n", encoding="utf-8")

    # Pre-populate index with the old entry
    existing = _make_array_index()
    existing["artefacts"].append({"path": old_rel})
    index_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    dest_rel = "docs/02_protocols/New_Protocol_v2.0.md"
    _make_source_doc(repo_root / "staging" / "New_Protocol_v2.0.md")

    manifest = _make_manifest(
        source_path=str(repo_root / "staging" / "New_Protocol_v2.0.md"),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        artefact_key="new_protocol",
        commit_enabled=True,
        supersedes=[old_rel],
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, actually_commit=True)

    result = run(manifest_path, ctx)

    assert result.success, f"Expected success, got: {result.failure_reason}"
    index_after = json.loads(index_path.read_bytes())
    old_entry = next(
        (e for e in index_after["artefacts"] if isinstance(e, dict) and e.get("path") == old_rel),
        None,
    )
    assert old_entry is not None
    assert old_entry.get("superseded_by") == dest_rel


# ─── AT-DI-16: idempotent re-run is no-op success ───────────────────────────


def test_AT_DI_16_idempotent_rerun(tmp_path):
    """Identical manifest re-run is idempotent no-op success."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)
    dest_rel = "docs/02_protocols/Test_Protocol_v1.0.md"

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        commit_enabled=True,
    )
    manifest_path = _write_manifest(tmp_path, manifest)

    # First run (commit)
    ctx = _make_runner_ctx(repo_root, actually_commit=True)
    result1 = run(manifest_path, ctx)
    assert result1.success

    # Second run with same manifest (different run_id to avoid log collision)
    ctx2 = _make_runner_ctx(repo_root, run_id="test-run-002", actually_commit=True)
    result2 = run(manifest_path, ctx2)

    assert result2.success
    assert result2.is_idempotent_noop


# ─── AT-DI-17: validator failure blocks commit ───────────────────────────────


def test_AT_DI_17_validator_failure_records_failure(tmp_path):
    """Invariant failure blocks commit and records failure result."""
    repo_root, _, _ = _scaffold_repo(tmp_path)

    # Source with missing headers → INV-10
    bad_source = repo_root / "staging" / "Bad_v1.0.md"
    bad_source.write_text("# No headers here\n\nContent.\n", encoding="utf-8")

    manifest = _make_manifest(
        source_path=str(bad_source),
        dest_path="docs/02_protocols/Bad_v1.0.md",
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        commit_enabled=True,
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    ctx = _make_runner_ctx(repo_root, actually_commit=True)

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_reason is not None
    assert result.failure_invariant is not None
    # No file committed
    assert not (repo_root / "docs/02_protocols/Bad_v1.0.md").exists()


# ─── AT-DI-18: workspace lock prevents concurrent conflicts ─────────────────


def test_AT_DI_18_workspace_lock(tmp_path):
    """Workspace lock prevents concurrent conflicting ingest runs."""
    import fcntl

    repo_root, source_path, _ = _scaffold_repo(tmp_path)

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path="docs/02_protocols/Test_Protocol_v1.0.md",
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)

    # Hold the lock manually
    lock_path = repo_root / "logs" / "steward_runner" / "doc_ingest.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w")
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

    try:
        ctx = _make_runner_ctx(repo_root)
        result = run(manifest_path, ctx)
        assert not result.success
        assert result.failure_invariant == "INV-20"
        assert "lock_conflict" in result.failure_reason
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


# ─── Unit tests for helper functions ─────────────────────────────────────────


def test_detect_index_shape_dict():
    data = {"artefacts": {"key": "val"}}
    assert _detect_index_shape(data) == "dict"


def test_detect_index_shape_array():
    data = {"artefacts": []}
    assert _detect_index_shape(data) == "array"


def test_detect_index_shape_unknown():
    data = {"artefacts": "bad"}
    assert _detect_index_shape(data) == "unknown"


def test_fingerprint_excludes_commit():
    m1 = {"schema": SCHEMA_ID, "source_path": "x", "commit": {"enabled": False, "message": "a"}}
    m2 = {"schema": SCHEMA_ID, "source_path": "x", "commit": {"enabled": False, "message": "b"}}
    assert _compute_fingerprint(m1) == _compute_fingerprint(m2)


def test_fingerprint_sensitive_to_content():
    m1 = {"schema": SCHEMA_ID, "source_path": "x"}
    m2 = {"schema": SCHEMA_ID, "source_path": "y"}
    assert _compute_fingerprint(m1) != _compute_fingerprint(m2)


def test_artefact_key_collision_dict():
    data = {"artefacts": {"existing_key": "docs/foo.md"}}
    assert _has_artefact_key_collision(data, "dict", "existing_key", "docs/foo.md")
    assert not _has_artefact_key_collision(data, "dict", "new_key", "docs/bar.md")


def test_artefact_key_collision_array():
    data = {"artefacts": [{"path": "docs/foo.md"}]}
    assert _has_artefact_key_collision(data, "array", "any_key", "docs/foo.md")
    assert not _has_artefact_key_collision(data, "array", "any_key", "docs/bar.md")


def test_update_index_dict_shape():
    data = {"artefacts": {"_comment": "comment"}}
    patches = _update_index(data, "dict", "new_key", "docs/new.md", [])
    assert data["artefacts"]["new_key"] == "docs/new.md"
    assert patches == []


def test_update_index_array_shape():
    data = {"artefacts": [{"path": "docs/old.md"}]}
    _update_index(data, "array", "new_key", "docs/new.md", ["docs/old.md"])
    entries = data["artefacts"]
    paths = [e.get("path") for e in entries if isinstance(e, dict)]
    assert "docs/new.md" in paths
    old_entry = next(e for e in entries if isinstance(e, dict) and e.get("path") == "docs/old.md")
    assert old_entry.get("superseded_by") == "docs/new.md"


# ─── Fix 1: permitted_target_index_paths semantics ───────────────────────────


def test_governance_index_rejected_by_default_config(tmp_path):
    """docs/01_governance/ARTEFACT_INDEX.json is rejected under default v1 config."""
    repo_root, source_path, _ = _scaffold_repo(tmp_path)

    gov_dir = repo_root / "docs" / "01_governance"
    gov_dir.mkdir(parents=True, exist_ok=True)
    gov_index = gov_dir / "ARTEFACT_INDEX.json"
    gov_index.write_text(json.dumps(_make_dict_index(), indent=2), encoding="utf-8")

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path="docs/02_protocols/Test_Protocol_v1.0.md",
        target_index_path="docs/01_governance/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    # Default ctx uses _DEFAULT_PERMITTED_INDEX_PATHS (02_protocols, 03_runtime only)
    ctx = _make_runner_ctx(repo_root)

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-11-perm"


def test_empty_permitted_index_paths_fails_closed(tmp_path):
    """Empty permitted_target_index_paths fails closed for all target indexes."""
    repo_root, source_path, _ = _scaffold_repo(tmp_path)

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path="docs/02_protocols/Test_Protocol_v1.0.md",
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    # Explicitly empty list → fail closed (no index is permitted)
    ctx = _make_runner_ctx(repo_root, permitted_index_paths=[])

    result = run(manifest_path, ctx)

    assert not result.success
    assert result.failure_invariant == "INV-11-perm"


# ─── Fix 2: authoritative idempotency from dl_doc result packets ─────────────


def test_idempotency_from_dl_doc_result_packet(tmp_path):
    """Idempotency detected from DOC_STEWARD_RESULT in dl_doc, not only completed.json."""
    repo_root, source_path, index_path = _scaffold_repo(tmp_path)
    dest_rel = "docs/02_protocols/Test_Protocol_v1.0.md"

    manifest = _make_manifest(
        source_path=str(source_path),
        dest_path=dest_rel,
        target_index_path="docs/02_protocols/ARTEFACT_INDEX.json",
        commit_enabled=True,
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    fingerprint = _compute_fingerprint(manifest)

    # Plant a successful DOC_STEWARD_RESULT packet in dl_doc
    prior_result = DocIngestResult(
        success=True,
        manifest_fingerprint=fingerprint,
        dest_path_written=dest_rel,
        staged_files=[dest_rel],
    )
    emit_result_packet(
        run_id="prior-run-001",
        repo_root=repo_root,
        ingest_result=prior_result,
        commit_sha="deadbeef001",
        manifest=manifest,
    )

    # Ensure local completed.json cache does NOT exist
    ledger_path = repo_root / "logs" / "steward_runner" / "doc_ingest" / "completed.json"
    if ledger_path.exists():
        ledger_path.unlink()

    # Second run: should detect idempotency from dl_doc, NOT from local cache
    ctx = _make_runner_ctx(repo_root, run_id="test-run-002", actually_commit=True)
    result = run(manifest_path, ctx)

    assert result.success, f"Expected idempotent success, got: {result.failure_reason}"
    assert result.is_idempotent_noop
