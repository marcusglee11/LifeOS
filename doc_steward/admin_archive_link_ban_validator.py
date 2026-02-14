"""
Admin archive link ban validator.

Enforces: No inbound links to docs/11_admin/archive/... from active docs.

Allowed exceptions:
- Links within archive/**/README.md files (to archived files in same subdir)
- Link from docs/11_admin/README.md to archive README only (not individual files)
"""
import re
from pathlib import Path

# Pattern to match markdown links: [text](url)
LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def check_admin_archive_link_ban(repo_root: str) -> list[str]:
    """
    Validate that active docs do not link into docs/11_admin/archive/.

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

    admin_archive_path = docs_path / "11_admin" / "archive"

    # Scan all markdown files in docs/
    for md_file in docs_path.rglob("*.md"):
        rel_path = md_file.relative_to(repo_path)

        # Skip files that are themselves inside the archive (archived files can link freely)
        try:
            md_file.relative_to(admin_archive_path)
            # File is inside archive, skip it (archived files can link to other archived files)
            continue
        except ValueError:
            # File is not in archive, continue checking
            pass

        # Determine if this file is allowed to link to archive
        is_admin_readme = (
            md_file.parent == docs_path / "11_admin"
            and md_file.name == "README.md"
        )

        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            # Skip files we can't read (don't fail on encoding issues)
            continue

        # Find all markdown links
        for match in LINK_PATTERN.finditer(content):
            link_text = match.group(1)
            link_url = match.group(2)

            # Normalize and resolve link target
            if link_url.startswith("http://") or link_url.startswith("https://"):
                # External link, skip
                continue

            # Remove fragment identifier
            link_url_clean = link_url.split("#")[0]

            # Resolve relative to the markdown file's directory
            try:
                link_target = (md_file.parent / link_url_clean).resolve()
            except Exception:
                # Skip malformed paths
                continue

            # Check if link points into archive
            try:
                # Check if the link target is under the archive directory
                link_target.relative_to(admin_archive_path)
                # If we get here, the link IS pointing into archive

                # Exception: Admin README can link to archive README only
                if is_admin_readme:
                    # Check if link points to an archive README
                    if link_target.name == "README.md" and link_target.parent.parent == admin_archive_path:
                        # Link to archive subdir README, allowed
                        continue
                    else:
                        # Link to individual archived file, NOT allowed
                        pass

                # If we reach here, it's a violation (active doc linking to archive)
                errors.append(
                    f"{rel_path}:{match.start()} links to archive: {link_url} "
                    f"(active docs must not link to archived files)"
                )

            except ValueError:
                # link_target is not under admin_archive_path, OK
                continue

    return errors
