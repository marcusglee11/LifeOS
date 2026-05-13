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
