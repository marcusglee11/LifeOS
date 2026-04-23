"""
Wiki lint validator for .context/wiki/ layer.

Checks:
- Required frontmatter fields on all wiki pages (source_docs, last_updated, concepts)
- All source_docs paths resolve to real files
- No page is stale (source doc mtime newer than page mtime when last_updated is unknown)
- All pages listed in SCHEMA.md page index exist; no orphaned pages
"""
import re
import subprocess
from pathlib import Path


_REQUIRED_FRONTMATTER = {"source_docs", "last_updated", "concepts"}
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_FIELD_RE = re.compile(r"^(\w+):", re.MULTILINE)
_PAGE_TABLE_RE = re.compile(r"`([a-z0-9_-]+\.md)`")


def _parse_frontmatter_fields(text: str) -> set[str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return set()
    return set(_FIELD_RE.findall(m.group(1)))


def _parse_source_docs(text: str) -> list[str]:
    """Extract source_docs list entries from frontmatter."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return []
    fm = m.group(1)
    in_source = False
    paths: list[str] = []
    for line in fm.splitlines():
        if line.strip().startswith("source_docs:"):
            in_source = True
            continue
        if in_source:
            if line.startswith("  - "):
                paths.append(line.strip().lstrip("- ").strip())
            elif line and not line.startswith(" "):
                break
    return paths


def _parse_last_updated(text: str) -> str | None:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("last_updated:"):
            val = stripped.split(":", 1)[1].strip()
            return val if val else None
    return None


def _commit_exists(sha: str, cwd: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "cat-file", "-t", sha],
            capture_output=True, text=True, timeout=5, cwd=cwd
        )
        return result.returncode == 0 and result.stdout.strip() == "commit"
    except Exception:
        return False


def _source_newer_than_page(source_path: Path, page_path: Path) -> bool:
    try:
        return source_path.stat().st_mtime > page_path.stat().st_mtime
    except OSError:
        return False


def _index_page_names(schema_text: str) -> set[str]:
    """Extract page filenames from the SCHEMA.md page index table."""
    names: set[str] = set()
    in_table = False
    for line in schema_text.splitlines():
        if "| File |" in line or "|------|" in line:
            in_table = True
            continue
        if in_table:
            if not line.strip().startswith("|"):
                in_table = False
                continue
            matches = _PAGE_TABLE_RE.findall(line)
            names.update(matches)
    return names


def check_wiki_lint(repo_root: str) -> list[str]:
    """
    Validate the .context/wiki/ layer.

    Returns:
        List of error strings (empty = passed).
    """
    errors: list[str] = []
    repo_path = Path(repo_root).resolve()
    wiki_dir = repo_path / ".context" / "wiki"

    if not wiki_dir.exists():
        errors.append(f"Wiki directory missing: {wiki_dir}")
        return errors

    schema_file = wiki_dir / "SCHEMA.md"
    if not schema_file.exists():
        errors.append(f"SCHEMA.md missing: {schema_file}")
        return errors

    schema_text = schema_file.read_text(encoding="utf-8")
    indexed_names = _index_page_names(schema_text)

    # Collect actual wiki pages (exclude SCHEMA.md and _pending_diff.patch)
    wiki_pages = [
        p for p in wiki_dir.glob("*.md")
        if p.name != "SCHEMA.md"
    ]
    wiki_page_names = {p.name for p in wiki_pages}

    # Check for pages in index that don't exist
    for name in indexed_names:
        if name not in wiki_page_names:
            errors.append(f"Page listed in SCHEMA.md index but missing: {name}")

    # Check for orphaned pages (exist but not in index)
    for name in wiki_page_names:
        if name not in indexed_names:
            errors.append(f"Orphaned wiki page (not in SCHEMA.md index): {name}")

    # Validate each existing page
    for page in wiki_pages:
        text = page.read_text(encoding="utf-8")
        fields = _parse_frontmatter_fields(text)

        # Required frontmatter fields
        missing = _REQUIRED_FRONTMATTER - fields
        if missing:
            errors.append(
                f"{page.name}: missing frontmatter fields: {', '.join(sorted(missing))}"
            )
            continue

        # source_docs resolve to real files
        source_docs = _parse_source_docs(text)
        for rel_path in source_docs:
            abs_path = repo_path / rel_path
            if not abs_path.exists():
                errors.append(
                    f"{page.name}: source_doc not found: {rel_path}"
                )

        # Staleness: if last_updated is a known commit SHA, verify it exists;
        # if unknown/placeholder, fall back to mtime comparison
        last_updated = _parse_last_updated(text)
        if last_updated and len(last_updated) >= 7:
            if not _commit_exists(last_updated, repo_path):
                errors.append(
                    f"{page.name}: last_updated SHA not found in repo: {last_updated}"
                )
        else:
            # Fallback: check if any source doc is newer than the page
            for rel_path in source_docs:
                abs_path = repo_path / rel_path
                if abs_path.exists() and _source_newer_than_page(abs_path, page):
                    errors.append(
                        f"{page.name}: stale — source doc is newer: {rel_path}"
                    )

    return errors
