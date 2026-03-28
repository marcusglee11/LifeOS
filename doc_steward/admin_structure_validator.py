"""
Admin structure validator for docs/11_admin/.

Enforces:
- Root file allowlist (REQUIRED + CANONICAL_OPTIONAL)
- Allowed subdirectories only (build_summaries/, archive/)
- Naming patterns for build summaries and archive subdirs
- Archive subdir README.md requirement

Fail-closed: any unexpected file or directory is an error.
"""
from __future__ import annotations

import re
from pathlib import Path

# Canonical allowlist for docs/11_admin/ root (exact)
REQUIRED_FILES = {
    "LIFEOS_STATE.md",
    "BACKLOG.md",
    "INBOX.md",
    "DECISIONS.md",
}

CANONICAL_OPTIONAL_FILES = {
    "LifeOS_Build_Loop_Production_Plan_v2.1.md",
    "LifeOS_Master_Execution_Plan_v1.1.md",
    "Plan_Supersession_Register.md",
    "Doc_Freshness_Gate_Spec_v1.0.md",
    "AUTONOMY_STATUS.md",
    "WIP_LOG.md",
    "lifeos-master-operating-manual-v2.1.md",
    "README.md",
    # Burn-in closure reports (produced by build/batch*-burn-in branches)
    "Batch1_BurnIn_Report.md",
    "Batch2_BurnIn_Report.md",
    # Tech debt inventory (living doc produced by audit passes)
    "TECH_DEBT_INVENTORY.md",
    # Repo-wide quality baseline summary (produced by quality audit passes)
    "QUALITY_AUDIT_BASELINE_v1.0.md",
}

ALLOWED_ROOT_FILES = REQUIRED_FILES | CANONICAL_OPTIONAL_FILES

# Allowed subdirectories (exact)
ALLOWED_SUBDIRS = {"build_summaries", "archive"}

# Naming patterns
BUILD_SUMMARY_PATTERN = re.compile(r'^.*_Build_Summary_\d{4}-\d{2}-\d{2}\.md$')
ARCHIVE_SUBDIR_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}_[a-z0-9_]+$')


def check_admin_structure(repo_root: str) -> list[str]:
    """
    Validate docs/11_admin/ structure against canonical allowlist.

    Args:
        repo_root: Path to repository root

    Returns:
        List of error strings for violations (empty if valid)
    """
    errors: list[str] = []
    admin_dir = Path(repo_root).resolve() / "docs" / "11_admin"

    if not admin_dir.exists():
        return ["docs/11_admin/ does not exist"]

    if not admin_dir.is_dir():
        return ["docs/11_admin/ is not a directory"]

    # Check for missing REQUIRED files
    for required_file in REQUIRED_FILES:
        file_path = admin_dir / required_file
        if not file_path.exists():
            errors.append(f"Missing required file: docs/11_admin/{required_file}")

    # Scan root directory
    for item in admin_dir.iterdir():
        rel_name = item.name

        if item.is_dir():
            # Check subdirectory allowlist
            if rel_name not in ALLOWED_SUBDIRS:
                errors.append(
                    f"Unexpected subdirectory: docs/11_admin/{rel_name}/ "
                    f"(allowed: {', '.join(sorted(ALLOWED_SUBDIRS))})"
                )

            # Validate archive subdirectory structure
            if rel_name == "archive":
                for archive_subdir in item.iterdir():
                    if archive_subdir.is_dir():
                        if not ARCHIVE_SUBDIR_PATTERN.match(archive_subdir.name):
                            errors.append(
                                "Invalid archive subdir name: "
                                f"docs/11_admin/archive/{archive_subdir.name}/ "
                                f"(must match: YYYY-MM-DD_<topic>)"
                            )

                        # Check for required README.md
                        readme_path = archive_subdir / "README.md"
                        if not readme_path.exists():
                            errors.append(
                                "Missing README.md in archive subdir: "
                                f"docs/11_admin/archive/{archive_subdir.name}/"
                            )

        elif item.is_file():
            # Check root file allowlist
            if rel_name not in ALLOWED_ROOT_FILES:
                errors.append(
                    f"Unexpected file at root: docs/11_admin/{rel_name} "
                    f"(not in allowlist)"
                )

    # Validate build_summaries/ naming pattern
    build_summaries_dir = admin_dir / "build_summaries"
    if build_summaries_dir.exists() and build_summaries_dir.is_dir():
        for summary_file in build_summaries_dir.iterdir():
            if summary_file.is_file() and summary_file.suffix == ".md":
                if not BUILD_SUMMARY_PATTERN.match(summary_file.name):
                    errors.append(
                        "Invalid build summary name: "
                        f"docs/11_admin/build_summaries/{summary_file.name} "
                        f"(must match: *_Build_Summary_YYYY-MM-DD.md)"
                    )

    return errors
