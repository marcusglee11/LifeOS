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
last_updated: abc1234
concepts:
  - alpha
---

# Alpha

## Summary

Alpha is a thing.

## Key Relationships

None.

## Current State

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
    bad_page = f"---\nsource_docs:\n  - docs/some_doc.md\nlast_updated: {sha}\n---\n\n# No concepts\n"
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
