#!/usr/bin/env python3
"""Run end-of-build closure flow: tests, stewardship gate, merge, cleanup."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.closure_policy import (  # noqa: E402
    BASE_BRANCH,
    CLOSURE_POLICY_VERSION,
    get_tier_execution_policy,
    resolve_closure_tier,
)
from runtime.tools.workflow_pack import (  # noqa: E402
    check_doc_stewardship,
    cleanup_after_merge,
    merge_to_main,
    run_closure_tests,
    run_quality_gates,
    update_state_and_backlog,
    update_structured_backlog,
)


def _close_build_record(repo_root: Path, branch: str) -> None:
    """Mark the local build record as closed after successful merge."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            return
        git_common = Path(result.stdout.strip())
        if not git_common.is_absolute():
            git_common = repo_root / git_common
        slug = branch.replace("/", "__")
        record_path = git_common / "lifeos" / "builds" / f"{slug}.json"
        if not record_path.exists():
            return
        record = json.loads(record_path.read_text())
        record["status"] = "closed"
        record["closed_at_utc"] = datetime.now(timezone.utc).isoformat()
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True))
    except Exception:
        pass


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
    # Use --untracked-files=no so untracked files from concurrent agent sessions
    # (e.g. council review artifacts still in-flight) do not block the merge gate.
    # The check still catches uncommitted tracked-file changes (staged or unstaged).
    return not _git_stdout(repo_root, ["status", "--short", "--untracked-files=no"])


def _is_primary_worktree(repo_root: Path) -> bool:
    return _git_stdout(repo_root, ["rev-parse", "--git-common-dir"]).strip() == ".git"


def _branch_requires_isolation(branch: str) -> bool:
    return branch.startswith(("build/", "fix/", "hotfix/", "spike/"))


def _current_working_tree_paths(repo_root: Path) -> list[str]:
    status_lines = _git_stdout(repo_root, ["status", "--short"]).splitlines()
    paths: list[str] = []
    for line in status_lines:
        if len(line) < 4:
            continue
        candidate = line[3:].strip()
        if " -> " in candidate:
            old_path, new_path = candidate.split(" -> ", 1)
            paths.extend([old_path.strip(), new_path.strip()])
        elif candidate:
            paths.append(candidate)
    deduped: list[str] = []
    seen: set[str] = set()
    for path in paths:
        normalized = path.replace("\\", "/")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _review_checkpoint_path(repo_root: Path, branch: str) -> Path:
    git_common = _git_stdout(repo_root, ["rev-parse", "--git-common-dir"]).strip()
    git_common_dir = Path(git_common) if git_common else repo_root / ".git"
    if not git_common_dir.is_absolute():
        git_common_dir = repo_root / git_common_dir
    slug = branch.replace("/", "__")
    return git_common_dir / "lifeos" / "reviews" / f"{slug}.md"


def _write_review_checkpoint(
    repo_root: Path,
    *,
    branch: str,
    changed_files: list[str],
    commits: list[str],
    test_results: list[str],
) -> tuple[bool, str]:
    try:
        checkpoint_path = _review_checkpoint_path(repo_root, branch)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        merge_base = _git_stdout(repo_root, ["merge-base", BASE_BRANCH, "HEAD"])
        diff_range = f"{merge_base}..HEAD" if merge_base else "HEAD~1..HEAD"
        diff_stat = _git_stdout(repo_root, ["diff", "--stat", diff_range]) or "Unavailable"

        review_commands = [
            f"BASE=$(git merge-base {BASE_BRANCH} HEAD)",
            'git log --oneline "$BASE"..HEAD',
            'git diff --stat "$BASE"..HEAD',
            'git diff "$BASE"..HEAD',
            "python3 scripts/workflow/quality_gate.py check --scope changed --json",
            "git diff --check",
        ]
        if any(path.endswith(".py") and path.startswith("runtime/") for path in changed_files):
            review_commands.extend(
                [
                    "/mnt/c/Users/cabra/Projects/LifeOS/.venv/bin/python -m ruff check runtime",
                    (
                        "/mnt/c/Users/cabra/Projects/LifeOS/.venv/bin/python "
                        "-m ruff format --check runtime"
                    ),
                ]
            )

        changed_lines = [f"- {path}" for path in changed_files[:80]] or ["- None detected"]
        if len(changed_files) > 80:
            changed_lines.append(f"- ... ({len(changed_files) - 80} more)")

        commit_lines = [f"- {line}" for line in commits] or ["- None"]
        result_lines = [f"- {line}" for line in test_results] or ["- None yet"]

        review_skill_path = (
            repo_root / ".claude" / "skills" / "review-build" / "SKILL.md"
        ).relative_to(repo_root)

        checkpoint_path.write_text(
            "\n".join(
                [
                    "# Post-Build Review Brief",
                    "",
                    f"Generated: {datetime.now(timezone.utc).isoformat()}",
                    f"Branch: `{branch}`",
                    f"Review Skill: `{review_skill_path}`",
                    "",
                    "## Review Commands",
                    "```bash",
                    *review_commands,
                    "```",
                    "",
                    "## Recent Commits",
                    *commit_lines,
                    "",
                    "## Changed Files",
                    *changed_lines,
                    "",
                    "## Closure Verification",
                    *result_lines,
                    "",
                    "## Diff Stat",
                    "```text",
                    diff_stat,
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return True, str(checkpoint_path)
    except Exception as exc:
        return False, f"Failed to write review checkpoint: {exc}"


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


def _print_report(result: dict) -> None:
    print("Branch")
    print(f"{result['branch']} -> {result['base_branch']}")
    print()

    print("Closure Policy")
    print(f"Version: {result['closure_policy_version']}")
    print(f"Tier: {result['closure_tier']}")
    print(f"Selected Checks: {', '.join(result['selected_checks']) or 'None'}")
    print(f"Skipped Checks: {', '.join(result['skipped_checks']) or 'None'}")
    print(
        "Post-Merge Updates Suppressed: "
        f"{'yes' if result['post_merge_updates_suppressed'] else 'no'}"
    )
    print()

    print("Commits")
    if result["commits"]:
        for line in result["commits"]:
            print(line)
    else:
        print("None")
    print()

    print("Test Results")
    if result["test_results"]:
        for line in result["test_results"]:
            print(line)
    else:
        print("None")
    print()

    print("What Was Done")
    if result["what_done"]:
        for line in result["what_done"]:
            print(line)
    else:
        print("None")
    print()

    print("What Remains")
    if result["what_remains"]:
        for line in result["what_remains"]:
            print(line)
    else:
        print("None")


def run_closure(
    repo_root: Path,
    *,
    dry_run: bool = False,
    no_cleanup: bool = False,
    no_state_update: bool = False,
    allow_concurrent_wip: bool = False,
) -> dict:
    branch = _git_stdout(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"

    commits = _git_stdout(repo_root, ["log", "--oneline", "-n", "10"]).splitlines()
    result = {
        "ok": False,
        "exit_code": 1,
        "branch": branch,
        "base_branch": "",
        "closure_policy_version": CLOSURE_POLICY_VERSION,
        "closure_tier": "full",
        "classification_reason": "",
        "selected_checks": [],
        "skipped_checks": [],
        "post_merge_updates_suppressed": False,
        "commits": commits,
        "test_results": [],
        "what_done": [],
        "what_remains": [],
        "changed_paths": [],
        "final_validated_paths": [],
        "no_changes": False,
        "outcome": "error",
    }

    def fail(message: str, *, exit_code: int = 1) -> dict:
        result["what_remains"].append(message)
        result["exit_code"] = exit_code
        return result

    if branch in {"main", "master"}:
        return fail("Switch to a feature/build branch before running close-build.")

    if _branch_requires_isolation(branch) and _is_primary_worktree(repo_root):
        result["what_remains"].append(
            "ISOLATION_REQUIRED: close-build for "
            f"'{branch}' must run from the linked worktree, not primary."
        )
        result["what_remains"].append(
            "Recover this branch in-place: "
            "python3 scripts/workflow/start_build.py --recover-primary"
        )
        result["what_remains"].append(
            "Or create a fresh isolated branch: "
            "python3 scripts/workflow/start_build.py <topic> --kind "
            f"{branch.split('/', 1)[0]}"
        )
        return result

    if not _working_tree_clean(repo_root):
        return fail("Working tree must be clean before close-build.")

    tier_info = resolve_closure_tier(repo_root)
    result["base_branch"] = tier_info["base_branch"]
    result["closure_tier"] = tier_info["closure_tier"]
    result["classification_reason"] = tier_info["classification_reason"]
    result["changed_paths"] = list(tier_info["changed_paths"])
    result["outcome"] = tier_info["outcome"]
    branch_kind = branch.split("/", 1)[0] if "/" in branch else None
    policy = get_tier_execution_policy(
        tier_info["closure_tier"],
        branch_kind=branch_kind,
        changed_paths=tier_info["changed_paths"],
    )
    result["selected_checks"] = list(policy["selected_checks"])
    result["skipped_checks"] = list(policy["skipped_checks"])
    result["post_merge_updates_suppressed"] = bool(policy["post_merge_updates_suppressed"])

    if tier_info["outcome"] == "full_fallback":
        result["what_done"].append(
            f"Closure tier fell back to full: {tier_info['classification_reason']}"
        )

    if tier_info["outcome"] == "no_changes":
        result["no_changes"] = True
        result["what_done"].append("No changes to close; closure exited as a no-op.")
        result["ok"] = True
        result["exit_code"] = 0
        return result

    changed_files = list(tier_info["changed_paths"])
    final_validation_paths = list(changed_files)

    if policy["run_targeted_pytest"] and tier_info["closure_tier"] == "full":
        test_run = run_closure_tests(
            repo_root,
            changed_files,
            closure_tier=tier_info["closure_tier"],
        )
        result["test_results"].append(
            f"{'PASS' if test_run['passed'] else 'FAIL'}: {test_run['summary']}"
        )
        for command in test_run["commands_run"]:
            result["test_results"].append(f"- {command}")
        if not test_run["passed"]:
            for failure in test_run["failures"]:
                result["test_results"].append(f"  {failure}")
            return fail("Fix failing closure tests.")
        result["what_done"].append("Closure targeted tests passed.")

    if policy["run_general_quality_gate"]:
        quality_check = run_quality_gates(repo_root, changed_files, scope="changed", fix=False)
        result["test_results"].append(
            f"{'PASS' if quality_check['passed'] else 'FAIL'}: {quality_check['summary']}"
        )
        for command in quality_check["commands_run"]:
            result["test_results"].append(f"- {command}")
        if not quality_check["passed"]:
            for row in quality_check["results"]:
                if row["passed"] or row["mode"] != "blocking":
                    continue
                detail = str(row["details"]).strip() or "blocking quality failure"
                result["test_results"].append(f"  {row['tool']}: {detail}")
            return fail("Fix blocking quality gate failures.")
        result["what_done"].append("Closure quality gate passed.")

    if policy["run_doc_stewardship"]:
        doc_check = check_doc_stewardship(repo_root, changed_files, auto_fix=True)
        if not doc_check["passed"]:
            result["test_results"].append("FAIL: Doc stewardship gate failed.")
            for err in doc_check["errors"]:
                result["test_results"].append(f"- {err}")
            return fail("Resolve doc stewardship gate failures.")

        if doc_check["required"]:
            if doc_check["auto_fixed"]:
                ok, msg = _commit_doc_autofix(repo_root)
                if not ok:
                    return fail(msg)
                result["what_done"].append(msg)
            result["what_done"].append("Doc stewardship gate passed.")
            final_validation_paths = sorted(
                {
                    *changed_files,
                    *[path for path in doc_check.get("docs_files", []) if isinstance(path, str)],
                    *_current_working_tree_paths(repo_root),
                }
            )
        else:
            result["what_done"].append("Doc stewardship gate skipped (no docs changes).")

    if policy["quality_tools"]:
        tool_check = run_quality_gates(
            repo_root,
            final_validation_paths,
            scope="changed",
            fix=False,
            tool_names=policy["quality_tools"],
        )
        result["test_results"].append(
            f"{'PASS' if tool_check['passed'] else 'FAIL'}: {tool_check['summary']}"
        )
        for command in tool_check["commands_run"]:
            result["test_results"].append(f"- {command}")
        if not tool_check["passed"]:
            for row in tool_check["results"]:
                if row["passed"] or row["mode"] != "blocking":
                    continue
                detail = str(row["details"]).strip() or "blocking quality failure"
                result["test_results"].append(f"  {row['tool']}: {detail}")
            return fail("Fix blocking quality gate failures.")
        result["what_done"].append(
            f"Tier-specific quality checks passed: {', '.join(policy['quality_tools'])}."
        )

    if policy["run_targeted_pytest"] and tier_info["closure_tier"] != "full":
        test_run = run_closure_tests(
            repo_root,
            final_validation_paths,
            closure_tier=tier_info["closure_tier"],
        )
        result["test_results"].append(
            f"{'PASS' if test_run['passed'] else 'FAIL'}: {test_run['summary']}"
        )
        for command in test_run["commands_run"]:
            result["test_results"].append(f"- {command}")
        if not test_run["passed"]:
            for failure in test_run["failures"]:
                result["test_results"].append(f"  {failure}")
            return fail("Fix failing closure tests.")
        result["what_done"].append("Closure targeted tests passed.")

    result["final_validated_paths"] = list(final_validation_paths)

    if policy["run_review_checkpoint"]:
        review_checkpoint_ok, review_checkpoint_msg = _write_review_checkpoint(
            repo_root,
            branch=branch,
            changed_files=final_validation_paths,
            commits=commits,
            test_results=result["test_results"],
        )
        if not review_checkpoint_ok:
            return fail(review_checkpoint_msg)
        result["what_done"].append(f"Generated review checkpoint: {review_checkpoint_msg}.")

    if dry_run:
        result["what_done"].append("Dry-run completed; merge and cleanup were skipped.")
        result["what_remains"].append("Run close-build without --dry-run to merge and clean up.")
        result["ok"] = True
        result["exit_code"] = 0
        return result

    merge = merge_to_main(repo_root, branch, allow_concurrent_wip=allow_concurrent_wip)
    if not merge["success"]:
        result["test_results"].append("FAIL: Merge to main failed.")
        for err in merge["errors"]:
            prefix = "- Git lock blocker: " if err.startswith("Git lock blocker:") else "- "
            result["test_results"].append(
                f"{prefix}{err.removeprefix('Git lock blocker: ') if err.startswith('Git lock blocker:') else err}"
            )
        return fail("Resolve merge blockers and retry close-build.")
    result["what_done"].append(f"Merged to main (squash): {merge['merge_sha']}.")
    for warning in merge.get("errors", []):
        result["what_remains"].append(f"Merge warning: {warning}")
    _close_build_record(repo_root, branch)

    primary_repo_str = merge.get("primary_repo")
    if primary_repo_str and policy["run_runtime_status_regeneration"]:
        primary_repo = Path(primary_repo_str)
        status_gen = primary_repo / "scripts" / "generate_runtime_status.py"
        if status_gen.exists():
            status_proc = subprocess.run(
                [sys.executable, str(status_gen)],
                check=False,
                cwd=str(primary_repo),
                capture_output=True,
                text=True,
            )
            if status_proc.returncode == 0:
                subprocess.run(
                    ["git", "-C", str(primary_repo), "add", "artifacts/status/runtime_status.json"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                has_staged = _git_stdout(primary_repo, ["diff", "--cached", "--name-only"])
                if has_staged:
                    commit_env = os.environ.copy()
                    commit_env["LIFEOS_MAIN_COMMIT_ALLOWED"] = "1"
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            str(primary_repo),
                            "commit",
                            "-m",
                            "chore: refresh runtime_status.json (post-merge)",
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                        env=commit_env,
                    )
                result["what_done"].append(
                    "Regenerated and committed runtime_status.json for freshness compliance."
                )
            else:
                result["what_remains"].append(
                    f"Runtime status generation failed: {status_proc.stderr.strip()}"
                )
    else:
        result["what_done"].append("Skipped runtime_status.json refresh per closure tier policy.")

    if not no_state_update and policy["run_state_backlog_updates"]:
        state_update = update_state_and_backlog(
            repo_root,
            branch=branch,
            merge_sha=merge["merge_sha"],
            test_summary=result["test_results"][0] if result["test_results"] else "No closure checks run.",
            skip_on_error=True,
        )
        if state_update["state_updated"]:
            result["what_done"].append("Updated LIFEOS_STATE.md with Recent Win.")
        if state_update["backlog_updated"]:
            if state_update["items_marked"] > 0:
                result["what_done"].append(
                    f"Updated BACKLOG.md: marked {state_update['items_marked']} item(s) done."
                )
            else:
                result["what_done"].append("Updated BACKLOG.md timestamp (no matching items).")
        for err in state_update["errors"]:
            result["what_remains"].append(f"State update warning: {err}")

        if policy["run_structured_backlog_updates"]:
            structured_update = update_structured_backlog(
                repo_root,
                merge_sha=merge["merge_sha"],
                skip_on_error=True,
            )
            if structured_update["updated"]:
                result["what_done"].append(
                    f"Marked {len(structured_update['tasks_completed'])} "
                    "task(s) complete in backlog.yaml: "
                    f"{', '.join(structured_update['tasks_completed'])}"
                )
            for err in structured_update["errors"]:
                result["what_remains"].append(f"Structured backlog warning: {err}")
    else:
        result["what_done"].append("Skipped STATE/BACKLOG updates per close-build policy.")

    if no_cleanup:
        result["what_done"].append("Cleanup skipped by --no-cleanup.")
    else:
        cleanup = cleanup_after_merge(repo_root, branch, clear_context=True)
        if cleanup["branch_deleted"]:
            result["what_done"].append(f"Deleted local branch: {branch}.")
        else:
            result["what_done"].append(f"Branch not deleted: {branch}.")
        if cleanup["context_cleared"]:
            result["what_done"].append("Cleared .context/active_work.yaml.")
        if cleanup.get("worktree_removed"):
            result["what_done"].append("Removed linked worktree.")
        for err in cleanup["errors"]:
            if err.startswith("Git lock blocker:"):
                result["what_remains"].append(err)
            else:
                result["what_remains"].append(err)

    result["ok"] = True
    result["exit_code"] = 0
    return result


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
    parser.add_argument(
        "--allow-concurrent-wip",
        action="store_true",
        help=(
            "Skip the primary-repo untracked-files gate and use --no-verify on the merge commit. "
            "For Article XIX chicken-and-egg: concurrent agent WIP is intentionally present. "
            "Documents the exemption in the commit message."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON result.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    result = run_closure(
        repo_root,
        dry_run=args.dry_run,
        no_cleanup=args.no_cleanup,
        no_state_update=args.no_state_update,
        allow_concurrent_wip=args.allow_concurrent_wip,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_report(result)
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
