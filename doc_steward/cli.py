#!/usr/bin/env python3
"""
doc_steward CLI — Stable command-line interface for documentation validators.

Usage:
    python -m doc_steward.cli dap-validate <doc_root>
    python -m doc_steward.cli index-check <doc_root> <index_path>
    python -m doc_steward.cli link-check <doc_root>

Exit codes:
    0 - Validation passed
    1 - Validation failed
"""

import argparse
import sys
from pathlib import Path

from .dap_validator import check_dap_compliance
from .index_checker import check_index
from .link_checker import check_links
from .admin_structure_validator import check_admin_structure
from .admin_archive_link_ban_validator import check_admin_archive_link_ban
from .freshness_validator import check_freshness, get_freshness_mode
from .protocols_structure_validator import check_protocols_structure
from .runtime_structure_validator import check_runtime_structure
from .archive_structure_validator import check_archive_structure
from .global_archive_link_ban_validator import check_global_archive_link_ban
from .version_duplicate_detector import check_version_duplicates_with_lineage
from .artefact_index_validator import check_artefact_index

def cmd_opencode_validate(args: argparse.Namespace) -> int:
    """Run OpenCode artefact validation."""
    # args.doc_root is historically named, but here acts as repo_root or context root
    root = Path(args.doc_root).resolve()
    target = root / "artifacts" / "opencode"
    
    if not target.exists():
        print(f"[FAILED] Missing required directory: {target}")
        return 1
        
    if not target.is_dir():
        print(f"[FAILED] Target is not a directory: {target}")
        return 1
        
    print(f"[PASSED] OpenCode artefact root exists: {target}")
    return 0


def cmd_dap_validate(args: argparse.Namespace) -> int:
    """Run DAP compliance validation."""
    doc_root = str(Path(args.doc_root).resolve())
    errors = check_dap_compliance(doc_root)
    
    if errors:
        print(f"[FAILED] DAP validation failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] DAP validation passed.")
        return 0


def cmd_index_check(args: argparse.Namespace) -> int:
    """Run index consistency check."""
    doc_root = str(Path(args.doc_root).resolve())
    index_path = str(Path(args.index_path).resolve())
    errors = check_index(doc_root, index_path)
    
    if errors:
        print(f"[FAILED] Index check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Index check passed.")
        return 0


def cmd_link_check(args: argparse.Namespace) -> int:
    """Run link validation."""
    doc_root = str(Path(args.doc_root).resolve())
    errors = check_links(doc_root)

    if errors:
        print(f"[FAILED] Link check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Link check passed.")
        return 0


def cmd_admin_structure_check(args: argparse.Namespace) -> int:
    """Run admin structure validation."""
    repo_root = str(Path(args.repo_root).resolve())
    errors = check_admin_structure(repo_root)

    if errors:
        print(f"[FAILED] Admin structure check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Admin structure check passed.")
        return 0


def cmd_admin_archive_link_ban_check(args: argparse.Namespace) -> int:
    """Run admin archive link ban validation."""
    repo_root = str(Path(args.repo_root).resolve())
    errors = check_admin_archive_link_ban(repo_root)

    if errors:
        print(f"[FAILED] Admin archive link ban check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Admin archive link ban check passed.")
        return 0


def cmd_freshness_check(args: argparse.Namespace) -> int:
    """Run freshness check (mode-gated)."""
    repo_root = str(Path(args.repo_root).resolve())
    mode = get_freshness_mode()

    warnings, errors = check_freshness(repo_root)

    if mode == "off":
        print("[SKIPPED] Freshness check disabled (LIFEOS_DOC_FRESHNESS_MODE=off)")
        return 0

    if warnings:
        print(f"[WARNINGS] Freshness check warnings ({len(warnings)}):\n")
        for warn in warnings:
            print(f"  * {warn}")

    if errors:
        print(f"\n[FAILED] Freshness check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1

    if not warnings and not errors:
        print(f"[PASSED] Freshness check passed (mode: {mode}).")
    elif mode == "warn":
        print(f"\n[PASSED] Freshness check passed with warnings (mode: {mode}).")

    return 0


def cmd_protocols_structure_check(args: argparse.Namespace) -> int:
    """Run protocols structure validation."""
    repo_root = str(Path(args.repo_root).resolve())
    errors = check_protocols_structure(repo_root)

    if errors:
        print(f"[FAILED] Protocols structure check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Protocols structure check passed.")
        return 0


def cmd_runtime_structure_check(args: argparse.Namespace) -> int:
    """Run runtime structure validation."""
    repo_root = str(Path(args.repo_root).resolve())
    errors = check_runtime_structure(repo_root)

    if errors:
        print(f"[FAILED] Runtime structure check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Runtime structure check passed.")
        return 0


def cmd_archive_structure_check(args: argparse.Namespace) -> int:
    """Run archive structure validation."""
    repo_root = str(Path(args.repo_root).resolve())
    errors = check_archive_structure(repo_root)

    if errors:
        print(f"[FAILED] Archive structure check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Archive structure check passed.")
        return 0


def cmd_docs_archive_link_ban_check(args: argparse.Namespace) -> int:
    """Run global archive link ban validation."""
    repo_root = str(Path(args.repo_root).resolve())
    errors = check_global_archive_link_ban(repo_root)

    if errors:
        print(f"[FAILED] Archive link ban check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Archive link ban check passed.")
        return 0


def cmd_artefact_index_check(args: argparse.Namespace) -> int:
    """Run artefact index validation."""
    repo_root = str(Path(args.repo_root).resolve())
    directory = args.directory if hasattr(args, 'directory') else None
    errors = check_artefact_index(repo_root, directory)

    if errors:
        print(f"[FAILED] Artefact index check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Artefact index check passed.")
        return 0


def cmd_version_duplicate_scan(args: argparse.Namespace) -> int:
    """Run version duplicate scan (report-only, never fails)."""
    repo_root = str(Path(args.repo_root).resolve())
    report = check_version_duplicates_with_lineage(repo_root)

    print("[REPORT] Version Duplicate Scan:\n")
    for line in report:
        print(line)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="doc_steward.cli",
        description="LifeOS Documentation Steward CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # dap-validate
    p_dap = subparsers.add_parser("dap-validate", help="Check DAP naming compliance")
    p_dap.add_argument("doc_root", help="Root directory to validate")
    p_dap.set_defaults(func=cmd_dap_validate)
    
    # index-check
    p_idx = subparsers.add_parser("index-check", help="Check index consistency")
    p_idx.add_argument("doc_root", help="Root directory of documentation")
    p_idx.add_argument("index_path", help="Path to INDEX.md file")
    p_idx.set_defaults(func=cmd_index_check)
    
    # link-check
    p_link = subparsers.add_parser("link-check", help="Check for broken links")
    p_link.add_argument("doc_root", help="Root directory to validate")
    p_link.set_defaults(func=cmd_link_check)

    # opencode-validate
    p_oc = subparsers.add_parser("opencode-validate", help="Validate OpenCode artefacts")
    p_oc.add_argument("doc_root", help="Repo root directory")
    p_oc.set_defaults(func=cmd_opencode_validate)

    # admin-structure-check
    p_admin_struct = subparsers.add_parser("admin-structure-check", help="Validate docs/11_admin/ structure")
    p_admin_struct.add_argument("repo_root", help="Repository root directory")
    p_admin_struct.set_defaults(func=cmd_admin_structure_check)

    # admin-archive-link-ban-check
    p_admin_archive = subparsers.add_parser("admin-archive-link-ban-check", help="Check for links to archived docs")
    p_admin_archive.add_argument("repo_root", help="Repository root directory")
    p_admin_archive.set_defaults(func=cmd_admin_archive_link_ban_check)

    # freshness-check
    p_freshness = subparsers.add_parser("freshness-check", help="Check doc freshness (mode-gated)")
    p_freshness.add_argument("repo_root", help="Repository root directory")
    p_freshness.set_defaults(func=cmd_freshness_check)

    # protocols-structure-check
    p_protocols = subparsers.add_parser("protocols-structure-check", help="Validate docs/02_protocols/ structure")
    p_protocols.add_argument("repo_root", help="Repository root directory")
    p_protocols.set_defaults(func=cmd_protocols_structure_check)

    # runtime-structure-check
    p_runtime = subparsers.add_parser("runtime-structure-check", help="Validate docs/03_runtime/ structure")
    p_runtime.add_argument("repo_root", help="Repository root directory")
    p_runtime.set_defaults(func=cmd_runtime_structure_check)

    # archive-structure-check
    p_archive = subparsers.add_parser("archive-structure-check", help="Validate docs/99_archive/ structure")
    p_archive.add_argument("repo_root", help="Repository root directory")
    p_archive.set_defaults(func=cmd_archive_structure_check)

    # docs-archive-link-ban-check
    p_link_ban = subparsers.add_parser("docs-archive-link-ban-check", help="Check for links to archived docs (global)")
    p_link_ban.add_argument("repo_root", help="Repository root directory")
    p_link_ban.set_defaults(func=cmd_docs_archive_link_ban_check)

    # artefact-index-check
    p_artefact = subparsers.add_parser("artefact-index-check", help="Validate ARTEFACT_INDEX.json files")
    p_artefact.add_argument("repo_root", help="Repository root directory")
    p_artefact.add_argument("--directory", help="Optional specific directory to check", default=None)
    p_artefact.set_defaults(func=cmd_artefact_index_check)

    # version-duplicate-scan
    p_version = subparsers.add_parser("version-duplicate-scan", help="Report version duplicates (warn-only)")
    p_version.add_argument("repo_root", help="Repository root directory")
    p_version.set_defaults(func=cmd_version_duplicate_scan)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
