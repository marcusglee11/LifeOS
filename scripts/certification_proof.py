#!/usr/bin/env python3
"""Repeat-run proof harness for local pipeline certification."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_certification import OUTPUT_PATH as CERTIFICATION_OUTPUT_PATH
from scripts.run_certification import current_worktree_clean


PROOF_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "certification_proof.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_readiness_artifact() -> dict[str, Any] | None:
    if not CERTIFICATION_OUTPUT_PATH.exists():
        return None
    return json.loads(CERTIFICATION_OUTPUT_PATH.read_text(encoding="utf-8"))


def run_proof() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": _now_iso(),
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
        result = subprocess.run(
            [sys.executable, "-m", "runtime.cli", "certify", "pipeline", "--profile", "local"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        artifact = _load_readiness_artifact()
        state = artifact.get("state") if artifact else None

        payload["runs"].append(
            {
                "run": run_number,
                "exit_code": result.returncode,
                "state": state,
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


def main() -> int:
    payload = run_proof()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["summary"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
