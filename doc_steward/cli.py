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
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
