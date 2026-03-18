"""Stability checks across repeated promotion-campaign runs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def check_stability(
    log_path: Path,
    required_consecutive: int = 5,
    relaxed_fields: dict[str, int] | None = None,
) -> dict[str, Any]:
    relaxed_fields = relaxed_fields or {"escalation_type": 4}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        grouped.setdefault(str(row["scenario_id"]), []).append(row)

    scenarios: dict[str, Any] = {}
    all_stable = True
    for scenario_id, rows in grouped.items():
        tail = rows[-required_consecutive:]
        families = [row["actual_packet_family"] for row in tail]
        effects = [row["side_effect_class"] for row in tail]
        stable = (
            len(tail) >= required_consecutive
            and len(set(families)) == 1
            and len(set(effects)) == 1
        )
        scenarios[scenario_id] = {
            "stable": stable,
            "families": families,
            "side_effects": effects,
        }
        all_stable = all_stable and stable

    return {"all_stable": all_stable, "scenarios": scenarios}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check promotion campaign stability.")
    parser.add_argument("--log", required=True)
    parser.add_argument("--required-consecutive", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check_stability(Path(args.log), required_consecutive=args.required_consecutive)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result)
    return 0 if result["all_stable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
