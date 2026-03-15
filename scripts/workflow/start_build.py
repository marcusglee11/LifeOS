#!/usr/bin/env python3
"""Create or recover an isolated worktree with a low-friction topic-first interface."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
_VALID_KINDS = ("build", "fix", "hotfix", "spike")
_PREFIX_RE = re.compile(r"^(build|fix|hotfix|spike)/(.*)$")
_WORKTREE_READY_RE = re.compile(r"Worktree ready at:\s*(.+)")
_SCOPED_PREFIXES = tuple(f"{kind}/" for kind in _VALID_KINDS)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _slugify_topic(raw: str) -> str:
    value = re.sub(r"[^a-z0-9-]", "-", raw.strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    if not value:
        raise ValueError("topic must contain at least one alphanumeric character")
    return value[:30].rstrip("-") or "work"


def _normalize_branch(topic: str, kind: str) -> tuple[str, str]:
    topic = topic.strip()
    if not topic:
        raise ValueError("topic is required")

    match = _PREFIX_RE.match(topic)
    if match:
        topic_kind = match.group(1)
        topic_rest = match.group(2)
        if kind != "build" and topic_kind != kind:
            raise ValueError(
                f"topic prefix '{topic_kind}/' conflicts with --kind '{kind}'"
            )
        kind = topic_kind
        topic = topic_rest

    if kind not in _VALID_KINDS:
        raise ValueError(f"kind must be one of: {', '.join(_VALID_KINDS)}")

    slug = _slugify_topic(topic)
    return kind, f"{kind}/{slug}"


def _extract_worktree_path(output: str, branch: str) -> Optional[str]:
    for line in output.splitlines():
        match = _WORKTREE_READY_RE.search(line)
        if match:
            return match.group(1).strip()

    # Deterministic fallback if output format changed.
    try:
        from scripts import git_workflow as gw

        primary = gw._resolve_primary_repo()
        if primary is not None:
            short = gw._derive_worktree_short_name(branch)
            return str((primary / ".worktrees" / short).resolve())
    except Exception:
        pass

    return None


def _git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _git_stdout(repo_root: Path, args: list[str]) -> str:
    proc = _git(repo_root, args)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _resolve_primary_repo() -> Optional[Path]:
    try:
        from scripts import git_workflow as gw
    except Exception:
        return None
    return gw._resolve_primary_repo()


def _derive_worktree_short_name(branch: str) -> str:
    try:
        from scripts import git_workflow as gw
        return gw._derive_worktree_short_name(branch)
    except Exception:
        short = branch.split("/", 1)[1] if "/" in branch else branch
        short = re.sub(r"[^a-z0-9-]", "-", short.lower())
        short = re.sub(r"-+", "-", short).strip("-")
        return (short[:30].rstrip("-") or "worktree")


def _validate_branch_name(branch: str) -> Optional[str]:
    try:
        from scripts import git_workflow as gw
        return gw.validate_branch_name(branch)
    except Exception:
        if not branch.startswith(_SCOPED_PREFIXES):
            return "branch must start with build/, fix/, hotfix/, or spike/"
        return None


def _branch_exists(repo_root: Path, branch: str) -> bool:
    return _git(repo_root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]).returncode == 0


def _default_base_branch(primary_repo: Path) -> Optional[str]:
    if _branch_exists(primary_repo, "main"):
        return "main"
    if _branch_exists(primary_repo, "master"):
        return "master"
    return None


def _linked_worktree_for_branch(primary_repo: Path, branch: str) -> Optional[Path]:
    proc = _git(primary_repo, ["worktree", "list", "--porcelain"])
    if proc.returncode != 0:
        return None

    candidate: Optional[Path] = None
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            candidate = Path(line.split(" ", 1)[1].strip())
            continue
        if line.startswith("branch refs/heads/") and candidate is not None:
            wt_branch = line.removeprefix("branch refs/heads/").strip()
            if wt_branch == branch and candidate != primary_repo:
                return candidate
    return None


def _stash_push_if_needed(primary_repo: Path, branch: str) -> tuple[Optional[str], Optional[str]]:
    status = _git_stdout(primary_repo, ["status", "--porcelain", "-uall"])
    if not status:
        return None, None

    token = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    marker = f"lifeos-recover-primary:{branch}:{token}"
    push = _git(primary_repo, ["stash", "push", "-u", "-m", marker])
    if push.returncode != 0:
        details = (push.stderr or "").strip() or (push.stdout or "").strip()
        return None, f"failed to stash primary worktree changes: {details or 'unknown error'}"

    list_proc = _git(primary_repo, ["stash", "list", "--format=%gd%x00%s"])
    if list_proc.returncode != 0:
        details = (list_proc.stderr or "").strip() or (list_proc.stdout or "").strip()
        return None, f"failed to inspect stash list: {details or 'unknown error'}"

    for line in list_proc.stdout.splitlines():
        if "\x00" not in line:
            continue
        ref, subject = line.split("\x00", 1)
        if marker in subject:
            return ref.strip(), None

    # `git stash push` can report success with "No local changes to save".
    output = f"{push.stdout}\n{push.stderr}".lower()
    if "no local changes to save" in output:
        return None, None
    return None, "stash was created but could not be located for apply"


def _upsert_active_branch_record(primary_repo: Path, branch: str, worktree_path: Path) -> None:
    try:
        from scripts import git_workflow as gw
    except Exception:
        return

    data = gw.load_active_branches(primary_repo)
    matches = [item for item in data.get("branches", []) if item.get("name") == branch]
    if matches:
        primary_item = max(matches, key=lambda item: str(item.get("created", "")))
        for item in matches:
            item["base"] = item.get("base") or "main"
            if item is primary_item:
                item["status"] = "active"
                item["worktree_path"] = str(worktree_path)
                item.pop("closed_at", None)
            elif item.get("status") == "active":
                item["status"] = "closed"
                item["worktree_path"] = None
                item["closed_at"] = datetime.now().isoformat()
        gw._mark_registry_updated(data)
        gw.save_active_branches(data, primary_repo)
        return

    data.setdefault("branches", []).append(
        {
            "name": branch,
            "created": datetime.now().isoformat(),
            "status": "active",
            "base": "main",
            "worktree_path": str(worktree_path),
        }
    )
    gw._mark_registry_updated(data)
    gw.save_active_branches(data, primary_repo)


def recover_primary_branch(branch: Optional[str] = None) -> dict:
    """Recover dirty scoped-branch work in primary by moving it to a linked worktree."""
    primary = _resolve_primary_repo()
    if primary is None:
        return {
            "ok": False,
            "error": "Cannot resolve primary worktree (main/master branch not found).",
            "branch": None,
            "worktree_path": None,
            "stash_ref": None,
            "worktree_created": False,
            "primary_repo": None,
        }

    current_branch = _git_stdout(primary, ["branch", "--show-current"])
    target_branch = (branch or current_branch).strip()
    if not target_branch:
        return {
            "ok": False,
            "error": "No branch to recover. Provide a scoped branch or check one out first.",
            "branch": None,
            "worktree_path": None,
            "stash_ref": None,
            "worktree_created": False,
            "primary_repo": str(primary),
        }

    validation_error = _validate_branch_name(target_branch)
    if validation_error:
        return {
            "ok": False,
            "error": validation_error,
            "branch": target_branch,
            "worktree_path": None,
            "stash_ref": None,
            "worktree_created": False,
            "primary_repo": str(primary),
        }

    if not _branch_exists(primary, target_branch):
        return {
            "ok": False,
            "error": f"Branch does not exist locally: {target_branch}",
            "branch": target_branch,
            "worktree_path": None,
            "stash_ref": None,
            "worktree_created": False,
            "primary_repo": str(primary),
        }

    linked = _linked_worktree_for_branch(primary, target_branch)
    if linked is None:
        linked = primary / ".worktrees" / _derive_worktree_short_name(target_branch)

    if linked.exists() and _linked_worktree_for_branch(primary, target_branch) is None:
        return {
            "ok": False,
            "error": (
                "Worktree path already exists but is not linked to target branch: "
                f"{linked}. Run 'git worktree prune' or remove the path."
            ),
            "branch": target_branch,
            "worktree_path": str(linked),
            "stash_ref": None,
            "worktree_created": False,
            "primary_repo": str(primary),
        }

    stash_ref: Optional[str] = None
    if current_branch == target_branch and _git_stdout(primary, ["rev-parse", "--git-common-dir"]) == ".git":
        stash_ref, stash_err = _stash_push_if_needed(primary, target_branch)
        if stash_err:
            return {
                "ok": False,
                "error": stash_err,
                "branch": target_branch,
                "worktree_path": str(linked),
                "stash_ref": None,
                "worktree_created": False,
                "primary_repo": str(primary),
            }

        base_branch = _default_base_branch(primary)
        if not base_branch:
            return {
                "ok": False,
                "error": "Primary repo missing both main and master branches.",
                "branch": target_branch,
                "worktree_path": str(linked),
                "stash_ref": stash_ref,
                "worktree_created": False,
                "primary_repo": str(primary),
            }
        switch_proc = _git(primary, ["checkout", base_branch])
        if switch_proc.returncode != 0:
            details = (switch_proc.stderr or "").strip() or (switch_proc.stdout or "").strip()
            return {
                "ok": False,
                "error": f"failed to switch primary repo to {base_branch}: {details or 'unknown error'}",
                "branch": target_branch,
                "worktree_path": str(linked),
                "stash_ref": stash_ref,
                "worktree_created": False,
                "primary_repo": str(primary),
            }

    worktree_created = False
    linked_registered = _linked_worktree_for_branch(primary, target_branch)
    if linked_registered is None:
        add_proc = _git(primary, ["worktree", "add", str(linked), target_branch])
        if add_proc.returncode != 0:
            details = (add_proc.stderr or "").strip() or (add_proc.stdout or "").strip()
            return {
                "ok": False,
                "error": f"failed to create linked worktree: {details or 'unknown error'}",
                "branch": target_branch,
                "worktree_path": str(linked),
                "stash_ref": stash_ref,
                "worktree_created": False,
                "primary_repo": str(primary),
            }
        worktree_created = True
    else:
        linked = linked_registered

    if stash_ref:
        pop_proc = _git(linked, ["stash", "pop", stash_ref])
        if pop_proc.returncode != 0:
            details = (pop_proc.stderr or "").strip() or (pop_proc.stdout or "").strip()
            return {
                "ok": False,
                "error": (
                    "moved to linked worktree but stash apply reported conflicts: "
                    f"{details or 'unknown error'}"
                ),
                "branch": target_branch,
                "worktree_path": str(linked),
                "stash_ref": stash_ref,
                "worktree_created": worktree_created,
                "primary_repo": str(primary),
            }

    _upsert_active_branch_record(primary, target_branch, linked)
    _write_build_record(
        primary_repo=primary,
        branch=target_branch,
        kind=target_branch.split("/")[0] if "/" in target_branch else "build",
        topic=target_branch.split("/", 1)[1] if "/" in target_branch else target_branch,
        worktree_path=str(linked),
        entrypoint="recover_primary",
    )
    return {
        "ok": True,
        "error": None,
        "branch": target_branch,
        "worktree_path": str(linked),
        "stash_ref": stash_ref,
        "worktree_created": worktree_created,
        "primary_repo": str(primary),
    }


def _write_build_record(
    primary_repo: Path,
    branch: str,
    kind: str,
    topic: str,
    worktree_path: str,
    entrypoint: str,
) -> None:
    """Write a local build record to the git common dir (not tracked by repo)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(primary_repo), "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            return
        git_common = Path(result.stdout.strip())
        if not git_common.is_absolute():
            git_common = primary_repo / git_common
        record_dir = git_common / "lifeos" / "builds"
        record_dir.mkdir(parents=True, exist_ok=True)
        slug = branch.replace("/", "__")
        record_path = record_dir / f"{slug}.json"
        record = {
            "version": 1,
            "branch": branch,
            "kind": kind,
            "topic": topic,
            "entrypoint": entrypoint,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "primary_repo": str(primary_repo),
            "worktree_path": worktree_path,
            "status": "active",
        }
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True))
    except Exception:
        pass  # best-effort; never block the build


def _should_auto_recover_existing_primary_branch(branch: str) -> bool:
    primary = _resolve_primary_repo()
    if primary is None:
        return False
    if _git_stdout(primary, ["rev-parse", "--git-common-dir"]) != ".git":
        return False
    if _git_stdout(primary, ["branch", "--show-current"]) != branch:
        return False
    return branch.startswith(_SCOPED_PREFIXES) and _branch_exists(primary, branch)


def _emit_recovery_text(result: dict) -> None:
    if result.get("ok"):
        print(f"✓ Recovered branch into linked worktree: {result['worktree_path']}")
        print(f"  Run: cd {result['worktree_path']}")
        if result.get("stash_ref"):
            print(f"  Applied stashed changes from: {result['stash_ref']}")
        return
    print(f"❌ {result.get('error', 'primary-branch recovery failed')}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "topic",
        nargs="?",
        help="Topic slug or full branch (e.g., auth-token or fix/auth-token)",
    )
    parser.add_argument(
        "--kind",
        default="build",
        choices=_VALID_KINDS,
        help="Branch kind prefix (default: build)",
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base branch (currently only 'main' is supported)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON result")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Reserved for automation; currently informational only",
    )
    parser.add_argument(
        "--recover-primary",
        action="store_true",
        help="Recover scoped branch work from primary into a linked worktree.",
    )
    args = parser.parse_args()

    if args.recover_primary:
        branch_override: Optional[str] = None
        if args.topic:
            try:
                _kind, branch_override = _normalize_branch(args.topic, args.kind)
            except ValueError:
                branch_override = args.topic.strip()

        result = recover_primary_branch(branch_override)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            _emit_recovery_text(result)
        return 0 if result.get("ok") else 1

    if not args.topic:
        err = "topic is required unless --recover-primary is set"
        if args.json:
            print(json.dumps({"ok": False, "error": err, "branch": None, "worktree_path": None}))
        else:
            print(f"❌ {err}", file=sys.stderr)
        return 2

    if args.base != "main":
        err = "Only --base main is currently supported."
        if args.json:
            print(json.dumps({"ok": False, "error": err, "branch": None, "worktree_path": None}))
        else:
            print(f"❌ {err}", file=sys.stderr)
        return 2

    try:
        kind, branch = _normalize_branch(args.topic, args.kind)
    except ValueError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": str(exc),
                        "branch": None,
                        "worktree_path": None,
                    }
                )
            )
        else:
            print(f"❌ {exc}", file=sys.stderr)
        return 2

    # Verify main is healthy before branching — catches orphaned staged changes
    # or untracked files left by a failed merge_to_main.
    _main_staged = _git_stdout(REPO_ROOT, ["diff", "--cached", "--name-only"])
    _main_untracked = _git_stdout(REPO_ROOT, ["ls-files", "--others", "--exclude-standard"])
    _health_issues: list[str] = []
    if _main_staged:
        _health_issues.append(
            f"{len(_main_staged.splitlines())} staged file(s) on main — "
            "likely from a failed merge. Run 'git reset HEAD' on main to unstage."
        )
    if _main_untracked:
        _health_issues.append(
            f"{len(_main_untracked.splitlines())} untracked file(s) on main — "
            "Article XIX will block future merges. Stage, gitignore, or remove them."
        )
    if _health_issues:
        err = "MAIN_UNHEALTHY: " + " | ".join(_health_issues)
        if args.json:
            print(json.dumps({"ok": False, "error": err, "branch": branch, "worktree_path": None}))
        else:
            print(f"❌ {err}", file=sys.stderr)
        return 1

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "git_workflow.py"),
        "branch",
        "create-worktree",
        branch,
    ]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    worktree_path = _extract_worktree_path(stdout, branch)
    auto_recovered = False

    if proc.returncode != 0 and _should_auto_recover_existing_primary_branch(branch):
        recovered = recover_primary_branch(branch)
        if recovered.get("ok"):
            auto_recovered = True
            proc = subprocess.CompletedProcess(
                cmd,
                0,
                stdout=(
                    (stdout.rstrip() + "\n\n" if stdout.strip() else "")
                    + f"ℹ️  Branch already existed in primary; recovered to {recovered['worktree_path']}\n"
                    + f"  Run: cd {recovered['worktree_path']}\n"
                ),
                stderr=stderr,
            )
            stdout = proc.stdout or ""
            worktree_path = recovered.get("worktree_path")

    if proc.returncode == 0 and worktree_path:
        primary = _resolve_primary_repo()
        if primary:
            m = _PREFIX_RE.match(branch)
            wt_kind = m.group(1) if m else kind
            wt_topic = m.group(2) if m else branch
            _write_build_record(
                primary_repo=primary,
                branch=branch,
                kind=wt_kind,
                topic=wt_topic,
                worktree_path=worktree_path,
                entrypoint="start_build",
            )

    if args.json:
        payload = {
            "ok": proc.returncode == 0,
            "kind": kind,
            "branch": branch,
            "worktree_path": worktree_path,
            "cd": f"cd {worktree_path}" if worktree_path else None,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": proc.returncode,
            "auto_recovered": auto_recovered,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
