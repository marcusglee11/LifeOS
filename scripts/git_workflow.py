#!/usr/bin/env python3
"""
Git Workflow Enforcement Script

Enforces the Git Workflow Protocol v1.0:
- Branch-per-build workflow
- No direct commits to main
- Test gates before merge
- Branch naming validation

Usage:
    python scripts/git_workflow.py branch create build/<topic>
    python scripts/git_workflow.py branch create-worktree build/<topic>
    python scripts/git_workflow.py branch list
    python scripts/git_workflow.py review prepare
    python scripts/git_workflow.py merge
    python scripts/git_workflow.py status
"""

import subprocess
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Valid branch patterns
BRANCH_PATTERNS = {
    "build": re.compile(r"^build/[a-z0-9][a-z0-9\-]*$"),
    "fix": re.compile(r"^fix/[a-z0-9][a-z0-9\-]*$"),
    "hotfix": re.compile(r"^hotfix/[a-z0-9][a-z0-9\-]*$"),
    "spike": re.compile(r"^spike/[a-z0-9][a-z0-9\-]*$"),
}

PROTECTED_BRANCHES = ["main", "master"]
REPO_ROOT = Path(__file__).resolve().parent.parent


def run_git(args: list[str], check: bool = True) -> Tuple[int, str, str]:
    """Run git command and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT
    )
    if check and result.returncode != 0:
        print(f"❌ Git error: {result.stderr}", file=sys.stderr)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run_git_in(path: Path, args: list[str]) -> Tuple[int, str, str]:
    """Run git command in an explicit repository path."""
    result = subprocess.run(
        ["git", "-C", str(path)] + args,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_current_branch(repo_root: Optional[Path] = None) -> str:
    """Get current branch name."""
    if repo_root is None:
        _, branch, _ = run_git(["branch", "--show-current"], check=False)
    else:
        _, branch, _ = run_git_in(repo_root, ["branch", "--show-current"])
    return branch or "(detached)"


def get_active_branches_file(repo_root: Optional[Path] = None) -> Path:
    """Get path to active branches tracking file."""
    resolved_root = repo_root or REPO_ROOT
    return resolved_root / "artifacts" / "active_branches.json"


def load_active_branches(repo_root: Optional[Path] = None) -> dict:
    """Load active branches tracking."""
    path = get_active_branches_file(repo_root)
    if path.exists():
        return json.loads(path.read_text())
    return {"branches": [], "created": datetime.now().isoformat()}


def save_active_branches(data: dict, repo_root: Optional[Path] = None):
    """Save active branches tracking."""
    path = get_active_branches_file(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _mark_registry_updated(data: dict) -> None:
    """Refresh top-level registry timestamp."""
    data["last_updated"] = datetime.now().isoformat()


def close_active_branch_records(
    branch: str,
    repo_root: Optional[Path] = None,
    *,
    closed_at: Optional[str] = None,
    worktree_path: Optional[str] = None,
) -> dict:
    """Close all active rows for a branch and clear stale worktree metadata."""
    data = load_active_branches(repo_root)
    timestamp = closed_at or datetime.now().isoformat()
    updated = 0

    for item in data.get("branches", []):
        if item.get("name") != branch or item.get("status") != "active":
            continue
        item["status"] = "closed"
        item["closed_at"] = timestamp
        if worktree_path is None or item.get("worktree_path") == worktree_path:
            item["worktree_path"] = None
        updated += 1

    if updated:
        _mark_registry_updated(data)
        save_active_branches(data, repo_root)
    return {"updated": updated, "path": str(get_active_branches_file(repo_root))}


def _resolve_primary_repo() -> Optional[Path]:
    """Find the primary worktree (prefer main/master checkout, fallback to git-common-dir=.git)."""
    code, output, _ = run_git_in(REPO_ROOT, ["worktree", "list", "--porcelain"])
    if code != 0:
        return None

    candidates: list[Path] = []
    candidate: Optional[Path] = None
    for line in output.splitlines():
        if line.startswith("worktree "):
            candidate = Path(line.split(" ", 1)[1].strip())
            candidates.append(candidate)
        elif line.startswith("branch refs/heads/"):
            branch = line.removeprefix("branch refs/heads/").strip()
            if branch in {"main", "master"} and candidate is not None:
                return candidate

    # Fallback: primary worktree is where git-common-dir resolves to ".git".
    for path in candidates:
        c, common_dir, _ = run_git_in(path, ["rev-parse", "--git-common-dir"])
        if c == 0 and common_dir.strip() == ".git":
            return path

    # Final fallback: current script root if it is primary.
    c, common_dir, _ = run_git_in(REPO_ROOT, ["rev-parse", "--git-common-dir"])
    if c == 0 and common_dir.strip() == ".git":
        return REPO_ROOT
    return None


def _derive_worktree_short_name(name: str) -> str:
    """Strip prefix, sanitize to [a-z0-9-], truncate at 30 chars."""
    short = name.split("/", 1)[1] if "/" in name else name
    short = re.sub(r"[^a-z0-9-]", "-", short.lower())
    short = re.sub(r"-+", "-", short).strip("-")
    short = short[:30].rstrip("-")
    return short or "worktree"


def validate_branch_name(name: str) -> Optional[str]:
    """Validate branch name against patterns. Returns error message or None if valid."""
    if name in PROTECTED_BRANCHES:
        return f"Cannot use protected branch name: {name}"
    
    for prefix, pattern in BRANCH_PATTERNS.items():
        if name.startswith(prefix + "/"):
            if pattern.match(name):
                return None
            else:
                return f"Invalid {prefix}/ branch name. Must match: {prefix}/[a-z0-9][a-z0-9-]*"
    
    valid_prefixes = ", ".join(f"{p}/" for p in BRANCH_PATTERNS.keys())
    return f"Branch name must start with one of: {valid_prefixes}"


def cmd_branch_create(name: str) -> int:
    """Create a new feature branch."""
    print(f"🔧 Creating branch: {name}")
    
    # Validate name
    error = validate_branch_name(name)
    if error:
        print(f"❌ {error}")
        return 1
    
    # Check we're on main or can reach it
    current = get_current_branch()
    if current != "main":
        print(f"⚠️  Currently on '{current}', switching to main first...")
        code, _, _ = run_git(["checkout", "main"])
        if code != 0:
            return 1
    
    # Pull latest main
    print("📥 Pulling latest main...")
    run_git(["pull", "--ff-only"], check=False)
    
    # Create and switch to new branch
    code, _, _ = run_git(["checkout", "-b", name])
    if code != 0:
        return 1
    
    # Track the branch
    data = load_active_branches()
    data["branches"].append({
        "name": name,
        "created": datetime.now().isoformat(),
        "status": "active",
        "base": "main"
    })
    save_active_branches(data)
    
    print(f"✅ Created and switched to branch: {name}")
    print(f"📝 Tracked in: artifacts/active_branches.json")
    return 0


def cmd_branch_create_worktree(name: str) -> int:
    """Create a feature branch in an isolated worktree (primary-repo-aware)."""
    error = validate_branch_name(name)
    if error:
        print(f"❌ {error}")
        return 1

    primary = _resolve_primary_repo()
    if primary is None:
        print("❌ Cannot resolve primary worktree (main/master branch not found).")
        return 1

    if REPO_ROOT != primary:
        print(f"ℹ️  Invoked from:  {REPO_ROOT}")
        print(f"ℹ️  Primary repo:  {primary}")

    short = _derive_worktree_short_name(name)
    wt_path = primary / ".worktrees" / short
    if wt_path.exists():
        print(f"❌ Worktree path already exists: {wt_path}")
        print("   To recover:  git worktree prune")
        print(f"           or:  git worktree remove --force {wt_path}")
        return 1

    print("📥 Pulling latest main...")
    run_git_in(primary, ["pull", "--ff-only"])

    code, _, stderr = run_git_in(
        primary,
        ["worktree", "add", "-b", name, str(wt_path), "main"],
    )
    if code != 0:
        print(f"❌ git worktree add failed: {stderr}")
        return 1

    data = load_active_branches(primary)
    data["branches"].append(
        {
            "name": name,
            "created": datetime.now().isoformat(),
            "status": "active",
            "base": "main",
            "worktree_path": str(wt_path),
        }
    )
    save_active_branches(data, primary)

    print(f"✓ Worktree ready at: {wt_path}")
    print(f"  Run: cd {wt_path}")
    return 0


def cmd_branch_list() -> int:
    """List active branches."""
    data = load_active_branches()
    
    if not data.get("branches"):
        print("No active branches tracked.")
        return 0
    
    print("📋 Active Branches:")
    print("-" * 60)
    for b in data["branches"]:
        status = b.get("status", "unknown")
        created = b.get("created", "unknown")[:10]
        print(f"  {b['name']:<40} [{status}] {created}")
    
    return 0


def cmd_review_prepare() -> int:
    """Prepare for review - run tests and check status."""
    current = get_current_branch()
    
    if current in PROTECTED_BRANCHES:
        print(f"❌ Cannot prepare review from protected branch: {current}")
        return 1
    
    print(f"🔍 Preparing review for: {current}")
    print("=" * 60)
    
    # Check for uncommitted changes
    code, status, _ = run_git(["status", "--porcelain"])
    if status:
        print("⚠️  Uncommitted changes detected:")
        for line in status.split("\n")[:5]:
            print(f"    {line}")
        print("\nCommit your changes before preparing review.")
        return 1
    
    # Run tests
    print("\n🧪 Running tests...")
    result = subprocess.run(
        ["python", "-m", "pytest", "runtime/tests/", "-q", "--tb=no",
         "--ignore=runtime/tests/orchestration/loop/test_configurable_policy.py"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    if result.returncode != 0:
        print("❌ Tests failed. Fix before proceeding.")
        print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        return 1
    
    print("✅ Tests passed")
    
    # Check for commits ahead of main
    code, ahead, _ = run_git(["log", "--oneline", f"main..{current}"])
    if not ahead:
        print("⚠️  No commits ahead of main. Nothing to review.")
        return 1
    
    commit_count = len(ahead.strip().split("\n"))
    print(f"✅ {commit_count} commit(s) ready for review")
    
    print("\n" + "=" * 60)
    print("✅ Ready for review. Next steps:")
    print(f"   1. Create PR on GitHub: {current} → main")
    print("   2. Get approval")
    print("   3. Run: python scripts/git_workflow.py merge")
    
    return 0


def cmd_merge() -> int:
    """Merge current branch to main."""
    current = get_current_branch()
    
    if current in PROTECTED_BRANCHES:
        print(f"❌ Already on {current}. Switch to feature branch first.")
        return 1
    
    print(f"🔀 Merging {current} to main")
    
    # Run safety gate first
    print("🔒 Running safety gate...")
    result = subprocess.run(
        ["python", "scripts/repo_safety_gate.py", "--operation", "merge"],
        cwd=Path(__file__).parent.parent
    )
    if result.returncode != 0:
        print("❌ Safety gate blocked merge. Resolve issues first.")
        return 1
    
    # Switch to main
    code, _, _ = run_git(["checkout", "main"])
    if code != 0:
        return 1
    
    # Pull latest
    run_git(["pull", "--ff-only"], check=False)
    
    # Merge with squash
    print(f"📦 Squash-merging {current}...")
    code, _, stderr = run_git(["merge", "--squash", current])
    if code != 0:
        print(f"❌ Merge failed: {stderr}")
        run_git(["checkout", current])
        return 1
    
    # Commit the squash
    code, _, _ = run_git(["commit", "-m", f"feat: Merge {current} (squashed)"])
    if code != 0:
        print("❌ Commit failed")
        return 1
    
    # Update tracking
    data = load_active_branches()
    for b in data["branches"]:
        if b["name"] == current:
            b["status"] = "merged"
            b["merged_at"] = datetime.now().isoformat()
    save_active_branches(data)
    
    print(f"✅ Merged {current} to main")
    
    # Offer to delete branch
    print(f"\n🗑️  Delete branch {current}? Run:")
    print(f"   git branch -d {current}")
    print(f"   git push origin --delete {current}")
    
    return 0


def cmd_status() -> int:
    """Show current workflow status."""
    current = get_current_branch()
    
    print("📊 Git Workflow Status")
    print("=" * 60)
    print(f"Current branch: {current}")
    
    # Check if on protected branch
    if current in PROTECTED_BRANCHES:
        print(f"⚠️  On protected branch. Create a feature branch to work:")
        print("   python scripts/git_workflow.py branch create-worktree build/<topic>")
    
    # Check for uncommitted changes
    code, status, _ = run_git(["status", "--porcelain"])
    if status:
        staged = len([l for l in status.split("\n") if l[0] != "?"])
        untracked = len([l for l in status.split("\n") if l.startswith("?")])
        print(f"Staged/modified: {staged} | Untracked: {untracked}")
    else:
        print("Working tree: Clean")
    
    # Show commits ahead/behind
    if current not in PROTECTED_BRANCHES:
        code, ahead, _ = run_git(["log", "--oneline", f"main..{current}"])
        code, behind, _ = run_git(["log", "--oneline", f"{current}..main"])
        ahead_count = len(ahead.strip().split("\n")) if ahead.strip() else 0
        behind_count = len(behind.strip().split("\n")) if behind.strip() else 0
        print(f"Ahead of main: {ahead_count} | Behind main: {behind_count}")
    
    # Show active branches
    data = load_active_branches()
    active = [b for b in data.get("branches", []) if b.get("status") == "active"]
    if active:
        print(f"\nActive feature branches: {len(active)}")
        for b in active[:3]:
            print(f"  • {b['name']}")
    
    return 0


def cmd_sync() -> int:
    """Sync local main with remote via PR (enforces CI gate)."""
    current = get_current_branch()
    
    if current != "main":
        print(f"[X] Must be on 'main' to sync. Currently on: {current}")
        print("   Run: git checkout main")
        return 1
    
    print("[~] Checking sync status...")
    
    # Fetch latest remote state
    run_git(["fetch", "origin", "main"], check=False)
    
    # Check commits ahead of origin/main
    code, ahead, _ = run_git(["log", "--oneline", "origin/main..main"])
    if not ahead.strip():
        print("[OK] Local main is in sync with origin/main. Nothing to push.")
        return 0
    
    commit_count = len(ahead.strip().split("\n"))
    print(f"[i] Local main is {commit_count} commit(s) ahead of origin/main")
    
    # Generate sync branch name
    sync_branch = f"sync/main-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"\n[>] Protocol: Pushing to sync branch '{sync_branch}'...")
    
    # Push to sync branch
    code, _, stderr = run_git(["push", "origin", f"main:{sync_branch}"])
    if code != 0:
        print(f"[X] Failed to push sync branch: {stderr}")
        return 1
    
    print(f"[OK] Pushed to: origin/{sync_branch}")
    
    # Try to create PR via gh CLI
    print("\n[>] Creating PR via GitHub CLI...")
    pr_result = subprocess.run(
        ["gh", "pr", "create",
         "--base", "main",
         "--head", sync_branch,
         "--title", f"Sync main ({commit_count} commits)",
         "--body", f"Automated sync PR from local main.\n\n**Commits:**\n```\n{ahead}\n```"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    if pr_result.returncode == 0:
        pr_url = pr_result.stdout.strip()
        print(f"[OK] PR created: {pr_url}")
        print("\n[i] Next steps:")
        print("   1. Wait for CI to pass")
        print("   2. Merge the PR on GitHub")
        print(f"   3. Delete sync branch: git push origin --delete {sync_branch}")
    else:
        print("[!] gh CLI failed (may not be installed or authenticated)")
        print(f"   Error: {pr_result.stderr}")
        print("\n[i] Manual steps:")
        print(f"   1. Go to GitHub and create PR: {sync_branch} -> main")
        print("   2. Merge after CI passes")
    
    return 0


def cmd_emergency(operation: str, reason: str) -> int:
    """Emergency override - logs the action."""
    print(f"⚠️  EMERGENCY OVERRIDE: {operation}")
    print(f"   Reason: {reason}")
    
    # Log the override
    log_file = Path(__file__).parent.parent / "artifacts" / "emergency_overrides.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "reason": reason,
        "branch": get_current_branch(),
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    print(f"📝 Logged to: {log_file}")
    
    if operation == "start-build-bypass":
        try:
            from datetime import timedelta
            git_common_result = subprocess.run(
                ["git", "rev-parse", "--git-common-dir"],
                capture_output=True, text=True, check=False,
            )
            if git_common_result.returncode == 0:
                git_common = Path(__file__).parent.parent / git_common_result.stdout.strip()
                if git_common_result.stdout.strip().startswith("/"):
                    git_common = Path(git_common_result.stdout.strip())
                current_branch = get_current_branch() or "unknown"
                slug = current_branch.replace("/", "__")
                bypass_dir = git_common / "lifeos" / "bypass"
                bypass_dir.mkdir(parents=True, exist_ok=True)
                bypass_token = {
                    "operation": operation,
                    "branch": current_branch,
                    "reason": reason,
                    "created_at_utc": datetime.now().isoformat(),
                    "expires_at_utc": (datetime.now() + timedelta(hours=4)).isoformat(),
                }
                token_path = bypass_dir / f"{slug}.json"
                token_path.write_text(json.dumps(bypass_token, indent=2))
                print(f"🔓 Bypass token written (4h): {token_path}")
        except Exception as exc:
            print(f"⚠️  Could not write bypass token: {exc}")

    print("⚠️  Proceeding with override. CEO review required.")
    
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Git Workflow Enforcement")
    parser.add_argument("--emergency", metavar="OPERATION", help="Emergency override")
    parser.add_argument("--reason", help="Reason for emergency override")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # branch subcommand
    branch_parser = subparsers.add_parser("branch", help="Branch operations")
    branch_sub = branch_parser.add_subparsers(dest="branch_cmd")
    
    create_parser = branch_sub.add_parser("create", help="Create new branch")
    create_parser.add_argument("name", help="Branch name (e.g., build/my-feature)")

    create_wt_parser = branch_sub.add_parser(
        "create-worktree",
        help="Create branch in isolated worktree",
    )
    create_wt_parser.add_argument("name", help="Branch name (e.g., build/my-feature)")
    
    branch_sub.add_parser("list", help="List active branches")
    
    # Other subcommands
    subparsers.add_parser("review", help="Prepare for review")
    subparsers.add_parser("merge", help="Merge to main")
    subparsers.add_parser("status", help="Show status")
    subparsers.add_parser("sync", help="Sync local main with remote via PR")
    
    args = parser.parse_args()
    
    # Emergency override
    if args.emergency:
        if not args.reason:
            print("❌ --reason required for emergency override")
            return 1
        return cmd_emergency(args.emergency, args.reason)
    
    # Route to command
    if args.command == "branch":
        if args.branch_cmd == "create":
            return cmd_branch_create(args.name)
        elif args.branch_cmd == "create-worktree":
            return cmd_branch_create_worktree(args.name)
        elif args.branch_cmd == "list":
            return cmd_branch_list()
        else:
            print("Usage: git_workflow.py branch [create|create-worktree|list]")
            return 1
    elif args.command == "review":
        return cmd_review_prepare()
    elif args.command == "merge":
        return cmd_merge()
    elif args.command == "status":
        return cmd_status()
    elif args.command == "sync":
        return cmd_sync()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
