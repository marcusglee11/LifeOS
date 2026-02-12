#!/usr/bin/env python3
"""
Repo Safety Gate - Preflight checks before dangerous git operations.

This script MUST be run before any branch switching, checkout, or cleanup operations
to prevent accidental file loss due to branch divergence.

Usage:
    python scripts/repo_safety_gate.py --operation checkout
    python scripts/repo_safety_gate.py --operation merge
    python scripts/repo_safety_gate.py --operation cleanup

Exit codes:
    0 = Safe to proceed
    1 = BLOCKED - issues detected that require human review
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

# Critical files that MUST exist after any operation
CRITICAL_FILES = [
    "GEMINI.md",
    "CLAUDE.md",
    "AGENTS.md",
    ".gitattributes",
    ".github/workflows/ci.yml",
    "docs/INDEX.md",
    "docs/11_admin/LIFEOS_STATE.md",
    "docs/12_productisation/assets/An_OS_for_Life.mp4",
    "runtime/engine.py",
    "pyproject.toml",
]

# Branches that should be in sync with main
SYNC_BRANCHES = [
    "origin/gov/repoint-canon",
    "origin/temp-restore-branch",
]


def run_git(args: list[str]) -> tuple[int, str]:
    """Run git command and return (exit_code, output)."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return result.returncode, result.stdout.strip()


def check_working_tree_clean() -> list[str]:
    """Check if working tree is clean."""
    issues = []
    code, output = run_git(["status", "--porcelain"])
    if output:
        staged = [l for l in output.split("\n") if l.startswith(("A ", "M ", "D "))]
        if staged:
            issues.append(f"STAGED CHANGES: {len(staged)} files staged but not committed")
    return issues


def check_branch_divergence() -> list[str]:
    """Check if any tracked branches have diverged from main."""
    issues = []
    for branch in SYNC_BRANCHES:
        code, _ = run_git(["rev-parse", "--verify", branch])
        if code != 0:
            continue  # Branch doesn't exist
        
        # Check if branch has commits not in main
        code, output = run_git(["log", "--oneline", f"main..{branch}"])
        if output:
            commit_count = len(output.strip().split("\n"))
            issues.append(f"DIVERGENCE: {branch} has {commit_count} commits not in main")
    
    return issues


def check_critical_files() -> list[str]:
    """Verify all critical files exist."""
    issues = []
    repo_root = Path(__file__).parent.parent
    
    for file_path in CRITICAL_FILES:
        full_path = repo_root / file_path
        if not full_path.exists():
            issues.append(f"MISSING: {file_path}")
    
    return issues


def check_uncommitted_on_other_branches() -> list[str]:
    """Check if current branch has work not on main."""
    issues = []
    
    code, current_branch = run_git(["branch", "--show-current"])
    if current_branch and current_branch != "main":
        # Check commits on this branch not in main
        code, output = run_git(["log", "--oneline", f"main..{current_branch}"])
        if output:
            commit_count = len(output.strip().split("\n"))
            issues.append(f"UNCOMMITTED WORK: Branch '{current_branch}' has {commit_count} commits not merged to main")
    
    return issues


def should_block_issue(operation: str, issue: str) -> bool:
    """Operation-aware blocking policy."""
    # Merge operations are expected to run from feature branches with commits
    # not yet in main; treat this as informational, not blocking.
    if operation == "merge" and issue.startswith("UNCOMMITTED WORK:"):
        return False
    # Temporary sync branch divergence should not block normal merges.
    if operation == "merge" and issue.startswith("DIVERGENCE: origin/temp-restore-branch"):
        return False
    return True


def create_snapshot() -> dict:
    """Create a snapshot of current repo state for recovery."""
    _, head = run_git(["rev-parse", "HEAD"])
    _, branch = run_git(["branch", "--show-current"])
    _, status = run_git(["status", "--porcelain"])
    
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "head": head,
        "branch": branch or "(detached)",
        "dirty_files": status.split("\n") if status else [],
    }
    
    # Save snapshot
    snapshot_dir = Path(__file__).parent.parent / "artifacts" / "safety_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshot_dir / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    snapshot_file.write_text(json.dumps(snapshot, indent=2))
    
    return snapshot


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Repo Safety Gate")
    parser.add_argument("--operation", required=True, choices=["checkout", "merge", "cleanup", "preflight"])
    parser.add_argument("--force", action="store_true", help="Skip interactive confirmation")
    args = parser.parse_args()
    
    print(f"🔒 Repo Safety Gate - {args.operation.upper()} preflight check")
    print("=" * 60)
    
    all_issues = []
    blocking_issues = []
    
    # Always check critical files
    issues = check_critical_files()
    if issues:
        print("\n⚠️  CRITICAL FILES CHECK:")
        for issue in issues:
            print(f"   • {issue}")
        all_issues.extend(issues)
        blocking_issues.extend([i for i in issues if should_block_issue(args.operation, i)])
    else:
        print("\n✅ Critical files: All present")
    
    # Check working tree
    issues = check_working_tree_clean()
    if issues:
        print("\n⚠️  WORKING TREE CHECK:")
        for issue in issues:
            print(f"   • {issue}")
        all_issues.extend(issues)
        blocking_issues.extend([i for i in issues if should_block_issue(args.operation, i)])
    else:
        print("✅ Working tree: Clean")
    
    # Check branch divergence
    issues = check_branch_divergence()
    if issues:
        print("\n🚨 BRANCH DIVERGENCE DETECTED:")
        for issue in issues:
            print(f"   • {issue}")
        all_issues.extend(issues)
        blocking_issues.extend([i for i in issues if should_block_issue(args.operation, i)])
    else:
        print("✅ Branch sync: No divergence detected")
    
    # Check for uncommitted work on other branches
    issues = check_uncommitted_on_other_branches()
    if issues:
        print("\n⚠️  UNCOMMITTED WORK:")
        for issue in issues:
            print(f"   • {issue}")
        all_issues.extend(issues)
        blocking_issues.extend([i for i in issues if should_block_issue(args.operation, i)])
    else:
        print("✅ Current branch: Merged to main or is main")
    
    print("\n" + "=" * 60)
    
    if blocking_issues:
        print(f"\n❌ BLOCKED: {len(blocking_issues)} issue(s) require attention before proceeding.")
        print("\nTo proceed anyway (at your own risk), run with --force")
        
        # Always create snapshot before risky operations
        snapshot = create_snapshot()
        print(f"\n📸 Snapshot saved: artifacts/safety_snapshots/snapshot_*.json")
        print(f"   Commit: {snapshot['head'][:8]}")
        print(f"   Branch: {snapshot['branch']}")
        
        if not args.force:
            return 1
        else:
            print("\n⚠️  --force specified, proceeding despite issues...")
    else:
        if all_issues:
            print(f"\n⚠️  Proceeding with {len(all_issues)} non-blocking warning(s) for this operation.")
        print("\n✅ All checks passed. Safe to proceed with operation.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
