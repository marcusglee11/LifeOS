#!/usr/bin/env python3
"""Emit clean-origin post-merge verification receipts for docs drift controls."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

DEFAULT_COMMANDS = (
    "python3 scripts/wiki/check_derived_outputs.py",
    "python3 -m doc_steward.cli wiki-lint .",
    "python3 scripts/workflow/quality_gate.py check --scope changed --json",
)

DRIFT_MARKERS = (
    "refresh_needed",
    "pending_diff",
    "needs refresh",
    "stale",
    "wiki-lint",
    "derived output",
    "provenance",
    "corpus",
)
TOOLING_MARKERS = (
    "no such file or directory",
    "command not found",
    "modulenotfounderror",
    "permission denied",
    "traceback",
    "failed to clone",
    "not a git repository",
)
BASELINE_MARKERS = (
    "baseline",
    "pre-existing",
    "unrelated",
)
SENSITIVE_PATTERNS = (
    re.compile(
        r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|secret|password|credential)"
        r"([\s:=]+)([^\s,;]+)"
    ),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(
        r"-----BEGIN (?:OPENSSH|RSA|EC|DSA)? ?PRIVATE KEY-----.*?"
        r"-----END (?:OPENSSH|RSA|EC|DSA)? ?PRIVATE KEY-----",
        re.DOTALL,
    ),
)


def _run(cmd: Sequence[str] | str, cwd: Path) -> subprocess.CompletedProcess[str]:
    argv = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)


def redact_sensitive(text: str) -> str:
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub(
            lambda match: (
                f"{match.group(1)}{match.group(2)}[REDACTED]"
                if match.lastindex == 3
                else "[REDACTED]"
            ),
            redacted,
        )
    return redacted


def _summarise(stdout: str, stderr: str, limit: int = 240) -> str:
    text = "\n".join(part.strip() for part in (stdout, stderr) if part.strip()).strip()
    if not text:
        return "command produced no output"
    text = " ".join(redact_sensitive(text).split())
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def classify_failure(summary: str) -> str:
    lowered = summary.lower()
    if any(marker in lowered for marker in TOOLING_MARKERS):
        return "tooling_failure"
    if any(marker in lowered for marker in BASELINE_MARKERS):
        return "baseline_noise"
    if any(marker in lowered for marker in DRIFT_MARKERS):
        return "new_drift"
    return "tooling_failure"


def is_dirty(repo_root: Path) -> bool:
    status = _run(["git", "status", "--short"], repo_root)
    return bool(status.stdout.strip()) or status.returncode != 0


def rev_parse(repo_root: Path, ref: str) -> str:
    result = _run(["git", "rev-parse", ref], repo_root)
    if result.returncode != 0:
        raise RuntimeError(_summarise(result.stdout, result.stderr))
    return result.stdout.strip()


def emit_yaml(receipt: dict) -> str:
    def scalar(value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "null"
        text = str(value)
        if not text or any(ch in text for ch in ":#[]{}\n") or text.strip() != text:
            return json.dumps(text)
        return text

    lines: list[str] = []
    for key in ("repo", "base_ref", "verified_commit"):
        lines.append(f"{key}: {scalar(receipt[key])}")
    lines.append("commands:")
    for command in receipt["commands"]:
        lines.append(f"  - {scalar(command)}")
    lines.append("results:")
    for result in receipt["results"]:
        lines.append(f"  - command: {scalar(result['command'])}")
        lines.append(f"    status: {scalar(result['status'])}")
        lines.append(f"    summary: {scalar(result['summary'])}")
        if result.get("failure_classification"):
            lines.append(f"    failure_classification: {scalar(result['failure_classification'])}")
    lines.append(
        f"dirty_worktree_after_verification: {scalar(receipt['dirty_worktree_after_verification'])}"
    )
    lines.append("follow_up_issues_created:")
    for url in receipt["follow_up_issues_created"]:
        lines.append(f"  - {scalar(url)}")
    if not receipt["follow_up_issues_created"]:
        lines[-1] += " []"
    lines.append(f"completion_claim: {scalar(receipt['completion_claim'])}")
    return "\n".join(lines) + "\n"


def build_receipt(
    repo_root: Path,
    commands: Sequence[str],
    follow_up_issues: Sequence[str] = (),
    keep_worktree: bool = False,
) -> tuple[dict, Path | None]:
    fetch = _run(["git", "fetch", "origin", "main", "--prune"], repo_root)
    if fetch.returncode != 0:
        raise RuntimeError(_summarise(fetch.stdout, fetch.stderr))

    verified_commit = rev_parse(repo_root, "origin/main")
    temp_parent = Path(tempfile.mkdtemp(prefix="lifeos-post-merge-verify."))
    verify_root = temp_parent / "origin-main"
    added = _run(["git", "worktree", "add", "--detach", str(verify_root), "origin/main"], repo_root)
    if added.returncode != 0:
        shutil.rmtree(temp_parent, ignore_errors=True)
        raise RuntimeError(_summarise(added.stdout, added.stderr))

    results: list[dict[str, str]] = []
    try:
        for command in commands:
            outcome = _run(command, verify_root)
            status = "pass" if outcome.returncode == 0 else "fail"
            summary = _summarise(outcome.stdout, outcome.stderr)
            row = {"command": command, "status": status, "summary": summary}
            if status == "fail":
                row["failure_classification"] = classify_failure(summary)
            results.append(row)
        dirty_after = is_dirty(verify_root)
    finally:
        if not keep_worktree:
            _run(["git", "worktree", "remove", "--force", str(verify_root)], repo_root)
            shutil.rmtree(temp_parent, ignore_errors=True)

    failed = [row for row in results if row["status"] == "fail"]
    completion_claim = "conductor_verified"
    if failed:
        completion_claim = "follow_up_required" if follow_up_issues else "failed"

    return (
        {
            "repo": "marcusglee11/LifeOS",
            "base_ref": "origin/main",
            "verified_commit": verified_commit,
            "commands": list(commands),
            "results": results,
            "dirty_worktree_after_verification": dirty_after,
            "follow_up_issues_created": list(follow_up_issues),
            "completion_claim": completion_claim,
        },
        verify_root if keep_worktree else None,
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", default=".", help="LifeOS checkout to control worktrees from"
    )
    parser.add_argument(
        "--command",
        action="append",
        dest="commands",
        help="Verification command to run in the clean origin/main worktree; repeatable",
    )
    parser.add_argument(
        "--follow-up-issue",
        action="append",
        default=[],
        help="Follow-up issue URL created for failed verification",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of YAML")
    parser.add_argument(
        "--keep-worktree", action="store_true", help="Keep verification worktree for debugging"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    commands = args.commands or list(DEFAULT_COMMANDS)
    receipt, verify_root = build_receipt(
        Path(args.repo_root).resolve(), commands, args.follow_up_issue, args.keep_worktree
    )
    if verify_root is not None:
        receipt["verification_worktree"] = str(verify_root)
    print(json.dumps(receipt, indent=2) if args.json else emit_yaml(receipt))
    return 0 if receipt["completion_claim"] == "conductor_verified" else 1


if __name__ == "__main__":
    sys.exit(main())
