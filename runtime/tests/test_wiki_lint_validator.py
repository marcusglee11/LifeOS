"""Tests for doc_steward.wiki_lint_validator."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from doc_steward.wiki_lint_validator import check_wiki_lint


_MINIMAL_SCHEMA = """\
---
type: schema
version: "1.0"
---

# Wiki Schema

## Page Index

| File | Topic |
|------|-------|
| `alpha.md` | Alpha topic |
| `beta.md` | Beta topic |
"""

_VALID_PAGE = """\
---
source_docs:
  - docs/some_doc.md
source_commit_max: abc1234
authority: derived
page_class: evergreen
concepts:
  - alpha
---

# Alpha

## Summary

Alpha is a thing.

## Key Relationships

None.

## Authority Note

Canonical source: `docs/some_doc.md`. That document wins.

## Current Truth

Active.

## Open Questions

None.
"""


@pytest.fixture()
def wiki_root(tmp_path: Path) -> tuple[Path, Path, str]:
    """Create a minimal repo root with wiki dir, a real source doc, and a real commit SHA."""
    wiki_dir = tmp_path / ".context" / "wiki"
    wiki_dir.mkdir(parents=True)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "some_doc.md").write_text("# Source\n")
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "add", "docs/some_doc.md"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True
    )
    sha_result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    )
    real_sha = sha_result.stdout.strip()
    return tmp_path, wiki_dir, real_sha


def test_missing_wiki_dir(tmp_path: Path) -> None:
    errors = check_wiki_lint(str(tmp_path))
    assert any("Wiki directory missing" in e for e in errors)


def test_missing_schema(tmp_path: Path) -> None:
    (tmp_path / ".context" / "wiki").mkdir(parents=True)
    errors = check_wiki_lint(str(tmp_path))
    assert any("SCHEMA.md missing" in e for e in errors)


def test_page_in_index_but_missing(wiki_root: tuple[Path, Path, str]) -> None:
    root, wiki_dir, _ = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_MINIMAL_SCHEMA)
    errors = check_wiki_lint(str(root))
    assert any("alpha.md" in e for e in errors)
    assert any("beta.md" in e for e in errors)


def test_orphaned_page(wiki_root: tuple[Path, Path, str]) -> None:
    root, wiki_dir, sha = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_MINIMAL_SCHEMA)
    page = _VALID_PAGE.replace("abc1234", sha)
    (wiki_dir / "alpha.md").write_text(page)
    (wiki_dir / "beta.md").write_text(page)
    (wiki_dir / "orphan.md").write_text(page)
    errors = check_wiki_lint(str(root))
    assert any("orphan.md" in e for e in errors)


def test_missing_frontmatter_field(wiki_root: tuple[Path, Path, str]) -> None:
    root, wiki_dir, sha = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_MINIMAL_SCHEMA)
    bad_page = (
        f"---\n"
        f"source_docs:\n  - docs/some_doc.md\n"
        f"source_commit_max: {sha}\n"
        f"authority: derived\n"
        f"page_class: evergreen\n"
        f"---\n\n## Summary\n\nNo concepts field.\n"
    )
    (wiki_dir / "alpha.md").write_text(bad_page)
    (wiki_dir / "beta.md").write_text(_VALID_PAGE.replace("abc1234", sha))
    errors = check_wiki_lint(str(root))
    assert any("alpha.md" in e and "concepts" in e for e in errors)


def test_source_doc_not_found(wiki_root: tuple[Path, Path, str]) -> None:
    root, wiki_dir, sha = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_MINIMAL_SCHEMA)
    page_missing_source = _VALID_PAGE.replace(
        "docs/some_doc.md", "docs/nonexistent.md"
    ).replace("abc1234", sha)
    (wiki_dir / "alpha.md").write_text(page_missing_source)
    (wiki_dir / "beta.md").write_text(_VALID_PAGE.replace("abc1234", sha))
    errors = check_wiki_lint(str(root))
    assert any("nonexistent.md" in e for e in errors)


def test_valid_wiki_passes(wiki_root: tuple[Path, Path, str]) -> None:
    root, wiki_dir, sha = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_MINIMAL_SCHEMA)
    page = _VALID_PAGE.replace("abc1234", sha)
    (wiki_dir / "alpha.md").write_text(page)
    (wiki_dir / "beta.md").write_text(page)
    errors = check_wiki_lint(str(root))
    assert errors == [], f"Expected no errors, got: {errors}"


# ── NEW TESTS (added in wiki remediation) ─────────────────────────────────────

def _schema_with_pages(*page_names: str) -> str:
    """Return a minimal SCHEMA.md that indexes the given page names in a proper table."""
    rows = "\n".join(f"| `{name}` | Test |" for name in page_names)
    return (
        '---\ntype: schema\nversion: "2.0"\n---\n\n# Wiki Schema\n\n'
        f"## Page Index\n\n| File | Topic |\n|------|-------|\n{rows}\n"
    )


def _compliant_page(sha: str) -> str:
    """Return a fully-compliant v2.0 wiki page for use in tests."""
    return (
        f"---\n"
        f"source_docs:\n"
        f"  - docs/some_doc.md\n"
        f"source_commit_max: {sha}\n"
        f"authority: derived\n"
        f"page_class: evergreen\n"
        f"concepts:\n"
        f"  - test\n"
        f"---\n\n"
        f"## Summary\n\nTest summary.\n\n"
        f"## Key Relationships\n\nNone.\n\n"
        f"## Authority Note\n\nCanonical source: `docs/some_doc.md`. That document wins.\n\n"
        f"## Current Truth\n\nTest truth.\n\n"
        f"## Open Questions\n\nNone.\n"
    )


def test_non_docs_source_rejected(wiki_root):
    """source_docs path outside docs/ must be an error."""
    tmp_path, wiki_dir, real_sha = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_schema_with_pages("bad_source.md"))
    content = _compliant_page(real_sha).replace(
        "  - docs/some_doc.md", "  - config/agent_roles/coo.md"
    )
    (wiki_dir / "bad_source.md").write_text(content)
    errors = check_wiki_lint(str(tmp_path))
    assert any("bad_source.md" in e and "not under docs/" in e for e in errors)


def test_directory_source_rejected(wiki_root):
    """source_docs pointing to a docs/ directory must be an error."""
    tmp_path, wiki_dir, real_sha = wiki_root
    (tmp_path / "docs" / "subdir").mkdir(exist_ok=True)
    (wiki_dir / "SCHEMA.md").write_text(_schema_with_pages("dir_source.md"))
    content = _compliant_page(real_sha).replace(
        "  - docs/some_doc.md", "  - docs/subdir"
    )
    (wiki_dir / "dir_source.md").write_text(content)
    errors = check_wiki_lint(str(tmp_path))
    assert any("dir_source.md" in e and "directory" in e.lower() for e in errors)


def test_stale_source_commit_max_detected(wiki_root):
    """source_commit_max that doesn't match actual newest commit must be an error."""
    tmp_path, wiki_dir, real_sha = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_schema_with_pages("stale.md"))
    stale_sha = "a" * 40  # guaranteed to differ from real_sha
    content = _compliant_page(real_sha).replace(real_sha, stale_sha)
    (wiki_dir / "stale.md").write_text(content)
    errors = check_wiki_lint(str(tmp_path))
    assert any("stale.md" in e and "stale" in e.lower() for e in errors)


def test_missing_authority_note_section_detected(wiki_root):
    """Page missing ## Authority Note section must be an error."""
    tmp_path, wiki_dir, real_sha = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_schema_with_pages("no_auth.md"))
    content = _compliant_page(real_sha).replace(
        "## Authority Note\n\nCanonical source: `docs/some_doc.md`. That document wins.\n\n",
        "",
    )
    (wiki_dir / "no_auth.md").write_text(content)
    errors = check_wiki_lint(str(tmp_path))
    assert any("no_auth.md" in e and "Authority Note" in e for e in errors)


def test_missing_current_truth_section_detected(wiki_root):
    """Page missing ## Current Truth section must be an error."""
    tmp_path, wiki_dir, real_sha = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_schema_with_pages("no_truth.md"))
    content = _compliant_page(real_sha).replace("## Current Truth\n\nTest truth.\n\n", "")
    (wiki_dir / "no_truth.md").write_text(content)
    errors = check_wiki_lint(str(tmp_path))
    assert any("no_truth.md" in e and "Current Truth" in e for e in errors)


def test_compliant_page_passes_all_new_checks(wiki_root):
    """A fully-compliant page must produce no errors from new checks."""
    tmp_path, wiki_dir, real_sha = wiki_root
    (wiki_dir / "SCHEMA.md").write_text(_schema_with_pages("compliant.md"))
    (wiki_dir / "compliant.md").write_text(_compliant_page(real_sha))
    errors = check_wiki_lint(str(tmp_path))
    assert not any("compliant.md" in e for e in errors)
