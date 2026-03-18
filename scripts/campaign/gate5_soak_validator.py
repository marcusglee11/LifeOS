"""Validate gate 5 soak results."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate_soak_result(result_path: Path) -> dict[str, Any]:
    result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    distribution = result.get("distribution") or {}
    violations: list[str] = []
    if int(result.get("clean_run_count", 0)) < 16:
        violations.append("clean_runs_below_threshold")
    if int(result.get("session_count", 0)) < 4:
        violations.append("session_count_below_threshold")
    if int(result.get("calendar_days", 0)) < 2:
        violations.append("calendar_days_below_threshold")
    if int(distribution.get("propose", 0)) < 6:
        violations.append("propose_distribution_below_threshold")
    if int(distribution.get("clear_direct", 0)) < 4:
        violations.append("clear_direct_distribution_below_threshold")
    if int(distribution.get("ambiguous_or_protected", 0)) < 2:
        violations.append("ambiguous_distribution_below_threshold")
    if int(distribution.get("repeated_pairs", 0)) < 2:
        violations.append("repeated_pairs_below_threshold")
    if int(distribution.get("continuity", 0)) < 2:
        violations.append("continuity_below_threshold")
    return {"pass": not violations, "violations": violations, "result": result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate gate 5 soak output.")
    parser.add_argument("--result", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = validate_soak_result(Path(args.result))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload)
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
