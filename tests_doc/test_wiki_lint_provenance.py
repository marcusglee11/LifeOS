from __future__ import annotations

from pathlib import Path

from doc_steward.wiki_lint_validator import check_wiki_lint


def _write_page(root: Path, extra_frontmatter: str) -> None:
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "source.md").write_text("# Source\n", encoding="utf-8")
    wiki = root / ".context" / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "SCHEMA.md").write_text(
        "| File | Purpose |\n|------|---------|\n| `home.md` | Home |\n",
        encoding="utf-8",
    )
    (wiki / "home.md").write_text(
        f"""---
source_docs:
  - docs/source.md
source_commit_max: abc123
authority: derived
page_class: evergreen
concepts:
  - test
{extra_frontmatter}---

## Summary

Test.

## Key Relationships

Test.

## Authority Note

Test.

## Current Truth

Test.

## Open Questions

None.
""",
        encoding="utf-8",
    )


def test_wiki_lint_requires_generated_provenance(tmp_path: Path, monkeypatch) -> None:
    _write_page(
        tmp_path,
        "derived_edit_mode: generated\n"
        "source_command: python3 scripts/wiki/refresh_wiki.py\n"
        "source_change_ref: pending\n",
    )
    monkeypatch.setattr(
        "doc_steward.wiki_lint_validator._compute_source_commit_max",
        lambda sources, cwd: "abc123",
    )

    errors = check_wiki_lint(str(tmp_path))

    assert any("source_change_ref" in error and "pending" in error for error in errors)


def test_wiki_lint_requires_emergency_follow_up_and_approval(tmp_path: Path, monkeypatch) -> None:
    _write_page(
        tmp_path,
        "derived_edit_mode: emergency-manual-repair\n"
        "reason: generator unavailable\n"
        "follow_up_required: true\n"
        "follow_up_issue: pending\n"
        "approval_evidence: pending\n",
    )
    monkeypatch.setattr(
        "doc_steward.wiki_lint_validator._compute_source_commit_max",
        lambda sources, cwd: "abc123",
    )

    errors = check_wiki_lint(str(tmp_path))

    assert any("follow_up_issue" in error and "pending" in error for error in errors)
    assert any("approval_evidence" in error and "pending" in error for error in errors)


def test_wiki_lint_accepts_generated_provenance(tmp_path: Path, monkeypatch) -> None:
    _write_page(
        tmp_path,
        "derived_edit_mode: generated\n"
        "source_command: python3 scripts/wiki/refresh_wiki.py\n"
        "source_change_ref: https://github.com/marcusglee11/LifeOS/issues/120\n",
    )
    monkeypatch.setattr(
        "doc_steward.wiki_lint_validator._compute_source_commit_max",
        lambda sources, cwd: "abc123",
    )

    errors = check_wiki_lint(str(tmp_path))

    assert errors == []
