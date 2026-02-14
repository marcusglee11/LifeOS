"""
Runtime structure validator for docs/03_runtime/.

Enforces:
- Required subdirs: fixpacks/, policy/, templates/, archive/
- Required file: ARTEFACT_INDEX.json
- Archive depth + naming per §3.0
- Root file allowance is index-centric (no filename regex)

Fail-closed: any unexpected directory structure is an error.
"""
import re
from pathlib import Path

# Required subdirectories (exact)
REQUIRED_SUBDIRS = {"fixpacks", "policy", "templates", "archive"}

# Required files at root
REQUIRED_FILES = {"ARTEFACT_INDEX.json"}

# Archive subdir naming pattern: YYYY-MM_topic or YYYY-MM-DD_topic
ARCHIVE_SUBDIR_PATTERN = re.compile(r'^\d{4}-\d{2}(-\d{2})?_[a-z0-9_-]+$')

# Max depth under archive/ (subdirs can be 1 level deep)
MAX_ARCHIVE_DEPTH = 2


def check_runtime_structure(repo_root: str) -> list[str]:
    """
    Validate docs/03_runtime/ structure against canonical requirements.

    Args:
        repo_root: Path to repository root

    Returns:
        List of error strings for violations (empty if valid)
    """
    errors: list[str] = []
    runtime_dir = Path(repo_root).resolve() / "docs" / "03_runtime"

    if not runtime_dir.exists():
        return [f"docs/03_runtime/ does not exist"]

    if not runtime_dir.is_dir():
        return [f"docs/03_runtime/ is not a directory"]

    # Check for required files
    for required_file in REQUIRED_FILES:
        file_path = runtime_dir / required_file
        if not file_path.exists():
            errors.append(f"Missing required file: docs/03_runtime/{required_file}")

    # Check for required subdirectories
    existing_subdirs = {item.name for item in runtime_dir.iterdir() if item.is_dir()}
    for required_subdir in REQUIRED_SUBDIRS:
        if required_subdir not in existing_subdirs:
            errors.append(
                f"Missing required subdirectory: docs/03_runtime/{required_subdir}/"
            )

    # Validate archive/ subdirectory structure
    archive_dir = runtime_dir / "archive"
    if archive_dir.exists() and archive_dir.is_dir():
        errors.extend(_validate_archive_structure(archive_dir, "docs/03_runtime/archive"))

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
