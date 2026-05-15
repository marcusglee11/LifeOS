#!/usr/bin/env python3
"""Emit a clean-origin post-merge verification receipt for documentation drift controls."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

REDACTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)authorization\s*:\s*(bearer\s+)?([^\s,'\"}]+)"),
    re.compile(
        r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|password|passwd|secret|authorization|bearer)\s*[:=]\s*([^\s,'\"}]+)"
    ),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
)

DRIFT_MARKERS = (
    "drift",
    "stale",
    "out of date",
    "source_commit",
    "refresh_needed",
    "wiki-lint",
    "derived_outputs",
)
TOOLING_MARKERS = (
    "command not found",
    "no such file or directory",
    "modulenotfounderror",
    "importerror",
    "permission denied",
    "timed out",
)


@dataclass(frozen=True)
class CommandResult:
    command: str
    status: str
    summary: str
    failure_class: str | None = None


def redact(text: str) -> str:
    redacted = text
    for pattern in REDACTION_PATTERNS:

        def repl(match: re.Match[str]) -> str:
            if match.re.pattern.lower().startswith("(?i)authorization"):
                return "Authorization: <REDACTED>"
            if match.lastindex and match.lastindex >= 2:
                return f"{match.group(1)}=<REDACTED>"
            return "<REDACTED>"

        redacted = pattern.sub(repl, redacted)
    return redacted


def summarize(stdout: str, stderr: str, limit: int) -> str:
    combined = redact("\n".join(part for part in (stdout, stderr) if part).strip())
    if not combined:
        return "no output"
    single_line = " | ".join(line.strip() for line in combined.splitlines() if line.strip())
    if len(single_line) <= limit:
        return single_line
    return single_line[: max(0, limit - 15)].rstrip() + " …<truncated>"


def classify_failure(command: str, summary: str, returncode: int) -> str:
    haystack = f"{command}\n{summary}".lower()
    if any(marker in haystack for marker in TOOLING_MARKERS):
        return "tooling_failure"
    if any(marker in haystack for marker in DRIFT_MARKERS):
        return "new_drift"
    if returncode != 0:
        return "baseline_noise"
    return "none"


def run_git(args: Sequence[str], repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return completed.stdout.strip()


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_command(command: str, cwd: Path, timeout: int, summary_limit: int) -> CommandResult:
    try:
        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=cwd,
            shell=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        summary = summarize(
            _as_text(exc.stdout),
            _as_text(exc.stderr) or "timed out",
            summary_limit,
        )
        return CommandResult(
            command=command,
            status="fail",
            summary=summary,
            failure_class="tooling_failure",
        )

    summary = summarize(completed.stdout, completed.stderr, summary_limit)
    if completed.returncode == 0:
        return CommandResult(command=command, status="pass", summary=summary)
    return CommandResult(
        command=command,
        status="fail",
        summary=summary,
        failure_class=classify_failure(command, summary, completed.returncode),
    )


def create_clean_worktree(source_repo: Path, base_ref: str) -> Path:
    temp_parent = Path(tempfile.mkdtemp(prefix="lifeos-clean-origin-receipt."))
    worktree = temp_parent / "worktree"
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(worktree), base_ref],
        cwd=source_repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return worktree


def remove_clean_worktree(source_repo: Path, worktree: Path) -> None:
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree)],
        cwd=source_repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    shutil.rmtree(worktree.parent, ignore_errors=True)


def build_receipt(args: argparse.Namespace) -> tuple[dict[str, object], int]:
    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        raise SystemExit(f"repo root does not exist: {repo_root}")

    run_git(["fetch", "origin", "main", "--prune"], repo_root)
    verified_commit = run_git(["rev-parse", args.base_ref], repo_root)
    worktree = create_clean_worktree(repo_root, args.base_ref)
    try:
        results = [
            run_command(command, worktree, args.timeout, args.summary_limit)
            for command in args.command
        ]
        dirty_status = run_git(["status", "--short"], worktree)
    finally:
        remove_clean_worktree(repo_root, worktree)

    failed = [result for result in results if result.status != "pass"]
    if not failed:
        completion_claim = "conductor_verified"
    elif any(result.failure_class == "new_drift" for result in failed):
        completion_claim = "follow_up_required"
    else:
        completion_claim = "failed"

    receipt: dict[str, object] = {
        "repo": args.repo,
        "base_ref": args.base_ref,
        "verified_commit": verified_commit,
        "commands": list(args.command),
        "results": [
            {
                key: value
                for key, value in {
                    "command": result.command,
                    "status": result.status,
                    "summary": result.summary,
                    "failure_class": result.failure_class,
                }.items()
                if value is not None
            }
            for result in results
        ],
        "dirty_worktree_after_verification": bool(dirty_status),
        "follow_up_issues_created": list(args.follow_up_issue),
        "completion_claim": completion_claim,
    }
    return receipt, 0 if completion_claim == "conductor_verified" else 1


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run post-merge verification from a clean origin/main worktree "
            "and emit a redacted receipt."
        )
    )
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--repo", default="marcusglee11/LifeOS")
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument(
        "--command",
        action="append",
        required=True,
        help="Verification command to run inside the clean detached worktree; repeatable.",
    )
    parser.add_argument("--follow-up-issue", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--summary-limit", type=int, default=500)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    receipt, exit_code = build_receipt(args)
    output = json.dumps(receipt, indent=2, sort_keys=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
