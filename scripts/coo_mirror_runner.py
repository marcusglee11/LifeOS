#!/usr/bin/env python3
"""Manual live mirror runner for COO propose/direct evaluation.

The live runner is observational for direct mode: it captures the inside packet
and outside evidence deltas, but it does not enqueue CEO escalations on the
operator's behalf. Because of that, a live `direct` run that returns an
escalation packet will usually report `inside_outside_consistent=false` with no
external side effect, and that is expected behavior for v1.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.orchestration.coo.claim_verifier import collect_evidence, verify_claims
from runtime.orchestration.coo.commands import _parse_escalation_packet, _parse_ntp
from runtime.orchestration.coo.context import build_propose_context
from runtime.orchestration.coo.invoke import invoke_coo_reasoning
from runtime.orchestration.coo.mirror import build_evaluation_row, diff_evidence
from runtime.orchestration.coo.parser import ParseError, _extract_yaml_payload_with_stage, parse_proposal_response
from runtime.receipts.invocation_receipt import finalize_run_receipts
from runtime.util.atomic_write import atomic_write_text
from runtime.util.canonical import compute_sha256


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _ensure_openclaw_receipt_ref() -> str:
    state_dir = Path(os.environ.get("OPENCLAW_STATE_DIR", str(Path.home() / ".openclaw")))
    receipts_dir = state_dir / "receipts"
    if not receipts_dir.exists():
        return "unavailable"
    candidates = sorted(
        (path for path in receipts_dir.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return "unavailable"
    latest = candidates[0]
    manifest = latest / "receipt_manifest.json"
    return str(manifest) if manifest.exists() else str(latest)


def _parse_mode_output(mode: str, raw_output: str) -> tuple[str, str, str]:
    """Return (packet_family, parse_stage, parse_status)."""
    _, stage = _extract_yaml_payload_with_stage(raw_output)
    if mode == "propose":
        try:
            parse_proposal_response(raw_output)
            return "task_proposal", stage, "pass"
        except ParseError:
            pass
        try:
            _parse_ntp(raw_output)
            return "nothing_to_propose", stage, "pass"
        except ParseError:
            return "unknown", stage, "fail"

    try:
        _parse_escalation_packet(raw_output)
        return "escalation_packet", stage, "pass"
    except ParseError:
        return "unknown", stage, "fail"


def _write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    atomic_write_text(path, existing + json.dumps(payload, sort_keys=True) + "\n")


def _run_propose(repo_root: Path, scenario_id: str, run_dir: Path) -> dict[str, Any]:
    context = build_propose_context(repo_root)
    _write_json(run_dir / "context.json", context)
    run_id = f"mirror-propose-{_utc_now()}-{compute_sha256(context)[:10]}"
    before = collect_evidence(repo_root)
    raw_output = invoke_coo_reasoning(context, mode="propose", repo_root=repo_root, run_id=run_id)
    atomic_write_text(run_dir / "raw_output.txt", raw_output)
    actual_packet_family, stage, parse_status = _parse_mode_output("propose", raw_output)
    after = collect_evidence(repo_root)
    receipt_index = finalize_run_receipts(run_id, repo_root)
    violations = verify_claims(raw_output, before, repo_root=repo_root)
    diff = diff_evidence(before, after)
    return build_evaluation_row(
        scenario_id=scenario_id,
        mode="propose",
        source_kind="live",
        input_ref=str(run_dir / "context.json"),
        expected_packet_family="operator_defined",
        actual_packet_family=actual_packet_family,
        parse_status=parse_status,
        parse_recovery_stage=stage,
        claim_verifier_status="pass" if not violations else "fail",
        diff=diff,
        invocation_receipt_ref=str(receipt_index) if receipt_index else None,
        token_usage=None,
        notes="live_propose",
        openclaw_runtime_observation=_ensure_openclaw_receipt_ref(),
    )


def _run_direct(repo_root: Path, scenario_id: str, run_dir: Path, intent: str) -> dict[str, Any]:
    context = {"intent": intent, "source": "coo_direct"}
    _write_json(run_dir / "context.json", context)
    run_id = f"mirror-direct-{_utc_now()}-{compute_sha256(context)[:10]}"
    before = collect_evidence(repo_root)
    raw_output = invoke_coo_reasoning(context, mode="direct", repo_root=repo_root, run_id=run_id)
    atomic_write_text(run_dir / "raw_output.txt", raw_output)
    actual_packet_family, stage, parse_status = _parse_mode_output("direct", raw_output)
    after = collect_evidence(repo_root)
    receipt_index = finalize_run_receipts(run_id, repo_root)
    violations = verify_claims(raw_output, before, repo_root=repo_root)
    diff = diff_evidence(before, after)
    return build_evaluation_row(
        scenario_id=scenario_id,
        mode="direct",
        source_kind="live",
        input_ref=str(run_dir / "context.json"),
        expected_packet_family="operator_defined",
        actual_packet_family=actual_packet_family,
        parse_status=parse_status,
        parse_recovery_stage=stage,
        claim_verifier_status="pass" if not violations else "fail",
        diff=diff,
        invocation_receipt_ref=str(receipt_index) if receipt_index else None,
        token_usage=None,
        notes=(
            "live_direct_read_only_runner: expected "
            "inside_outside_consistent=false for escalation_packet because "
            "the runner observes but does not queue escalations"
        ),
        openclaw_runtime_observation=_ensure_openclaw_receipt_ref(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual COO mirror runner.")
    parser.add_argument("--repo-root", default=".", help="Repo root to evaluate.")
    parser.add_argument("--scenario-id", default="", help="Optional scenario identifier.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    subparsers.add_parser("propose", help="Run a live propose mirror evaluation.")

    direct = subparsers.add_parser(
        "direct",
        help=(
            "Run a live direct mirror evaluation. Read-only: escalation packets "
            "are observed, not queued, so consistency may be false by design."
        ),
    )
    direct.add_argument("intent", help="Operator intent to send through direct mode.")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    scenario_id = args.scenario_id or f"{args.mode}_{_utc_now().lower()}"

    run_dir = repo_root / "artifacts" / "coo" / "mirror_runs" / scenario_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "propose":
        row = _run_propose(repo_root, scenario_id, run_dir)
    else:
        row = _run_direct(repo_root, scenario_id, run_dir, args.intent)

    _write_json(run_dir / "row.json", row)
    _append_jsonl(repo_root / "artifacts" / "coo" / "mirror_runs" / "results.jsonl", row)
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
