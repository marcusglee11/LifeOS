#!/usr/bin/env python3
"""Run end-of-build closure flow: tests, stewardship gate, merge, cleanup."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.workflow_pack import (  # noqa: E402
    check_doc_stewardship,
    cleanup_after_merge,
    discover_changed_files,
    merge_to_main,
    run_closure_tests,
    update_state_and_backlog,
)


def _git_stdout(repo_root: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _working_tree_clean(repo_root: Path) -> bool:
    return not _git_stdout(repo_root, ["status", "--short"])


def _commit_doc_autofix(repo_root: Path) -> tuple[bool, str]:
    status_lines = _git_stdout(repo_root, ["status", "--short"]).splitlines()
    changed = [line[3:].strip() for line in status_lines if len(line) >= 4]
    if not changed:
        return True, "No doc auto-fix changes to commit."

    docs_only = all(path.startswith("docs/") for path in changed)
    if not docs_only:
        return False, "Unexpected non-doc changes detected after doc auto-fix."

    add_proc = subprocess.run(
        ["git", "-C", str(repo_root), "add", "docs/INDEX.md", "docs/LifeOS_Strategic_Corpus.md"],
        check=False,
        capture_output=True,
        text=True,
    )
    if add_proc.returncode != 0:
        details = (add_proc.stderr or "").strip() or (add_proc.stdout or "").strip()
        return False, f"Failed to stage doc auto-fix changes: {details or 'unknown error'}"

    commit_proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "commit",
            "-m",
            "chore: apply doc stewardship auto-fix before close",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if commit_proc.returncode != 0:
        details = (commit_proc.stderr or "").strip() or (commit_proc.stdout or "").strip()
        return False, f"Failed to commit doc auto-fix changes: {details or 'unknown error'}"
    return True, "Doc auto-fix changes committed."


def _print_report(
    *,
    branch: str,
    commits: list[str],
    test_results: list[str],
    what_done: list[str],
    what_remains: list[str],
) -> None:
    print("Branch")
    print(f"{branch} -> main")
    print()

    print("Commits")
    if commits:
        for line in commits:
            print(line)
    else:
        print("None")
    print()

    print("Test Results")
    if test_results:
        for line in test_results:
            print(line)
    else:
        print("None")
    print()

    print("What Was Done")
    if what_done:
        for line in what_done:
            print(line)
    else:
        print("None")
    print()

    print("What Remains")
    if what_remains:
        for line in what_remains:
            print(line)
    else:
        print("None")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run validation gates only; skip merge and cleanup.",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip post-merge cleanup (branch delete + active context clear).",
    )
    parser.add_argument(
        "--no-state-update",
        action="store_true",
        help="Skip automatic STATE/BACKLOG updates after merge.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    branch = _git_stdout(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"

    commits = _git_stdout(repo_root, ["log", "--oneline", "-n", "10"]).splitlines()
    test_results: list[str] = []
    what_done: list[str] = []
    what_remains: list[str] = []

    if branch in {"main", "master"}:
        what_remains.append("Switch to a feature/build branch before running close-build.")
        _print_report(
            branch=branch,
            commits=commits,
            test_results=test_results,
            what_done=what_done,
            what_remains=what_remains,
        )
        return 1

    if not _working_tree_clean(repo_root):
        what_remains.append("Working tree must be clean before close-build.")
        _print_report(
            branch=branch,
            commits=commits,
            test_results=test_results,
            what_done=what_done,
            what_remains=what_remains,
        )
        return 1

    changed_files = discover_changed_files(repo_root)
    test_run = run_closure_tests(repo_root, changed_files)
    test_results.append(f"{'PASS' if test_run['passed'] else 'FAIL'}: {test_run['summary']}")
    for command in test_run["commands_run"]:
        test_results.append(f"- {command}")
    if not test_run["passed"]:
        for failure in test_run["failures"]:
            test_results.append(f"  {failure}")
        what_remains.append("Fix failing closure tests.")
        _print_report(
            branch=branch,
            commits=commits,
            test_results=test_results,
            what_done=what_done,
            what_remains=what_remains,
        )
        return 1
    what_done.append("Closure targeted tests passed.")

    doc_check = check_doc_stewardship(repo_root, changed_files, auto_fix=True)
    if not doc_check["passed"]:
        test_results.append("FAIL: Doc stewardship gate failed.")
        for err in doc_check["errors"]:
            test_results.append(f"- {err}")
        what_remains.append("Resolve doc stewardship gate failures.")
        _print_report(
            branch=branch,
            commits=commits,
            test_results=test_results,
            what_done=what_done,
            what_remains=what_remains,
        )
        return 1

    if doc_check["required"]:
        if doc_check["auto_fixed"]:
            ok, msg = _commit_doc_autofix(repo_root)
            if not ok:
                what_remains.append(msg)
                _print_report(
                    branch=branch,
                    commits=commits,
                    test_results=test_results,
                    what_done=what_done,
                    what_remains=what_remains,
                )
                return 1
            what_done.append(msg)
        what_done.append("Doc stewardship gate passed.")
    else:
        what_done.append("Doc stewardship gate skipped (no docs changes).")

    if args.dry_run:
        what_done.append("Dry-run completed; merge and cleanup were skipped.")
        what_remains.append("Run close-build without --dry-run to merge and clean up.")
        _print_report(
            branch=branch,
            commits=commits,
            test_results=test_results,
            what_done=what_done,
            what_remains=what_remains,
        )
        return 0

    merge = merge_to_main(repo_root, branch)
    if not merge["success"]:
        test_results.append("FAIL: Merge to main failed.")
        for err in merge["errors"]:
            test_results.append(f"- {err}")
        what_remains.append("Resolve merge blockers and retry close-build.")
        _print_report(
            branch=branch,
            commits=commits,
            test_results=test_results,
            what_done=what_done,
            what_remains=what_remains,
        )
        return 1
    what_done.append(f"Merged to main (squash): {merge['merge_sha']}.")

    # Update STATE and BACKLOG
    if not args.no_state_update:
        state_update = update_state_and_backlog(
            repo_root,
            branch=branch,
            merge_sha=merge["merge_sha"],
            test_summary=test_run["summary"],
            skip_on_error=True,
        )
        if state_update["state_updated"]:
            what_done.append("Updated LIFEOS_STATE.md with Recent Win.")
        if state_update["backlog_updated"]:
            if state_update["items_marked"] > 0:
                what_done.append(
                    f"Updated BACKLOG.md: marked {state_update['items_marked']} item(s) done."
                )
            else:
                what_done.append("Updated BACKLOG.md timestamp (no matching items).")
        for err in state_update["errors"]:
            what_remains.append(f"State update warning: {err}")
    else:
        what_done.append("State update skipped by --no-state-update.")

    if args.no_cleanup:
        what_done.append("Cleanup skipped by --no-cleanup.")
    else:
        cleanup = cleanup_after_merge(repo_root, branch, clear_context=True)
        if cleanup["branch_deleted"]:
            what_done.append(f"Deleted local branch: {branch}.")
        else:
            what_done.append(f"Branch not deleted: {branch}.")
        if cleanup["context_cleared"]:
            what_done.append("Cleared .context/active_work.yaml.")
        for err in cleanup["errors"]:
            what_remains.append(err)

    _print_report(
        branch=branch,
        commits=commits,
        test_results=test_results,
        what_done=what_done,
        what_remains=what_remains,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
