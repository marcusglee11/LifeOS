"""Scenario runner for the COO unsandboxed promotion campaign."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.coo.claim_verifier import collect_evidence, verify_claims
from runtime.orchestration.coo.commands import classify_coo_response
from runtime.orchestration.coo.mirror import build_evaluation_row, diff_evidence
from runtime.orchestration.coo.parser import _extract_yaml_payload_with_stage
from runtime.util.atomic_write import atomic_write_text


def _build_command(mode: str, scenario: dict[str, Any]) -> list[str]:
    if mode == "propose":
        return ["python3", "-m", "runtime.cli", "coo", "propose", "--yaml"]
    return ["python3", "-m", "runtime.cli", "coo", "direct", str(scenario["intent"])]


def run_scenario(
    scenario: dict[str, Any],
    repo_root: Path,
    capture_dir: Path,
    gate: str,
) -> dict[str, Any]:
    scenario_id = str(scenario["scenario_id"])
    mode = str(scenario["mode"])
    env = os.environ.copy()
    env["LIFEOS_COO_CAPTURE_DIR"] = str(capture_dir)
    env["LIFEOS_COO_CAPTURE_LABEL"] = scenario_id

    before = collect_evidence(repo_root)
    proc = subprocess.run(
        _build_command(mode, scenario),
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    after = collect_evidence(repo_root)

    raw_output = proc.stdout
    _, stage = _extract_yaml_payload_with_stage(raw_output)
    actual_family = classify_coo_response(mode, raw_output)
    diff = diff_evidence(before, after)
    violations = verify_claims(raw_output, before, repo_root=repo_root)
    row = build_evaluation_row(
        scenario_id=scenario_id,
        mode=mode,
        source_kind=str(scenario.get("source_kind", "live")),
        input_ref=str(scenario.get("input_ref", "")),
        expected_packet_family=str(scenario["expected_packet_family"]),
        actual_packet_family=actual_family,
        parse_status="pass",
        parse_recovery_stage=stage,
        claim_verifier_status="pass" if not violations else "fail",
        diff=diff,
        invocation_receipt_ref=None,
        token_usage=None,
        notes=f"gate={gate};rc={proc.returncode}",
    )
    row["returncode"] = proc.returncode
    return row


def run_campaign(manifest_path: Path, repo_root: Path, gate: str) -> dict[str, Any]:
    manifest = yaml.safe_load(Path(manifest_path).read_text(encoding="utf-8")) or {}
    scenarios = list(manifest.get("scenarios") or [])
    capture_dir = repo_root / "artifacts" / "coo" / "promotion_campaign" / "captures" / gate
    log_path = repo_root / "artifacts" / "coo" / "promotion_campaign" / f"campaign_log_{gate}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [run_scenario(scenario, repo_root, capture_dir, gate) for scenario in scenarios]
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    atomic_write_text(log_path, payload)

    return {
        "total": len(rows),
        "parse_pass": sum(1 for row in rows if row["parse_status"] == "pass"),
        "claim_pass": sum(1 for row in rows if row["claim_verifier_status"] == "pass"),
        "family_match": sum(
            1 for row in rows if row["actual_packet_family"] == row["expected_packet_family"]
        ),
        "consistent": sum(1 for row in rows if row["inside_outside_consistent"]),
        "log_path": str(log_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the COO promotion campaign.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = run_campaign(Path(args.manifest), Path(args.repo_root), args.gate)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
