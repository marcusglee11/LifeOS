"""Tests for drift_sweep_issue_creator — dry-run preview builder for entrypoint freshness drift."""

from __future__ import annotations

from pathlib import Path

from doc_steward.drift_sweep_issue_creator import (
    CHECK_ID,
    SCHEMA_VERSION,
    SWEEP_ID,
    TARGET,
    _compute_fingerprints,
    _group_findings,
    _normalize_evidence,
    build_preview,
    main,
    render_markdown,
    write_preview,
)
from doc_steward.freshness_validator import check_entrypoint_freshness

# ---------------------------------------------------------------------------
# Fixture helpers (local copy — avoids cross-test-module import coupling)
# ---------------------------------------------------------------------------

CLEAN_README = """# LifeOS

**Current Status**: Live COO operations.

Repo canon wins on conflict. The strategic corpus and wiki are derived.

1. [docs/INDEX.md](docs/INDEX.md)
2. [onboarding](docs/08_manuals/LifeOS_Operator_Onboarding.md)
3. [state](docs/11_admin/LIFEOS_STATE.md)
4. [architecture](docs/00_foundations/LifeOS%20Target%20Architecture%20v2.3c.md)
"""

CLEAN_REGISTRY = """doc_groups:
  - id: canonical-root-navigation
    authority: canonical
    paths:
      - docs/INDEX.md
  - id: derived-strategic-corpus
    authority: derived
    paths:
      - docs/LifeOS_Strategic_Corpus.md
"""


def _write_entrypoint_fixture(
    root: Path, readme: str | None = None, registry: str | None = None
) -> None:
    (root / "docs" / "11_admin").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "08_manuals").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "00_foundations").mkdir(parents=True, exist_ok=True)
    (root / "config" / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (root / "docs" / "LifeOS_Strategic_Corpus.md").write_text(
        "# Derived corpus\n", encoding="utf-8"
    )
    (root / "docs" / "11_admin" / "LIFEOS_STATE.md").write_text(
        "# LifeOS State\n\n## COO Bootstrap Campaign\nLive COO operational.\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        readme or CLEAN_README,
        encoding="utf-8",
    )
    (root / "config" / "docs" / "authority_registry.yaml").write_text(
        registry or CLEAN_REGISTRY,
        encoding="utf-8",
    )


def _find_by_id(findings: list[dict], fid: str) -> dict | None:
    return next((f for f in findings if f.get("id") == fid), None)


# ===================================================================
# GROUP A: Six drift classes detected
# ===================================================================


def test_a1_detects_missing_required_file(tmp_path):
    """entrypoint-required-file-missing: no fixture at all."""
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    assert preview["summary"]["total_findings"] == 1
    assert "entrypoint-required-file-missing" in preview["findings_by_class"]
    f = preview["findings_by_class"]["entrypoint-required-file-missing"][0]
    assert f["severity"] == "warning"
    assert "README.md" in f["paths"]
    assert f["authority_class"] == "canonical"


def test_a2_detects_missing_read_order_links(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    assert "entrypoint-read-order-missing-links" in preview["findings_by_class"]
    f = preview["findings_by_class"]["entrypoint-read-order-missing-links"][0]
    assert "docs/INDEX.md" in f["evidence"]
    assert f["paths"] == ["README.md"]


def test_a3_detects_stale_phase4_status(tmp_path):
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
    preview = build_preview(findings)

    assert "entrypoint-readme-status-contradicts-lifeos-state" in preview["findings_by_class"]
    f = preview["findings_by_class"]["entrypoint-readme-status-contradicts-lifeos-state"][0]
    assert "Phase 4" in f["evidence"] or "Tier-3" in f["evidence"]


def test_a4_detects_missing_derived_boundary(tmp_path):
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
    preview = build_preview(findings)

    assert "entrypoint-derived-surface-boundary-missing" in preview["findings_by_class"]
    f = preview["findings_by_class"]["entrypoint-derived-surface-boundary-missing"][0]
    assert "derived" in f["evidence"].lower()


def test_a5_detects_index_registry_mismatch(tmp_path):
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
    preview = build_preview(findings)

    assert "entrypoint-index-authority-registry-mismatch" in preview["findings_by_class"]
    f = preview["findings_by_class"]["entrypoint-index-authority-registry-mismatch"][0]
    assert "authority_registry" in f["evidence"] or "INDEX.md" in f["evidence"]


def test_a6_detects_corpus_registry_mismatch(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        registry="""doc_groups:
  - id: canonical-root-navigation
    authority: canonical
    paths:
      - docs/INDEX.md
""",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    assert "entrypoint-corpus-authority-registry-mismatch" in preview["findings_by_class"]


# ===================================================================
# GROUP B: Clean state
# ===================================================================


def test_b1_clean_fixture_no_findings(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    assert preview["summary"]["total_findings"] == 0
    assert preview["summary"]["total_classes"] == 0
    assert preview["findings_by_class"] == {}
    assert preview["fingerprints"] == {}


# ===================================================================
# GROUP C: Fingerprint stability
# ===================================================================


def test_c1_fingerprint_deterministic(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview1 = build_preview(findings)
    preview2 = build_preview(findings)

    assert preview1["fingerprints"] == preview2["fingerprints"]


def test_c2_fingerprint_differs_on_input_change(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings_a = check_entrypoint_freshness(tmp_path)
    fp_a = build_preview(findings_a)["fingerprints"]

    # Different README -> different findings -> different fingerprints
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n",
    )
    findings_b = check_entrypoint_freshness(tmp_path)
    fp_b = build_preview(findings_b)["fingerprints"]

    assert fp_a != fp_b


def test_c3_fingerprint_stable_across_runs(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    for _, fp in preview["fingerprints"].items():
        assert isinstance(fp, str)
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)


def test_c4_fingerprint_16_char_hex(tmp_path):
    groups = _group_findings(
        [{"id": "test-class", "evidence": "some evidence", "authority_class": "canonical"}]
    )
    fps = _compute_fingerprints(groups)
    fp = fps["test-class"]

    assert isinstance(fp, str)
    assert len(fp) == 16
    assert all(c in "0123456789abcdef" for c in fp)


# ===================================================================
# GROUP D: JSON shape
# ===================================================================


def test_d1_required_top_level_keys(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    required = {
        "sweep_metadata",
        "summary",
        "findings_by_class",
        "fingerprints",
        "parent_link",
        "receipt",
    }
    assert required.issubset(preview.keys())


def test_d2_metadata_types(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)
    meta = preview["sweep_metadata"]

    assert meta["sweep_id"] == SWEEP_ID
    assert meta["target"] == TARGET
    assert meta["check_id"] == CHECK_ID
    assert meta["schema_version"] == SCHEMA_VERSION
    assert isinstance(meta["generation_timestamp"], str)


def test_d3_receipt_dry_run_true(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)
    receipt = preview["receipt"]

    assert receipt["dry_run"] is True
    assert receipt["mutated"] is False
    assert receipt["tool"] == "drift_sweep_issue_creator"


def test_d4_summary_counts_match_findings(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)
    summary = preview["summary"]

    total = 0
    for info in summary["classes"].values():
        total += info["count"]
    assert total == summary["total_findings"]
    assert summary["total_classes"] == len(preview["findings_by_class"])


# ===================================================================
# GROUP E: Markdown rendering
# ===================================================================


def test_e1_render_with_findings(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)
    md = render_markdown(preview)

    assert "# Advisory Documentation Drift Sweep Preview" in md
    assert "finding(s) across" in md
    assert "entrypoint-read-order-missing-links" in md
    assert "No files were mutated" in md


def test_e2_render_empty_state(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)
    md = render_markdown(preview)

    assert "# Advisory Documentation Drift Sweep Preview" in md
    assert "No drift findings detected" in md
    assert "| Drift Class | Count | Fingerprint |" not in md
    assert "finding(s) across" not in md


def test_e3_render_with_parent_link(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings, parent_link="https://github.com/example/123")
    md = render_markdown(preview)

    assert "Parent issue" in md
    assert "https://github.com/example/123" in md


def test_e4_render_without_parent_link(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)
    md = render_markdown(preview)

    assert "Parent issue" not in md


# ===================================================================
# GROUP F: Safe repeated runs
# ===================================================================


def test_f1_same_fixture_same_preview(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview1 = build_preview(findings)
    preview2 = build_preview(findings)

    assert preview1["summary"] == preview2["summary"]
    assert preview1["fingerprints"] == preview2["fingerprints"]


def test_f2_write_twice_no_error(tmp_path):
    _write_entrypoint_fixture(
        tmp_path,
        readme="# LifeOS\n\nRepo canon wins on conflict. The strategic corpus is derived.\n",
    )
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)
    out = tmp_path / "out"

    write_preview(preview, out)  # first write
    write_preview(preview, out)  # second write — no error


# ===================================================================
# GROUP G: Output directory
# ===================================================================


def test_g1_output_dir_auto_created(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    out = tmp_path / "nonexistent" / "subdir"
    write_preview(preview, out)

    assert out.is_dir()


def test_g2_json_and_md_files_written(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    out = tmp_path / "out"
    files = write_preview(preview, out)

    for f in files:
        assert f.exists(), f"Expected {f} to exist"
    assert any(f.suffix == ".json" for f in files)
    assert any(f.suffix == ".md" for f in files)


def test_g3_latest_files_written(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    out = tmp_path / "out"
    write_preview(preview, out)

    assert (out / "drift_sweep_preview_latest.json").exists()
    assert (out / "drift_sweep_preview_latest.md").exists()


def test_g4_custom_output_dir(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    custom = tmp_path / "custom_output"
    write_preview(preview, custom)

    files = list(custom.iterdir())
    assert len(files) >= 4  # timestamped json+md + latest json+md


# ===================================================================
# GROUP H: Parent link
# ===================================================================


def test_h1_parent_link_in_json_when_set(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings, parent_link="https://github.com/example/456")

    assert preview["parent_link"] == "https://github.com/example/456"


def test_h2_parent_link_none_when_omitted(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    findings = check_entrypoint_freshness(tmp_path)
    preview = build_preview(findings)

    assert preview["parent_link"] is None


# ===================================================================
# GROUP I: CLI integration
# ===================================================================


def test_i1_main_exit_zero(tmp_path):
    _write_entrypoint_fixture(tmp_path)
    rc = main([str(tmp_path)])
    assert rc == 0


def test_i2_main_exit_zero_with_findings(tmp_path):
    # No fixture -> required file missing -> findings present
    rc = main([str(tmp_path)])
    assert rc == 0


# ===================================================================
# Internal helpers unit tests
# ===================================================================


def test_normalize_evidence_stable_order():
    findings = [
        {"id": "b-class", "evidence": "ZZZ"},
        {"id": "a-class", "evidence": "AAA"},
    ]
    result = _normalize_evidence(findings)
    assert result == "aaa | zzz"


def test_group_findings_preserves_order():
    findings = [
        {"id": "z-first", "evidence": "z"},
        {"id": "a-second", "evidence": "a"},
        {"id": "z-first", "evidence": "z again"},
    ]
    groups = _group_findings(findings)
    keys = list(groups.keys())
    assert keys == ["z-first", "a-second"]
    assert len(groups["z-first"]) == 2
