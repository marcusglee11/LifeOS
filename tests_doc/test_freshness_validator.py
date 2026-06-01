"""Tests for freshness validator."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from doc_steward.freshness_validator import (
    check_entrypoint_freshness,
    check_freshness,
    get_freshness_mode,
)


def _write_entrypoint_fixture(
    root: Path, readme: str | None = None, registry: str | None = None
) -> None:
    (root / "docs" / "11_admin").mkdir(parents=True)
    (root / "docs" / "08_manuals").mkdir(parents=True)
    (root / "docs" / "00_foundations").mkdir(parents=True)
    (root / "config" / "docs").mkdir(parents=True)
    (root / "docs" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (root / "docs" / "LifeOS_Strategic_Corpus.md").write_text(
        "# Derived corpus\n", encoding="utf-8"
    )
    (root / "docs" / "11_admin" / "LIFEOS_STATE.md").write_text(
        "# LifeOS State\n\n## COO Bootstrap Campaign\nLive COO operational.\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        readme
        or """# LifeOS

**Current Status**: Live COO operations.

Repo canon wins on conflict. The strategic corpus and wiki are derived.

1. [docs/INDEX.md](docs/INDEX.md)
2. [onboarding](docs/08_manuals/LifeOS_Operator_Onboarding.md)
3. [state](docs/11_admin/LIFEOS_STATE.md)
4. [architecture](docs/00_foundations/LifeOS%20Target%20Architecture%20v2.3c.md)
""",
        encoding="utf-8",
    )
    (root / "config" / "docs" / "authority_registry.yaml").write_text(
        registry
        or """doc_groups:
  - id: canonical-root-navigation
    authority: canonical
    paths:
      - docs/INDEX.md
  - id: derived-strategic-corpus
    authority: derived
    paths:
      - docs/LifeOS_Strategic_Corpus.md
""",
        encoding="utf-8",
    )


def test_entrypoint_freshness_clean_fixture_has_no_findings(tmp_path):
    _write_entrypoint_fixture(tmp_path)

    assert check_entrypoint_freshness(tmp_path) == []


def test_entrypoint_freshness_detects_missing_read_order_links(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )

    findings = check_entrypoint_freshness(tmp_path)

    assert {finding["id"] for finding in findings} >= {"entrypoint-read-order-missing-links"}
    missing = next(f for f in findings if f["id"] == "entrypoint-read-order-missing-links")
    assert "docs/INDEX.md" in str(missing["evidence"])
    assert missing["paths"] == ["README.md"]


def test_entrypoint_freshness_detects_stale_phase4_status(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="""# LifeOS

**Current Status**: Phase 4 Preparation — Tier-3 Authorized.

Repo canon wins on conflict. The strategic corpus is derived.

[docs/INDEX.md](docs/INDEX.md)
[onboarding](docs/08_manuals/LifeOS_Operator_Onboarding.md)
[state](docs/11_admin/LIFEOS_STATE.md)
[architecture](docs/00_foundations/LifeOS%20Target%20Architecture%20v2.3c.md)
""",
    )

    findings = check_entrypoint_freshness(tmp_path)

    assert any(f["id"] == "entrypoint-readme-status-contradicts-lifeos-state" for f in findings)


def test_entrypoint_freshness_detects_authority_registry_mismatch(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        registry="""doc_groups:
  - id: wrong-root-navigation
    authority: derived
    paths:
      - docs/INDEX.md
""",
    )

    findings = check_entrypoint_freshness(tmp_path)

    ids = {finding["id"] for finding in findings}
    assert "entrypoint-index-authority-registry-mismatch" in ids
    assert "entrypoint-corpus-authority-registry-mismatch" in ids


def test_entrypoint_freshness_parses_quoted_yaml_registry_paths(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        registry="""doc_groups:
  - id: canonical-root-navigation
    authority: "canonical"
    paths:
      - "docs/INDEX.md"
  - id: derived-strategic-corpus
    authority: "derived"
    paths:
      - "docs/LifeOS_Strategic_Corpus.md"
""",
    )

    assert check_entrypoint_freshness(tmp_path) == []


def test_entrypoint_freshness_malformed_registry_fails_closed(tmp_path):
    _write_entrypoint_fixture(tmp_path, registry="doc_groups: [unterminated")

    findings = check_entrypoint_freshness(tmp_path)

    ids = {finding["id"] for finding in findings}
    assert "entrypoint-index-authority-registry-mismatch" in ids
    assert "entrypoint-corpus-authority-registry-mismatch" in ids


def test_entrypoint_freshness_non_list_registry_groups_fail_closed(tmp_path):
    _write_entrypoint_fixture(tmp_path, registry="doc_groups: 1")

    findings = check_entrypoint_freshness(tmp_path)

    ids = {finding["id"] for finding in findings}
    assert "entrypoint-index-authority-registry-mismatch" in ids
    assert "entrypoint-corpus-authority-registry-mismatch" in ids


def test_entrypoint_freshness_non_mapping_registry_root_fails_closed(tmp_path):
    _write_entrypoint_fixture(tmp_path, registry="- not-a-mapping")

    findings = check_entrypoint_freshness(tmp_path)

    ids = {finding["id"] for finding in findings}
    assert "entrypoint-index-authority-registry-mismatch" in ids
    assert "entrypoint-corpus-authority-registry-mismatch" in ids


def test_entrypoint_freshness_non_mapping_registry_group_fails_closed(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        registry="""doc_groups:
  - not-a-mapping
""",
    )

    findings = check_entrypoint_freshness(tmp_path)

    ids = {finding["id"] for finding in findings}
    assert "entrypoint-index-authority-registry-mismatch" in ids
    assert "entrypoint-corpus-authority-registry-mismatch" in ids


def test_entrypoint_freshness_non_list_registry_paths_fail_closed(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        registry="""doc_groups:
  - id: bad-paths
    authority: canonical
    paths: docs/INDEX.md
""",
    )

    findings = check_entrypoint_freshness(tmp_path)

    assert any(f["id"] == "entrypoint-index-authority-registry-mismatch" for f in findings)


def test_entrypoint_freshness_detects_missing_derived_boundary(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="""# LifeOS

**Current Status**: Live COO operations.

1. [docs/INDEX.md](docs/INDEX.md)
2. [onboarding](docs/08_manuals/LifeOS_Operator_Onboarding.md)
3. [state](docs/11_admin/LIFEOS_STATE.md)
4. [architecture](docs/00_foundations/LifeOS%20Target%20Architecture%20v2.3c.md)
""",
    )

    findings = check_entrypoint_freshness(tmp_path)

    assert any(f["id"] == "entrypoint-derived-surface-boundary-missing" for f in findings)


def test_entrypoint_freshness_missing_required_input_returns_single_finding(tmp_path):
    findings = check_entrypoint_freshness(tmp_path)

    assert len(findings) == 1
    assert findings[0]["id"] == "entrypoint-required-file-missing"
    assert findings[0]["paths"] == [
        "README.md",
        "docs/11_admin/LIFEOS_STATE.md",
        "config/docs/authority_registry.yaml",
    ]


def test_freshness_mode_off_by_default():
    """Test that freshness mode defaults to 'off'."""
    with mock.patch.dict(os.environ, {}, clear=True):
        assert get_freshness_mode() == "off"


def test_freshness_mode_from_env():
    """Test that freshness mode can be set via env var."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        assert get_freshness_mode() == "warn"

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        assert get_freshness_mode() == "block"


def test_freshness_mode_invalid_defaults_to_off():
    """Test that invalid freshness mode defaults to 'off'."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "invalid"}):
        assert get_freshness_mode() == "off"


def test_freshness_check_off_mode_returns_empty(tmp_path):
    """Test that off mode returns no warnings or errors."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "off"}):
        warnings, errors = check_freshness(tmp_path)
        assert warnings == []
        assert errors == []


def test_freshness_check_missing_status_file_warn_mode(tmp_path):
    """Test that missing status file generates warning in warn mode."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "missing" in warnings[0].lower()
        assert errors == []


def test_freshness_check_missing_status_file_block_mode(tmp_path):
    """Test that missing status file generates error in block mode."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(errors) == 1
        assert "missing" in errors[0].lower()


def test_freshness_check_fresh_status_file(tmp_path):
    """Test that a fresh status file passes."""
    # Create a fresh status file (current time)
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"
    status_file.write_text(json.dumps({"contradictions": []}))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert warnings == []
        assert errors == []


def test_freshness_check_stale_status_file_warn_mode(tmp_path):
    """Test that a stale status file generates warning in warn mode."""
    # Create a stale status file (26 hours old)
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"
    status_file.write_text(json.dumps({"contradictions": []}))

    # Set file mtime to 26 hours ago
    stale_time = datetime.now(timezone.utc) - timedelta(hours=26)
    os.utime(status_file, (stale_time.timestamp(), stale_time.timestamp()))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "stale" in warnings[0].lower()
        assert errors == []


def test_freshness_check_stale_status_file_block_mode(tmp_path):
    """Test that a stale status file generates error in block mode."""
    # Create a stale status file (26 hours old)
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"
    status_file.write_text(json.dumps({"contradictions": []}))

    # Set file mtime to 26 hours ago
    stale_time = datetime.now(timezone.utc) - timedelta(hours=26)
    os.utime(status_file, (stale_time.timestamp(), stale_time.timestamp()))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(errors) == 1
        assert "stale" in errors[0].lower()


def test_freshness_check_contradictions_warn_severity(tmp_path):
    """Test that contradictions with 'warn' severity generate warnings."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"

    status_data = {
        "contradictions": [
            {"id": "C1", "severity": "warn", "message": "Test warning", "refs": ["ref1.md"]}
        ]
    }
    status_file.write_text(json.dumps(status_data))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "C1" in warnings[0]
        assert "Test warning" in warnings[0]
        assert errors == []


def test_freshness_check_contradictions_block_severity_warn_mode(tmp_path):
    """Test that contradictions with 'block' severity generate warnings in warn mode."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"

    status_data = {
        "contradictions": [
            {"id": "C1", "severity": "block", "message": "Test blocking issue", "refs": ["ref1.md"]}
        ]
    }
    status_file.write_text(json.dumps(status_data))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "C1" in warnings[0]
        assert errors == []


def test_freshness_check_contradictions_block_severity_block_mode(tmp_path):
    """Test that contradictions with 'block' severity generate errors in block mode."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"

    status_data = {
        "contradictions": [
            {
                "id": "C1",
                "severity": "block",
                "message": "Test blocking issue",
                "refs": ["ref1.md", "ref2.md"],
            }
        ]
    }
    status_file.write_text(json.dumps(status_data))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(errors) == 1
        assert "C1" in errors[0]
        assert "Test blocking issue" in errors[0]
        assert "ref1.md" in errors[0]


def test_freshness_check_missing_contradictions_field(tmp_path):
    """Test that missing contradictions field is treated as empty (backward compatibility)."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"

    # Status file without contradictions field
    status_file.write_text(json.dumps({}))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        # Should not error on missing field
        assert errors == []


def test_freshness_check_invalid_json(tmp_path):
    """Test that invalid JSON generates appropriate error/warning."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"
    status_file.write_text("invalid json{")

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "parse" in warnings[0].lower()

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(errors) == 1
        assert "parse" in errors[0].lower()
