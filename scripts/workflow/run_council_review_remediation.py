#!/usr/bin/env python3
"""Run Council V2 dogfood review for the Batch 1 remediation plan."""

from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CCP = REPO_ROOT / "artifacts" / "council_reviews" / "remediation_plan.ccp.yaml"
POLICY_PATH = REPO_ROOT / "config" / "policy" / "council_policy.yaml"
OUT_DIR = REPO_ROOT / "artifacts" / "council_reviews"
FORBIDDEN_FAMILIES = {"anthropic", "openai"}
MIN_DISTINCT_MODELS = 3

sys.path.insert(0, str(REPO_ROOT))


def _load_env_file(path: Path) -> bool:
    if not path.exists():
        return False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)
    return True


def _load_env() -> None:
    candidates = [
        REPO_ROOT / ".env",
        REPO_ROOT.parents[2] / ".env",
    ]
    for candidate in candidates:
        _load_env_file(candidate)


def _subject_hash(ccp: Mapping[str, Any]) -> str:
    payload = json.dumps(ccp, sort_keys=True, default=str).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _normalize_verdict(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"accept", "approved", "go", "pass"}:
        return "Accept"
    if text in {"reject", "rejected", "block", "blocked", "defer", "escalate"}:
        return "Reject"
    return "Revise"


def _extract_evidence_refs(text: str) -> list[str]:
    refs = []
    for token in text.split("REF:")[1:]:
        ref = token.strip().split()[0] if token.strip() else ""
        if ref:
            refs.append(f"REF:{ref}")
    if refs:
        return refs
    if "[ASSUMPTION]" in text:
        return ["ASSUMPTION"]
    return ["ASSUMPTION: missing explicit reference"]


def _claim_strings(packet: Mapping[str, Any]) -> list[str]:
    claims: list[str] = []
    for field in ("key_findings", "risks", "fixes"):
        value = packet.get(field)
        if isinstance(value, list):
            claims.extend(str(item).strip() for item in value if str(item).strip())
    if claims:
        return claims
    for fallback in ("content", "rationale", "notes"):
        value = packet.get(fallback)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
    return ["No structured claims were provided by the reviewer output."]


def _operator_view(packet: Mapping[str, Any]) -> list[str]:
    value = packet.get("operator_view")
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        if items:
            return items
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    rationale = packet.get("rationale")
    if isinstance(rationale, str) and rationale.strip():
        return [rationale.strip()]
    return ["No operator summary returned."]


def _normalize_lens_output(
    raw: Mapping[str, Any] | str,
    lens_name: str,
    run_type: str,
    planned_model: str,
) -> dict[str, Any]:
    packet: dict[str, Any]
    if isinstance(raw, Mapping):
        packet = dict(raw)
    else:
        try:
            parsed = yaml.safe_load(str(raw))
        except Exception:
            parsed = None
        if isinstance(parsed, Mapping):
            packet = dict(parsed)
        else:
            packet = {"content": str(raw)}

    # If already schema-shaped, preserve and stamp actual model.
    if (
        packet.get("run_type") == run_type
        and packet.get("lens_name") == lens_name
        and isinstance(packet.get("claims"), list)
    ):
        packet.setdefault(
            "_actual_model",
            packet.get("model_version") or packet.get("model_used") or planned_model,
        )
        return packet

    confidence = str(packet.get("confidence", "medium")).strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    claims = []
    for idx, text in enumerate(_claim_strings(packet), start=1):
        claims.append(
            {
                "claim_id": f"{lens_name.lower()}-{idx:02d}",
                "statement": text,
                "evidence_refs": _extract_evidence_refs(text),
            }
        )

    actual_model = str(packet.get("model_version") or packet.get("model_used") or planned_model)
    return {
        "run_type": run_type,
        "lens_name": lens_name,
        "confidence": confidence,
        "notes": str(packet.get("notes") or packet.get("rationale") or "Normalized lens output."),
        "operator_view": _operator_view(packet),
        "claims": claims,
        "verdict_recommendation": _normalize_verdict(packet.get("verdict")),
        "_actual_model": actual_model,
    }


def _contains_tool_call_markers(raw: Mapping[str, Any] | str) -> bool:
    if isinstance(raw, Mapping):
        text = json.dumps(raw, sort_keys=True, default=str)
    else:
        text = str(raw)
    lowered = text.lower()
    markers = (
        "[tool_call]",
        "tool =>",
        "read_doc",
        "filesystem_",
        "i need to examine",
        "let me retrieve",
    )
    return any(marker in lowered for marker in markers)


def _selected_models(model_plan: Mapping[str, Any]) -> list[str]:
    selected: list[str] = []
    for key in ("primary", "independent"):
        value = str(model_plan.get(key, "")).strip()
        if value:
            selected.append(value)
    overrides = model_plan.get("seat_overrides", {})
    if isinstance(overrides, Mapping):
        for value in overrides.values():
            model = str(value).strip()
            if model:
                selected.append(model)
    return selected


def _preflight(
    selected_models: list[str],
    policy,
) -> list[str]:
    issues: list[str] = []
    distinct = sorted(set(selected_models))
    if len(distinct) < MIN_DISTINCT_MODELS:
        issues.append(
            f"Need >= {MIN_DISTINCT_MODELS} distinct selected models, got {len(distinct)}: {distinct}"
        )

    for model_name in distinct:
        from runtime.orchestration.council.policy import resolve_model_family

        family = resolve_model_family(model_name, policy.model_families)
        if family in FORBIDDEN_FAMILIES:
            issues.append(
                f"Model '{model_name}' resolves to forbidden family '{family}'."
            )

    if not os.environ.get("ZEN_REVIEWER_KEY"):
        issues.append("ZEN_REVIEWER_KEY missing after loading .env.")

    return issues


def _postrun_blocking_issues(result, core_assignments: Mapping[str, Any], policy) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    decision = result.decision_payload or {}
    run_log = result.run_log or {}

    if result.status != "complete":
        issues.append(
            {
                "id": "council_status",
                "detail": f"Council status is '{result.status}' (expected 'complete').",
            }
        )
    if decision.get("verdict") != "Accept":
        issues.append(
            {
                "id": "protocol_verdict",
                "detail": f"Protocol verdict is '{decision.get('verdict')}', expected 'Accept'.",
            }
        )
    if decision.get("decision_status") != "NORMAL":
        issues.append(
            {
                "id": "decision_status",
                "detail": (
                    f"Decision status is '{decision.get('decision_status')}', expected 'NORMAL'."
                ),
            }
        )

    lens_results = run_log.get("lens_results", {}) if isinstance(run_log, Mapping) else {}
    actual_models = sorted(
        {
            str(packet.get("_actual_model", "")).strip()
            for packet in lens_results.values()
            if isinstance(packet, Mapping) and str(packet.get("_actual_model", "")).strip()
        }
    )
    if len(actual_models) < MIN_DISTINCT_MODELS:
        issues.append(
            {
                "id": "model_diversity",
                "detail": f"Observed {len(actual_models)} distinct lens models: {actual_models}",
            }
        )

    from runtime.orchestration.council.policy import resolve_model_family

    for model_name in actual_models:
        family = resolve_model_family(model_name, policy.model_families)
        if family in FORBIDDEN_FAMILIES:
            issues.append(
                {
                    "id": "model_family_policy",
                    "detail": f"Observed forbidden family '{family}' via model '{model_name}'.",
                }
            )

    # Planned assignments should also avoid forbidden families.
    for seat, model_name in sorted(core_assignments.items()):
        family = resolve_model_family(str(model_name), policy.model_families)
        if family in FORBIDDEN_FAMILIES:
            issues.append(
                {
                    "id": "planned_model_family_policy",
                    "detail": f"Seat '{seat}' planned model '{model_name}' is forbidden family '{family}'.",
                }
            )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Council V2 remediation review.")
    parser.add_argument("--dry-run", action="store_true", help="Compile-only mode.")
    parser.add_argument("--ccp", default=str(DEFAULT_CCP), help="Path to CCP YAML.")
    args = parser.parse_args()

    _load_env()

    ccp_path = Path(args.ccp)
    if not ccp_path.exists():
        print(f"ERROR: CCP not found: {ccp_path}")
        return 1
    with ccp_path.open("r", encoding="utf-8") as handle:
        ccp = yaml.safe_load(handle)
    if not isinstance(ccp, Mapping):
        print("ERROR: CCP must be a mapping.")
        return 1

    from runtime.orchestration.council.compiler import compile_council_run_plan_v2
    from runtime.orchestration.council.policy import load_council_policy

    policy = load_council_policy(POLICY_PATH)
    header = ccp.get("header", {})
    model_plan = header.get("model_plan_v1", {}) if isinstance(header, Mapping) else {}
    if not isinstance(model_plan, Mapping):
        print("ERROR: header.model_plan_v1 must be a mapping.")
        return 1

    selected = _selected_models(model_plan)
    issues = _preflight(selected, policy)
    if issues:
        print("ERROR: model preflight failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    plan = compile_council_run_plan_v2(ccp, policy)
    core = plan["core"]
    print(f"CCP loaded: {header.get('aur_id', 'unknown')}")
    print(f"Touches:    {header.get('touches', [])}")
    print(f"Tier:       {core['tier']}")
    print(f"Topology:   {core['topology']}")
    print(f"Lenses:     {core['required_lenses']}")
    print(f"Models:     {dict(core['model_assignments'])}")

    if args.dry_run:
        print("Dry run complete.")
        return 0

    from runtime.agents.models import load_model_config
    from runtime.orchestration.council.fsm import CouncilFSMv2
    from runtime.orchestration.council.multi_provider import build_multi_provider_executor

    model_config = load_model_config(str(REPO_ROOT / "config" / "models.yaml"))
    model_config = copy.deepcopy(model_config)
    # Keep the run high-end only: avoid implicit role fallback chain.
    for role_name in ("council_reviewer", "council_reviewer_security"):
        agent_cfg = model_config.agents.get(role_name)
        if agent_cfg is not None:
            agent_cfg.fallback = []

    base_executor = build_multi_provider_executor(config=model_config)

    def lens_executor(lens_name: str, lens_ccp: Mapping[str, Any], plan_core, retry_count: int) -> dict[str, Any]:
        raw = base_executor(lens_name, lens_ccp, plan_core, retry_count)
        if _contains_tool_call_markers(raw):
            retry_ccp = copy.deepcopy(dict(lens_ccp))
            sections = retry_ccp.setdefault("sections", {})
            retry_note = (
                "Execution note: tool calls are unavailable. "
                "Use only this packet and return final review YAML without any tool request markers."
            )
            constraints = sections.get("constraints")
            if isinstance(constraints, list):
                if retry_note not in constraints:
                    constraints.append(retry_note)
            else:
                sections["constraints"] = [retry_note]
            raw_retry = base_executor(lens_name, retry_ccp, plan_core, retry_count + 1)
            if not _contains_tool_call_markers(raw_retry):
                raw = raw_retry
        planned_model = str(plan_core.model_assignments.get(lens_name, "auto"))
        return _normalize_lens_output(raw, lens_name, plan_core.run_type, planned_model)

    fsm = CouncilFSMv2(policy=policy, lens_executor=lens_executor)
    result = fsm.run(ccp)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result_path = OUT_DIR / f"remediation_plan_{ts}.json"
    approval_path = OUT_DIR / f"remediation_plan_approval_{ts}.json"

    result_path.write_text(json.dumps(dataclasses.asdict(result), indent=2, default=str), encoding="utf-8")

    blocking = _postrun_blocking_issues(result, core["model_assignments"], policy)
    strict_go = len(blocking) == 0
    decision = result.decision_payload or {}
    approval_packet = {
        "verdict": "GO" if strict_go else "BLOCK",
        "review_packet_id": str(decision.get("run_id") or ""),
        "subject_hash": _subject_hash(ccp),
        "rationale": "Strict approval satisfied." if strict_go else "Strict approval blocked.",
        "conditions": [],
        "blocking_issues": blocking,
        "votes": {
            "council_status": result.status,
            "protocol_verdict": decision.get("verdict"),
            "decision_status": decision.get("decision_status"),
            "tier": decision.get("tier"),
        },
        "models": {
            "selected": sorted(set(selected)),
            "planned_assignments": core["model_assignments"],
        },
        "result_path": str(result_path),
    }
    approval_path.write_text(json.dumps(approval_packet, indent=2), encoding="utf-8")

    print(f"Council result:   {result_path}")
    print(f"Approval packet:  {approval_path}")
    print(f"Council status:   {result.status}")
    print(f"Protocol verdict: {decision.get('verdict')}")
    print(f"Decision status:  {decision.get('decision_status')}")
    print(f"Strict approval:  {'GO' if strict_go else 'BLOCK'}")
    if blocking:
        print("Blocking issues:")
        for issue in blocking:
            print(f"  - {issue['id']}: {issue['detail']}")

    return 0 if strict_go else 1


if __name__ == "__main__":
    raise SystemExit(main())
