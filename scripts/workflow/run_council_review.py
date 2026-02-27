#!/usr/bin/env python3
"""One-shot Council V2 review runner for COO Dispatch Phase 1.

Usage:
    python3 scripts/workflow/run_council_review.py [--dry-run] [--ccp PATH]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# -- Model family registry (from config/policy/council_policy.yaml) --------
_FORBIDDEN_FAMILIES = {"anthropic", "openai"}
_FAMILY_MAP: dict[str, str] = {}  # populated by _load_family_map()

REQUIRED_DISTINCT_MODELS = 3
REVIEW_MODELS = {"openrouter/moonshotai/kimi-k2.5", "openrouter/z-ai/glm-5", "openrouter/minimax/minimax-m2.5"}


def _load_family_map(policy_path: Path) -> dict[str, str]:
    """Return model_id → family_name from council_policy.yaml."""
    with policy_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    families: dict[str, str] = {}
    for family, models in (raw.get("model_families") or {}).items():
        for m in models:
            families[m] = family
            # also map opencode/<model> prefix variant
            families[f"opencode/{m}"] = family
    return families


def _preflight(assignments: dict[str, str], family_map: dict[str, str]) -> None:
    """Fail-closed preflight. Raises SystemExit(2) if any check fails."""
    errors: list[str] = []

    # 1. ZEN_REVIEWER_KEY must be set
    if not os.environ.get("ZEN_REVIEWER_KEY"):
        errors.append("ZEN_REVIEWER_KEY not set in environment")

    # 2. Must have >= REQUIRED_DISTINCT_MODELS distinct models
    distinct = set(assignments.values())
    if len(distinct) < REQUIRED_DISTINCT_MODELS:
        errors.append(
            f"Only {len(distinct)} distinct model(s) in assignments "
            f"(need >= {REQUIRED_DISTINCT_MODELS}): {sorted(distinct)}"
        )

    # 3. No anthropic/openai family
    for seat, model in assignments.items():
        family = family_map.get(model, "unknown")
        if family in _FORBIDDEN_FAMILIES:
            errors.append(f"Forbidden family '{family}' for seat '{seat}' (model: {model})")

    if errors:
        print("PREFLIGHT FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  \u2717 {e}", file=sys.stderr)
        sys.exit(2)

    print(f"Preflight OK: {len(distinct)} distinct models \u2014 {sorted(distinct)}")


def _check_actual_models(run_log: dict) -> set[str]:
    """Extract _actual_model values from run_log if present (best-effort)."""
    actual: set[str] = set()
    for key, val in run_log.items():
        if isinstance(val, dict):
            m = val.get("_actual_model") or val.get("model") or val.get("model_id")
            if m:
                actual.add(str(m))
    return actual


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Council V2 review \u2014 COO Dispatch Phase 1")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compile run plan + preflight; no LLM calls")
    parser.add_argument("--ccp", default=None,
                        help="Path to CCP YAML (default: artifacts/council_reviews/coo_dispatch_phase1.ccp.yaml)")
    args = parser.parse_args(argv)

    policy_path = REPO_ROOT / "config" / "policy" / "council_policy.yaml"
    family_map = _load_family_map(policy_path)

    ccp_path = Path(args.ccp) if args.ccp else (
        REPO_ROOT / "artifacts" / "council_reviews" / "coo_dispatch_phase1.ccp.yaml"
    )
    if not ccp_path.exists():
        print(f"ERROR: CCP not found: {ccp_path}", file=sys.stderr)
        return 1

    with ccp_path.open(encoding="utf-8") as f:
        ccp: dict = yaml.safe_load(f)

    header = ccp.get("header", ccp)
    model_plan = header.get("model_plan_v1", {})
    print(f"CCP:        {header['aur_id']}")
    print(f"Touches:    {header['touches']}")
    print(f"Primary:    {model_plan.get('primary', '(default)')}")
    print(f"Independent:{model_plan.get('independent', '(default)')}")
    print(f"Overrides:  {model_plan.get('seat_overrides', {})}")

    from runtime.orchestration.council.policy import load_council_policy
    policy = load_council_policy(policy_path)

    if args.dry_run:
        from runtime.orchestration.council.compiler import compile_council_run_plan_v2
        plan = compile_council_run_plan_v2(ccp, policy)
        core = plan["core"]
        assignments = dict(core["model_assignments"])
        print("\n=== DRY RUN \u2014 Run Plan (no LLM calls) ===")
        print(f"Tier:         {core['tier']}")
        print(f"Topology:     {core['topology']}")
        print(f"Lenses:       {core['required_lenses']}")
        print(f"Independence: {core['independence_required']}")
        print(f"Assignments:\n{json.dumps(assignments, indent=2)}")
        _preflight(assignments, family_map)
        return 0

    # -- Live run ------------------------------------------------------------------
    # Run preflight on planned assignments before spending API tokens
    from runtime.orchestration.council.compiler import compile_council_run_plan_v2
    plan = compile_council_run_plan_v2(ccp, policy)
    _preflight(dict(plan["core"]["model_assignments"]), family_map)

    from runtime.orchestration.council.fsm import CouncilFSMv2
    from runtime.orchestration.council.multi_provider import build_multi_provider_executor

    lens_executor = build_multi_provider_executor()
    council = CouncilFSMv2(policy=policy, lens_executor=lens_executor)

    print("\nRunning council review (live API calls)...")
    result = council.run(ccp)

    # Write result to tmp (ephemeral -- no repo impact)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path("/tmp") / f"council_v2_dispatch_phase1_{ts}.json"
    out_path.write_text(
        json.dumps(dataclasses.asdict(result), indent=2, default=str),
        encoding="utf-8",
    )

    dp = result.decision_payload or {}
    verdict = dp.get("verdict", "")
    decision_status = dp.get("decision_status", "")
    dp_status = dp.get("status", "")

    print(f"\n=== COUNCIL VERDICT ===")
    print(f"result.status:          {result.status}")
    print(f"decision_payload.status:{dp_status}")
    print(f"verdict:                {verdict}")
    print(f"decision_status:        {decision_status}")
    if dp.get("fix_plan"):
        print(f"fix_plan:  {dp['fix_plan']}")
    if result.block_report:
        print(f"block_report: {result.block_report}")

    # Best-effort: check actual models used
    actual_models = _check_actual_models(result.run_log or {})
    if actual_models:
        print(f"Actual models used: {sorted(actual_models)}")
        for m in actual_models:
            fam = family_map.get(m, "unknown")
            if fam in _FORBIDDEN_FAMILIES:
                print(f"ERROR: forbidden family '{fam}' in actual run (model: {m})", file=sys.stderr)
                return 1

    print(f"Result at:  {out_path}")

    # Strict approval bar
    is_approved = (
        result.status == "complete"
        and dp_status == "COMPLETE"
        and verdict == "Accept"
        and decision_status == "NORMAL"
    )
    if is_approved:
        print("\n\u2713 COUNCIL APPROVED \u2014 ready to merge build/coo-dispatch \u2192 main")
        return 0
    else:
        print(f"\n\u2717 Not approved ({result.status} / {dp_status} / {verdict} / {decision_status})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
