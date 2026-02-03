#!/usr/bin/env python3
"""
Doc Hygiene - Markdown Linting Automation

Runs markdownlint with --fix on specified directory (defaults to docs/).
Provides structured output for CI integration and human review.

Usage:
    doc_hygiene_markdown_lint.py [path] [--dry-run] [--json]

Exit codes:
    0: Success (no issues or all fixed)
    1: Issues found that couldn't be auto-fixed
    127: Missing dependency (markdownlint-cli)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def check_markdownlint_available() -> bool:
    """Check if markdownlint-cli is installed."""
    try:
        subprocess.run(
            ["markdownlint", "--version"],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_markdownlint(
    path: Path,
    dry_run: bool = False,
    config_file: Optional[Path] = None
) -> tuple[int, str, str, str]:
    """
    Run markdownlint on the specified path.

    Args:
        path: Directory or file to lint
        dry_run: If True, don't modify files
        config_file: Path to .markdownlint.json config

    Returns:
        Tuple of (exit_code, stdout, stderr, before_output)
        before_output contains issues found before fixing
    """
    # Build path pattern
    if path.is_dir():
        path_pattern = str(path / "**" / "*.md")
    else:
        path_pattern = str(path)

    # First, run without --fix to see what issues exist
    cmd_check = ["markdownlint"]
    if config_file and config_file.exists():
        cmd_check.extend(["--config", str(config_file)])
    cmd_check.append(path_pattern)

    try:
        check_result = subprocess.run(
            cmd_check,
            capture_output=True,
            text=True
        )
        before_output = check_result.stdout + check_result.stderr
    except FileNotFoundError:
        return 127, "", "markdownlint command not found", ""

    # If dry-run, just return check results
    if dry_run:
        return check_result.returncode, check_result.stdout, check_result.stderr, before_output

    # Run with --fix to actually fix issues
    cmd_fix = ["markdownlint", "--fix"]
    if config_file and config_file.exists():
        cmd_fix.extend(["--config", str(config_file)])
    cmd_fix.append(path_pattern)

    try:
        fix_result = subprocess.run(
            cmd_fix,
            capture_output=True,
            text=True
        )
        return fix_result.returncode, fix_result.stdout, fix_result.stderr, before_output
    except FileNotFoundError:
        return 127, "", "markdownlint command not found", ""


def parse_markdownlint_output(stdout: str, stderr: str) -> Dict:
    """
    Parse markdownlint output into structured format.

    Args:
        stdout: Standard output from markdownlint
        stderr: Standard error from markdownlint

    Returns:
        Dictionary with parsed results
    """
    lines = (stdout + stderr).strip().split('\n')
    issues = []
    files_affected = set()

    for line in lines:
        if not line.strip():
            continue

        # Parse lines like: "path/file.md:10 MD013/line-length ..."
        if ':' in line and any(rule in line for rule in ['MD', 'error', 'warning']):
            parts = line.split(':')
            if len(parts) >= 2:
                file_path = parts[0]
                files_affected.add(file_path)
                issues.append({
                    'file': file_path,
                    'raw': line
                })

    return {
        'total_issues': len(issues),
        'files_affected': len(files_affected),
        'files': sorted(files_affected),
        'issues': issues
    }


def format_summary(
    exit_code: int,
    stdout: str,
    stderr: str,
    before_output: str,
    dry_run: bool
) -> str:
    """
    Format human-readable summary.

    Args:
        exit_code: Exit code from markdownlint
        stdout: Standard output
        stderr: Standard error
        before_output: Output from check run (before fixing)
        dry_run: Whether this was a dry run

    Returns:
        Formatted summary string
    """
    # Parse issues from before_output to see what was found
    parsed_before = parse_markdownlint_output(before_output, "")
    parsed_after = parse_markdownlint_output(stdout, stderr)

    # If no issues before, clean file
    if parsed_before['total_issues'] == 0:
        return "✓ No markdown linting issues found."

    # If issues before but none after (and exit code 0), they were fixed
    if parsed_before['total_issues'] > 0 and exit_code == 0:
        action = "would be fixed" if dry_run else "fixed"
        return (
            f"✓ Markdown linting complete: {parsed_before['total_issues']} issues {action} "
            f"in {parsed_before['files_affected']} files."
        )

    # If issues remain after fix attempt
    if exit_code == 1:
        if dry_run:
            return (
                f"⚠ Found {parsed_before['total_issues']} markdown issues "
                f"in {parsed_before['files_affected']} files."
            )
        else:
            return (
                f"⚠ Found {parsed_after['total_issues']} issues that couldn't be auto-fixed "
                f"in {parsed_after['files_affected']} files. Manual review required."
            )

    return f"✗ Unexpected exit code: {exit_code}"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run markdownlint with auto-fix on documentation"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="docs",
        help="Path to lint (default: docs/)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check without modifying files"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to .markdownlint.json config (default: auto-detect)"
    )

    args = parser.parse_args()

    # Check for markdownlint
    if not check_markdownlint_available():
        print(
            "ERROR: markdownlint-cli is not installed.\n\n"
            "Install with:\n"
            "  npm install -g markdownlint-cli\n\n"
            "Or via package manager:\n"
            "  brew install markdownlint-cli\n"
            "  apt install node-markdownlint-cli",
            file=sys.stderr
        )
        return 127

    # Resolve path
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"ERROR: Path not found: {path}", file=sys.stderr)
        return 1

    # Auto-detect config file if not specified
    config_file = args.config
    if config_file is None:
        # Look for .markdownlint.json in repo root
        repo_root = Path(__file__).resolve().parent.parent
        candidate = repo_root / ".markdownlint.json"
        if candidate.exists():
            config_file = candidate

    # Run markdownlint
    exit_code, stdout, stderr, before_output = run_markdownlint(
        path,
        dry_run=args.dry_run,
        config_file=config_file
    )

    # Output results
    if args.json:
        parsed_before = parse_markdownlint_output(before_output, "")
        parsed_after = parse_markdownlint_output(stdout, stderr)
        result = {
            'exit_code': exit_code,
            'dry_run': args.dry_run,
            'path': str(path),
            'config': str(config_file) if config_file else None,
            'before': parsed_before,
            'after': parsed_after
        }
        print(json.dumps(result, indent=2))
    else:
        summary = format_summary(exit_code, stdout, stderr, before_output, args.dry_run)
        print(summary)

        # Show details if there are issues
        parsed_before = parse_markdownlint_output(before_output, "")
        if parsed_before['files']:
            print(f"\nFiles affected ({len(parsed_before['files'])}):")
            for f in parsed_before['files'][:10]:  # Show first 10
                print(f"  - {f}")
            if len(parsed_before['files']) > 10:
                print(f"  ... and {len(parsed_before['files']) - 10} more")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
