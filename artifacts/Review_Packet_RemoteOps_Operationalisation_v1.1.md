---
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
mission_ref: "Close validator mission + enforce safe_cleanup isolation safeguards"
version: "1.1"
status: "PENDING_REVIEW"
---

# Review_Packet_RemoteOps_Operationalisation_v1.1

## Scope Envelope

- Allowed: `scripts/**`, `runtime/tests/**`, `artifacts/validation_samples/v2.1a-p0/**`
- Forbidden observed: none

## Summary

Validator mission is closed with delegated remote housekeeping semantics; local DNS failures no longer block mission closure. Isolation enforcement is hardened via explicit `--apply`, rationale requirement, protected-path guardrails, invoker logging, and updated pre-commit guidance.

## Acceptance Mapping

- Mission closure artifact with verbatim evidence: PASS
- Isolation mutation requires explicit apply+rationale: PASS
- Protected path isolation blocked unless override: PASS
- Invoker metadata logged for isolate actions: PASS
- Tests: PASS (27 passed)

## Changed Files

- `scripts/safe_cleanup.py`
- `scripts/hooks/pre-commit`
- `runtime/tests/test_safe_cleanup.py`
- `artifacts/validation_samples/v2.1a-p0/MISSION_CLOSURE_VALIDATOR_P0R.md`
- `artifacts/validation_samples/v2.1a-p0/enforcement_pytest_output.txt`

## Appendix A — Flattened Code

### File: `scripts/safe_cleanup.py`

````python
#!/usr/bin/env python3
"""
Safe Cleanup - Enforces Isolation-by-Default for untracked files.

This script prevents accidental deletion of work products by moving unclassified 
untracked files to an isolation vault instead of deleting them.

Usage:
    python scripts/safe_cleanup.py --isolate
    python scripts/safe_cleanup.py --isolate --apply --rationale "why isolation is needed"
    python scripts/safe_cleanup.py --delete --file <path> --manifest <manifest_path> --rationale "<reason>"
"""

import os
import sys
import shutil
import subprocess
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).parent.parent.resolve()
ISOLATION_VAULT = REPO_ROOT / "artifacts" / "99_archive" / "stray"
CLEANUP_LOG = REPO_ROOT / "logs" / "cleanup_ledger.jsonl"
PROTECTED_PREFIXES = (".github/", "runtime/", "scripts/", "tests/", "docs/")


def run_git(args: List[str], repo_root: Path = REPO_ROOT) -> str:
    result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=repo_root)
    return result.stdout.strip()


def get_untracked_files(repo_root: Path = REPO_ROOT) -> List[Path]:
    # Only get untracked files, excluding ignored ones
    output = run_git(["ls-files", "--others", "--exclude-standard"], repo_root=repo_root)
    if not output:
        return []
    return [repo_root / f for f in output.split("\n")]


def get_hash(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()))


def _best_effort_parent_cmd(ppid: int) -> Optional[str]:
    if ppid <= 0:
        return None
    try:
        result = subprocess.run(
            ["ps", "-o", "command=", "-p", str(ppid)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        return output if output else None
    except Exception:
        return None


def _invoker_info() -> Dict[str, Any]:
    ppid = os.getppid()
    return {
        "pid": os.getpid(),
        "ppid": ppid,
        "argv": list(sys.argv),
        "parent_cmd": _best_effort_parent_cmd(ppid),
    }


def is_protected_path(file_path: Path, repo_root: Path = REPO_ROOT) -> bool:
    rel = file_path.resolve().relative_to(repo_root.resolve()).as_posix()
    return any(rel.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def log_action(
    action: str,
    file_path: Path,
    repo_root: Path,
    target_path: Optional[Path] = None,
    rationale: Optional[str] = None,
    manifest: Optional[Path] = None,
) -> None:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "file": _relative_to_repo(Path(file_path), repo_root),
        "hash": get_hash(file_path) if Path(file_path).exists() else None,
        "target": _relative_to_repo(Path(target_path), repo_root) if target_path else None,
        "rationale": rationale,
        "manifest": _relative_to_repo(Path(manifest), repo_root) if manifest else None,
        "invoker": _invoker_info(),
    }
    CLEANUP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CLEANUP_LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry) + "\n")


def isolate(
    *,
    apply: bool,
    rationale: Optional[str],
    allow_protected: bool,
    repo_root: Path = REPO_ROOT,
) -> int:
    files = get_untracked_files(repo_root=repo_root)
    if not files:
        print("✅ No untracked files to isolate.")
        return 0

    protected = [f for f in files if is_protected_path(f, repo_root=repo_root)]
    if protected and not allow_protected:
        print("🚫 BLOCKED: Protected paths detected in isolate candidate set.")
        for path in protected:
            print(f"   • {path.relative_to(repo_root)}")
        print("")
        print("Stage these files instead, or rerun with --allow-protected when intentional.")
        return 1

    if not apply:
        print(f"🔍 Dry run: {len(files)} untracked file(s) would be isolated.")
        for path in files:
            print(f"   • {path.relative_to(repo_root)}")
        print("")
        print("No files moved. Re-run with --apply --rationale \"...\" to isolate.")
        return 0

    if not rationale:
        print("❌ Error: --isolate --apply requires --rationale")
        return 1

    date_str = datetime.now().strftime("%Y%m%d")
    isolation_dir = (repo_root / "artifacts" / "99_archive" / "stray" / date_str).resolve()
    isolation_dir.mkdir(parents=True, exist_ok=True)

    print(f"📦 Isolating {len(files)} untracked file(s) to {isolation_dir}...")

    for f in files:
        target = isolation_dir / f.name
        # Ensure unique name in vault
        count = 1
        while target.exists():
            target = isolation_dir / f"{f.stem}_{count}{f.suffix}"
            count += 1

        log_action("isolate", f, repo_root=repo_root, target_path=target, rationale=rationale)
        shutil.move(str(f), str(target))
        print(f"   • {f.relative_to(repo_root)} -> {target.relative_to(repo_root)}")

    return 0


def delete_file(file_path: str, manifest: str, rationale: str, repo_root: Path = REPO_ROOT) -> int:
    p = repo_root / file_path
    if not p.exists():
        print(f"❌ Error: File not found: {file_path}")
        return 1

    m = repo_root / manifest
    if not m.exists():
        print(f"❌ Error: Manifest not found: {manifest}")
        return 1

    # Simple check for manifest content
    manifest_content = m.read_text(encoding="utf-8")
    if str(file_path) not in manifest_content:
        print(f"❌ Error: File {file_path} not found in manifest {manifest}")
        return 1

    print(f"🗑️  Deleting {file_path}...")
    log_action("delete", p, repo_root=repo_root, rationale=rationale, manifest=m)
    p.unlink()
    print("   • Deleted successfully.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Safe Cleanup Wrapper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--isolate", action="store_true", help="Isolate untracked files (dry-run unless --apply)")
    group.add_argument("--delete", action="store_true", help="Permanently delete a file (requires manifest)")

    parser.add_argument("--apply", action="store_true", help="Apply isolation (required to mutate)")
    parser.add_argument("--allow-protected", action="store_true", help="Allow isolation of protected paths")
    parser.add_argument("--file", help="File to delete")
    parser.add_argument("--manifest", help="Path to Review Packet containing deletion manifest")
    parser.add_argument("--rationale", help="Rationale for isolate/apply or deletion")

    args = parser.parse_args(argv)

    if args.isolate:
        if args.apply and not args.rationale:
            print("❌ Error: --isolate --apply requires --rationale")
            return 1
        return isolate(
            apply=args.apply,
            rationale=args.rationale,
            allow_protected=args.allow_protected,
            repo_root=REPO_ROOT,
        )

    if args.delete:
        if not all([args.file, args.manifest, args.rationale]):
            print("❌ Error: --delete requires --file, --manifest, and --rationale")
            return 1
        return delete_file(args.file, args.manifest, args.rationale, repo_root=REPO_ROOT)

    return 1

if __name__ == "__main__":
    sys.exit(main())
````

### File: `scripts/hooks/pre-commit`

````text
#!/bin/bash
#
# Git Pre-Commit Hook for LifeOS
#
# Enforces Git Workflow Protocol v1.0:
# - No direct commits to main/master
# - Must use feature branches
#
# Installation:
#   cp scripts/hooks/pre-commit .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit

PROTECTED_BRANCHES=("main" "master")
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)

# Check if on protected branch
for branch in "${PROTECTED_BRANCHES[@]}"; do
    if [ "$CURRENT_BRANCH" = "$branch" ]; then
        echo ""
        echo "🚫 BLOCKED: Direct commits to '$branch' are not allowed."
        echo ""
        echo "Git Workflow Protocol v1.0 requires feature branches."
        echo ""
        echo "To create a feature branch:"
        echo "   python scripts/git_workflow.py branch create build/<topic>"
        echo ""
        echo "To bypass in emergency (requires justification):"
        echo "   git commit --no-verify -m 'message'"
        echo "   python scripts/git_workflow.py --emergency 'direct-commit' --reason 'your reason'"
        echo ""
        exit 1
    fi
done

# Validate branch naming convention
VALID_PREFIXES=("build/" "fix/" "hotfix/" "spike/")
IS_VALID=false

for prefix in "${VALID_PREFIXES[@]}"; do
    if [[ "$CURRENT_BRANCH" == $prefix* ]]; then
        IS_VALID=true
        break
    fi
done

if [ "$IS_VALID" = false ] && [ -n "$CURRENT_BRANCH" ]; then
    echo ""
    echo "⚠️  WARNING: Branch '$CURRENT_BRANCH' doesn't follow naming convention."
    echo ""
    echo "Valid prefixes: build/, fix/, hotfix/, spike/"
    echo "Example: build/my-feature"
    echo ""
    echo "Proceeding anyway, but consider renaming your branch."
    echo ""
fi

# ------------------------------------------------------------------------------
# Article XIX Enforcement: Untracked Asset Stewardship (Anti-Deletion)
# ------------------------------------------------------------------------------

UNTRACKED_FILES=$(git ls-files --others --exclude-standard)

if [ -n "$UNTRACKED_FILES" ]; then
    echo ""
    echo "🚨 BLOCKED: Untracked files detected in working tree."
    echo "============================================================"
    echo "$UNTRACKED_FILES"
    echo "============================================================"
    echo ""
    echo "Article XIX requires untracked assets to be staged or intentionally isolated."
    echo ""
    echo "Recommended: stage active work files for this commit:"
    echo "   git add <file>"
    echo ""
    echo "If isolation is intentional (moves files to archive vault):"
    echo "   python scripts/safe_cleanup.py --isolate --apply --rationale \"why isolation is needed\""
    echo ""
    echo "Note: protected paths (.github/, runtime/, scripts/, tests/, docs/) require --allow-protected."
    echo ""
    echo "To bypass (emergency only):"
    echo "   git commit --no-verify"
    echo ""
    exit 1
fi

exit 0
````

### File: `runtime/tests/test_safe_cleanup.py`

````python
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True)


def _load_safe_cleanup_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "safe_cleanup.py"
    spec = importlib.util.spec_from_file_location("safe_cleanup_under_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "init")
    return repo


def _configure_module_paths(module, repo: Path) -> None:
    module.REPO_ROOT = repo
    module.ISOLATION_VAULT = repo / "artifacts" / "99_archive" / "stray"
    module.CLEANUP_LOG = repo / "logs" / "cleanup_ledger.jsonl"


def test_isolate_without_apply_is_dry_run(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    (repo / "draft.txt").write_text("hello\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.isolate(apply=False, rationale=None, allow_protected=False, repo_root=repo)
    assert rc == 0
    assert (repo / "draft.txt").exists()


def test_isolate_apply_requires_rationale(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    (repo / "draft.txt").write_text("hello\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.main(["--isolate", "--apply"])
    assert rc == 1
    assert (repo / "draft.txt").exists()


def test_isolate_blocks_protected_paths_without_override(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    target = repo / "runtime" / "tmp.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("protected\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.isolate(
        apply=True,
        rationale="cleanup",
        allow_protected=False,
        repo_root=repo,
    )
    assert rc == 1
    assert target.exists()


def test_isolate_allow_protected_moves_and_logs_invoker(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    target = repo / "runtime" / "tmp.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("protected\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.isolate(
        apply=True,
        rationale="intentional isolation",
        allow_protected=True,
        repo_root=repo,
    )
    assert rc == 0
    assert not target.exists()

    date_str = mod.datetime.now().strftime("%Y%m%d")
    isolated = repo / "artifacts" / "99_archive" / "stray" / date_str / "tmp.txt"
    assert isolated.exists()

    ledger = repo / "logs" / "cleanup_ledger.jsonl"
    assert ledger.exists()
    entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert entries
    last = entries[-1]
    assert last["rationale"] == "intentional isolation"
    assert "invoker" in last
    assert set(last["invoker"]).issuperset({"pid", "ppid", "argv", "parent_cmd"})
````

### File: `artifacts/validation_samples/v2.1a-p0/MISSION_CLOSURE_VALIDATOR_P0R.md`

````markdown
# MISSION_CLOSURE_VALIDATOR_P0R

Closure policy: delegated remote cleanup (server-side workflow owns remote branch deletion).

## Current branch
~~~bash
git rev-parse --abbrev-ref HEAD
~~~
~~~text
build/eol-clean-invariant
~~~
exit_code: 0

## Latest commit
~~~bash
git log -1 --oneline
~~~
~~~text
cd4455d docs: closure-grade final reconciliation (v2.2)
~~~
exit_code: 0

## Merge commit detail
~~~bash
git show --name-only --oneline d07a6b4
~~~
~~~text
d07a6b4 feat(validation): validator suite v2.1a P0 + hardening (P0.8)
~~~
exit_code: 0

## Containment: hardening commit
~~~bash
git branch --contains 7875d8e
~~~
~~~text
* build/eol-clean-invariant
~~~
exit_code: 0

## Containment: merge commit
~~~bash
git branch --contains d07a6b4
~~~
~~~text
* build/eol-clean-invariant
~~~
exit_code: 0

## Local branch ref check
~~~bash
git branch --list validator-suite-v2.1a-p0
~~~
~~~text

~~~
exit_code: 0

## Workflow presence
~~~bash
ls -l .github/workflows/branch_housekeeping_delete_merged_validator_suite.yml
~~~
~~~text
-rwxrwxrwx 1 cabra cabra 4937 Feb 10 14:29 .github/workflows/branch_housekeeping_delete_merged_validator_suite.yml
~~~
exit_code: 0

## Remote branch lookup (expected network-dependent)
~~~bash
git ls-remote --heads origin validator-suite-v2.1a-p0
~~~
~~~text
ssh: Could not resolve hostname github.com: Temporary failure in name resolution
fatal: Could not read from remote repository.

Please make sure you have the correct access rights
and the repository exists.
~~~
exit_code: 128

## gh availability (expected optional)
~~~bash
gh --version
~~~
~~~text
environment: line 12: gh: command not found
~~~
exit_code: 127

## Closure decision

- Validator P0/P0.8 is merged into build/eol-clean-invariant (contains d07a6b4 and 7875d8e).
- Local validator branch ref is absent.
- Remote branch cleanup is delegated to server-side workflow to avoid workstation DNS dependency.
- Mission status: CLOSED (delegated remote housekeeping).

````

### File: `artifacts/validation_samples/v2.1a-p0/enforcement_pytest_output.txt`

````text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /mnt/c/Users/cabra/Projects/LifeOS
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 27 items

runtime/tests/test_safe_cleanup.py ....                                  [ 14%]
runtime/tests/orchestration/test_remote_ops.py ....                      [ 29%]
runtime/tests/orchestration/test_validation_orchestrator.py .....        [ 48%]
runtime/tests/orchestration/test_workspace_lock.py ...                   [ 59%]
runtime/tests/validation/test_cleanliness.py ....                        [ 74%]
runtime/tests/validation/test_gate_runner_and_acceptor.py ....           [ 88%]
runtime/tests/validation/test_evidence.py ...                            [100%]

============================== 27 passed in 3.71s ==============================
````

