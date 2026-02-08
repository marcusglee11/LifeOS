#!/usr/bin/env python3
"""
Cleanliness Gate - Agent-agnostic repository cleanliness checker.

Ensures git working tree is clean before and/or after operations.
Designed for headless agent integration and fail-closed execution.

Usage:
    python scripts/cleanliness_gate.py check
        Check if repo is clean. Exit 0 if clean, non-zero otherwise.

    python scripts/cleanliness_gate.py wrap -- <command...>
        Assert clean before command, run command, assert clean after.
        Captures evidence to gitignored location on failure.
"""

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_repo_root() -> Path:
    """Get git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        return Path(result.stdout.strip())
    except Exception as e:
        print(f"ERROR: Failed to get repo root: {e}", file=sys.stderr)
        sys.exit(1)


def check_cleanliness(repo_root: Path) -> tuple[bool, str]:
    """
    Check if repository is clean.

    Returns:
        (is_clean, porcelain_output)
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "-uall"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10
        )

        porcelain = result.stdout.strip()
        is_clean = len(porcelain) == 0

        return is_clean, porcelain

    except Exception as e:
        print(f"ERROR: Failed to check git status: {e}", file=sys.stderr)
        sys.exit(1)


def write_evidence(repo_root: Path, phase: str, porcelain: str, cmd: list = None) -> Path:
    """
    Write evidence of cleanliness failure to gitignored location.

    Args:
        repo_root: Repository root
        phase: "pre" or "post"
        porcelain: Git porcelain output
        cmd: Command that was run (for post phase)

    Returns:
        Path to evidence file
    """
    # Prefer gitignored in-repo location
    evidence_dir = repo_root / "artifacts" / "99_archive"

    # Fallback to /tmp if artifacts/99_archive doesn't exist or isn't ignored
    if not evidence_dir.exists():
        evidence_dir = Path("/tmp/lifeos_clean_gate_evidence")
        evidence_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    evidence_file = evidence_dir / f"cleanliness_gate_failure_{phase}_{timestamp}.txt"

    with open(evidence_file, "w", encoding="utf-8") as f:
        f.write("=== Cleanliness Gate Failure ===\n")
        f.write(f"Phase: {phase}\n")
        f.write(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Repo Root: {repo_root}\n")

        if cmd:
            f.write(f"Command: {' '.join(cmd)}\n")

        f.write("\n=== Git Status (Porcelain) ===\n")
        f.write(porcelain)
        f.write("\n")

        # Also capture full diff
        try:
            diff_result = subprocess.run(
                ["git", "diff"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            f.write("\n=== Git Diff ===\n")
            f.write(diff_result.stdout)
        except Exception:
            f.write("\n(Failed to capture git diff)\n")

    return evidence_file


def cmd_check(args) -> int:
    """Check cleanliness and exit with appropriate code."""
    repo_root = get_repo_root()
    is_clean, porcelain = check_cleanliness(repo_root)

    if is_clean:
        print("✓ Repository is clean")
        return 0
    else:
        print("✗ Repository is dirty", file=sys.stderr)
        print("\nModified files:", file=sys.stderr)
        print(porcelain, file=sys.stderr)
        return 1


def cmd_wrap(args) -> int:
    """Wrap a command with pre/post cleanliness checks."""
    if not args.command:
        print("ERROR: No command specified for wrap mode", file=sys.stderr)
        print("Usage: cleanliness_gate.py wrap -- <command>", file=sys.stderr)
        return 1

    repo_root = get_repo_root()

    # Pre-check
    print("Cleanliness gate: Pre-check...")
    is_clean, porcelain = check_cleanliness(repo_root)

    if not is_clean:
        print("✗ FAIL: Repository is dirty before command execution", file=sys.stderr)
        evidence_path = write_evidence(repo_root, "pre", porcelain, args.command)
        print(f"Evidence written to: {evidence_path}", file=sys.stderr)
        print("\nModified files:", file=sys.stderr)
        print(porcelain, file=sys.stderr)
        return 1

    print("✓ Pre-check passed (clean)")

    # Run command
    print(f"\nRunning: {' '.join(args.command)}")
    try:
        result = subprocess.run(args.command, cwd=repo_root)
        cmd_exit_code = result.returncode
    except Exception as e:
        print(f"ERROR: Failed to execute command: {e}", file=sys.stderr)
        return 1

    # Post-check
    print("\nCleanliness gate: Post-check...")
    is_clean, porcelain = check_cleanliness(repo_root)

    if not is_clean:
        print("✗ FAIL: Repository is dirty after command execution", file=sys.stderr)
        evidence_path = write_evidence(repo_root, "post", porcelain, args.command)
        print(f"Evidence written to: {evidence_path}", file=sys.stderr)
        print("\nModified files:", file=sys.stderr)
        print(porcelain, file=sys.stderr)
        return 1

    print("✓ Post-check passed (clean)")

    if cmd_exit_code != 0:
        print(f"\nWarning: Command exited with code {cmd_exit_code}", file=sys.stderr)

    return cmd_exit_code


def main():
    parser = argparse.ArgumentParser(
        description="Cleanliness gate for headless agent integration"
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # check subcommand
    parser_check = subparsers.add_parser(
        "check",
        help="Check if repository is clean"
    )
    parser_check.set_defaults(func=cmd_check)

    # wrap subcommand
    parser_wrap = subparsers.add_parser(
        "wrap",
        help="Wrap command with pre/post cleanliness checks"
    )
    parser_wrap.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute (use -- before command)"
    )
    parser_wrap.set_defaults(func=cmd_wrap)

    args = parser.parse_args()

    # Handle the '--' separator for wrap command
    if args.subcommand == "wrap" and args.command and args.command[0] == "--":
        args.command = args.command[1:]

    exit_code = args.func(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
