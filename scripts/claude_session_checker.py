#!/usr/bin/env python3
"""
Claude Code Session Eligibility Checker

Determines whether a Claude Code session qualifies for Lightweight Stewardship mode
per GEMINI.md Article XVIII.

Eligibility criteria (ALL must be true):
- Total files modified ≤ 5
- No governance-controlled paths modified
- No new code logic introduced (heuristic)

Exit codes:
  0: Eligible for lightweight mode
  1: NOT eligible (standard mode required)
  2: Error condition
"""

import sys
import json
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set


def run_git_command(cmd: List[str], repo_root: Path) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{e.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Git command timed out: {' '.join(cmd)}")


def get_modified_files(repo_root: Path) -> List[str]:
    """Get list of modified files from git."""
    # Get both staged and unstaged changes
    output = run_git_command(["git", "diff", "--name-only", "HEAD"], repo_root)
    files = [f for f in output.split('\n') if f.strip()]

    # Also get untracked files that might be new
    output_untracked = run_git_command(["git", "ls-files", "--others", "--exclude-standard"], repo_root)
    untracked = [f for f in output_untracked.split('\n') if f.strip()]

    # Combine, removing duplicates
    all_files = list(set(files + untracked))
    return all_files


def load_governance_baseline(repo_root: Path) -> Set[str]:
    """Load protected paths from governance baseline."""
    baseline_path = repo_root / "config" / "governance_baseline.yaml"

    if not baseline_path.exists():
        raise RuntimeError(f"Governance baseline not found: {baseline_path}")

    with open(baseline_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # Extract artifact paths
    protected_paths = set()
    for artifact in data.get('artifacts', []):
        path = artifact.get('path', '')
        if path:
            protected_paths.add(path)

    return protected_paths


def check_governance_violations(modified_files: List[str], protected_paths: Set[str]) -> List[str]:
    """Check if any modified files are in protected governance paths."""
    violations = []
    for file in modified_files:
        if file in protected_paths:
            violations.append(file)
    return violations


def detect_new_code_logic(modified_files: List[str], repo_root: Path) -> Dict[str, Any]:
    """
    Heuristic to detect new code logic.

    Returns:
      - new_py_files: List of new .py files
      - large_py_changes: List of .py files with >50 lines changed
      - has_new_logic: Boolean flag
    """
    new_py_files = []
    large_py_changes = []

    for file in modified_files:
        if not file.endswith('.py'):
            continue

        file_path = repo_root / file

        # Check if file is new (untracked)
        try:
            run_git_command(["git", "ls-files", "--error-unmatch", file], repo_root)
            # File is tracked, check diff size
            try:
                diff_output = run_git_command(
                    ["git", "diff", "HEAD", "--", file],
                    repo_root
                )
                # Count added/removed lines (lines starting with + or -)
                added_lines = sum(1 for line in diff_output.split('\n')
                                if line.startswith('+') and not line.startswith('+++'))
                removed_lines = sum(1 for line in diff_output.split('\n')
                                  if line.startswith('-') and not line.startswith('---'))

                total_changed = added_lines + removed_lines

                if total_changed > 50:
                    large_py_changes.append({
                        'file': file,
                        'lines_changed': total_changed
                    })
            except RuntimeError:
                # If diff fails, skip this file
                pass

        except subprocess.CalledProcessError:
            # File is untracked (new)
            new_py_files.append(file)

    has_new_logic = len(new_py_files) > 0 or len(large_py_changes) > 0

    return {
        'new_py_files': new_py_files,
        'large_py_changes': large_py_changes,
        'has_new_logic': has_new_logic
    }


def check_lightweight_eligibility(repo_root: Path) -> Dict[str, Any]:
    """
    Check if session qualifies for lightweight mode.

    Returns a dict with:
      - eligible: bool
      - violations: list of reasons for ineligibility
      - stats: dict of metrics
    """
    violations = []
    stats = {}

    try:
        # 1. Count modified files
        modified_files = get_modified_files(repo_root)
        file_count = len(modified_files)
        stats['file_count'] = file_count
        stats['modified_files'] = modified_files

        if file_count > 5:
            violations.append(f"Too many files modified ({file_count} > 5)")

        # 2. Check governance paths
        protected_paths = load_governance_baseline(repo_root)
        gov_violations = check_governance_violations(modified_files, protected_paths)
        stats['governance_violations'] = gov_violations

        if gov_violations:
            violations.append(f"Governance-controlled paths modified: {', '.join(gov_violations)}")

        # 3. Detect new code logic
        code_analysis = detect_new_code_logic(modified_files, repo_root)
        stats['code_analysis'] = code_analysis

        if code_analysis['has_new_logic']:
            details = []
            if code_analysis['new_py_files']:
                details.append(f"{len(code_analysis['new_py_files'])} new .py files")
            if code_analysis['large_py_changes']:
                details.append(f"{len(code_analysis['large_py_changes'])} files with >50 lines changed")
            violations.append(f"New code logic detected: {', '.join(details)}")

        eligible = len(violations) == 0

        return {
            'eligible': eligible,
            'violations': violations,
            'stats': stats
        }

    except Exception as e:
        return {
            'eligible': False,
            'violations': [f"Error during eligibility check: {str(e)}"],
            'stats': {}
        }


def main():
    """Main entry point."""
    # Determine repo root (current working directory or parent with .git)
    repo_root = Path.cwd()

    while repo_root != repo_root.parent:
        if (repo_root / ".git").exists():
            break
        repo_root = repo_root.parent
    else:
        print(json.dumps({
            'eligible': False,
            'violations': ['Not in a git repository'],
            'stats': {}
        }), file=sys.stderr)
        sys.exit(2)

    # Check eligibility
    result = check_lightweight_eligibility(repo_root)

    # Output JSON to stdout
    print(json.dumps(result, indent=2))

    # Exit code based on eligibility
    if result['eligible']:
        sys.exit(0)  # Eligible for lightweight
    else:
        sys.exit(1)  # NOT eligible (standard mode required)


if __name__ == "__main__":
    main()
