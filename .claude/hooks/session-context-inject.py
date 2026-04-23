#!/usr/bin/env python3
"""SessionStart hook: inject project state context into Claude Code session.

Gathers git branch, status summary, and key fields from LIFEOS_STATE.md.
Also injects latest entropy scan summary when available.
Outputs {"additionalContext": "..."} JSON to stdout.
Always exits 0 (never blocks session start).
"""

import glob
import json
import os
import re
import subprocess
import sys


PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
STATE_FILE = os.path.join(PROJECT_DIR, "docs", "11_admin", "LIFEOS_STATE.md")
CANONICAL_STATE_FILE = os.path.join(PROJECT_DIR, "artifacts", "status", "canonical_state.yaml")
ENTROPY_GLOB = os.path.join(PROJECT_DIR, "artifacts", "entropy", "scan_*.json")
MAX_CONTEXT_CHARS = 900
ENTROPY_MAX_CHARS = 80
WORKTREE_WARNING_THRESHOLD = 8


def run_git(args: list[str], timeout: int = 3) -> str:
    """Run a git command, return stdout or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", PROJECT_DIR] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def git_context() -> str:
    """Return compact git branch + status summary."""
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    status_raw = run_git(["status", "--porcelain"])

    if not status_raw:
        status = "clean"
    else:
        lines = status_raw.splitlines()
        status = f"{len(lines)} changed file(s)"

    return f"Branch: {branch} | Status: {status}"


def _parse_state_from_markdown(content: str) -> list[str]:
    """Extract focus/wip/next fields from LIFEOS_STATE.md markdown."""
    fields = []
    for pattern in [
        r"\*\*Current Focus:\*\*\s*(.+)",
        r"\*\*Active WIP:\*\*\s*(.+)",
    ]:
        m = re.search(pattern, content)
        if m:
            fields.append(m.group(1).strip())
    next_match = re.search(r"\*\*Next immediate:\*\*\s*(.+)", content)
    if next_match:
        fields.append("Next: " + next_match.group(1).strip())
    return fields


def _parse_canonical_yaml(path: str) -> dict:
    """Parse canonical_state.yaml without importing yaml (simple key: value parser)."""
    result = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip()
                if ": " in line and not line.startswith(" "):
                    key, _, val = line.partition(": ")
                    result[key.strip()] = val.strip().strip('"')
    except Exception:
        pass
    return result


def state_context() -> str:
    """Extract key fields from state. Uses canonical_state.yaml when fresh, else regex fallback."""
    fields = []

    # Phase 5: Try canonical YAML first (freshness check via mtime)
    try:
        if os.path.exists(CANONICAL_STATE_FILE) and os.path.exists(STATE_FILE):
            yaml_mtime = os.path.getmtime(CANONICAL_STATE_FILE)
            state_mtime = os.path.getmtime(STATE_FILE)
            if yaml_mtime >= state_mtime:
                canonical = _parse_canonical_yaml(CANONICAL_STATE_FILE)
                focus = canonical.get("current_focus", "")
                wip = canonical.get("active_wip", "")
                if focus:
                    fields.append(focus)
                if wip:
                    fields.append(wip)
                if fields:
                    return " | ".join(fields)
    except Exception:
        pass

    # Fallback: Markdown regex (original behavior)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""

    fields = _parse_state_from_markdown(content)
    return " | ".join(fields)


def entropy_context() -> str:
    """Return compact entropy scan summary if available (max ENTROPY_MAX_CHARS)."""
    try:
        scan_files = sorted(glob.glob(ENTROPY_GLOB))
        if not scan_files:
            return ""
        latest = scan_files[-1]
        with open(latest, "r", encoding="utf-8") as f:
            report = json.load(f)
        summary = report.get("summary", {})
        ok = summary.get("ok", 0)
        warn = summary.get("warn", 0)
        error = summary.get("error", 0)
        snippet = f"Entropy: ok={ok} warn={warn} err={error}"
        return snippet[:ENTROPY_MAX_CHARS]
    except Exception:
        return ""


def isolation_warning() -> str:
    """Warn when in primary worktree with a mismatched Active WIP branch."""
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or ""
    if branch in {"main", "master", "", "unknown", "HEAD"}:
        return ""

    common_dir = run_git(["rev-parse", "--git-common-dir"])
    if common_dir != ".git":
        return ""

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""

    match = re.search(r"\*\*Active WIP:\*\*\s*(.+)", content)
    if not match:
        return ""

    active_wip = match.group(1).strip()
    if active_wip and active_wip != branch:
        return (
            f"⚠️ ISOLATION: primary worktree on '{branch}' but "
            f"LIFEOS_STATE Active WIP='{active_wip}'. "
            "Use /new-build (python3 scripts/workflow/start_build.py <topic>) "
            "or recover existing work with python3 scripts/workflow/start_build.py --recover-primary."
        )
    return ""


def worktree_audit() -> str:
    """Prune stale worktree registrations and warn on high linked-worktree count."""
    dry_run = run_git(["worktree", "prune", "--dry-run"])
    pruned = False
    if dry_run:
        run_git(["worktree", "prune"])
        pruned = True

    worktree_listing = run_git(["worktree", "list", "--porcelain"])
    count = sum(1 for line in worktree_listing.splitlines() if line.startswith("worktree "))
    if not pruned and count <= WORKTREE_WARNING_THRESHOLD:
        return ""

    parts = []
    if pruned:
        parts.append("Worktree audit pruned stale registrations.")
    if count > WORKTREE_WARNING_THRESHOLD:
        parts.append(
            f"Worktree audit: {count} linked worktrees registered; review for stale entries."
        )
    return " ".join(parts)


def main() -> int:
    parts = []

    audit = worktree_audit()
    if audit:
        parts.append(audit)

    git = git_context()
    if git:
        parts.append(git)

    state = state_context()
    if state:
        parts.append(state)

    entropy = entropy_context()
    if entropy:
        parts.append(entropy)

    warning = isolation_warning()
    if warning:
        parts.insert(0, warning)

    pending_marker = os.path.join(PROJECT_DIR, ".context", "wiki", "_refresh_needed")
    if os.path.exists(pending_marker) and os.path.getsize(pending_marker) > 0:
        parts.append("[wiki] Docs changed since last wiki refresh — run: python3 scripts/wiki/refresh_wiki.py")

    if not parts:
        # Nothing to inject
        print(json.dumps({"additionalContext": ""}))
        return 0

    context = " || ".join(parts)

    # Cap to avoid token waste
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[: MAX_CONTEXT_CHARS - 3] + "..."

    output = {"additionalContext": context}
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
