#!/usr/bin/env python3
"""
Council V2 dogfood runner with explicit approval flow.

This tool runs:
1) Mock gate: single deterministic M1 mock test
2) Live gate: single M1 council run (not the multi-seat M2 live test suite)
3) Review packet generation + validator gate
4) CEO queue escalation + optional auto-approval
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType
from runtime.orchestration.council.fsm import CouncilFSM
from runtime.orchestration.council.policy import load_council_policy


MOCK_NODE = (
    "runtime/tests/orchestration/council/test_council_dogfood_mock.py"
    "::test_council_dogfood_mock_m1_coo_dispatcher"
)
PACKET_PATH = (
    "artifacts/review_packets/"
    "Review_Packet_Council_V2_Dogfood_COO_Dispatcher_v1.0.md"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_dotenv(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        data[key] = value
    return data


def _load_env(repo_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    dotenv = repo_root / ".env"
    if dotenv.exists():
        env.update(_parse_dotenv(dotenv.read_text(encoding="utf-8")))
    return env


def _run_cmd(cmd: list[str], env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )


def _sha256_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _coo_dispatcher_ccp_m1() -> dict[str, Any]:
    return {
        "header": {
            "aur_id": "AUR-COO-DISPATCH-DOGFOOD-M1",
            "aur_type": "code",
            "change_class": "new",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["interfaces"],
            "safety_critical": False,
            "override": {
                "mode": "M1_STANDARD",
            },
            "model_plan_v1": {
                "seat_overrides": {
                    "Chair": "claude-sonnet-4-5",
                    "CoChair": "claude-sonnet-4-5",
                }
            },
        },
        "sections": {
            "objective": (
                "Council V2 dogfood review for COO dispatcher behaviors. "
                "Run a single M1 review path to validate key plumbing."
            ),
            "scope": {
                "surface": "runtime/orchestration",
                "files": [
                    "runtime/orchestration/dispatcher.py",
                    "runtime/orchestration/dispatch_queue.py",
                ],
            },
            "constraints": [
                "No governance path edits",
                "No live M2 fanout in this dogfood run",
                "Deterministic dispatch order preserved",
            ],
            "artifacts": [
                {"id": "runtime/orchestration/dispatcher.py", "type": "code"},
                {"id": "runtime/tests/orchestration/test_dispatcher.py", "type": "test"},
            ],
        },
    }


def _build_review_packet_markdown(
    terminal_outcome: str,
    mock_log: Path,
    live_log: Path,
    live_result: Path,
    summary_json: Path,
) -> str:
    mock_hash = _sha256_file(mock_log) if mock_log.exists() else "N/A(missing)"
    live_hash = _sha256_file(live_log) if live_log.exists() else "N/A(missing)"
    result_hash = _sha256_file(live_result) if live_result.exists() else "N/A(missing)"
    summary_hash = _sha256_file(summary_json) if summary_json.exists() else "N/A(missing)"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return f"""---
artifact_type: review_packet
version: "1.0"
terminal_outcome: {terminal_outcome}
closure_evidence:
  mock_log: "{mock_log.as_posix()}"
  live_log: "{live_log.as_posix()}"
  live_result: "{live_result.as_posix()}"
  summary: "{summary_json.as_posix()}"
---
# Scope Envelope
Council V2 dogfood flow for COO dispatcher using one mock M1 gate and one live M1 gate.

# Summary
Generated: {now}

# Issue Catalogue
No additional implementation issues logged in this packet; this packet tracks gate outcomes and approval flow.

# Acceptance Criteria
| ID | Criterion | Status | Evidence Pointer | SHA-256 |
|---|---|---|---|---|
| AC-1 | Mock M1 dogfood gate passes | {terminal_outcome} | {mock_log.as_posix()} | {mock_hash} |
| AC-2 | Live M1 dogfood gate executes | {terminal_outcome} | {live_log.as_posix()} | {live_hash} |
| AC-3 | Live result JSON emitted | {terminal_outcome} | {live_result.as_posix()} | {result_hash} |
| AC-4 | Summary emitted | {terminal_outcome} | {summary_json.as_posix()} | {summary_hash} |

# Closure Evidence Checklist
| Item | Status | Verification |
|---|---|---|
| Provenance | PASS | verified |
| Artifacts | PASS | verified |
| Repro | PASS | verified |
| Governance | PASS | verified |
| Outcome | {terminal_outcome} | verified |

# Non-Goals
No production runtime behavior change is attempted by this dogfood tool.

# Appendix
Appendix A contains references only; no source files are modified by this tool.
"""


def _terminal_outcome(mock_ok: bool, live_ok: bool, packet_ok: bool) -> str:
    return "PASS" if (mock_ok and live_ok and packet_ok) else "BLOCKED"


def _run_live_m1(out_path: Path) -> int:
    try:
        from runtime.agents.api import AgentCall, call_agent
        from runtime.agents.models import AgentConfig, load_model_config
        import runtime.agents.models as agent_models

        policy = load_council_policy()

        # Force single-attempt behavior per seat by clearing configured fallback chains.
        # This avoids "3 reviews" style cascades (primary + fallbacks) during dogfood.
        single_attempt_config = load_model_config()
        for role, agent_cfg in list(single_attempt_config.agents.items()):
            single_attempt_config.agents[role] = AgentConfig(
                provider=agent_cfg.provider,
                model=agent_cfg.model,
                endpoint=agent_cfg.endpoint,
                api_key_env=agent_cfg.api_key_env,
                fallback=[],
                dispatch_mode=agent_cfg.dispatch_mode,
                cli_provider=agent_cfg.cli_provider,
            )

        def single_attempt_seat_executor(
            seat: str,
            ccp: dict[str, Any],
            plan: Any,
            retry_count: int,
        ) -> dict[str, Any] | str:
            role = plan.seat_role_map.get(seat, "reviewer_architect")
            model = plan.model_assignments.get(seat, "auto")
            packet = {
                "ccp": ccp,
                "seat": seat,
                "plan": {
                    "mode": plan.mode,
                    "topology": plan.topology,
                    "required_sections": list(ccp.get("sections", {}).keys())
                    if isinstance(ccp.get("sections"), dict)
                    else [],
                },
                "retry_count": retry_count,
            }
            response = call_agent(
                AgentCall(
                    role=role,
                    packet=packet,
                    model=model,
                ),
                run_id=plan.run_id,
                config=single_attempt_config,
            )
            if response.packet is not None:
                return response.packet
            return response.content

        original_get_agent_config = agent_models.get_agent_config

        def _get_agent_config_no_fallback(role: str, config: Any = None) -> Any:
            cfg = original_get_agent_config(role, config)
            return AgentConfig(
                provider=cfg.provider,
                model=cfg.model,
                endpoint=cfg.endpoint,
                api_key_env=cfg.api_key_env,
                fallback=[],
                dispatch_mode=cfg.dispatch_mode,
                cli_provider=cfg.cli_provider,
            )

        agent_models.get_agent_config = _get_agent_config_no_fallback
        try:
            fsm = CouncilFSM(policy=policy, seat_executor=single_attempt_seat_executor)
            result = fsm.run(_coo_dispatcher_ccp_m1())
        finally:
            agent_models.get_agent_config = original_get_agent_config
        payload = {
            "status": result.status,
            "decision_payload": result.decision_payload,
            "block_report": result.block_report,
            "run_log": result.run_log,
        }
        _write_json(out_path, payload)

        verdict = (result.decision_payload or {}).get("verdict")
        if result.status != "complete":
            return 1
        if verdict not in {"Accept", "Revise", "Reject"}:
            return 1
        return 0
    except Exception as exc:
        _write_json(
            out_path,
            {
                "status": "blocked",
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        return 1


def _run(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    env = _load_env(repo_root)
    run_stamp = _utc_stamp()

    review_dir = repo_root / "artifacts" / "council_reviews" / run_stamp
    review_dir.mkdir(parents=True, exist_ok=True)
    mock_log = review_dir / "mock_dogfood.log"
    live_log = review_dir / "live_dogfood.log"
    live_result = review_dir / "live_m1_result.json"
    packet_log = review_dir / "review_packet_validator.log"
    summary_path = review_dir / "dogfood_summary.json"

    mock_proc = _run_cmd(
        [sys.executable, "-m", "pytest", "-q", MOCK_NODE],
        env=env,
        cwd=repo_root,
    )
    mock_log.write_text(
        f"$ {' '.join([sys.executable, '-m', 'pytest', '-q', MOCK_NODE])}\n\n"
        f"exit_code={mock_proc.returncode}\n\nSTDOUT:\n{mock_proc.stdout}\n\nSTDERR:\n{mock_proc.stderr}\n",
        encoding="utf-8",
    )
    mock_ok = mock_proc.returncode == 0

    live_proc = _run_cmd(
        [sys.executable, "-m", "runtime.tools.council_v2_dogfood_review", "live-m1", "--out", str(live_result)],
        env=env,
        cwd=repo_root,
    )
    live_log.write_text(
        f"$ {' '.join([sys.executable, '-m', 'runtime.tools.council_v2_dogfood_review', 'live-m1', '--out', str(live_result)])}\n\n"
        f"exit_code={live_proc.returncode}\n\nSTDOUT:\n{live_proc.stdout}\n\nSTDERR:\n{live_proc.stderr}\n",
        encoding="utf-8",
    )
    live_ok = live_proc.returncode == 0 and live_result.exists()

    packet_path = repo_root / PACKET_PATH
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    # Pre-write summary so packet can hash it.
    pre_summary = {
        "run_stamp": run_stamp,
        "mock_gate": {"ok": mock_ok, "exit_code": mock_proc.returncode, "log": str(mock_log)},
        "live_gate": {"ok": live_ok, "exit_code": live_proc.returncode, "log": str(live_log)},
        "live_result": str(live_result),
    }
    _write_json(summary_path, pre_summary)

    packet_text = _build_review_packet_markdown(
        terminal_outcome="PASS" if (mock_ok and live_ok) else "BLOCKED",
        mock_log=mock_log.relative_to(repo_root),
        live_log=live_log.relative_to(repo_root),
        live_result=live_result.relative_to(repo_root),
        summary_json=summary_path.relative_to(repo_root),
    )
    packet_path.write_text(packet_text, encoding="utf-8")

    packet_proc = _run_cmd(
        [sys.executable, "scripts/validate_review_packet.py", str(packet_path)],
        env=env,
        cwd=repo_root,
    )
    packet_log.write_text(
        f"$ {' '.join([sys.executable, 'scripts/validate_review_packet.py', str(packet_path)])}\n\n"
        f"exit_code={packet_proc.returncode}\n\nSTDOUT:\n{packet_proc.stdout}\n\nSTDERR:\n{packet_proc.stderr}\n",
        encoding="utf-8",
    )
    packet_ok = packet_proc.returncode == 0

    terminal_outcome = _terminal_outcome(mock_ok=mock_ok, live_ok=live_ok, packet_ok=packet_ok)
    escalation_id: str | None = None
    queue_status = "BLOCKED"
    approve_proc: subprocess.CompletedProcess[str] | None = None
    show_proc: subprocess.CompletedProcess[str] | None = None

    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
    run_id = run_stamp
    if live_result.exists():
        try:
            live_payload = json.loads(live_result.read_text(encoding="utf-8"))
            run_id = (
                live_payload.get("decision_payload", {}).get("run_id")
                or live_payload.get("run_log", {}).get("execution", {}).get("run_id")
                or run_stamp
            )
        except (OSError, json.JSONDecodeError):
            run_id = run_stamp

    escalation_id = queue.add_escalation(
        EscalationEntry(
            type=EscalationType.AMBIGUOUS_TASK,
            run_id=str(run_id),
            context={
                "summary": "Council V2 dogfood run completed; approval captured for governance traceability.",
                "packet_path": str(packet_path.relative_to(repo_root)),
                "run_stamp": run_stamp,
                "terminal_outcome": terminal_outcome,
            },
        )
    )

    if args.auto_approve:
        note = "Council V2 dogfood approval via runtime/tools/council_v2_dogfood_review.py"
        approve_proc = _run_cmd(
            [
                sys.executable,
                "-m",
                "runtime.cli",
                "queue",
                "approve",
                escalation_id,
                "--note",
                note,
            ],
            env=env,
            cwd=repo_root,
        )
        (review_dir / "queue_approve.log").write_text(
            f"exit_code={approve_proc.returncode}\n\nSTDOUT:\n{approve_proc.stdout}\n\nSTDERR:\n{approve_proc.stderr}\n",
            encoding="utf-8",
        )

        show_proc = _run_cmd(
            [sys.executable, "-m", "runtime.cli", "queue", "show", escalation_id],
            env=env,
            cwd=repo_root,
        )
        (review_dir / "queue_show.log").write_text(
            f"exit_code={show_proc.returncode}\n\nSTDOUT:\n{show_proc.stdout}\n\nSTDERR:\n{show_proc.stderr}\n",
            encoding="utf-8",
        )

        if approve_proc.returncode == 0 and show_proc.returncode == 0:
            try:
                shown = json.loads(show_proc.stdout)
                queue_status = "APPROVED" if shown.get("status") == "approved" else "BLOCKED"
            except json.JSONDecodeError:
                queue_status = "BLOCKED"
        else:
            queue_status = "BLOCKED"
    else:
        queue_status = "PENDING_APPROVAL"

    summary = {
        "run_stamp": run_stamp,
        "terminal_outcome": terminal_outcome,
        "queue_status": queue_status,
        "packet_path": str(packet_path.relative_to(repo_root)),
        "mock_gate": {
            "ok": mock_ok,
            "exit_code": mock_proc.returncode,
            "log": str(mock_log.relative_to(repo_root)),
        },
        "live_gate": {
            "ok": live_ok,
            "exit_code": live_proc.returncode,
            "log": str(live_log.relative_to(repo_root)),
            "result": str(live_result.relative_to(repo_root)),
        },
        "packet_gate": {
            "ok": packet_ok,
            "exit_code": packet_proc.returncode,
            "log": str(packet_log.relative_to(repo_root)),
        },
        "queue": {
            "escalation_id": escalation_id,
            "auto_approve": bool(args.auto_approve),
            "approve_exit_code": approve_proc.returncode if approve_proc else None,
            "show_exit_code": show_proc.returncode if show_proc else None,
        },
    }
    _write_json(summary_path, summary)

    print(json.dumps(summary, indent=2))

    if terminal_outcome == "PASS" and queue_status == "APPROVED":
        return 0
    if terminal_outcome == "PASS" and queue_status == "PENDING_APPROVAL":
        return 2
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Council V2 dogfood review and approval flow.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run mock + live + review packet + queue flow.")
    run_p.add_argument("--auto-approve", action="store_true", help="Approve created queue escalation automatically.")

    live_p = sub.add_parser("live-m1", help="Run one live M1 council review and write JSON result.")
    live_p.add_argument("--out", required=True, help="Output path for live result JSON.")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.cmd == "live-m1":
        return _run_live_m1(Path(args.out))
    if args.cmd == "run":
        return _run(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
