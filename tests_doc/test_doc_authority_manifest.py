from pathlib import Path

from doc_steward.doc_authority_manifest import check_doc_authority_manifest


def _write(path: Path, content: str = "# Title\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _manifest(root: Path, body: str) -> Path:
    path = root / "config" / "docs" / "authority_registry.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_unclassified_active_doc_fails_with_path_and_recovery(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _manifest(
        tmp_path,
        """
version: 1
doc_groups: []
""",
    )

    errors = check_doc_authority_manifest(tmp_path)

    assert any("docs/02_protocols/Runbook.md" in error for error in errors)
    assert any("add it to config/docs/authority_registry.yaml" in error for error in errors)


def test_invalid_authority_class_fails(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: bad
    authority: important
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
""",
    )

    errors = check_doc_authority_manifest(tmp_path)

    assert any("authority 'important' is invalid" in error for error in errors)


def test_derived_surface_requires_source_paths(tmp_path):
    _write(tmp_path / "docs" / "LifeOS_Strategic_Corpus.md")
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: corpus
    authority: derived
    steward: Docs Steward
    paths:
      - docs/LifeOS_Strategic_Corpus.md
    source_paths: []
""",
    )

    errors = check_doc_authority_manifest(tmp_path)

    assert any("derived group 'corpus' must declare source_paths" in error for error in errors)


def test_frontmatter_conflict_fails_against_manifest(tmp_path):
    _write(
        tmp_path / "docs" / "02_protocols" / "Runbook.md",
        """---
authority: proposal-only
---
# Runbook
""",
    )
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
""",
    )

    errors = check_doc_authority_manifest(tmp_path)

    assert any(
        "frontmatter authority 'proposal-only' conflicts with manifest authority 'canonical'"
        in error
        for error in errors
    )


def test_protected_transition_requires_one_record_per_path_with_approval_url(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
authority_transitions:
  - changed_paths:
      - docs/02_protocols/Runbook.md
    from: proposal-only
    to: canonical
    approval_evidence:
      type: bot
      url: not-a-url
      verdict: approved
""",
    )

    errors = check_doc_authority_manifest(tmp_path)

    assert any(
        "authority transition for docs/02_protocols/Runbook.md has invalid approval_evidence.type"
        in error
        for error in errors
    )
    assert any(
        "authority transition for docs/02_protocols/Runbook.md approval_evidence.url" in error
        and "must be a GitHub URL" in error
        for error in errors
    )


def test_derived_source_paths_must_resolve_to_canonical_docs(tmp_path):
    _write(tmp_path / "docs" / "plans" / "Draft.md")
    _write(tmp_path / "docs" / "LifeOS_Strategic_Corpus.md")
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: corpus
    authority: derived
    steward: Docs Steward
    paths:
      - docs/LifeOS_Strategic_Corpus.md
    source_paths:
      - docs/plans/*.md
  - id: plans
    authority: proposal-only
    steward: Docs Steward
    paths:
      - docs/plans/*.md
""",
    )

    errors = check_doc_authority_manifest(tmp_path)

    assert any(
        "source_paths pattern docs/plans/*.md matches docs/plans/Draft.md" in error
        and "must resolve only to canonical docs" in error
        for error in errors
    )


def test_manifest_schema_validation_fails_with_path(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    schema = tmp_path / "config" / "schemas" / "doc_authority_registry_v1.json"
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object",'
        '"required":["version"],"properties":{"version":{"const":1}}}',
        encoding="utf-8",
    )
    _manifest(
        tmp_path,
        """
schema: config/schemas/doc_authority_registry_v1.json
version: 2
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
""",
    )

    errors = check_doc_authority_manifest(tmp_path)

    assert any("schema violation at version" in error for error in errors)


def test_duplicate_transition_records_for_same_path_fail(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
authority_transitions:
  - changed_paths:
      - docs/02_protocols/Runbook.md
    from: proposal-only
    to: canonical
    approval_evidence:
      type: aa
      url: https://github.com/marcusglee11/LifeOS/issues/117#issuecomment-1
      verdict: approved
  - changed_paths:
      - docs/02_protocols/Runbook.md
    from: deferred
    to: canonical
    approval_evidence:
      type: aa
      url: https://github.com/marcusglee11/LifeOS/issues/117#issuecomment-2
      verdict: approved
""",
    )

    errors = check_doc_authority_manifest(tmp_path)

    assert any(
        "authority transition for docs/02_protocols/Runbook.md is duplicated" in error
        and "keep exactly one authority_transitions record" in error
        for error in errors
    )


def test_protected_manifest_change_requires_transition_record(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    previous = tmp_path / "previous.yaml"
    previous.write_text(
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
""",
        encoding="utf-8",
    )
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: derived
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
    source_paths:
      - docs/01_strategy/*.md
authority_transitions: []
""",
    )

    errors = check_doc_authority_manifest(tmp_path, previous_manifest_path=previous)

    assert any(
        "docs/02_protocols/Runbook.md: authority changed from canonical to derived" in error
        and "add one authority_transitions record" in error
        for error in errors
    )


def test_protected_manifest_change_requires_matching_transition_record(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    previous = tmp_path / "previous.yaml"
    previous.write_text(
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
""",
        encoding="utf-8",
    )
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: derived
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
    source_paths:
      - docs/01_strategy/*.md
authority_transitions:
  - changed_paths:
      - docs/02_protocols/Runbook.md
    from: canonical
    to: proposal-only
    approval_evidence:
      type: aa
      url: https://github.com/marcusglee11/LifeOS/issues/117#issuecomment-1
      verdict: approved
""",
    )

    errors = check_doc_authority_manifest(tmp_path, previous_manifest_path=previous)

    assert any(
        "authority_transitions record must match manifest change from canonical to derived" in error
        for error in errors
    )


def test_canonical_doc_change_requires_reconciliation_packet_or_exemption(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
    derived_surfaces:
      - docs/LifeOS_Strategic_Corpus.md
""",
    )

    errors = check_doc_authority_manifest(tmp_path, changed_paths=["docs/02_protocols/Runbook.md"])

    assert any(
        "missing reconciliation packet or non-semantic exemption" in error
        and "docs/02_protocols/Runbook.md" in error
        for error in errors
    )


def test_reconciliation_exemption_rejects_other_reason(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _write(
        tmp_path / "docs" / "10_meta" / "reconciliation_packets" / "2026-05-14-runbook.md",
        """---
reconciliation_exemption:
  reason: other
  affected_derived_surfaces: none
  semantic_change: false
---
# Exemption
""",
    )
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
    derived_surfaces:
      - docs/LifeOS_Strategic_Corpus.md
""",
    )

    errors = check_doc_authority_manifest(
        tmp_path,
        changed_paths=[
            "docs/02_protocols/Runbook.md",
            "docs/10_meta/reconciliation_packets/2026-05-14-runbook.md",
        ],
    )

    assert any("invalid reconciliation_exemption.reason 'other'" in error for error in errors)


def test_generated_refresh_only_exemption_requires_source_change_ref(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _write(
        tmp_path / "docs" / "10_meta" / "reconciliation_packets" / "2026-05-14-runbook.md",
        """---
reconciliation_exemption:
  reason: generated-refresh-only
  affected_derived_surfaces: none
  semantic_change: false
---
# Exemption
""",
    )
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
    derived_surfaces:
      - docs/LifeOS_Strategic_Corpus.md
""",
    )

    errors = check_doc_authority_manifest(
        tmp_path,
        changed_paths=[
            "docs/02_protocols/Runbook.md",
            "docs/10_meta/reconciliation_packets/2026-05-14-runbook.md",
        ],
    )

    assert any(
        "generated-refresh-only exemption requires source_change_ref" in error for error in errors
    )


def test_reconciliation_packet_must_cover_changed_canonical_path(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _write(tmp_path / "docs" / "03_runtime" / "Runtime.md")
    _write(
        tmp_path / "docs" / "10_meta" / "reconciliation_packets" / "2026-05-14-runbook.md",
        """---
changed_canonical_paths:
  - docs/03_runtime/Runtime.md
affected_derived_surfaces:
  - docs/LifeOS_Strategic_Corpus.md
regeneration_required: false
authority_class_changes: []
post_merge_verification_commands: []
not_affected_reason: No semantic changes to derived surfaces.
---
# Packet
""",
    )
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
    derived_surfaces:
      - docs/LifeOS_Strategic_Corpus.md
  - id: runtime
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/03_runtime/*.md
    derived_surfaces:
      - docs/LifeOS_Strategic_Corpus.md
""",
    )

    errors = check_doc_authority_manifest(
        tmp_path,
        changed_paths=[
            "docs/02_protocols/Runbook.md",
            "docs/10_meta/reconciliation_packets/2026-05-14-runbook.md",
        ],
    )

    assert any("reconciliation packet present but stale/irrelevant" in error for error in errors)


def test_valid_reconciliation_packet_passes(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _write(
        tmp_path / "docs" / "10_meta" / "reconciliation_packets" / "2026-05-14-runbook.md",
        """---
changed_canonical_paths:
  - docs/02_protocols/Runbook.md
affected_derived_surfaces:
  - docs/LifeOS_Strategic_Corpus.md
regeneration_required: false
authority_class_changes: []
post_merge_verification_commands: []
not_affected_reason: No semantic changes to derived surfaces.
---
# Packet
""",
    )
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
    derived_surfaces:
      - docs/LifeOS_Strategic_Corpus.md
  - id: meta
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/10_meta/**/*.md
""",
    )

    assert (
        check_doc_authority_manifest(
            tmp_path,
            changed_paths=[
                "docs/02_protocols/Runbook.md",
                "docs/10_meta/reconciliation_packets/2026-05-14-runbook.md",
            ],
        )
        == []
    )


def test_valid_manifest_passes(tmp_path):
    _write(tmp_path / "docs" / "02_protocols" / "Runbook.md")
    _write(tmp_path / "docs" / "LifeOS_Strategic_Corpus.md")
    _manifest(
        tmp_path,
        """
version: 1
doc_groups:
  - id: protocols
    authority: canonical
    steward: Docs Steward
    paths:
      - docs/02_protocols/*.md
    derived_surfaces:
      - docs/LifeOS_Strategic_Corpus.md
  - id: corpus
    authority: derived
    steward: Docs Steward
    paths:
      - docs/LifeOS_Strategic_Corpus.md
    source_paths:
      - docs/02_protocols/*.md
""",
    )

    assert check_doc_authority_manifest(tmp_path) == []
