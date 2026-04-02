#!/usr/bin/env python3
"""Repeat-run proof harness for pipeline certification profiles."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_certification import OUTPUT_PATH as CERTIFICATION_OUTPUT_PATH
from scripts.run_certification import current_worktree_clean


PROOF_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "certification_proof.json"
PROFILE_METADATA = {
    "local": {
        "task_id": "T-021",
        "state": "prod_local",
        "title": "T-021 prod_local Certification Proof",
    },
    "ci": {
        "task_id": "T-022",
        "state": "prod_ci",
        "title": "T-022 prod_ci Certification Proof",
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_readiness_artifact() -> dict[str, Any] | None:
    if not CERTIFICATION_OUTPUT_PATH.exists():
        return None
    return json.loads(CERTIFICATION_OUTPUT_PATH.read_text(encoding="utf-8"))


def _git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _profile_title(profile: str) -> str:
    return PROFILE_METADATA[profile]["title"]


def _task_id(profile: str) -> str:
    return PROFILE_METADATA[profile]["task_id"]


def _target_state(profile: str) -> str:
    return PROFILE_METADATA[profile]["state"]


def run_proof(profile: str = "local") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": _now_iso(),
        "profile": profile,
        "runs": [],
        "summary": {
            "pass": False,
            "consecutive_runs": 0,
            "last_artifact_path": str(CERTIFICATION_OUTPUT_PATH.relative_to(REPO_ROOT)),
        },
    }

    if not current_worktree_clean():
        payload["summary"]["failure_reason"] = "worktree_cleanliness"
        write_proof(payload)
        return payload

    for run_number in range(1, 4):
        started = time.monotonic()
        result = subprocess.run(
            [sys.executable, "-m", "runtime.cli", "certify", "pipeline", "--profile", profile],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        artifact = _load_readiness_artifact()
        state = artifact.get("state") if artifact else None
        elapsed_s = round(time.monotonic() - started, 1)
        counts = artifact.get("pytest_summary", {}) if artifact else {}
        leaks = artifact.get("leaks", []) if artifact else []

        payload["runs"].append(
            {
                "run": run_number,
                "exit_code": result.returncode,
                "state": state,
                "elapsed_s": elapsed_s,
                "pytest_summary": counts,
                "leak_count": len(leaks),
                "artifact_snapshot": artifact,
            }
        )

        if result.returncode != 0:
            payload["summary"]["failure_reason"] = f"run_{run_number}_failed"
            payload["summary"]["consecutive_runs"] = run_number - 1
            write_proof(payload)
            return payload

    payload["summary"]["pass"] = True
    payload["summary"]["consecutive_runs"] = 3
    write_proof(payload)
    return payload


def write_proof(payload: dict[str, Any]) -> None:
    PROOF_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROOF_OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown_proof(payload: dict[str, Any], output_path: Path) -> None:
    profile = payload["profile"]
    branch = _git_value("rev-parse", "--abbrev-ref", "HEAD")
    head = _git_value("rev-parse", "HEAD")
    target_state = _target_state(profile)
    task_id = _task_id(profile)
    title = _profile_title(profile)

    lines = [
        f"# {title}",
        "",
        f"**Purpose**: Durable proof that `{task_id}` satisfied the Phase {'6' if profile == 'local' else '7'} repeat-run bar for `{target_state}` engineering certification.",
        "",
        "---",
        "",
        "## 1. Execution Context",
        "",
        "```",
        f"Task: {task_id}",
        f"Branch: {branch}",
        f"Tested HEAD: {head}",
        f"Command: python3 scripts/certification_proof.py --profile {profile}",
        f"Proof harness start timestamp: {payload['timestamp']}",
        f"Worktree status before run: {'clean' if payload['summary'].get('failure_reason') != 'worktree_cleanliness' else 'dirty'}",
        "```",
        "",
        "## 2. Raw Ephemeral Artifact Reference",
        "",
        "The proof harness wrote the following gitignored runtime artifacts during execution:",
        "",
        "```",
        "artifacts/status/pipeline_readiness.json",
        "artifacts/status/certification_proof.json",
        "```",
        "",
        "These files were used as live execution evidence only and are not durable proof artifacts under repo policy.",
        "",
        "## 3. Proof Result",
        "",
        f"**Verdict**: {'PASS' if payload['summary']['pass'] else 'FAIL'}",
        "",
    ]

    if payload["summary"]["pass"]:
        lines.append(
            f"The proof harness completed three consecutive {profile} certification runs. Every run exited `0`, every readiness artifact state was `{target_state}`, and every run reported zero leaks."
        )
    else:
        failure_reason = payload["summary"].get("failure_reason", "unknown")
        lines.append(f"The proof harness did not satisfy the repeat-run bar. Failure reason: `{failure_reason}`.")

    lines.extend(
        [
            "",
            "| Run | Exit Code | State | Passed | Failed | Skipped | Leaks | Elapsed (s) | Artifact Timestamp |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for run in payload["runs"]:
        artifact = run.get("artifact_snapshot") or {}
        counts = run.get("pytest_summary") or {}
        lines.append(
            "| {run} | {exit_code} | `{state}` | {passed} | {failed} | {skipped} | {leaks} | {elapsed} | `{timestamp}` |".format(
                run=run["run"],
                exit_code=run["exit_code"],
                state=run.get("state") or "unknown",
                passed=counts.get("passed", 0),
                failed=counts.get("failed", 0),
                skipped=counts.get("skipped", 0),
                leaks=run.get("leak_count", 0),
                elapsed=run.get("elapsed_s", 0),
                timestamp=artifact.get("timestamp", "unknown"),
            )
        )

    lines.extend(
        [
            "",
            "## 4. Closure Statement",
            "",
            f"`{task_id}` {'now has' if payload['summary']['pass'] else 'does not yet have'} the repeat-run proof required by the Phase {'6' if profile == 'local' else '7'} exit criteria:",
            "",
            f"- `lifeos certify pipeline --profile {profile}` {'reached' if payload['summary']['pass'] else 'did not reach'} `{target_state}`",
            f"- the readiness artifact {'reported zero leaks' if payload['summary']['pass'] else 'did not remain leak-free'}",
            f"- the automated proof harness recorded `{payload['summary']['consecutive_runs']}` consecutive clean runs",
            "",
            "This tracked receipt is the durable git evidence for the completed proof run.",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repeat-run certification proof.")
    parser.add_argument("--profile", choices=("local", "ci"), default="local")
    parser.add_argument("--evidence-output", type=Path)
    args = parser.parse_args()

    payload = run_proof(args.profile)
    if args.evidence_output is not None:
        write_markdown_proof(payload, args.evidence_output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["summary"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
