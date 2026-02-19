#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.openclaw_egress_policy import classify_payload_text


def _ts_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_jobs(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [j for j in payload if isinstance(j, dict)]
    if isinstance(payload, dict):
        jobs = payload.get("jobs")
        if isinstance(jobs, list):
            return [j for j in jobs if isinstance(j, dict)]
    return []


def _job_enabled(job: Dict[str, Any]) -> bool:
    enabled = job.get("enabled")
    if isinstance(enabled, bool):
        return enabled
    if enabled is None:
        return True
    return bool(enabled)


def _delivery_obj(job: Dict[str, Any]) -> Dict[str, Any]:
    candidates: List[Any] = [
        job.get("delivery"),
        (job.get("request") or {}).get("delivery") if isinstance(job.get("request"), dict) else None,
        (job.get("job") or {}).get("delivery") if isinstance(job.get("job"), dict) else None,
        (job.get("spec") or {}).get("delivery") if isinstance(job.get("spec"), dict) else None,
        (job.get("schedule") or {}).get("delivery") if isinstance(job.get("schedule"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    return {}


def _delivery_mode(job: Dict[str, Any]) -> str:
    delivery = _delivery_obj(job)
    mode = delivery.get("mode")
    if isinstance(mode, str) and mode.strip():
        return mode.strip().lower()

    fallback = job.get("deliveryMode")
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip().lower()
    return "unknown"


def _payload_hint(job: Dict[str, Any]) -> str:
    candidates: List[Any] = [
        job.get("message"),
        job.get("prompt"),
        job.get("template"),
    ]
    request = job.get("request")
    if isinstance(request, dict):
        candidates.extend([request.get("message"), request.get("prompt"), request.get("template"), request.get("payload")])
        delivery = request.get("delivery")
        if isinstance(delivery, dict):
            candidates.extend([delivery.get("message"), delivery.get("payload"), delivery.get("template")])
    delivery = _delivery_obj(job)
    candidates.extend([delivery.get("message"), delivery.get("payload"), delivery.get("template")])

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        if isinstance(candidate, dict):
            try:
                return json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            except Exception:
                continue
    return ""


def evaluate_jobs(jobs: List[Dict[str, Any]], require_parked: bool) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    violations: List[str] = []

    for job in jobs:
        job_id = str(job.get("id") or "")
        name = str(job.get("name") or job_id or "<unnamed>")
        enabled = _job_enabled(job)
        mode = _delivery_mode(job)
        hint = _payload_hint(job)
        classify = classify_payload_text(hint) if hint else {
            "classification": "contentful",
            "allowed_for_scheduled": False,
            "reasons": ["payload_missing"],
        }

        row = {
            "id": job_id,
            "name": name,
            "enabled": enabled,
            "delivery_mode": mode,
            "payload_classification": classify["classification"],
            "payload_reasons": classify["reasons"],
        }
        rows.append(row)

        if not enabled:
            continue

        if require_parked and mode != "none":
            violations.append(f"{name}: enabled delivery.mode={mode} (must be none while cron egress is parked)")
        elif (not require_parked) and mode != "none" and not classify["allowed_for_scheduled"]:
            joined = ",".join(classify["reasons"]) if classify["reasons"] else "policy_rejected"
            violations.append(f"{name}: scheduled payload classified contentful ({joined})")

    return {
        "jobs": rows,
        "violations": violations,
        "pass": len(violations) == 0,
    }


def run_guard(openclaw_bin: str, marker_path: Path, ignore_marker: bool) -> Dict[str, Any]:
    cmd = [openclaw_bin, "cron", "list", "--all", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    result: Dict[str, Any] = {
        "ts_utc": _ts_utc(),
        "command": cmd,
        "command_exit_code": int(proc.returncode),
        "marker_path": str(marker_path),
        "marker_present": marker_path.exists(),
        "require_parked": True,
        "pass": False,
        "jobs": [],
        "violations": [],
    }

    if proc.returncode != 0:
        result["violations"] = ["cron_list_failed"]
        result["command_stderr"] = (proc.stderr or "").strip()[:1000]
        return result

    try:
        raw_payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        result["violations"] = ["cron_list_not_json"]
        result["command_stdout_head"] = (proc.stdout or "").strip()[:1000]
        return result

    jobs = _extract_jobs(raw_payload)
    if not jobs:
        result["pass"] = True
        result["jobs"] = []
        result["violations"] = []
        result["require_parked"] = False if (marker_path.exists() and not ignore_marker) else True
        return result

    require_parked = True
    if marker_path.exists() and not ignore_marker:
        require_parked = False
    evaluated = evaluate_jobs(jobs, require_parked=require_parked)

    result["jobs"] = evaluated["jobs"]
    result["violations"] = evaluated["violations"]
    result["pass"] = evaluated["pass"]
    result["require_parked"] = require_parked
    return result


def main() -> int:
    default_state_dir = Path(os.environ.get("OPENCLAW_STATE_DIR", str(Path.home() / ".openclaw")))
    default_marker = default_state_dir / "runtime" / "gates" / "cron_egress_policy_ready.marker"

    parser = argparse.ArgumentParser(description="Fail-closed cron delivery guard for OpenClaw COO startup.")
    parser.add_argument("--openclaw-bin", default=os.environ.get("OPENCLAW_BIN", "openclaw"))
    parser.add_argument("--marker-path", default=str(default_marker))
    parser.add_argument("--ignore-marker", action="store_true", help="Always require delivery.mode=none even if marker exists.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    marker_path = Path(args.marker_path).expanduser()
    result = run_guard(args.openclaw_bin, marker_path=marker_path, ignore_marker=bool(args.ignore_marker))

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        if result["pass"]:
            print(
                "PASS cron_delivery_guard=true "
                f"jobs={len(result['jobs'])} "
                f"require_parked={'true' if result['require_parked'] else 'false'}"
            )
        else:
            top = result["violations"][0] if result["violations"] else "unknown_violation"
            print(
                "FAIL cron_delivery_guard=false "
                f"require_parked={'true' if result['require_parked'] else 'false'} "
                f"reason={top}",
                flush=True,
            )

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
