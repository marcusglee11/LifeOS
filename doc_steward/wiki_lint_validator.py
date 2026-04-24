"""
Wiki lint validator for .context/wiki/ layer.

Checks:
- Required frontmatter fields on all wiki pages (source_docs, source_commit_max, authority,
  page_class, concepts)
- Required frontmatter field VALUES: authority must equal "derived"; page_class must be
  "evergreen" or "status"; concepts must be non-empty; source_docs must be non-empty
- All source_docs paths resolve to files under docs/ (no directories, no non-docs/ paths)
- source_commit_max matches actual newest git commit among declared sources
- Required body sections present in ORDER: Summary, Key Relationships, Authority Note,
  Current Truth, Open Questions
- All pages listed in SCHEMA.md page index exist; no orphaned pages
"""
import re
import subprocess
from pathlib import Path


_REQUIRED_FRONTMATTER = {"source_docs", "source_commit_max", "authority", "page_class", "concepts"}
_REQUIRED_SECTIONS = (
    "## Summary",
    "## Key Relationships",
    "## Authority Note",
    "## Current Truth",
    "## Open Questions",
)
_VALID_PAGE_CLASSES = frozenset({"evergreen", "status"})
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


def _parse_field(text: str, field: str) -> str | None:
    """Extract a scalar frontmatter field value."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{field}:"):
            val = stripped.split(":", 1)[1].strip()
            return val if val else None
    return None


def _parse_list_field(text: str, field: str) -> list[str]:
    """Extract a YAML list field from frontmatter."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return []
    fm = m.group(1)
    in_list = False
    items: list[str] = []
    for line in fm.splitlines():
        if line.strip().startswith(f"{field}:"):
            in_list = True
            continue
        if in_list:
            if line.startswith("  - "):
                items.append(line.strip().lstrip("- ").strip())
            elif line and not line.startswith(" "):
                break
    return items


def _validate_frontmatter_values(page_name: str, text: str) -> list[str]:
    """Validate frontmatter field values, not just presence."""
    errors = []
    authority = _parse_field(text, "authority")
    if authority != "derived":
        errors.append(f"{page_name}: authority must be 'derived', got '{authority}'")
    page_class = _parse_field(text, "page_class")
    if page_class not in _VALID_PAGE_CLASSES:
        errors.append(
            f"{page_name}: page_class must be 'evergreen' or 'status', got '{page_class}'"
        )
    if not _parse_list_field(text, "concepts"):
        errors.append(f"{page_name}: concepts must be a non-empty list")
    if not _parse_source_docs(text):
        errors.append(f"{page_name}: source_docs must be a non-empty list")
    return errors


def _compute_source_commit_max(source_docs: list[str], cwd: Path) -> str | None:
    """Return the git SHA of the newest commit among source_docs files."""
    if not source_docs:
        return None
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--"] + source_docs,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        sha = result.stdout.strip()
        return sha if sha else None
    except (OSError, subprocess.SubprocessError):
        return None


def _validate_source_paths(page_name: str, source_docs: list[str], repo_root: Path) -> list[str]:
    """Validate all source_docs are files under docs/. No directories, no non-docs/ paths."""
    errors = []
    for src in source_docs:
        if not src.startswith("docs/"):
            errors.append(
                f"{page_name}: source_docs '{src}' is not under docs/ — non-docs sources forbidden"
            )
            continue
        abs_path = repo_root / src
        if abs_path.is_dir():
            errors.append(f"{page_name}: source_docs '{src}' is a directory, not a file")
        elif not abs_path.exists():
            errors.append(f"{page_name}: source_docs '{src}' not found")
    return errors


def _validate_source_commit_max(
    page_name: str, text: str, source_docs: list[str], repo_root: Path
) -> list[str]:
    """Validate source_commit_max is present and equals actual newest commit among sources."""
    errors = []
    stored = _parse_field(text, "source_commit_max")
    if not stored:
        errors.append(f"{page_name}: missing source_commit_max")
        return errors
    # Only validate against valid docs/ sources (non-docs/ sources already caught above)
    valid_sources = [s for s in source_docs if s.startswith("docs/") and (repo_root / s).is_file()]
    if not valid_sources:
        return errors
    expected = _compute_source_commit_max(valid_sources, repo_root)
    if expected and stored != expected:
        errors.append(
            f"{page_name}: stale source_commit_max (stored={stored[:8]}, expected={expected[:8]})"
        )
    return errors


def _validate_required_sections(page_name: str, text: str) -> list[str]:
    """Check that required body sections exist in order."""
    errors = []
    positions = [text.find(s) for s in _REQUIRED_SECTIONS]
    for section, pos in zip(_REQUIRED_SECTIONS, positions):
        if pos == -1:
            errors.append(f"{page_name}: missing required section '{section}'")
    if errors:
        return errors
    for i in range(len(positions) - 1):
        if positions[i] >= positions[i + 1]:
            errors.append(
                f"{page_name}: section order violation — '{_REQUIRED_SECTIONS[i]}'"
                f" must appear before '{_REQUIRED_SECTIONS[i + 1]}'"
            )
    return errors


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

        # Validate frontmatter values
        errors.extend(_validate_frontmatter_values(page.name, text))

        source_docs = _parse_source_docs(text)

        # Validate source_docs paths (docs/** files only, no directories)
        errors.extend(_validate_source_paths(page.name, source_docs, repo_path))

        # Validate source_commit_max freshness
        errors.extend(_validate_source_commit_max(page.name, text, source_docs, repo_path))

        # Validate required body sections
        errors.extend(_validate_required_sections(page.name, text))

    return errors
