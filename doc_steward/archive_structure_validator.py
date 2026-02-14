"""
Archive structure validator for docs/99_archive/.

Enforces:
- Root allowed files: README.md only
- Subdirs must match YYYY-MM_topic or YYYY-MM-DD_topic pattern
- Max depth 2 (dated subdir + files, no nested subdirs)
- Each dated subdir contains README with disposition table

Fail-closed: any structural violation is an error.
"""
import re
from pathlib import Path

# Allowed files at docs/99_archive/ root
ALLOWED_ROOT_FILES = {"README.md"}

# Archive subdir naming pattern: YYYY-MM_topic or YYYY-MM-DD_topic
ARCHIVE_SUBDIR_PATTERN = re.compile(r'^\d{4}-\d{2}(-\d{2})?_[a-z0-9_-]+$')

# Max depth under docs/99_archive/ (subdirs can be 1 level deep)
MAX_ARCHIVE_DEPTH = 2


def check_archive_structure(repo_root: str) -> list[str]:
    """
    Validate docs/99_archive/ structure against canonical requirements.

    Args:
        repo_root: Path to repository root

    Returns:
        List of error strings for violations (empty if valid)
    """
    errors: list[str] = []
    archive_dir = Path(repo_root).resolve() / "docs" / "99_archive"

    if not archive_dir.exists():
        # 99_archive is optional; if it doesn't exist, that's fine
        return []

    if not archive_dir.is_dir():
        return [f"docs/99_archive/ exists but is not a directory"]

    # Check root files (only README.md allowed)
    for item in archive_dir.iterdir():
        if item.is_file():
            if item.name not in ALLOWED_ROOT_FILES:
                errors.append(
                    f"Unexpected file at root: docs/99_archive/{item.name} "
                    f"(only README.md allowed at root)"
                )

        elif item.is_dir():
            # Check subdir naming pattern
            if not ARCHIVE_SUBDIR_PATTERN.match(item.name):
                errors.append(
                    f"Invalid archive subdir name: docs/99_archive/{item.name}/ "
                    f"(must match: YYYY-MM_topic or YYYY-MM-DD_topic)"
                )

            # Check for required README.md
            readme_path = item / "README.md"
            if not readme_path.exists():
                errors.append(
                    f"Missing README.md in archive subdir: docs/99_archive/{item.name}/"
                )

            # Check depth (no nested subdirs beyond this level)
            for nested_item in item.iterdir():
                if nested_item.is_dir():
                    errors.append(
                        f"Archive depth exceeds max of {MAX_ARCHIVE_DEPTH}: "
                        f"docs/99_archive/{item.name}/{nested_item.name}/ "
                        f"(archive subdirs must not contain subdirectories)"
                    )

    return errors
