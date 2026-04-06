#!/usr/bin/env python3
"""Canonical council V2 review runner.

Handles all CCP-driven council reviews. Produces a timestamped archive dir
under artifacts/council_reviews/<UTC stamp>/ before making any LLM calls.

Exit codes:
  0  council approved (verdict=Accept, status=NORMAL)
  1  council completed but not approved (Revise / Reject)
  2  preflight or provider block (blocked_provider)
  3  malformed seat output or synthesis failure

Usage:
    python3 scripts/workflow/run_council_review.py --ccp PATH [options]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Model family registry (from config/policy/council_policy.yaml)
# ---------------------------------------------------------------------------

_FORBIDDEN_FAMILIES = {"anthropic", "openai"}

DEFAULT_CCP = REPO_ROOT / "artifacts" / "council_reviews" / "coo_dispatch_phase1.ccp.yaml"
DEFAULT_ARCHIVE_ROOT = REPO_ROOT / "artifacts" / "council_reviews"
DEFAULT_SEAT_TIMEOUT = 120
DEFAULT_PREFLIGHT_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )


def _load_family_map(policy_path: Path) -> dict[str, str]:
    """Return model_id → family_name from council_policy.yaml."""
    with policy_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    families: dict[str, str] = {}
    for family, models in (raw.get("model_families") or {}).items():
        for m in models:
            families[m] = family
            families[f"opencode/{m}"] = family
    return families


def _model_preflight(assignments: dict[str, str], family_map: dict[str, str]) -> list[str]:
    """Check model family constraints. Returns list of error strings."""
    errors: list[str] = []
    distinct = set(assignments.values())
    if len(distinct) < 3:
        errors.append(
            f"only {len(distinct)} distinct model(s) (need >= 3): {sorted(distinct)}"
        )
    for seat, model in assignments.items():
        family = family_map.get(model, "unknown")
        if family in _FORBIDDEN_FAMILIES:
            errors.append(f"forbidden family '{family}' for seat '{seat}' (model: {model})")
    return errors


def _append_run_log(run_log_path: Path, entry: dict[str, Any]) -> None:
    """Append a JSON entry to run_log.json (append-only stage log)."""
    existing: list[dict[str, Any]] = []
    if run_log_path.exists():
        try:
            existing = json.loads(run_log_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.append(entry)
    _write_json(run_log_path, existing)


def _log_stage(
    run_log_path: Path,
    stage: str,
    status: str,
    detail: dict[str, Any] | None = None,
) -> None:
    entry: dict[str, Any] = {
        "stage": stage,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if detail:
        entry.update(detail)
    _append_run_log(run_log_path, entry)
    print(f"[{stage}] {status}")


def _rel(path: Path) -> str:
    """Return repo-relative path string, or absolute if outside repo."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _extract_carry_forward_providers(
    ccp: dict[str, Any],
    assignments: Mapping[str, str],
) -> set[str]:
    """Resolve declared carry-forward seats/models/providers into provider keys."""
    header = ccp.get("header") or ccp
    if not isinstance(header, dict):
        return set()

    providers: set[str] = set()

    def _as_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if str(item).strip()]
        return []

    for key in ("carry_forward_providers", "carry_forward_models"):
        providers.update(_as_list(header.get(key)))

    for seat_name in _as_list(header.get("carry_forward_seats")):
        model = assignments.get(seat_name)
        if model:
            providers.add(model)

    carry_forward = header.get("carry_forward")
    if isinstance(carry_forward, dict):
        for key in ("providers", "models"):
            providers.update(_as_list(carry_forward.get(key)))
        for seat_name in _as_list(carry_forward.get("seats")):
            model = assignments.get(seat_name)
            if model:
                providers.add(model)

    return providers


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Council V2 canonical review runner")
    parser.add_argument(
        "--ccp",
        default=None,
        help=f"Path to CCP YAML (default: {DEFAULT_CCP.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--review-packet",
        default=None,
        help="Path to review packet markdown (optional)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compile run plan + preflight; no LLM calls",
    )
    parser.add_argument(
        "--archive-dir",
        default=None,
        help="Override archive directory (default: artifacts/council_reviews/<stamp>/)",
    )
    parser.add_argument(
        "--seat-timeout-seconds",
        type=int,
        default=DEFAULT_SEAT_TIMEOUT,
        help=f"Per-seat LLM timeout in seconds (default: {DEFAULT_SEAT_TIMEOUT})",
    )
    parser.add_argument(
        "--preflight-timeout-seconds",
        type=int,
        default=DEFAULT_PREFLIGHT_TIMEOUT,
        help=f"Provider echo-check timeout in seconds (default: {DEFAULT_PREFLIGHT_TIMEOUT})",
    )
    args = parser.parse_args(argv)

    policy_path = REPO_ROOT / "config" / "policy" / "council_policy.yaml"
    family_map = _load_family_map(policy_path)

    ccp_path = Path(args.ccp) if args.ccp else DEFAULT_CCP
    if not ccp_path.exists():
        print(f"ERROR: CCP not found: {ccp_path}", file=sys.stderr)
        return 2

    with ccp_path.open(encoding="utf-8") as f:
        ccp: dict = yaml.safe_load(f)

    # -- Archive dir: created immediately, before any LLM calls ---------------
    run_stamp = _utc_stamp()
    archive_dir = Path(args.archive_dir) if args.archive_dir else DEFAULT_ARCHIVE_ROOT / run_stamp
    archive_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = archive_dir / "run_log.json"

    _log_stage(
        run_log_path, "init", "started",
        {"ccp_path": str(ccp_path), "run_stamp": run_stamp},
    )

    # -- Compile run plan ------------------------------------------------------
    from runtime.orchestration.council.policy import load_council_policy
    policy = load_council_policy(policy_path)

    from runtime.orchestration.council.compiler import compile_council_run_plan_v2
    from runtime.orchestration.council.models import CouncilBlockedError
    try:
        plan = compile_council_run_plan_v2(ccp, policy)
    except CouncilBlockedError as exc:
        _log_stage(
            run_log_path, "compile", "blocked",
            {"category": exc.category, "detail": exc.detail},
        )
        print(f"ERROR: CCP compile blocked [{exc.category}]: {exc.detail}", file=sys.stderr)
        return 2
    core = plan["core"]
    assignments: dict[str, str] = dict(core["model_assignments"])

    header = ccp.get("header", ccp)
    print(f"CCP:        {header.get('aur_id', '(unknown)')}")
    print(f"Tier:       {core['tier']}")
    print(f"Topology:   {core['topology']}")
    print(f"Lenses:     {core['required_lenses']}")

    # -- Model family preflight ------------------------------------------------
    model_errors = _model_preflight(assignments, family_map)
    if model_errors:
        _log_stage(run_log_path, "preflight", "blocked_model_policy", {"errors": model_errors})
        for e in model_errors:
            print(f"  \u2717 {e}", file=sys.stderr)
        return 2

    # -- Provider preflight (auth + echo check) --------------------------------
    _log_stage(run_log_path, "preflight", "started")
    from runtime.orchestration.council.provider_preflight import (
        is_run_blocked,
        provider_health_to_dict,
        run_preflight,
    )

    # Build model→model mapping (one check per distinct model)
    provider_models: dict[str, str] = {}
    for _seat, model in assignments.items():
        provider_models[model] = model

    health_results = run_preflight(
        provider_models,
        timeout=float(args.preflight_timeout_seconds),
        skip_echo=args.dry_run,  # dry-run skips network echo probe (no LLM calls)
    )

    health_dict = provider_health_to_dict(health_results)
    _write_json(archive_dir / "provider_health.json", health_dict)
    _log_stage(run_log_path, "preflight", "completed", {"health": health_dict})

    blocked, block_reason = is_run_blocked(
        health_results,
        required_providers=set(provider_models.keys()),
        carry_forward_allowed=bool(
            (ccp.get("header") or ccp).get("carry_forward_allowed", False)
        ),
        carry_forward_providers=_extract_carry_forward_providers(ccp, assignments),
    )

    # -- Build and write run_manifest.json ------------------------------------
    from runtime.orchestration.council.models import RunManifest
    from runtime.orchestration.council.seat_payload_builder import build_seat_payload, hash_payload

    prompt_hashes: dict[str, str] = {}
    for seat in core["required_lenses"]:
        payload = build_seat_payload(
            ccp=ccp,
            lens_name=seat,
            review_packet_excerpt="",
            token_budget=8000,
        )
        prompt_hashes[seat] = hash_payload(payload)

    # Extract run_id from plan meta (CouncilRunMeta dataclass)
    meta = plan.get("meta")
    run_id = meta.run_id if meta is not None and hasattr(meta, "run_id") else run_stamp

    manifest = RunManifest(
        run_stamp=run_stamp,
        run_id=run_id,
        ccp_path=_rel(ccp_path),
        archive_path=_rel(archive_dir),
        seat_map=list(core["required_lenses"]),
        provider_bindings=assignments,
        prompt_hashes=prompt_hashes,
        seat_timeout_seconds=args.seat_timeout_seconds,
        preflight_timeout_seconds=args.preflight_timeout_seconds,
        review_packet_path=args.review_packet,
    )
    _write_json(archive_dir / "run_manifest.json", manifest.to_dict())

    if blocked:
        _log_stage(run_log_path, "preflight", "blocked_provider", {"reason": block_reason})
        failures = {
            p: r.to_dict()
            for p, r in health_results.items()
            if r.status.value != "seat_completed"
        }
        _write_json(archive_dir / "provider_failures.json", failures)
        print(f"\n\u2717 {block_reason}", file=sys.stderr)
        print(f"Archive:    {archive_dir}")
        return 2

    # -- Dry run: stop here after compiling and preflighting -------------------
    if args.dry_run:
        print("\n=== DRY RUN \u2014 Run Plan (no LLM calls) ===")
        print(f"Assignments:\n{json.dumps(assignments, indent=2)}")
        print("\u2713 Preflight passed")
        print(f"Archive:    {archive_dir}")
        _log_stage(run_log_path, "dry_run", "completed")
        return 0

    # -- Live run --------------------------------------------------------------
    _log_stage(run_log_path, "seats", "started")
    from runtime.orchestration.council.fsm import CouncilFSMv2
    from runtime.orchestration.council.multi_provider import build_multi_provider_executor

    lens_executor = build_multi_provider_executor()
    council = CouncilFSMv2(policy=policy, lens_executor=lens_executor)

    print("\nRunning council review (live API calls)...")
    try:
        result = council.run(ccp)
    except Exception as exc:
        _log_stage(run_log_path, "seats", "failed", {"error": str(exc)})
        print(f"ERROR: council FSM raised: {exc}", file=sys.stderr)
        return 3

    # -- Write live result to archive -----------------------------------------
    live_result_path = archive_dir / "live_result.json"
    _write_json(live_result_path, dataclasses.asdict(result))
    _log_stage(run_log_path, "seats", "completed", {"result_path": str(live_result_path)})

    # -- Synthesis artifacts ---------------------------------------------------
    _log_stage(run_log_path, "synthesis", "started")
    dp = result.decision_payload or {}
    verdict = dp.get("verdict", "")
    decision_status = dp.get("decision_status", "")
    dp_status = dp.get("status", "")

    # Check for synthesis failure — write summary.json before returning
    if result.status not in ("complete", "blocked"):
        _log_stage(run_log_path, "synthesis", "failed", {"status": result.status})
        _write_json(archive_dir / "summary.json", {
            "run_stamp": run_stamp,
            "terminal_outcome": "BLOCKED",
            "council_status": result.status,
            "ccp_path": _rel(ccp_path),
        })
        return 3

    # Validate actual models used
    family_errors: list[str] = []
    run_log_data = result.run_log or {}
    for _key, val in (run_log_data.items() if isinstance(run_log_data, dict) else {}.items()):
        if isinstance(val, dict):
            m = val.get("_actual_model") or val.get("model") or val.get("model_id")
            if m:
                fam = family_map.get(str(m), "unknown")
                if fam in _FORBIDDEN_FAMILIES:
                    family_errors.append(f"forbidden family '{fam}' in actual run (model: {m})")

    summary: dict[str, Any] = {
        "run_stamp": run_stamp,
        "terminal_outcome": "PASS" if (
            result.status == "complete"
            and verdict == "Accept"
            and decision_status == "NORMAL"
        ) else "BLOCKED",
        "verdict": verdict,
        "decision_status": decision_status,
        "dp_status": dp_status,
        "council_status": result.status,
        "ccp_path": _rel(ccp_path),
        "live_result": _rel(live_result_path),
        "family_errors": family_errors,
    }
    if result.block_report:
        summary["block_report"] = result.block_report

    _write_json(archive_dir / "summary.json", summary)

    # Draft ruling
    _log_stage(run_log_path, "ruling_draft", "started")
    aur_id = str(header.get("aur_id", "unknown")).replace("/", "_").replace(" ", "_")
    draft_ruling_path = archive_dir / f"draft_ruling_{aur_id}.md"
    approved = verdict == "Accept" and decision_status == "NORMAL" and result.status == "complete"
    fix_items = dp.get("fix_plan") or []
    if not isinstance(fix_items, list):
        fix_items = [str(fix_items)]
    fix_text = "\n".join(f"- {item}" for item in fix_items) if fix_items else "- None recorded."
    draft_ruling_path.write_text(
        f"# Draft Ruling: {header.get('aur_id', 'Council Review')}\n\n"
        f"Archive: `{archive_dir}`\n"
        f"Run stamp: `{run_stamp}`\n"
        f"Council verdict: `{verdict}`\n"
        f"Decision status: `{decision_status}`\n\n"
        f"## Draft Verdict\n\n{'APPROVE' if approved else 'DO NOT APPROVE'}\n\n"
        f"## Fix Plan\n\n{fix_text}\n",
        encoding="utf-8",
    )
    _log_stage(run_log_path, "ruling_draft", "completed", {"path": _rel(draft_ruling_path)})

    if result.block_report or family_errors:
        _write_json(archive_dir / "provider_failures.json", {
            "block_report": result.block_report,
            "family_errors": family_errors,
        })

    _log_stage(run_log_path, "synthesis", "completed")

    # -- Final verdict ---------------------------------------------------------
    print("\n=== COUNCIL VERDICT ===")
    print(f"result.status:          {result.status}")
    print(f"decision_payload.status:{dp_status}")
    print(f"verdict:                {verdict}")
    print(f"decision_status:        {decision_status}")
    if dp.get("fix_plan"):
        print(f"fix_plan:  {dp['fix_plan']}")
    if result.block_report:
        print(f"block_report: {result.block_report}")
    print(f"Archive:    {archive_dir}")

    if family_errors:
        for e in family_errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 3

    if approved:
        print("\n\u2713 COUNCIL APPROVED")
        return 0
    print(f"\n\u2717 Not approved ({result.status} / {dp_status} / {verdict} / {decision_status})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
