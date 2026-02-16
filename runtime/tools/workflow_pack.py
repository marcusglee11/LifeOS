"""Workflow pack helpers for low-friction multi-agent handoffs."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Sequence

from runtime.util.atomic_write import atomic_write_text

# Import for BACKLOG parsing (will handle import error gracefully)
try:
    from recursive_kernel.backlog_parser import ItemStatus, mark_item_done, parse_backlog
except ImportError:
    parse_backlog = None
    mark_item_done = None
    ItemStatus = None


ACTIVE_WORK_RELATIVE_PATH = Path(".context/active_work.yaml")


def _unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build_active_work_payload(
    *,
    branch: str,
    latest_commits: Sequence[str],
    focus: Sequence[str],
    tests_targeted: Sequence[str],
    findings_open: Sequence[dict[str, str]],
) -> dict:
    """Build normalized active-work payload."""
    normalized_findings = []
    for finding in findings_open:
        finding_id = str(finding.get("id", "")).strip()
        severity = str(finding.get("severity", "")).strip().lower()
        status = str(finding.get("status", "")).strip().lower()
        if not finding_id or not severity or not status:
            continue
        normalized_findings.append(
            {"id": finding_id, "severity": severity, "status": status}
        )

    return {
        "version": "1.0",
        "branch": branch.strip() or "unknown",
        "latest_commits": _unique_ordered(latest_commits),
        "focus": _unique_ordered(focus),
        "tests_targeted": _unique_ordered(tests_targeted),
        "findings_open": normalized_findings,
    }


def write_active_work(repo_root: Path, payload: dict) -> Path:
    """Write .context/active_work.yaml deterministically."""
    output_path = Path(repo_root) / ACTIVE_WORK_RELATIVE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def read_active_work(repo_root: Path) -> dict:
    """Read .context/active_work.yaml, returning a normalized fallback when absent."""
    input_path = Path(repo_root) / ACTIVE_WORK_RELATIVE_PATH
    if not input_path.exists():
        return build_active_work_payload(
            branch="unknown",
            latest_commits=[],
            focus=[],
            tests_targeted=[],
            findings_open=[],
        )
    try:
        loaded = json.loads(input_path.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    return build_active_work_payload(
        branch=str(loaded.get("branch", "unknown")),
        latest_commits=loaded.get("latest_commits") or [],
        focus=loaded.get("focus") or [],
        tests_targeted=loaded.get("tests_targeted") or [],
        findings_open=loaded.get("findings_open") or [],
    )


def _matches(file_path: str, prefixes: Sequence[str]) -> bool:
    return any(file_path == prefix or file_path.startswith(prefix) for prefix in prefixes)


def route_targeted_tests(changed_files: Sequence[str]) -> list[str]:
    """Map changed files to targeted test commands."""
    files = _unique_ordered(changed_files)

    routed: list[str] = []

    def add(command: str) -> None:
        if command not in routed:
            routed.append(command)

    for file_path in files:
        if _matches(
            file_path,
            (
                "runtime/orchestration/openclaw_bridge.py",
                "runtime/tests/orchestration/test_openclaw_bridge.py",
            ),
        ):
            add("pytest -q runtime/tests/orchestration/test_openclaw_bridge.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/orchestration/missions/autonomous_build_cycle.py",
                "runtime/tests/orchestration/missions/test_autonomous_loop.py",
            ),
        ):
            add("pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/agents/api.py",
                "runtime/agents/opencode_client.py",
                "runtime/tests/test_agent_api_usage_plumbing.py",
                "tests/test_agent_api.py",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py"
            )
            continue

        if _matches(
            file_path,
            (
                "runtime/tools/workflow_pack.py",
                "runtime/tests/test_workflow_pack.py",
                "scripts/workflow/",
            ),
        ):
            add("pytest -q runtime/tests/test_workflow_pack.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/tools/openclaw_models_preflight.sh",
                "runtime/tools/openclaw_model_policy_assert.py",
                "runtime/tests/test_openclaw_model_policy_assert.py",
            ),
        ):
            add("pytest -q runtime/tests/test_openclaw_model_policy_assert.py")
            continue

    if not routed:
        routed.append("pytest -q runtime/tests")
    return routed


def discover_changed_files(repo_root: Path) -> list[str]:
    """Discover changed files with staged-first precedence."""
    repo = Path(repo_root)
    probes = [
        ["git", "-C", str(repo), "diff", "--name-only", "--cached"],
        ["git", "-C", str(repo), "diff", "--name-only"],
        ["git", "-C", str(repo), "diff", "--name-only", "HEAD~1..HEAD"],
    ]
    for cmd in probes:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            continue
        files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if files:
            return _unique_ordered(files)
    return []


def run_closure_tests(repo_root: Path, changed_files: Sequence[str]) -> dict:
    """Run targeted closure tests derived from changed files."""
    commands = route_targeted_tests(changed_files)
    commands_run: list[str] = []
    failures: list[str] = []
    passed_count = 0

    for command in commands:
        commands_run.append(command)
        proc = subprocess.run(
            shlex.split(command),
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            passed_count += 1
            continue
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        details = stderr or stdout or f"exit code {proc.returncode}"
        failures.append(f"{command}: {details}")

    passed = not failures
    summary = f"{passed_count}/{len(commands_run)} targeted test command(s) passed."
    if failures:
        summary += f" Failures: {len(failures)}."

    return {
        "passed": passed,
        "commands_run": commands_run,
        "summary": summary,
        "failures": failures,
    }


def check_doc_stewardship(
    repo_root: Path,
    changed_files: Sequence[str],
    auto_fix: bool = True,
) -> dict:
    """Run doc stewardship gate only when docs paths are present."""
    docs_changed = any(path == "docs" or path.startswith("docs/") for path in changed_files)
    if not docs_changed:
        return {
            "required": False,
            "passed": True,
            "errors": [],
            "auto_fixed": False,
        }

    errors = []

    # Check if docs/11_admin/ files changed -> run admin validators
    admin_changed = any(
        path == "docs/11_admin" or path.startswith("docs/11_admin/")
        for path in changed_files
    )

    if admin_changed:
        # Admin structure check (always blocking)
        admin_struct_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "admin-structure-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if admin_struct_proc.returncode != 0:
            errors.append(f"Admin structure check failed:\n{admin_struct_proc.stdout}")

        # Admin archive link ban check (always blocking)
        admin_archive_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "admin-archive-link-ban-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if admin_archive_proc.returncode != 0:
            errors.append(f"Admin archive link ban check failed:\n{admin_archive_proc.stdout}")

        # Freshness check (mode-gated: off/warn/block)
        freshness_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "freshness-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if freshness_proc.returncode != 0:
            errors.append(f"Freshness check failed:\n{freshness_proc.stdout}")

    # Check if docs/02_protocols/ files changed -> run protocols validators
    protocols_changed = any(
        path == "docs/02_protocols" or path.startswith("docs/02_protocols/")
        for path in changed_files
    )

    if protocols_changed:
        # Protocols structure check (always blocking)
        protocols_struct_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "protocols-structure-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if protocols_struct_proc.returncode != 0:
            errors.append(f"Protocols structure check failed:\n{protocols_struct_proc.stdout}")

        # Artefact index check (always blocking)
        protocols_index_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "artefact-index-check", str(repo_root), "--directory", "docs/02_protocols"],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if protocols_index_proc.returncode != 0:
            errors.append(f"Protocols artefact index check failed:\n{protocols_index_proc.stdout}")

        # Global archive link ban check (always blocking)
        protocols_link_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "docs-archive-link-ban-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if protocols_link_proc.returncode != 0:
            errors.append(f"Archive link ban check failed:\n{protocols_link_proc.stdout}")

    # Check if docs/03_runtime/ files changed -> run runtime validators
    runtime_changed = any(
        path == "docs/03_runtime" or path.startswith("docs/03_runtime/")
        for path in changed_files
    )

    if runtime_changed:
        # Runtime structure check (always blocking)
        runtime_struct_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "runtime-structure-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if runtime_struct_proc.returncode != 0:
            errors.append(f"Runtime structure check failed:\n{runtime_struct_proc.stdout}")

        # Artefact index check (always blocking)
        runtime_index_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "artefact-index-check", str(repo_root), "--directory", "docs/03_runtime"],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if runtime_index_proc.returncode != 0:
            errors.append(f"Runtime artefact index check failed:\n{runtime_index_proc.stdout}")

        # Global archive link ban check (always blocking)
        runtime_link_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "docs-archive-link-ban-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if runtime_link_proc.returncode != 0:
            errors.append(f"Archive link ban check failed:\n{runtime_link_proc.stdout}")

    # Check if docs/99_archive/ files changed -> run archive validators
    archive_changed = any(
        path == "docs/99_archive" or path.startswith("docs/99_archive/")
        for path in changed_files
    )

    if archive_changed:
        # Archive structure check (always blocking)
        archive_struct_proc = subprocess.run(
            [sys.executable, "-m", "doc_steward.cli", "archive-structure-check", str(repo_root)],
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if archive_struct_proc.returncode != 0:
            errors.append(f"Archive structure check failed:\n{archive_struct_proc.stdout}")

    # Run existing canonical doc stewardship gate (unchanged)
    cmd = [sys.executable, "scripts/claude_doc_stewardship_gate.py"]
    if auto_fix:
        cmd.append("--auto-fix")

    proc = subprocess.run(
        cmd,
        check=False,
        cwd=Path(repo_root),
        capture_output=True,
        text=True,
    )

    payload: dict = {}
    stdout = (proc.stdout or "").strip()
    if stdout:
        try:
            loaded = json.loads(stdout)
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            payload = loaded

    for item in payload.get("errors", []):
        text = str(item).strip()
        if text:
            errors.append(text)
    if not payload and proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        errors.append(stderr or "doc stewardship gate returned non-zero without JSON output")

    passed = (not errors) and bool(payload.get("passed")) and proc.returncode == 0
    auto_fixed = bool(payload.get("auto_fix_applied") or payload.get("auto_fix_success"))

    return {
        "required": True,
        "passed": passed,
        "errors": errors,
        "auto_fixed": auto_fixed,
        "docs_files": payload.get("docs_files", []),
    }


def merge_to_main(repo_root: Path, branch: str) -> dict:
    """Merge a feature branch into main using squash merge."""
    source_branch = branch.strip()
    if not source_branch:
        return {"success": False, "merge_sha": None, "errors": ["source branch is empty"]}
    if source_branch in {"main", "master"}:
        return {
            "success": False,
            "merge_sha": None,
            "errors": [f"cannot merge protected branch '{source_branch}'"],
        }

    repo = Path(repo_root)
    errors: list[str] = []

    safety = subprocess.run(
        [sys.executable, "scripts/repo_safety_gate.py", "--operation", "merge"],
        check=False,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if safety.returncode != 0:
        details = (safety.stderr or "").strip() or (safety.stdout or "").strip()
        return {
            "success": False,
            "merge_sha": None,
            "errors": [f"safety gate blocked merge: {details or 'unknown failure'}"],
        }

    steps = [
        ("checkout main", ["git", "-C", str(repo), "checkout", "main"]),
        ("pull --ff-only", ["git", "-C", str(repo), "pull", "--ff-only"]),
        ("squash merge", ["git", "-C", str(repo), "merge", "--squash", source_branch]),
        (
            "commit squash merge",
            ["git", "-C", str(repo), "commit", "-m", f"feat: Merge {source_branch} (squashed)"],
        ),
    ]

    for label, cmd in steps:
        run_env = None
        if label == "commit squash merge":
            run_env = os.environ.copy()
            run_env["LIFEOS_MAIN_COMMIT_ALLOWED"] = "1"
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            env=run_env,
        )
        if proc.returncode == 0:
            continue
        details = (proc.stderr or "").strip() or (proc.stdout or "").strip()
        if label == "pull --ff-only":
            lowered = details.lower()
            offline_markers = (
                "could not resolve hostname",
                "temporary failure in name resolution",
                "could not read from remote repository",
                "failed to connect",
            )
            if any(marker in lowered for marker in offline_markers):
                # Offline fallback: proceed with local main if remote is unreachable.
                continue
        errors.append(f"{label} failed: {details or f'exit code {proc.returncode}'}")
        subprocess.run(
            ["git", "-C", str(repo), "checkout", source_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        return {"success": False, "merge_sha": None, "errors": errors}

    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    merge_sha = head.stdout.strip() if head.returncode == 0 else None
    if not merge_sha:
        errors.append("failed to resolve merge commit SHA")
        return {"success": False, "merge_sha": None, "errors": errors}

    return {"success": True, "merge_sha": merge_sha, "errors": []}


def cleanup_after_merge(repo_root: Path, branch: str, clear_context: bool = True) -> dict:
    """Cleanup local branch and active context artifact after merge."""
    repo = Path(repo_root)
    source_branch = branch.strip()

    errors: list[str] = []
    branch_deleted = False
    if source_branch and source_branch not in {"main", "master"}:
        proc = subprocess.run(
            ["git", "-C", str(repo), "branch", "-d", source_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            branch_deleted = True
        else:
            details = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            errors.append(
                f"failed to delete local branch '{source_branch}': {details or f'exit code {proc.returncode}'}"
            )

    context_path = repo / ACTIVE_WORK_RELATIVE_PATH
    context_cleared = False
    if clear_context:
        try:
            if context_path.exists():
                context_path.unlink()
            context_cleared = not context_path.exists()
        except OSError as exc:
            errors.append(f"failed to clear {ACTIVE_WORK_RELATIVE_PATH}: {exc}")

    return {
        "branch_deleted": branch_deleted,
        "context_cleared": context_cleared,
        "errors": errors,
    }


def _extract_win_details(
    repo_root: Path,
    branch: str,
    merge_sha: str,
    test_summary: str,
) -> dict:
    """
    Extract meaningful Recent Win entry from branch and commits.

    Args:
        repo_root: Repository root path
        branch: Branch name (e.g., "build/doc-refresh-and-test-debt")
        merge_sha: Merge commit SHA
        test_summary: Test summary string from test run

    Returns:
        dict with keys: title, details, merge_sha_short
    """
    # Extract title from branch name
    # Remove prefixes like "build/", "fix/", "hotfix/", "spike/"
    title_raw = re.sub(r"^(build|fix|hotfix|spike)/", "", branch)
    # Replace hyphens/underscores with spaces and title-case
    title_words = re.split(r"[-_]+", title_raw)
    title = " ".join(word.capitalize() for word in title_words if word)

    # Get commit messages
    commits_output = ""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "log", "--format=%s", f"{branch}", "--not", "main"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        commits_output = proc.stdout.strip()

    # Build details from commits
    if commits_output:
        commit_lines = [line.strip() for line in commits_output.splitlines() if line.strip()]
        # Truncate to first 5 if too many
        if len(commit_lines) > 5:
            details = "; ".join(commit_lines[:5]) + f" (and {len(commit_lines) - 5} more)"
        else:
            details = "; ".join(commit_lines)
    else:
        # Fallback to title if git log fails
        details = title

    # Include test metrics if non-trivial
    if test_summary and "passed" in test_summary.lower():
        details += f" — {test_summary}"

    return {
        "title": title,
        "details": details,
        "merge_sha_short": merge_sha[:7],
    }


def _update_lifeos_state(
    state_path: Path,
    title: str,
    details: str,
    merge_sha_short: str,
    skip_on_error: bool = True,
) -> dict:
    """
    Update LIFEOS_STATE.md with Recent Win and timestamp.

    Args:
        state_path: Path to LIFEOS_STATE.md
        title: Win title (e.g., "Doc Refresh And Test Debt")
        details: Win details (e.g., "Fixed bugs; Added tests")
        merge_sha_short: Short merge SHA (7 chars)
        skip_on_error: If True, return error dict instead of raising

    Returns:
        dict with keys: success (bool), errors (list)
    """
    errors = []

    if not state_path.exists():
        msg = f"STATE file not found: {state_path}"
        if skip_on_error:
            return {"success": False, "errors": [msg]}
        raise FileNotFoundError(msg)

    try:
        content = state_path.read_text(encoding="utf-8")
    except Exception as exc:
        msg = f"Failed to read STATE file: {exc}"
        if skip_on_error:
            return {"success": False, "errors": [msg]}
        raise

    # Update Last Updated timestamp and revision
    today = datetime.now().strftime("%Y-%m-%d")

    def increment_revision(match):
        rev_str = match.group(1)
        try:
            rev_num = int(rev_str)
            return f"**Last Updated:** {today} (rev{rev_num + 1})"
        except ValueError:
            # If can't parse, just use (updated)
            return f"**Last Updated:** {today} (updated)"

    # Try to update Last Updated line with revision increment
    updated_content, num_subs = re.subn(
        r"\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2} \(rev(\d+)\)",
        increment_revision,
        content,
    )

    # If no match with revision, try without revision
    if num_subs == 0:
        updated_content = re.sub(
            r"\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}",
            f"**Last Updated:** {today}",
            content,
        )

    # Find the Recent Wins section and add new entry
    recent_wins_pattern = r"(## 🟩 Recent Wins\s*\n)"
    new_win_entry = f"- **{today}:** {title} — {details} (merge commit {merge_sha_short})\n"

    match = re.search(recent_wins_pattern, updated_content)
    if match:
        # Insert new win right after the section header
        insert_pos = match.end()
        updated_content = (
            updated_content[:insert_pos]
            + new_win_entry
            + updated_content[insert_pos:]
        )
    else:
        # Recent Wins section not found - skip win addition
        msg = "Recent Wins section not found in STATE file"
        errors.append(msg)

    # Write atomically
    try:
        atomic_write_text(state_path, updated_content)
    except Exception as exc:
        msg = f"Failed to write STATE file: {exc}"
        if skip_on_error:
            return {"success": False, "errors": [msg]}
        raise

    return {"success": True, "errors": errors}


def _match_backlog_item(
    branch: str,
    commit_messages: list[str],
    backlog_items: list,
    threshold: float = 0.7,
):
    """
    Match branch/commits to BACKLOG items using fuzzy similarity.

    Args:
        branch: Branch name (e.g., "build/doc-refresh-and-test-debt")
        commit_messages: List of commit message subjects
        backlog_items: List of BacklogItem objects
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        Best matching BacklogItem or None if no match above threshold
    """
    if not backlog_items:
        return None

    # Extract keywords from branch and commits
    keywords = []
    # Remove branch prefix and split on hyphens/underscores
    branch_clean = re.sub(r"^(build|fix|hotfix|spike)/", "", branch)
    keywords.extend(re.split(r"[-_/]+", branch_clean.lower()))

    # Add words from commit messages
    for msg in commit_messages:
        keywords.extend(msg.lower().split())

    # Combine into a search string
    search_text = " ".join(keywords)

    # Score each BACKLOG item
    best_match = None
    best_score = 0.0

    for item in backlog_items:
        item_text = item.title.lower()
        # Use SequenceMatcher for fuzzy matching
        score = SequenceMatcher(None, search_text, item_text).ratio()

        # Also check for substring matches (boost score)
        for keyword in keywords:
            if len(keyword) > 3 and keyword in item_text:
                score += 0.15  # Boost for keyword match

        if score > best_score:
            best_score = score
            best_match = item

    if best_score >= threshold:
        return best_match

    return None


def _update_backlog_state(
    backlog_path: Path,
    branch: str,
    commit_messages: list[str],
    skip_on_error: bool = True,
) -> dict:
    """
    Update BACKLOG.md timestamp and mark matching items as done.

    Args:
        backlog_path: Path to BACKLOG.md
        branch: Branch name
        commit_messages: List of commit message subjects
        skip_on_error: If True, return error dict instead of raising

    Returns:
        dict with keys: success (bool), items_marked (int), errors (list)
    """
    errors = []
    items_marked = 0

    if not backlog_path.exists():
        msg = f"BACKLOG file not found: {backlog_path}"
        if skip_on_error:
            return {"success": False, "items_marked": 0, "errors": [msg]}
        raise FileNotFoundError(msg)

    # Update timestamp
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        content = backlog_path.read_text(encoding="utf-8")
        updated_content = re.sub(
            r"\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}",
            f"**Last Updated:** {today}",
            content,
        )
        atomic_write_text(backlog_path, updated_content)
    except Exception as exc:
        msg = f"Failed to update BACKLOG timestamp: {exc}"
        if skip_on_error:
            return {"success": False, "items_marked": 0, "errors": [msg]}
        raise

    # Try to find and mark matching item
    if parse_backlog is None or mark_item_done is None:
        errors.append("backlog_parser not available (import failed)")
        return {"success": True, "items_marked": 0, "errors": errors}

    try:
        items = parse_backlog(backlog_path)
        # Filter to TODO items only
        todo_items = [item for item in items if item.status == ItemStatus.TODO]

        if todo_items:
            matched_item = _match_backlog_item(
                branch=branch,
                commit_messages=commit_messages,
                backlog_items=todo_items,
                threshold=0.3,  # Lower threshold to catch more matches
            )

            if matched_item:
                mark_item_done(backlog_path, matched_item)
                items_marked = 1
        else:
            errors.append("No TODO items found in BACKLOG")

    except Exception as exc:
        msg = f"Failed to mark BACKLOG item: {exc}"
        if skip_on_error:
            errors.append(msg)
        else:
            raise

    return {"success": True, "items_marked": items_marked, "errors": errors}


def update_state_and_backlog(
    repo_root: Path,
    branch: str,
    merge_sha: str,
    test_summary: str,
    skip_on_error: bool = True,
) -> dict:
    """
    Orchestrate STATE and BACKLOG updates after successful merge.

    Args:
        repo_root: Repository root path
        branch: Branch name (e.g., "build/test-debt-stabilization")
        merge_sha: Merge commit SHA
        test_summary: Test summary string from test run
        skip_on_error: If True, continue on errors (warn, don't block)

    Returns:
        dict with keys:
            - state_updated (bool): STATE file was updated
            - backlog_updated (bool): BACKLOG file was updated
            - items_marked (int): Number of BACKLOG items marked done
            - errors (list): Any errors/warnings encountered
    """
    repo_root = Path(repo_root)
    errors = []
    state_updated = False
    backlog_updated = False
    items_marked = 0

    # Extract win details
    win_details = _extract_win_details(
        repo_root=repo_root,
        branch=branch,
        merge_sha=merge_sha,
        test_summary=test_summary,
    )

    # Get commit messages for BACKLOG matching
    commit_messages = []
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "log", "--format=%s", f"{branch}", "--not", "main"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        commit_messages = [
            line.strip() for line in proc.stdout.splitlines() if line.strip()
        ]

    # Update STATE
    state_path = repo_root / "docs" / "11_admin" / "LIFEOS_STATE.md"
    state_result = _update_lifeos_state(
        state_path=state_path,
        title=win_details["title"],
        details=win_details["details"],
        merge_sha_short=win_details["merge_sha_short"],
        skip_on_error=skip_on_error,
    )
    state_updated = state_result["success"]
    errors.extend(state_result["errors"])

    # Update BACKLOG
    backlog_path = repo_root / "docs" / "11_admin" / "BACKLOG.md"
    backlog_result = _update_backlog_state(
        backlog_path=backlog_path,
        branch=branch,
        commit_messages=commit_messages,
        skip_on_error=skip_on_error,
    )
    backlog_updated = backlog_result["success"]
    items_marked = backlog_result.get("items_marked", 0)
    errors.extend(backlog_result["errors"])

    return {
        "state_updated": state_updated,
        "backlog_updated": backlog_updated,
        "items_marked": items_marked,
        "errors": errors,
    }
