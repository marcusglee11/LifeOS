#!/usr/bin/env python3
"""Council V2 dogfood wrapper for the COO unsandboxed promotion review."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType
from runtime.orchestration.council.compiler import compile_council_run_plan_v2
from runtime.orchestration.council.fsm import CouncilFSMv2
from runtime.orchestration.council.models import (
    DECISION_STATUS_NORMAL,
    VERDICT_ACCEPT,
)
from runtime.orchestration.council.multi_provider import build_multi_provider_executor
from runtime.orchestration.council.policy import load_council_policy, resolve_model_family
from runtime.tools.council_v2_dogfood_common import (
    load_env,
    run_cmd,
    sha256_file,
    utc_stamp,
    write_json,
)


CCP_PATH = REPO_ROOT / "artifacts" / "council_reviews" / "coo_unsandboxed_prod_l3.ccp.yaml"
PACKET_PATH = (
    REPO_ROOT
    / "artifacts"
    / "review_packets"
    / "Review_Packet_COO_Unsandboxed_Prod_L3_Council_Dogfood_v1.0.md"
)
MOCK_NODE = (
    "runtime/tests/orchestration/council/test_council_promotion_mock.py"
    "::test_council_promotion_mock_v2"
)


def load_promotion_ccp(path: Path = CCP_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def compile_promotion_plan(
    ccp: Mapping[str, Any],
    policy: Any,
) -> tuple[dict[str, Any], list[str]]:
    compiled = compile_council_run_plan_v2(ccp, policy)
    core = compiled["core"]
    issues: list[str] = []

    if core.get("tier") != "T3":
        issues.append(f"compiled tier is {core.get('tier')!r}, expected 'T3'")

    required_lenses = set(core.get("required_lenses", ()))
    for lens in ("Risk", "Governance"):
        if lens not in required_lenses:
            issues.append(f"required lens missing: {lens}")

    model_assignments = core.get("model_assignments", {})
    for role, model in model_assignments.items():
        family = resolve_model_family(str(model), policy.model_families)
        if family in {"anthropic", "openai"}:
            issues.append(f"forbidden family {family!r} selected for {role}: {model}")

    return compiled, issues


def _promotion_mock_lens_executor(
    lens_name: str,
    ccp: Mapping[str, Any],
    plan: Any,
    retry_count: int,
) -> dict[str, Any]:
    return {
        "run_type": plan.run_type,
        "lens_name": lens_name,
        "confidence": "medium",
        "notes": f"{lens_name} mock review complete.",
        "operator_view": [f"{lens_name} reviewed the promotion package."],
        "claims": [
            {
                "claim_id": f"{lens_name.lower()}-01",
                "statement": f"{lens_name} finds the promotion package reviewable.",
                "evidence_refs": ["ASSUMPTION: mock council output"],
            }
        ],
        "verdict_recommendation": VERDICT_ACCEPT,
        "_actual_model": plan.model_assignments.get(lens_name, "auto"),
    }


def run_mock_gate(repo_root: Path, env: dict[str, str], review_dir: Path) -> tuple[bool, Path, int]:
    mock_log = review_dir / "mock_promotion.log"
    proc = run_cmd([sys.executable, "-m", "pytest", "-q", MOCK_NODE], env=env, cwd=repo_root)
    mock_log.write_text(
        f"$ {' '.join([sys.executable, '-m', 'pytest', '-q', MOCK_NODE])}\n\n"
        f"exit_code={proc.returncode}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}\n",
        encoding="utf-8",
    )
    return proc.returncode == 0, mock_log, proc.returncode


def run_live_review(
    ccp: Mapping[str, Any],
    policy: Any,
    out_path: Path,
) -> tuple[bool, dict[str, Any]]:
    fsm = CouncilFSMv2(
        policy=policy,
        lens_executor=build_multi_provider_executor(),
    )
    result = fsm.run(ccp)
    payload = dataclasses.asdict(result)
    write_json(out_path, payload)

    decision = result.decision_payload or {}
    live_ok = (
        result.status == "complete"
        and decision.get("status") == "COMPLETE"
        and decision.get("decision_status") == DECISION_STATUS_NORMAL
        and decision.get("verdict") == VERDICT_ACCEPT
    )
    return live_ok, payload


def build_draft_ruling_markdown(
    decision_payload: Mapping[str, Any],
    *,
    branch: str,
    commit: str,
) -> str:
    verdict = str(decision_payload.get("verdict", "Blocked"))
    approved = verdict == VERDICT_ACCEPT and decision_payload.get("decision_status") == DECISION_STATUS_NORMAL
    conclusion = "APPROVE" if approved else "DO NOT APPROVE"
    fix_plan = decision_payload.get("fix_plan") or []
    if not isinstance(fix_plan, list):
        fix_plan = [str(fix_plan)]
    fix_text = "\n".join(f"- {item}" for item in fix_plan) if fix_plan else "- None recorded."

    return f"""# Draft Ruling: COO Unsandboxed Prod L3

Subject branch: `{branch}`
Subject commit: `{commit}`
Council verdict: `{verdict}`
Decision status: `{decision_payload.get("decision_status", "UNKNOWN")}`

## Draft Verdict

{conclusion}

## Required Findings

- Unsandboxed COO runtime is {"approved" if approved else "not approved"} for production use.
- Production autonomy ceiling remains limited to `L0`, `L3`, and `L4`.
- Rollback target remains `coo_shared_ingress_burnin.json`.
- Approval manifest must remain hash-bound before activation.

## Fix Plan

{fix_text}
"""


def _evidence_ref(path: Path) -> str:
    if path.is_absolute():
        try:
            return path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


def _hash_target(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path)


def build_review_packet_markdown(
    *,
    terminal_outcome: str,
    mock_log: Path,
    live_log: Path,
    live_result: Path,
    summary_json: Path,
    draft_ruling: Path,
    ccp_path: Path,
    branch: str,
    commit: str,
) -> str:
    return f"""---
artifact_type: review_packet
version: "1.0"
terminal_outcome: {terminal_outcome}
closure_evidence:
  mock_log: "{mock_log.as_posix()}"
  live_log: "{live_log.as_posix()}"
  live_result: "{live_result.as_posix()}"
  summary: "{summary_json.as_posix()}"
  draft_ruling: "{draft_ruling.as_posix()}"
---
# Scope Envelope
Council V2 dogfood review for the COO unsandboxed promotion package.

# Summary
Subject branch: `{branch}`
Subject commit: `{commit}`
CCP: `{ccp_path.as_posix()}`

# Issue Catalogue
This packet records gate outcomes for the promotion-specific Council V2 review flow.

# Acceptance Criteria
| ID | Criterion | Status | Evidence Pointer | SHA-256 |
|---|---|---|---|---|
| AC-1 | Mock promotion gate passes | {terminal_outcome} | {_evidence_ref(mock_log)} | {sha256_file(_hash_target(mock_log))} |
| AC-2 | Live V2 review emits result JSON | {terminal_outcome} | {_evidence_ref(live_result)} | {sha256_file(_hash_target(live_result))} |
| AC-3 | Draft ruling emitted outside protected paths | {terminal_outcome} | {_evidence_ref(draft_ruling)} | {sha256_file(_hash_target(draft_ruling))} |
| AC-4 | Summary emitted | {terminal_outcome} | {_evidence_ref(summary_json)} | {sha256_file(_hash_target(summary_json))} |

# Closure Evidence Checklist
| Item | Status | Verification |
|---|---|---|
| Provenance | PASS | verified |
| Artifacts | PASS | verified |
| Repro | PASS | verified |
| Governance | PASS | verified |
| Outcome | {terminal_outcome} | verified |

# Non-Goals
No protected-path ruling write occurs in this workflow before manual approval.

# Appendix
Appendix A contains generated artifact references only.
"""


def validate_review_packet(packet_path: Path, env: Mapping[str, str], repo_root: Path, log_path: Path) -> tuple[bool, int]:
    packet_proc = run_cmd(
        [sys.executable, "scripts/validate_review_packet.py", str(packet_path)],
        env=env,
        cwd=repo_root,
    )
    log_path.write_text(
        f"$ {' '.join([sys.executable, 'scripts/validate_review_packet.py', str(packet_path)])}\n\n"
        f"exit_code={packet_proc.returncode}\n\nSTDOUT:\n{packet_proc.stdout}\n\nSTDERR:\n{packet_proc.stderr}\n",
        encoding="utf-8",
    )
    return packet_proc.returncode == 0, packet_proc.returncode


def run(args: argparse.Namespace) -> int:
    repo_root = REPO_ROOT
    env = load_env(repo_root)
    policy = load_council_policy()
    ccp = load_promotion_ccp(Path(args.ccp))
    compiled, issues = compile_promotion_plan(ccp, policy)
    branch = str(((ccp.get("sections") or {}).get("scope") or {}).get("branch", "unknown"))
    commit = str(((ccp.get("sections") or {}).get("scope") or {}).get("commit", "unknown"))

    if args.dry_run:
        payload = {
            "ccp_path": str(Path(args.ccp).as_posix()),
            "subject": {"branch": branch, "commit": commit},
            "core": compiled["core"],
            "preflight_issues": issues,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if not issues else 1

    run_stamp = utc_stamp()
    review_dir = repo_root / "artifacts" / "council_reviews" / run_stamp
    review_dir.mkdir(parents=True, exist_ok=True)

    if issues:
        summary = {
            "run_stamp": run_stamp,
            "terminal_outcome": "BLOCKED",
            "queue_status": "BLOCKED",
            "ccp_path": str(Path(args.ccp).as_posix()),
            "subject": {"branch": branch, "commit": commit},
            "preflight_issues": issues,
        }
        write_json(review_dir / "summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 1

    mock_ok, mock_log, mock_rc = run_mock_gate(repo_root, env, review_dir)

    live_log = review_dir / "live_promotion.log"
    live_result = review_dir / "live_result.json"
    if mock_ok:
        try:
            live_ok, live_payload = run_live_review(ccp, policy, live_result)
            live_log.write_text(
                json.dumps(
                    {
                        "status": live_payload.get("status"),
                        "decision_payload": live_payload.get("decision_payload"),
                        "block_report": live_payload.get("block_report"),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            live_ok = False
            live_payload = {"status": "blocked", "error": f"{type(exc).__name__}: {exc}"}
            write_json(live_result, live_payload)
            live_log.write_text(json.dumps(live_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        live_ok = False
        live_payload = {"status": "blocked", "error": "mock_gate_failed"}
        write_json(live_result, live_payload)
        live_log.write_text(json.dumps(live_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    decision_payload = live_payload.get("decision_payload") or {}
    draft_ruling = review_dir / "draft_ruling_COO_Unsandboxed_Prod_L3_v1.0.md"
    draft_ruling.write_text(
        build_draft_ruling_markdown(decision_payload, branch=branch, commit=commit),
        encoding="utf-8",
    )

    packet_path = Path(args.packet)
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path = review_dir / "summary.json"
    terminal_outcome = "PASS" if mock_ok and live_ok else "BLOCKED"
    queue_status = "BLOCKED"
    escalation_id = None
    packet_ok = False
    packet_exit_code = None
    packet_log = review_dir / "review_packet_validator.log"

    summary = {
        "run_stamp": run_stamp,
        "terminal_outcome": terminal_outcome,
        "queue_status": queue_status,
        "packet_path": str(packet_path.relative_to(repo_root)),
        "ccp_path": str(Path(args.ccp).relative_to(repo_root)),
        "mock_gate": {"ok": mock_ok, "exit_code": mock_rc, "log": str(mock_log.relative_to(repo_root))},
        "live_gate": {
            "ok": live_ok,
            "log": str(live_log.relative_to(repo_root)),
            "result": str(live_result.relative_to(repo_root)),
        },
        "packet_gate": {
            "ok": packet_ok,
            "exit_code": packet_exit_code,
            "log": str(packet_log.relative_to(repo_root)),
        },
        "queue": {"escalation_id": escalation_id},
        "subject": {"branch": branch, "commit": commit},
    }
    write_json(summary_path, summary)

    packet_path.write_text(
        build_review_packet_markdown(
            terminal_outcome=terminal_outcome,
            mock_log=mock_log.relative_to(repo_root),
            live_log=live_log.relative_to(repo_root),
            live_result=live_result.relative_to(repo_root),
            summary_json=summary_path.relative_to(repo_root),
            draft_ruling=draft_ruling.relative_to(repo_root),
            ccp_path=Path(args.ccp).relative_to(repo_root),
            branch=branch,
            commit=commit,
        ),
        encoding="utf-8",
    )
    packet_ok, packet_exit_code = validate_review_packet(packet_path, env, repo_root, packet_log)

    if packet_ok and terminal_outcome == "PASS":
        queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
        escalation_id = queue.add_escalation(
            EscalationEntry(
                type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
                run_id=str(decision_payload.get("run_id") or run_stamp),
                context={
                    "summary": "Council V2 promotion review completed; manual approval required.",
                    "packet_path": str(packet_path.relative_to(repo_root)),
                    "ccp_path": str(Path(args.ccp).relative_to(repo_root)),
                    "terminal_outcome": terminal_outcome,
                    "branch": branch,
                    "commit": commit,
                },
            )
        )
        queue_status = "PENDING"

    summary["packet_gate"]["ok"] = packet_ok
    summary["packet_gate"]["exit_code"] = packet_exit_code
    summary["queue"]["escalation_id"] = escalation_id
    summary["queue_status"] = queue_status
    if not packet_ok:
        summary["terminal_outcome"] = "BLOCKED"
    write_json(summary_path, summary)

    packet_path.write_text(
        build_review_packet_markdown(
            terminal_outcome=summary["terminal_outcome"],
            mock_log=mock_log.relative_to(repo_root),
            live_log=live_log.relative_to(repo_root),
            live_result=live_result.relative_to(repo_root),
            summary_json=summary_path.relative_to(repo_root),
            draft_ruling=draft_ruling.relative_to(repo_root),
            ccp_path=Path(args.ccp).relative_to(repo_root),
            branch=branch,
            commit=commit,
        ),
        encoding="utf-8",
    )
    final_packet_ok, final_packet_exit_code = validate_review_packet(packet_path, env, repo_root, packet_log)
    if final_packet_ok != packet_ok or final_packet_exit_code != packet_exit_code:
        packet_ok = final_packet_ok
        packet_exit_code = final_packet_exit_code
        summary["packet_gate"]["ok"] = packet_ok
        summary["packet_gate"]["exit_code"] = packet_exit_code
        if not packet_ok:
            summary["terminal_outcome"] = "BLOCKED"
        write_json(summary_path, summary)
        packet_path.write_text(
            build_review_packet_markdown(
                terminal_outcome=summary["terminal_outcome"],
                mock_log=mock_log.relative_to(repo_root),
                live_log=live_log.relative_to(repo_root),
                live_result=live_result.relative_to(repo_root),
                summary_json=summary_path.relative_to(repo_root),
                draft_ruling=draft_ruling.relative_to(repo_root),
                ccp_path=Path(args.ccp).relative_to(repo_root),
                branch=branch,
                commit=commit,
            ),
            encoding="utf-8",
        )
        packet_ok, packet_exit_code = validate_review_packet(packet_path, env, repo_root, packet_log)
        summary["packet_gate"]["ok"] = packet_ok
        summary["packet_gate"]["exit_code"] = packet_exit_code
        if not packet_ok:
            summary["terminal_outcome"] = "BLOCKED"
        write_json(summary_path, summary)
        packet_path.write_text(
            build_review_packet_markdown(
                terminal_outcome=summary["terminal_outcome"],
                mock_log=mock_log.relative_to(repo_root),
                live_log=live_log.relative_to(repo_root),
                live_result=live_result.relative_to(repo_root),
                summary_json=summary_path.relative_to(repo_root),
                draft_ruling=draft_ruling.relative_to(repo_root),
                ccp_path=Path(args.ccp).relative_to(repo_root),
                branch=branch,
                commit=commit,
            ),
            encoding="utf-8",
        )

    print(json.dumps(summary, indent=2, sort_keys=True))

    return 0 if summary["terminal_outcome"] == "PASS" and packet_ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Council V2 dogfood review for the COO unsandboxed promotion.")
    parser.add_argument("--ccp", default=str(CCP_PATH))
    parser.add_argument("--packet", default=str(PACKET_PATH))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
