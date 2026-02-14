"""
Protocols structure validator for docs/02_protocols/.

Enforces:
- Required subdirs: templates/, schemas/, archive/
- Required file: ARTEFACT_INDEX.json
- Max depth for archive/ = 2 and naming per §3.0
- Root .md files only if referenced in ARTEFACT_INDEX (via artefact-index validator)

Fail-closed: any unexpected directory structure is an error.
"""
import re
from pathlib import Path

# Required subdirectories (exact)
REQUIRED_SUBDIRS = {"templates", "schemas", "archive"}

# Required files at root
REQUIRED_FILES = {"ARTEFACT_INDEX.json"}

# Archive subdir naming pattern: YYYY-MM_topic or YYYY-MM-DD_topic
ARCHIVE_SUBDIR_PATTERN = re.compile(r'^\d{4}-\d{2}(-\d{2})?_[a-z0-9_-]+$')

# Max depth under archive/ (subdirs can be 1 level deep)
MAX_ARCHIVE_DEPTH = 2


def check_protocols_structure(repo_root: str) -> list[str]:
    """
    Validate docs/02_protocols/ structure against canonical requirements.

    Args:
        repo_root: Path to repository root

    Returns:
        List of error strings for violations (empty if valid)
    """
    errors: list[str] = []
    protocols_dir = Path(repo_root).resolve() / "docs" / "02_protocols"

    if not protocols_dir.exists():
        return [f"docs/02_protocols/ does not exist"]

    if not protocols_dir.is_dir():
        return [f"docs/02_protocols/ is not a directory"]

    # Check for required files
    for required_file in REQUIRED_FILES:
        file_path = protocols_dir / required_file
        if not file_path.exists():
            errors.append(f"Missing required file: docs/02_protocols/{required_file}")

    # Check for required subdirectories
    existing_subdirs = {item.name for item in protocols_dir.iterdir() if item.is_dir()}
    for required_subdir in REQUIRED_SUBDIRS:
        if required_subdir not in existing_subdirs:
            errors.append(
                f"Missing required subdirectory: docs/02_protocols/{required_subdir}/"
            )

    # Validate archive/ subdirectory structure
    archive_dir = protocols_dir / "archive"
    if archive_dir.exists() and archive_dir.is_dir():
        errors.extend(_validate_archive_structure(archive_dir, "docs/02_protocols/archive"))

    return errors


def _validate_archive_structure(archive_dir: Path, context_path: str) -> list[str]:
    """
    Validate archive subdirectory structure: max depth 2, naming pattern, README requirement.

    Args:
        archive_dir: Path to archive directory
        context_path: Human-readable path for error messages

    Returns:
        List of error strings
    """
    errors: list[str] = []

    for item in archive_dir.iterdir():
        if item.is_dir():
            # Check naming pattern
            if not ARCHIVE_SUBDIR_PATTERN.match(item.name):
                errors.append(
                    f"Invalid archive subdir name: {context_path}/{item.name}/ "
                    f"(must match: YYYY-MM_topic or YYYY-MM-DD_topic)"
                )

            # Check for required README.md
            readme_path = item / "README.md"
            if not readme_path.exists():
                errors.append(
                    f"Missing README.md in archive subdir: {context_path}/{item.name}/"
                )

            # Check depth (no nested subdirs beyond this level)
            for nested_item in item.iterdir():
                if nested_item.is_dir():
                    errors.append(
                        f"Archive depth exceeds max of {MAX_ARCHIVE_DEPTH}: "
                        f"{context_path}/{item.name}/{nested_item.name}/ "
                        f"(archive subdirs must not contain subdirectories)"
                    )

    return errors
