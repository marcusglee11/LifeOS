"""
Global archive link ban validator.

Enforces: No active docs under docs/ may link into any /archive/ paths or docs/99_archive/.

Exceptions only:
- archive READMEs linking within their own dated subdir
- directory READMEs linking to archive README(s) only (not individual files)

Fail-closed: any violation is an error.
"""
import re
from pathlib import Path

# Pattern to match markdown links: [text](url)
LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def check_global_archive_link_ban(repo_root: str) -> list[str]:
    """
    Validate that active docs do not link into any archive paths.

    Scans all docs under docs/ and fails if any link references:
    - Any path containing /archive/
    - docs/99_archive/

    Args:
        repo_root: Path to repository root

    Returns:
        List of error strings for violations (empty if valid)
    """
    errors: list[str] = []
    repo_path = Path(repo_root).resolve()
    docs_path = repo_path / "docs"

    if not docs_path.exists():
        return []  # No docs directory, nothing to check

    # Scan all markdown files in docs/
    for md_file in docs_path.rglob("*.md"):
        rel_path = md_file.relative_to(repo_path)

        # Skip files that are themselves inside any archive
        if _is_in_archive(md_file, docs_path):
            continue

        # Determine if this file has special privileges
        is_directory_readme = md_file.name == "README.md"
        parent_dir = md_file.parent

        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            # Skip files we can't read (don't fail on encoding issues)
            continue

        # Find all markdown links
        for match in LINK_PATTERN.finditer(content):
            link_text = match.group(1)
            link_url = match.group(2)

            # Skip external links
            if link_url.startswith("http://") or link_url.startswith("https://"):
                continue

            # Remove fragment identifier
            link_url_clean = link_url.split("#")[0]

            # Resolve relative to the markdown file's directory
            try:
                link_target = (md_file.parent / link_url_clean).resolve()
            except Exception:
                # Skip malformed paths
                continue

            # Check if link points into any archive
            if _is_in_archive(link_target, docs_path):
                # Exception: Directory README can link to archive README only
                if is_directory_readme:
                    # Check if link points to an archive README in the same directory's archive
                    archive_parent = parent_dir / "archive"
                    if link_target.name == "README.md":
                        # Check if it's linking to immediate child archive README
                        try:
                            rel_to_archive = link_target.parent.relative_to(archive_parent)
                            # If rel_to_archive has no parts, it's directly under archive/
                            if len(rel_to_archive.parts) <= 1:
                                # Allowed: directory README linking to archive README
                                continue
                        except ValueError:
                            # Not under this directory's archive
                            pass

                    # Also allow linking to docs/99_archive README directly
                    if link_target == docs_path / "99_archive" / "README.md":
                        continue

                # If we reach here, it's a violation
                errors.append(
                    f"{rel_path}:{match.start()} links to archive: {link_url} "
                    f"(active docs must not link to archived files)"
                )

    return errors


def _is_in_archive(path: Path, docs_path: Path) -> bool:
    """
    Check if a path is inside any archive directory.

    Args:
        path: Path to check
        docs_path: Root docs directory

    Returns:
        True if path is inside any /archive/ or docs/99_archive/
    """
    # Check if path is under docs/99_archive/
    try:
        path.relative_to(docs_path / "99_archive")
        return True
    except ValueError:
        pass

    # Check if any parent directory is named "archive"
    for parent in path.parents:
        if parent.name == "archive" and parent.parent != docs_path:
            # This is an archive subdir (not docs/99_archive itself)
            return True
        if parent == docs_path:
            # Reached docs root without finding archive
            break

    return False
