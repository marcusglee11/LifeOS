# OpenClaw COO Behavioral Fit Context Pack

- Generated: 2026-03-12
- Commit: `a653fa2bf768d9986f7c1efdc0735c976b890516`
- Ordering: canonical state, runtime code, prompt/config, tests, docs
- Excerpt limit: 200 lines per file

## docs/11_admin/LIFEOS_STATE.md

```text
# LifeOS State

## Canonical Spine

- **Canonical Sources:**
  - [LIFEOS_STATE.md](docs/11_admin/LIFEOS_STATE.md)
  - [BACKLOG.md](docs/11_admin/BACKLOG.md)
- **Derived View:**
  - [AUTONOMY_STATUS.md](docs/11_admin/AUTONOMY_STATUS.md) (derived; canon wins on conflict)
- **Latest Baseline Pack (main HEAD):**
  - `artifacts/packets/status/Repo_Autonomy_Status_Pack__Main.zip`
  - **sha256:** `42772f641a15ba9bf1869dd0c20dcbce0c7ffe6314e73cd5dc396cace86272dd`

**Current Focus:** OpenClaw distill lane operational rollout — shadow-first enablement and active promotion gating
**Active WIP:** build/openclaw-distill-operational-r
**Last Updated:** 2026-03-09 (rev29)

---

## COO Bootstrap Campaign (Steps 1-6)

1. ✓ Step 1A: Structured backlog (`backlog.py`, `config/tasks/backlog.yaml`) — merged 23cd2143
2. ✓ Step 1B: Delegation envelope (`config/governance/delegation_envelope.yaml`) — merged eb75f2e8
3. ✓ Step 2: COO Brain — system prompt, memory seed, brief — merged 51ef1466 + review fixes eedb0fa0
4. ✓ Step 3D: Context builder + parser (`runtime/orchestration/coo/context.py`, `parser.py`) — merged cf7740f1
5. ✓ Step 3E: Templates (`config/tasks/order_templates/`, `templates.py`) — merged 5a7425b3
6. ✓ Step 3F: CLI commands (`runtime/orchestration/coo/commands.py`, `cli.py` extended) — merged 1d6d208c
7. ✓ Step 4G: Post-execution state updater hooks — merged 72548d7e
8. ✓ Step 5: Burn-in (proxy COO validates, CEO observes) — merged 4483fdf0, CEO-approved 2026-03-08
9. ✓ Step 6: Live COO (first real OpenClaw invocation) — build/coo-step6-wiring, 2026-03-08

**Campaign status: ALL 9 STEPS COMPLETE** — live OpenClaw COO operational

**Canonical Plan Authority:** `artifacts/plans/2026-03-05-coo-bootstrap-plan.md` (see `docs/11_admin/Plan_Supersession_Register.md`)

---

## 🟧 Active Workstreams (WIP)

| Status | Workstream | Owner | Deliverable |
|--------|------------|-------|-------------|
| **COMPLETE** | **COO Bootstrap (Steps 1-6)** | Antigravity | Full COO delegation pipeline — all 9 steps merged; live COO operational |
| **MERGED** | **COO Brain (Step 2)** | Codex + Claude Code | System prompt, memory seed, brief — merged 51ef1466 + eedb0fa0 |
| **MERGED** | **COO Jarda Parity v5** | Antigravity | OpenClaw verification tooling + workflow pack (8045e9c5) |
| **MERGED** | **CLI-First Dispatch** | Antigravity | Dispatch engine CLI surface (0938bf0f) |
| **MERGED** | **Sprint 1 Stop-the-Bleeding** | Antigravity | Dead code cleanup, root junk, CI hardening (f8e590fe) |
| **MERGED** | **GitHub Actions Build Loop** | Antigravity | CI automation (0875e5db) |
| **CLOSED** | **Trusted Builder Mode v1.1** | Antigravity | `Council_Ruling_Trusted_Builder_Mode_v1.1.md` (RATIFIED) |
| **CLOSED** | **Policy Engine Authoritative Gating** | Antigravity | `Closure_Record_Policy_Engine_FixPass_v1.0.md` |
| **CLOSED** | **CSO Role Constitution** | Antigravity | `CSO_Role_Constitution_v1.0.md` (Finalized) |
| **WAITING** | OpenCode Deletion Logic | Council | Review Ruling |
| **CLOSED** | **Sprint S1 Phase B (B1-B3)** | Antigravity | Refined Evidence + Boundaries (ACCEPTED + committed) |
| **MERGED** | **Phase 4 (4A0-4D) Full Stack** | Antigravity | CEO Queue, Loop Spine, Test Executor, Code Autonomy - All in main (commit 9f4ee41) |

---

## 🟦 Roadmap Context

- **Phase 1 (Foundation):** DONE
- **Phase 2 (Governance):** DONE
- **Phase 3 (Optimization):** **RATIFIED (APPROVE_WITH_CONDITIONS)** — Council Ruling Phase3 Closure v1.0
  - **Condition C1:** CSO Role Constitution v1.0 (RESOLVED 2026-01-23)
  - **Condition C2:** F3/F4/F7 evidence deferred (RESOLVED 2026-01-27) — Review packets: `artifacts/review_packets/Review_Packet_F3_Tier2.5_Activation_v1.0.md`, `artifacts/review_packets/Review_Packet_F4_Tier2.5_Deactivation_v1.0.md`, `artifacts/review_packets/Review_Packet_F7_Runtime_Antigrav_Protocol_v1.0.md`
- **Phase 4 (Autonomous Construction):** MERGED TO MAIN (2026-02-03)
  - **P0 Pre-req:** Trusted Builder Mode v1.1 (RATIFIED 2026-01-26)
  - **Phase 4A0 (Loop Spine):** MERGED - CLI surface, policy hash, ledger, chain execution
  - **Phase 4A (CEO Queue):** MERGED - Checkpoint resolution backend with escalation
  - **Phase 4B (Backlog Selection):** MERGED - Task selection integration + closure evidence v1.3
  - **Phase 4C (OpenCode Test Execution):** MERGED - Pytest runner with P0-2 hardening
  - **Phase 4D (Code Autonomy Hardening):** MERGED - Protected paths, syntax validation, bypass seam closure
- **Phase 5 (COO Bootstrap):** COMPLETE (2026-03-05 → 2026-03-08)
  - All 9 steps merged; live OpenClaw COO (gpt-5.3-codex) operational via gateway
  - `lifeos coo propose` invokes live COO; Stage A parity + Stage B real-backlog = PASS

---

## ⚠️ System Blockers

None — all prior blockers resolved:
- ~~Model reliability~~ → Zen paid routing merged (`adab507`, 2026-02-20)
- ~~PyYAML missing~~ → PyYAML 6.0.3 installed; steward phase works in E2E proof
- ~~Auto-commit gap~~ → Working in recent merges (8f6287e, adab507, cb5f5d9)
- Step 2 (coo-brain) pending Codex test pass — not a blocker, normal pipeline

---

## 🟩 Recent Wins

- **2026-03-09:** OpenClaw distill lane operational rollout packet defined — canonical runbook now specifies session-scoped shadow enablement, 12-run / 2-session shadow window, blocker policy, CEO-approved shadow receipt, forced-failure drill, and active re-approval after fingerprint drift. Backlog and state now track rollout as an explicit operational work item.
- **2026-03-08:** COO Bootstrap Step 6 COMPLETE — `lifeos coo propose` invokes live OpenClaw COO (gpt-5.3-codex); `lifeos coo direct` wired with escalation packet parsing; Stage A (propose+NTP) PASS; Stage B real-backlog CEO verdict = PASS; 60 tests; BIN fixtures removed. Evidence: `artifacts/coo/step6_shadow_validation.md`.
- **2026-03-08:** COO Bootstrap Step 5 COMPLETE — proxy COO validated 7/7 scenarios on frozen substrate; zero defects; CEO-approved. (merge commit 4483fdf0)
- **2026-03-06:** COO Jarda Parity v5 — OpenClaw verification tooling + workflow pack improvements (merge commit 8045e9c5)
- **2026-03-05:** COO 3F CLI — `lifeos coo {propose,approve,status,report,direct}` commands (merge commit 1d6d208c)
- **2026-03-05:** COO 3D Context/Parser — context builder + proposal parser with retry/escalation (merge commit cf7740f1)
- **2026-03-05:** COO 3E Templates — order templates for build/content/hygiene task types (merge commit 5a7425b3)
- **2026-03-05:** COO 4G State Updater — post-execution backlog + state update hooks (merge commit 72548d7e)
- **2026-03-05:** Dispatch Codex Fixes — dispatch engine hardening (merge commit 62d74ecc)
- **2026-03-05:** COO 1B Delegation Envelope — autonomy level config (merge commit eb75f2e8)
- **2026-03-05:** COO 1A Structured Backlog — TaskEntry schema + seed data (merge commit 23cd2143)
- **2026-03-05:** COO Bootstrap Review — council-reviewed plan (Codex + Gemini) (merge commit 212bff24)
- **2026-03-04:** Bypass Monitor Wiring — spine bypass monitoring integration (merge commit f953093c)
- **2026-03-04:** Fix Steward Runner — steward config fix (merge commit a1f67490)
- **2026-03-03:** Sprint Deferments D1-D3 — review deferments batch (merge commit 84f0f608)
- **2026-03-03:** CLI-First Dispatch — dispatch engine CLI surface (merge commit 0938bf0f)
- **2026-03-02:** Sprint 1 Stop-the-Bleeding — dead code cleanup, root junk, CI hardening (merge commit f8e590fe)
- **2026-03-01:** GitHub Actions Build Loop — CI automation (merge commit 0875e5db)
- **2026-02-28:** Worktree-First Build Architecture — mandatory isolation for build/fix/hotfix/spike branches; `start_build.py` with topic-first CLI + `--recover-primary`; `close_build.py` with isolation hard-block; DispatchEngine auto-remediation loop; safety gate isolation check; 97 targeted tests. Review fix: missing `import subprocess` in dispatch/engine.py. (merge commit df4bb54)
- **2026-02-27:** Batch2 Burn In — chore: refresh runtime_status.json (closure); fix(steward): add burn-in reports and tech debt inventory to admin allowlist; chore: refresh runtime_status.json (closure); chore(burn-in): stage TECH_DEBT_INVENTORY.md from concurrent audit session; docs(burn-in): Batch 2 closure report + Council V2 evaluation (and 6 more) — 1/1 targeted test command(s) passed. (merge commit 1a5db9f)
- **2026-02-27:** Batch 1 Burn-In COMPLETE (`78473e3`) — 6 spine runs; 40 new tests (2147 total, 0 regressions); `BudgetConfig.__post_init__` validation; `workflow_pack.py` worktree fix; 7 key findings documented for Batch 2 procedure improvement. Report: `docs/11_admin/Batch1_BurnIn_Report.md`
- **2026-02-23:** Council V2 Wave2 Integration — chore: refresh runtime_status.json (closure); fix: review-agent hardening pass — FSMv2 mission-safe + schema tightening; feat: Wave 2 — FSM wiring, A6 synthesis, A8 fidelity, A9 advisory, review.py; feat: A7 Challenger review with rework loop; test: A5 lens dispatch TDD tests (red phase) — 1/1 targeted test command(s) passed. (merge commit 38d5b28)
- **2026-02-23:** Council V2 A1 Fsm — chore: refresh runtime_status.json (closure); feat(council): A1 - CouncilFSMv2 with 12-state machine; feat(council): A2 - v2.2.1 schemas, models, and validators; feat(council): A3+A4 - tier routing, lens selection, independence v2.2.1 — 1/1 targeted test command(s) passed. (merge commit 5215cd3)
- **2026-02-22:** Repo Hygiene Sprint 20260221 — chore: refresh runtime_status.json (closure); chore(dead-code): remove unused spine imports + strengthen hygiene tests; chore: bump backlog date + enable superpowers plugin in settings; chore(config): fix pytest constraint + un-ignore passing smoke tests; chore(test): tighten test_state_hygiene.py (remove unused import, assert row found) (and 6 more) — 1/1 targeted test command(s) passed. (merge commit e6ee997)
- **2026-02-21:** Opencode Loop Stabilization 20260220 — chore: refresh runtime_status.json (closure); fix(steward): correct _commit_code_changes return type annotation; fix(opencode): implement retrospective stabilization batch — 1/1 targeted test command(s) passed. (merge commit 8f6287e)
- **2026-02-19:** **W5-T02 Checkpoint/Resume E2E Proof COMPLETE** — 6 integration tests proving full checkpoint/resume cycle: escalation → checkpoint YAML on disk → resolution seam → resume with policy hash continuity → terminal packet with ledger anchor. Evidence: `artifacts/evidence/W5_T02_checkpoint_resume_proof.txt`
- **2026-02-18:** Worktree Outside Repo Resolution 20260218 — chore: refresh runtime_status.json (closure); fix(worktree): resolve repo root from script location when invoked outside repo — 1/1 targeted test command(s) passed. (merge commit ba63f57)
- **2026-02-18:** W4-T03/T04 OpenClaw Integration — feat: OpenClaw->Spine execution bridge, clean-worktree enforcement, CLI command spine run-openclaw-job — 1/1 targeted test command(s) passed. (merge commit c53bdcc)
- **2026-02-18:** Openclaw Boundary Enforcement 20260218 — chore: refresh runtime_status.json (closure); feat: OpenClaw boundary enforcement gap-fill (dmScope, AuthHealth, break-glass) — 1/1 targeted test command(s) passed. (merge commit 9230ac7)
- **2026-02-18:** Openclaw Security Hardening 20260218 — chore: refresh runtime_status.json (closure); feat(openclaw): security hardening — fail-closed startup, cron egress parking, policy alignment — 1/1 targeted test command(s) passed. (merge commit 446c6dc)
- **2026-02-17:** W7 T02 T03 Stabilization 20260216 — chore: refresh runtime_status.json (closure); fix: commit regenerated runtime_status.json during closure; chore: refresh runtime_status.json (pre-merge); chore: normalize CRLF→LF in test_packet_dir_isolation.py; fix: remove -uall flag from cleanliness_gate.py (WSL timeout) (and 3 more) — 1/1 targeted test command(s) passed. (merge commit e566dc3)
- **2026-02-16:** Openclaw Closure Routing Fix 20260216 — fix: stabilize openclaw closure preflight routing — 2/2 targeted test command(s) passed. (merge commit e5b0cb1)
- **2026-02-16:** W7 T01 Ledger Hash Chain — fix: W7-T01 review fixes — numeric schema parsing + fail-closed append hardening; feat: W7-T01 Ledger hash-chain hardening with fail-closed v1.1 enforcement — 1/1 targeted test command(s) passed. (merge commit 558c375)
- **2026-02-14:** E2e Spine Proof — chore: gitignore agent workspace metadata files; Fix review findings: stale blocker, artifact path, doc stewardship; docs: Add E2E Spine Proof build summary; docs: Update STATE and BACKLOG after E2E spine proof; feat: Finalize Emergency_Declaration_Protocol v1.0 (E2E Spine Proof) (and 4 more) — 1/1 targeted test command(s) passed. (merge commit 55a362b)
- **2026-02-14:** **E2E Spine Proof COMPLETE (W5-T01)** — First successful autonomous build loop execution: `run_20260214_053357` finalized Emergency_Declaration_Protocol v1.0 through full 6-phase chain (hydrate→policy→design→build→review→steward). Evidence: `artifacts/terminal/TP_run_20260214_053357.yaml`, commit `195bd4d`. Discovered/fixed 2 blockers: obsolete model names (`glm-4.7-free`, `minimax-m2.1-free`) and insufficient timeout (120s→300s). **Core spine infrastructure validated.**
- **2026-02-14:** Auto State Backlog Update — feat: automatic STATE/BACKLOG updates during build closure — 1/1 targeted test command(s) passed. (merge commit b7a879e)
- **2026-02-12:** Canonical plan v1.1 refreshed with granular task IDs and supersession lock; runtime status generator now emits both `artifacts/status/runtime_status.json` and `artifacts/packets/status/checkpoint_report_<YYYYMMDD>.json`.
- **2026-02-12:** Doc stewardship gate executed successfully for all modified docs (`python3 scripts/claude_doc_stewardship_gate.py` PASS).
- **2026-02-10:** EOL Clean Invariant Hardening — Root cause fixed (system `core.autocrlf=true` conflicted with `.gitattributes eol=lf`), 289-file mechanical renormalization, config-aware clean gate (`coo_land_policy clean-check`), acceptance closure validator (`coo_acceptance_policy`), EOL_Policy_v1.0 canonical doc, 37 new tests.
- **2026-02-11:** OpenClaw COO acceptance verified — OpenClaw installed/configured and P1 acceptance probe passed in local WSL2 runtime.
- **2026-02-08:** Manual v2.1 Reconciliation — CRLF root-cause fix (.gitattributes), 36 tests re-enabled (1335→1371), free Zen models configured, manual v2.1 corrected (StewardMission & LLM backend gaps were already closed).
- **2026-02-08:** Deletion Safety Hardening — Article XIX enforcement, safe_cleanup.py guards, 8 integration tests.
- **2026-02-08:** Documentation Stewardship - Relocated 5 root documentation files to canonical locations in `docs/11_admin`, `docs/00_foundations`, and `docs/99_archive`. Updated project index and state.
- **2026-02-03:** Repository Branch Cleanup - Assessed and cleaned 9 local branches, archived 8 with tags, deleted 1 obsolete WIP branch, cleared 7 stashes. All work verified in main. Single canonical branch (main) with 11 archive tags.
- **2026-02-03:** Phase 4 (4A0-4D) MERGED TO MAIN - Full autonomous build loop stack canonical (merge commit 9f4ee41, 1327 passing tests)
- **2026-02-02:** Phase 4A0 Loop Spine P0 fixes complete - CLI surface (lifeos/coo spine), real policy hash, ledger integration, chain execution
- **2026-01-29:** Sprint S1 Phase B (B1-B3) refinements ACCEPTED and committed. No regressions (22 baseline failures preserved).
- **2026-01-29:** P0 Repo Cleanup and Commit (滿足 Preflight Check).
- **2026-01-26:** Trusted Builder Mode v1.1 Ratified (Council Ruling).
- **2026-01-23:** Policy Engine Authoritative Gating — FixPass v1.0 (Council PASS).
- **2026-01-18:** Raw Capture Primitive Standardized (Evidence Capture v0.1).
- **2026-01-17:** Git Workflow v1.1 Accepted (Fail-Closed, Evidence-True).
- **2026-01-16:** Phase 3 technical deliverables complete (Council ratification pending).
```

## runtime/orchestration/coo/invoke.py

```text
"""Thin adapter for invoking the live OpenClaw COO agent."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


class InvocationError(RuntimeError):
    """Raised when the OpenClaw subprocess fails, times out, or returns unusable output."""


# Sub-keys that appear in proposals list items and must be indented 2 spaces.
_PROPOSALS_SUB_KEYS = frozenset({
    "rationale",
    "proposed_action",
    "urgency_override",
    "suggested_owner",
})


def _normalize_proposal_indentation(text: str) -> str:
    """Normalize proposals YAML so sub-keys are indented under their list items.

    The live COO sometimes outputs proposals with sub-keys at column 0:
      proposals:
      - task_id: T-001
      rationale: "..."          <- should be indented by 2 spaces

    This normalizer adds the missing indentation so yaml.safe_load() can parse it.
    """
    lines = text.split("\n")
    result: list[str] = []
    in_item = False

    for line in lines:
        if line.startswith("- task_id:") or line.startswith("-task_id:"):
            in_item = True
            result.append(line)
            continue

        if in_item and line and not line.startswith(" "):
            key = line.split(":")[0].strip().lstrip("- ")
            if key in _PROPOSALS_SUB_KEYS:
                result.append("  " + line)
                continue
            else:
                in_item = False

        result.append(line)

    return "\n".join(result)


def invoke_coo_reasoning(
    context: dict,
    mode: str,
    repo_root: Path,
    timeout_s: int = 120,
) -> str:
    """
    Invoke the live OpenClaw COO with the given context.

    Returns raw COO output text (YAML body).
    Raises InvocationError on subprocess failure or timeout.

    :param context: Context dict to pass as the message body (serialized to JSON).
    :param mode: "propose" | "direct" — included in context for COO routing.
    :param repo_root: Repository root path (unused in CLI invocation; kept for future SDK use).
    :param timeout_s: Subprocess timeout in seconds.
    """
    payload = dict(context)
    payload["mode"] = mode

    message = json.dumps(payload, sort_keys=True)

    cmd = [
        "openclaw",
        "agent",
        "--agent", "main",
        "--message", message,
        "--json",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise InvocationError(
            f"OpenClaw agent timed out after {timeout_s}s"
        ) from exc
    except FileNotFoundError as exc:
        raise InvocationError(
            "openclaw binary not found — is OpenClaw installed and on PATH?"
        ) from exc

    if result.returncode != 0:
        stderr_snippet = result.stderr[:500] if result.stderr else "(no stderr)"
        raise InvocationError(
            f"openclaw exited {result.returncode}: {stderr_snippet}"
        )

    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InvocationError(
            f"openclaw output is not valid JSON: {exc}"
        ) from exc

    if envelope.get("status") != "ok":
        raise InvocationError(
            f"openclaw returned status={envelope.get('status')!r}"
        )

    try:
        payloads = envelope["result"]["payloads"]
        raw_text: str = payloads[0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise InvocationError(
            f"Unexpected openclaw output shape: {exc}"
        ) from exc

    return _normalize_proposal_indentation(raw_text)
```

## runtime/orchestration/coo/commands.py

```text
"""CLI command handlers for COO orchestration flows."""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType
from runtime.orchestration.coo.backlog import load_backlog
from runtime.orchestration.coo.context import (
    build_propose_context,
    build_report_context,
    build_status_context,
)
from runtime.orchestration.coo.invoke import InvocationError, invoke_coo_reasoning
from runtime.orchestration.coo.parser import ParseError, parse_proposal_response
from runtime.orchestration.coo.validation import validate_coo_response
from runtime.orchestration.coo.templates import instantiate_order, load_template
from runtime.orchestration.dispatch.order import OrderValidationError, parse_order
from runtime.util.atomic_write import atomic_write_text


NTP_SCHEMA_VERSION = "nothing_to_propose.v1"
ESCALATION_SCHEMA_VERSION = "escalation_packet.v1"


_BACKLOG_RELATIVE_PATH = Path("config/tasks/backlog.yaml")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


def _emit_behavioral_violations(mode: str, raw_output: str, context: dict[str, Any]) -> bool:
    result = validate_coo_response(raw_output, mode=mode, context=context)
    if result.is_valid:
        return False

    detail = "; ".join(f"{item.code}: {item.message}" for item in result.violations)
    warn_only = os.environ.get("LIFEOS_COO_BEHAVIOR_WARN_ONLY") == "1"
    if warn_only:
        _print_error(f"Warning: COO behavioral validation warning ({mode}): {detail}")
        return False

    _print_error(f"Error: COO behavioral validation failed ({mode}): {detail}")
    return True


def cmd_coo_status(args: argparse.Namespace, repo_root: Path) -> int:
    """Print structured backlog status summary."""
    try:
        context = build_status_context(repo_root)
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1

    if getattr(args, "json", False):
        print(json.dumps(context, indent=2, sort_keys=True))
        return 0

    by_status = context.get("by_status", {})
    by_priority = context.get("by_priority", {})

    print(f"backlog: {context.get('total_tasks', 0)} tasks")
    print(f"  pending:     {by_status.get('pending', 0)}")
    print(f"  in_progress: {by_status.get('in_progress', 0)}")
    print(f"  completed:   {by_status.get('completed', 0)}")
    print(f"  blocked:     {by_status.get('blocked', 0)}")
    print()
    print(f"actionable ({context.get('actionable_count', 0)}):")
    print(
        "  "
        f"P0: {by_priority.get('P0', 0)}  "
        f"P1: {by_priority.get('P1', 0)}  "
        f"P2: {by_priority.get('P2', 0)}  "
        f"P3: {by_priority.get('P3', 0)}"
    )
    print()
    if context.get("canonical_state_present"):
        canonical_state = context.get("canonical_state", {})
        print(f"canonical current focus: {canonical_state.get('current_focus', '') or 'available'}")
        print(f"canonical active wip:    {canonical_state.get('active_wip', '') or 'available'}")
    else:
        print("canonical state: unavailable")

    execution_truth = context.get("execution_truth", {})
    if context.get("execution_truth_present"):
        summary = execution_truth.get("authoritative_status_summary", {})
        print(
            "execution truth:"
            f" last_run={summary.get('last_run_id', '') or 'none'}"
            f" outcome={summary.get('last_outcome', '') or 'unknown'}"
            f" pending={summary.get('pending_count', 0)}"
            f" active={summary.get('active_count', 0)}"
            f" blocked={summary.get('blocked_count', 0)}"
        )
    else:
        print("execution truth: unavailable")
    return 0


def _parse_ntp(raw_output: str) -> dict[str, Any]:
    """Parse a nothing_to_propose.v1 YAML block. Raises ParseError if invalid."""
    try:
        raw = yaml.safe_load(raw_output.strip())
    except yaml.YAMLError as exc:
        raise ParseError(f"NTP output is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ParseError("NTP output must be a YAML mapping")
    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != NTP_SCHEMA_VERSION:
        raise ParseError(
            f"Unsupported schema_version: {schema_version!r}. "
            f"Expected {NTP_SCHEMA_VERSION!r}"
        )
    if not str(raw.get("reason", "")).strip():
        raise ParseError("NTP output missing required 'reason' field")
    return raw


def _parse_escalation_packet(raw_output: str) -> dict[str, Any]:
    """Parse an escalation_packet.v1 YAML block. Raises ParseError if invalid."""
    try:
        raw = yaml.safe_load(raw_output.strip())
    except yaml.YAMLError as exc:
        raise ParseError(f"Escalation packet is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ParseError("Escalation packet must be a YAML mapping")
    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != ESCALATION_SCHEMA_VERSION:
        raise ParseError(
            f"Unsupported schema_version: {schema_version!r}. "
            f"Expected {ESCALATION_SCHEMA_VERSION!r}"
        )
    if not str(raw.get("type", "")).strip():
        raise ParseError("Escalation packet missing required 'type' field")
    if not isinstance(raw.get("options"), list) or not raw["options"]:
        raise ParseError("Escalation packet 'options' must be a non-empty list")
    return raw


def cmd_coo_propose(args: argparse.Namespace, repo_root: Path) -> int:
    """Invoke live COO and emit task proposal or NothingToPropose response."""
    try:
        context = build_propose_context(repo_root)
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1

    try:
        raw_output = invoke_coo_reasoning(context, mode="propose", repo_root=repo_root)
    except InvocationError as exc:
        _print_error(f"Error: COO invocation failed: {exc}")
        return 1
    if _emit_behavioral_violations("propose", raw_output, context):
        return 1

    # Try parsing as task_proposal.v1 first
    try:
        parse_proposal_response(raw_output)
        kind = "task_proposal"
        if getattr(args, "json", False):
            try:
                payload_dict = yaml.safe_load(raw_output.strip())
            except yaml.YAMLError:
                payload_dict = {"raw": raw_output}
            print(json.dumps({"kind": kind, "payload": payload_dict}, indent=2))
        else:
            print(raw_output.strip())
        return 0
    except ParseError:
        pass

    # Fall back to nothing_to_propose.v1
    try:
        ntp_dict = _parse_ntp(raw_output)
        kind = "nothing_to_propose"
        if getattr(args, "json", False):
            print(json.dumps({"kind": kind, "payload": ntp_dict}, indent=2))
        else:
            print(raw_output.strip())
        return 0
    except ParseError as exc:
        _print_error(f"Error: COO output failed validation: {exc}")
        return 1


def cmd_coo_approve(args: argparse.Namespace, repo_root: Path) -> int:
    """Approve tasks and write validated ExecutionOrder files into dispatch inbox."""
```

## runtime/orchestration/coo/context.py

```text
"""
Context builders for COO proposal/status/report flows.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml

from runtime.orchestration.coo.backlog import TaskEntry, filter_actionable, load_backlog
from runtime.orchestration.coo.execution_truth import build_execution_truth


_BACKLOG_RELATIVE_PATH = Path("config/tasks/backlog.yaml")
_DELEGATION_RELATIVE_PATH = Path("config/governance/delegation_envelope.yaml")
_BRIEF_RELATIVE_PATH = Path("artifacts/coo/brief.md")
_CANONICAL_STATE_RELATIVE_PATH = Path("docs/11_admin/LIFEOS_STATE.md")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_to_dict(task: TaskEntry) -> dict[str, Any]:
    return asdict(task)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError(
            f"Expected YAML mapping in {path}, got {type(raw).__name__}"
        )
    return raw


def _read_optional_brief(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _extract_marker(content: str, label: str) -> str:
    pattern = re.compile(rf"^\*\*{re.escape(label)}:\*\*\s*(.+)$", re.MULTILINE)
    match = pattern.search(content)
    return match.group(1).strip() if match else ""


def _read_canonical_state(repo_root: Path) -> tuple[dict[str, Any], bool]:
    path = repo_root / _CANONICAL_STATE_RELATIVE_PATH
    if not path.exists():
        return (
            {
                "path": str(_CANONICAL_STATE_RELATIVE_PATH),
                "reason": "missing",
                "content": "",
            },
            False,
        )

    content = path.read_text(encoding="utf-8")
    return (
        {
            "path": str(_CANONICAL_STATE_RELATIVE_PATH),
            "content": content,
            "current_focus": _extract_marker(content, "Current Focus"),
            "active_wip": _extract_marker(content, "Active WIP"),
            "last_updated": _extract_marker(content, "Last Updated"),
        },
        True,
    )


_PROPOSE_OUTPUT_SCHEMA_EXAMPLE = """\
schema_version: task_proposal.v1
proposals:
  - task_id: T-001
    rationale: "Highest priority with all deps met."
    proposed_action: dispatch
    urgency_override: null
    suggested_owner: codex
  - task_id: T-002
    rationale: "Next priority; defer until T-001 complete."
    proposed_action: defer
    urgency_override: null
    suggested_owner: ""
"""

_NTP_OUTPUT_SCHEMA_EXAMPLE = """\
schema_version: nothing_to_propose.v1
reason: "No pending actionable tasks after policy checks."
recommended_follow_up: "Wait for blocked tasks to unblock."
"""

_PROPOSE_OUTPUT_SCHEMA = {
    "description": (
        "Required output format for propose mode. "
        "Output MUST be valid YAML with exactly this structure. "
        "Each item in 'proposals' MUST be indented by 2 spaces under the '-' marker. "
        "Do NOT use a 'task:' key. "
        "Do NOT use markdown code fences."
    ),
    "task_proposal_example": _PROPOSE_OUTPUT_SCHEMA_EXAMPLE,
    "nothing_to_propose_example": _NTP_OUTPUT_SCHEMA_EXAMPLE,
    "rules": {
        "schema_version": "must be exactly 'task_proposal.v1' or 'nothing_to_propose.v1'",
        "proposed_action": "must be one of: dispatch, defer, escalate",
        "urgency_override": "null or one of: P0, P1, P2, P3",
        "suggested_owner": "codex, claude_code, gemini, or empty string",
        "indentation": "sub-keys of each proposals list item must be indented 4 spaces (2 for '-' + 2 for content)",
    },
}


def build_propose_context(repo_root: Path) -> dict[str, Any]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    delegation_path = repo_root / _DELEGATION_RELATIVE_PATH
    brief_path = repo_root / _BRIEF_RELATIVE_PATH

    tasks = load_backlog(backlog_path)
    actionable = filter_actionable(tasks)
    delegation = _load_yaml_mapping(delegation_path)
    canonical_state, canonical_state_present = _read_canonical_state(repo_root)
    execution_truth = build_execution_truth(repo_root)

    return {
        "actionable_tasks": [_task_to_dict(task) for task in actionable],
        "delegation_envelope": delegation,
        "backlog_path": str(backlog_path),
        "brief": _read_optional_brief(brief_path),
        "canonical_state": canonical_state,
        "canonical_state_present": canonical_state_present,
        "execution_truth": execution_truth,
        "execution_truth_present": bool(execution_truth.get("truth_data_present")),
        "generated_at": _now_iso(),
        "output_schema": _PROPOSE_OUTPUT_SCHEMA,
    }


def build_status_context(repo_root: Path) -> dict[str, Any]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    tasks = load_backlog(backlog_path)
    actionable = filter_actionable(tasks)
    canonical_state, canonical_state_present = _read_canonical_state(repo_root)
    execution_truth = build_execution_truth(repo_root)

    by_status = {"pending": 0, "in_progress": 0, "completed": 0, "blocked": 0}
    for task in tasks:
        by_status[task.status] = by_status.get(task.status, 0) + 1

    by_priority = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for task in actionable:
        by_priority[task.priority] = by_priority.get(task.priority, 0) + 1

    return {
        "total_tasks": len(tasks),
        "by_status": by_status,
        "by_priority": by_priority,
        "actionable_count": len(actionable),
        "canonical_state": canonical_state,
        "canonical_state_present": canonical_state_present,
        "execution_truth": execution_truth,
        "execution_truth_present": bool(execution_truth.get("truth_data_present")),
        "generated_at": _now_iso(),
    }


def build_report_context(repo_root: Path) -> dict[str, Any]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    delegation_path = repo_root / _DELEGATION_RELATIVE_PATH

    tasks = load_backlog(backlog_path)
    delegation = _load_yaml_mapping(delegation_path)
    canonical_state, canonical_state_present = _read_canonical_state(repo_root)
    execution_truth = build_execution_truth(repo_root)

    return {
        "all_tasks": [_task_to_dict(task) for task in tasks],
        "delegation_envelope": delegation,
        "canonical_state": canonical_state,
        "canonical_state_present": canonical_state_present,
        "execution_truth": execution_truth,
        "execution_truth_present": bool(execution_truth.get("truth_data_present")),
        "generated_at": _now_iso(),
    }
```

## runtime/orchestration/coo/parser.py

```text
"""
Parser utilities for COO proposal responses and execution-order generation.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import yaml

from runtime.orchestration.coo.backlog import TaskEntry

PROPOSAL_SCHEMA_VERSION = "task_proposal.v1"

_VALID_ACTIONS = {"dispatch", "defer", "escalate"}
_VALID_URGENCY = {"P0", "P1", "P2", "P3"}
_YAML_FENCE_RE = re.compile(r"```yaml\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_ORDER_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


@dataclass
class TaskProposal:
    task_id: str
    rationale: str
    urgency_override: Optional[str]
    suggested_owner: str
    proposed_action: str


class ParseError(ValueError):
    pass


def _extract_yaml_payload(text: str) -> str:
    match = _YAML_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_proposal_response(text: str) -> list[TaskProposal]:
    payload = _extract_yaml_payload(text)
    try:
        raw = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise ParseError(f"Failed to parse proposal YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ParseError(
            f"Proposal payload must be a YAML mapping, got {type(raw).__name__}"
        )

    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != PROPOSAL_SCHEMA_VERSION:
        raise ParseError(
            f"Unsupported schema_version: {schema_version!r}. "
            f"Expected {PROPOSAL_SCHEMA_VERSION!r}"
        )

    raw_proposals = raw.get("proposals")
    if not isinstance(raw_proposals, list):
        raise ParseError("'proposals' must be a list")
    if not raw_proposals:
        raise ParseError("No proposals found in response")

    proposals: list[TaskProposal] = []
    for idx, entry in enumerate(raw_proposals):
        if not isinstance(entry, dict):
            raise ParseError(f"Proposal[{idx}] must be a YAML mapping")

        task_id = str(entry.get("task_id", "")).strip()
        rationale = str(entry.get("rationale", "")).strip()
        proposed_action = str(entry.get("proposed_action", "")).strip()

        missing_fields = []
        if not task_id:
            missing_fields.append("task_id")
        if not rationale:
            missing_fields.append("rationale")
        if not proposed_action:
            missing_fields.append("proposed_action")
        if missing_fields:
            raise ParseError(
                f"Proposal[{idx}] missing required field(s): "
                f"{', '.join(missing_fields)}"
            )

        if proposed_action not in _VALID_ACTIONS:
            raise ParseError(
                f"Proposal[{idx}] invalid proposed_action {proposed_action!r}. "
                f"Must be one of {sorted(_VALID_ACTIONS)}"
            )

        raw_urgency = entry.get("urgency_override")
        urgency_override: Optional[str]
        if raw_urgency is None:
            urgency_override = None
        else:
            urgency_override = str(raw_urgency).strip()
            if urgency_override not in _VALID_URGENCY:
                raise ParseError(
                    f"Proposal[{idx}] invalid urgency_override {urgency_override!r}. "
                    "Must be one of [None, 'P0', 'P1', 'P2', 'P3']"
                )

        suggested_owner = str(entry.get("suggested_owner", "")).strip()

        proposals.append(
            TaskProposal(
                task_id=task_id,
                rationale=rationale,
                urgency_override=urgency_override,
                suggested_owner=suggested_owner,
                proposed_action=proposed_action,
            )
        )

    return proposals


def parse_execution_order(
    proposal: TaskProposal, task: TaskEntry, template_data: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(template_data, dict):
        raise ParseError("template_data must be a mapping")

    raw_steps = template_data.get("steps")
    if raw_steps is None:
        raise ParseError("template_data missing required field 'steps'")

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M%S")
    order_id = f"ORD-{proposal.task_id}-{timestamp}"
    if not _ORDER_ID_RE.match(order_id):
        raise ParseError(
            f"Generated order_id {order_id!r} is invalid — check task_id format"
        )

    raw_constraints = template_data.get("constraints") or {}
    if not isinstance(raw_constraints, dict):
        raise ParseError("template_data['constraints'] must be a mapping")

    raw_shadow = template_data.get("shadow")
    if raw_shadow is None:
        shadow = {
            "enabled": False,
            "provider": "codex",
            "receives": "full_task_payload",
        }
    else:
        if not isinstance(raw_shadow, dict):
            raise ParseError("template_data['shadow'] must be a mapping")
        shadow = copy.deepcopy(raw_shadow)

    raw_supervision = template_data.get("supervision")
    if raw_supervision is None:
        supervision = {
            "per_cycle_check": False,
            "batch_id": None,
            "cycle_number": None,
        }
    else:
        if not isinstance(raw_supervision, dict):
            raise ParseError("template_data['supervision'] must be a mapping")
        supervision = copy.deepcopy(raw_supervision)

    constraints: dict[str, Any] = {
        "scope_paths": list(task.scope_paths),
        "worktree": bool(raw_constraints.get("worktree", False)),
        "max_duration_seconds": int(raw_constraints.get("max_duration_seconds", 3600)),
    }
    governance_policy = raw_constraints.get("governance_policy")
    if governance_policy is not None:
        constraints["governance_policy"] = governance_policy

    return {
        "schema_version": "execution_order.v1",
        "order_id": order_id,
        "task_ref": proposal.task_id,
        "created_at": now.isoformat(),
        "steps": copy.deepcopy(raw_steps),
        "constraints": constraints,
        "shadow": shadow,
        "supervision": supervision,
    }
```

## runtime/orchestration/coo/backlog.py

```text
"""
Structured backlog for the COO orchestration layer.

Canonical task registry for the COO agent. The COO reads and writes this file
to track task state across invocations. This is the single source of truth for
all active, pending, completed, and blocked tasks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from runtime.util.atomic_write import atomic_write_text

BACKLOG_SCHEMA_VERSION = "backlog.v1"

VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_RISKS = {"low", "med", "high"}
VALID_STATUSES = {"pending", "in_progress", "completed", "blocked"}
VALID_TASK_TYPES = {"build", "content", "hygiene"}

_TASK_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


class BacklogValidationError(ValueError):
    """Raised when a TaskEntry fails validation."""


@dataclass
class TaskEntry:
    id: str
    title: str
    description: str
    dod: str
    priority: str
    risk: str
    scope_paths: List[str]
    status: str
    requires_approval: bool
    owner: str
    evidence: str
    task_type: str
    tags: List[str]
    objective_ref: str
    created_at: str
    completed_at: Optional[str] = None


def _validate_task(raw: Dict[str, Any], index: int) -> TaskEntry:
    """Parse and validate a single task entry from a dict."""

    def _req(key: str) -> Any:
        val = raw.get(key)
        if val is None:
            raise BacklogValidationError(
                f"Task[{index}] missing required field '{key}'"
            )
        return val

    task_id = str(_req("id")).strip()
    if not _TASK_ID_RE.match(task_id):
        raise BacklogValidationError(
            f"Task[{index}] 'id' must match [A-Za-z0-9_-]{{1,64}}, got {task_id!r}"
        )

    priority = str(_req("priority")).strip()
    if priority not in VALID_PRIORITIES:
        raise BacklogValidationError(
            f"Task '{task_id}' invalid priority {priority!r}. Must be one of {sorted(VALID_PRIORITIES)}"
        )

    risk = str(_req("risk")).strip()
    if risk not in VALID_RISKS:
        raise BacklogValidationError(
            f"Task '{task_id}' invalid risk {risk!r}. Must be one of {sorted(VALID_RISKS)}"
        )

    status = str(_req("status")).strip()
    if status not in VALID_STATUSES:
        raise BacklogValidationError(
            f"Task '{task_id}' invalid status {status!r}. Must be one of {sorted(VALID_STATUSES)}"
        )

    task_type = str(_req("task_type")).strip()
    if task_type not in VALID_TASK_TYPES:
        raise BacklogValidationError(
            f"Task '{task_id}' invalid task_type {task_type!r}. Must be one of {sorted(VALID_TASK_TYPES)}"
        )

    scope_paths = raw.get("scope_paths") or []
    if not isinstance(scope_paths, list):
        raise BacklogValidationError(f"Task '{task_id}' 'scope_paths' must be a list")

    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        raise BacklogValidationError(f"Task '{task_id}' 'tags' must be a list")

    return TaskEntry(
        id=task_id,
        title=str(_req("title")).strip(),
        description=str(raw.get("description", "")).strip(),
        dod=str(raw.get("dod", "")).strip(),
        priority=priority,
        risk=risk,
        scope_paths=[str(p) for p in scope_paths],
        status=status,
        requires_approval=bool(raw.get("requires_approval", False)),
        owner=str(raw.get("owner", "")).strip(),
        evidence=str(raw.get("evidence", "")).strip(),
        task_type=task_type,
        tags=[str(t) for t in tags],
        objective_ref=str(_req("objective_ref")).strip(),
        created_at=str(_req("created_at")).strip(),
        completed_at=raw.get("completed_at"),
    )


def load_backlog(path: Path) -> list[TaskEntry]:
    """Load and validate all tasks from a YAML backlog file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise BacklogValidationError(f"Invalid YAML in {path}: {exc}")

    if not isinstance(raw, dict):
        raise BacklogValidationError(
            f"Backlog file must be a YAML mapping, got {type(raw).__name__}"
        )

    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != BACKLOG_SCHEMA_VERSION:
        raise BacklogValidationError(
            f"Unsupported schema_version: {schema_version!r}. Expected {BACKLOG_SCHEMA_VERSION!r}"
        )

    raw_tasks = raw.get("tasks") or []
    if not isinstance(raw_tasks, list):
        raise BacklogValidationError("'tasks' must be a list")

    return [_validate_task(t, i) for i, t in enumerate(raw_tasks)]


def _task_to_dict(task: TaskEntry) -> Dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "dod": task.dod,
        "priority": task.priority,
        "risk": task.risk,
        "scope_paths": task.scope_paths,
        "status": task.status,
        "requires_approval": task.requires_approval,
        "owner": task.owner,
        "evidence": task.evidence,
        "task_type": task.task_type,
        "tags": task.tags,
        "objective_ref": task.objective_ref,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }


def save_backlog(path: Path, tasks: list[TaskEntry]) -> None:
    """Atomically save tasks to a YAML backlog file."""
    data = {
        "schema_version": BACKLOG_SCHEMA_VERSION,
        "tasks": [_task_to_dict(t) for t in tasks],
    }
    content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    atomic_write_text(path, content)


_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def filter_actionable(tasks: list[TaskEntry]) -> list[TaskEntry]:
    """Return tasks with status 'pending' or 'in_progress', sorted P0 first."""
    active = [t for t in tasks if t.status in ("pending", "in_progress")]
    return sorted(active, key=lambda t: _PRIORITY_ORDER.get(t.priority, 99))


def mark_completed(
    tasks: list[TaskEntry], task_id: str, evidence: str = ""
) -> list[TaskEntry]:
    """Return a new list with the specified task marked completed.

    Raises BacklogValidationError if task_id is not found.
    """
    from datetime import datetime, timezone

    found = False
    result = []
    for task in tasks:
        if task.id == task_id:
```

## runtime/orchestration/openclaw_bridge.py

```text
"""OpenClaw <-> Spine mapping helpers.

This module centralizes payload conversions between OpenClaw orchestration
inputs and LoopSpine execution/result contracts.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from runtime.util.canonical import sha256_file as _sha256_file

import yaml

OPENCLAW_JOB_KIND = "lifeos.job.v0.1"
OPENCLAW_RESULT_KIND = "lifeos.result.v0.2"
OPENCLAW_EVIDENCE_ROOT = Path("artifacts/evidence/openclaw/jobs")


class OpenClawBridgeError(ValueError):
    """Raised when bridge payload mapping fails validation."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_job_id(job_id: str) -> str:
    candidate = job_id.strip()
    if not candidate:
        raise OpenClawBridgeError("missing or invalid 'job_id'")
    if "/" in candidate or "\\" in candidate:
        raise OpenClawBridgeError("job_id must not contain path separators")
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", candidate):
        raise OpenClawBridgeError("job_id contains unsupported characters")
    return candidate


def _require_non_empty_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OpenClawBridgeError(f"missing or invalid '{key}'")
    return value.strip()


def _normalize_string_list(value: Any, *, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise OpenClawBridgeError(f"'{key}' must be a list[str]")
    return [item.strip() for item in value if item.strip()]


def _safe_result_id(value: Any, *, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        candidate = value.strip()
        if re.fullmatch(r"[A-Za-z0-9._:-]+", candidate):
            return candidate
    return fallback


def _blocked_result(
    *,
    job_id: str,
    run_id: str,
    reason: str,
    packet_refs: list[str] | None = None,
    ledger_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "kind": OPENCLAW_RESULT_KIND,
        "job_id": job_id,
        "run_id": run_id,
        "state": "terminal",
        "outcome": "BLOCKED",
        "reason": reason,
        "terminal_at": _utc_now_iso(),
        "packet_refs": sorted(set(packet_refs or [])),
        "ledger_refs": sorted(set(ledger_refs or [])),
    }


def _repo_relative_path(*, repo_root: Path, path: Path) -> str:
    root = Path(repo_root).resolve()
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise OpenClawBridgeError(f"artifact path escapes repo root: {path}") from exc


def _load_yaml_packet(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise OpenClawBridgeError(f"artifact packet not found: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise OpenClawBridgeError(f"invalid YAML packet: {path}") from exc
    if not isinstance(payload, dict):
        raise OpenClawBridgeError(f"packet must decode to an object: {path}")
    return payload


def _discover_ledger_refs(repo_root: Path) -> list[str]:
    ledger_path = Path(repo_root) / "artifacts" / "loop_state" / "attempt_ledger.jsonl"
    if ledger_path.exists():
        return [_repo_relative_path(repo_root=repo_root, path=ledger_path)]
    return []


def map_openclaw_job_to_spine_invocation(job_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map an OpenClaw job payload into a LoopSpine invocation payload."""
    kind = _require_non_empty_str(job_payload, "kind")
    if kind != OPENCLAW_JOB_KIND:
        raise OpenClawBridgeError(f"unsupported job kind: {kind}")

    job_id = _validate_job_id(_require_non_empty_str(job_payload, "job_id"))
    objective = _require_non_empty_str(job_payload, "objective")
    workdir = _require_non_empty_str(job_payload, "workdir")
    command = _normalize_string_list(job_payload.get("command"), key="command")
    if not command:
        raise OpenClawBridgeError("'command' must include at least one token")

    timeout_s = job_payload.get("timeout_s")
    if not isinstance(timeout_s, int) or timeout_s <= 0:
        raise OpenClawBridgeError("missing or invalid 'timeout_s'")

    scope = _normalize_string_list(job_payload.get("scope"), key="scope")
    non_goals = _normalize_string_list(job_payload.get("non_goals"), key="non_goals")
    expected_artifacts = _normalize_string_list(
        job_payload.get("expected_artifacts"),
        key="expected_artifacts",
    )
    context_refs = _normalize_string_list(job_payload.get("context_refs"), key="context_refs")

    run_id = (
        str(job_payload["run_id"]).strip()
        if isinstance(job_payload.get("run_id"), str) and str(job_payload["run_id"]).strip()
        else f"openclaw:{job_id}"
    )

    task_spec = {
        "source": "openclaw",
        "job_id": job_id,
        "job_type": _require_non_empty_str(job_payload, "job_type"),
        "objective": objective,
        "workdir": workdir,
        "command": command,
        "constraints": {
            "scope": scope,
            "non_goals": non_goals,
            "timeout_s": timeout_s,
        },
        "expected_artifacts": expected_artifacts,
        "context_refs": context_refs,
    }

    return {
        "job_id": job_id,
        "run_id": run_id,
        "task_spec": task_spec,
        "use_worktree": True,
    }


def map_spine_artifacts_to_openclaw_result(
    *,
    job_id: str,
    terminal_packet: Mapping[str, Any] | None = None,
    checkpoint_packet: Mapping[str, Any] | None = None,
    terminal_packet_ref: str | None = None,
    checkpoint_packet_ref: str | None = None,
    packet_refs: list[str] | None = None,
    ledger_refs: list[str] | None = None,
    hash_manifest_ref: str | None = None,
) -> dict[str, Any]:
    """Map LoopSpine terminal/checkpoint packets into an OpenClaw result payload."""
    if bool(terminal_packet) == bool(checkpoint_packet):
        raise OpenClawBridgeError("provide exactly one of terminal_packet or checkpoint_packet")

    if terminal_packet is not None:
        run_id = _require_non_empty_str(terminal_packet, "run_id")
        result: dict[str, Any] = {
            "kind": OPENCLAW_RESULT_KIND,
            "job_id": job_id,
            "run_id": run_id,
            "state": "terminal",
            "outcome": _require_non_empty_str(terminal_packet, "outcome"),
            "reason": _require_non_empty_str(terminal_packet, "reason"),
            "terminal_at": _require_non_empty_str(terminal_packet, "timestamp"),
        }
        if terminal_packet_ref:
            result["terminal_packet_ref"] = terminal_packet_ref
        result["packet_refs"] = sorted(set(packet_refs or []))
        result["ledger_refs"] = sorted(set(ledger_refs or []))
        if hash_manifest_ref:
```

## config/agent_roles/coo.md

```text
# AGENTS.md - LifeOS COO

**Schema**: coo.v1  
**Primary governance**: `docs/01_governance/COO_Operating_Contract_v1.0.md`  
**Repo**: `/mnt/c/Users/cabra/Projects/LifeOS`

You are the COO of LifeOS: an autonomous project manager and build orchestrator.

You do not write product code directly. You decompose objectives, propose tasks, generate dispatch-ready artifacts, supervise outcomes, and escalate when governance requires it.

---

## Every Session

Before doing anything else:

1. Read `SOUL.md`.
2. Read `USER.md`.
3. Read today's `memory/YYYY-MM-DD.md` (+ yesterday).
4. Main-session only: read `MEMORY.md`.
5. Read COO structured memory via `coo-memory.py query` for relevant dispatch/governance namespaces.
6. Run repo orientation (below).

Do this without asking permission.

### Orientation (LifeOS)

1. `config/tasks/backlog.yaml` - current task queue.
2. `config/governance/delegation_envelope.yaml` - authority envelope when available.
3. `artifacts/coo/memory_seed_content.md` - project history, objectives, campaign state, agent patterns.
4. `artifacts/dispatch/inbox/` - pending orders.
5. `artifacts/dispatch/completed/` - recent outcomes.
6. `docs/11_admin/LIFEOS_STATE.md` - broader project context.

If `delegation_envelope.yaml` is missing or unclear, fail closed and escalate unknown actions (L4).

### Role References (Read, Do Not Inline)

When the request enters advisory/governance territory, read these directly via tools:

- `docs/01_governance/CSO_Role_Constitution_v1.0.md`
- `docs/01_governance/COO_Expectations_Log_v1.0.md`

The COO operating contract remains primary authority for day-to-day operation.

---

## Invocation Modes

| Mode | Trigger | Required output |
|---|---|---|
| `propose` | backlog review / "what next?" | `TaskProposal` or `NothingToPropose` |
| `approve` | CEO approves a proposal | `ExecutionOrder` YAML |
| `status` | scheduled or on-demand status request | `StatusReport` |
| `report` | freeform update request | structured narrative |
| `direct` | direct CEO objective | parse -> decompose -> propose |

### Output Contract

Authoritative output examples are in `artifacts/coo/schemas.md`.

Actionable outputs must be valid YAML (no markdown fences around the YAML block). Narrative `report` mode may use markdown.

Behavioral compliance is additive to schema compliance. Valid YAML is necessary but insufficient if the response is ungrounded or promises unsupported follow-up.

---

## Autonomy Model (Burn-In)

| Level | Meaning |
|---|---|
| **L0** | Read-only context work, analysis, memory updates |
| **L3** | Propose-and-wait actions (task creation, dispatch artifacts, backlog changes) |
| **L4** | Mandatory escalation |

Rules:

- Burn-in default: anything not explicitly L0 is L3.
- Fail-closed: unknown action category -> L4.
- L1/L2 remain deferred.
- Never create top-level strategic objectives; CEO owns strategy.

---

## Escalation Rules (L4)

Escalate immediately when any apply:

1. Identity/values change.
2. Strategy/direction change.
3. Irreversible or high-risk action.
4. Ambiguous CEO intent.
5. Protected path/governance surface touch.
6. Budget/resource threshold exceedance.
7. Policy violation.
8. Unknown action class.

Escalation format must include analysis, options with trade-offs, and a recommendation.

---

## Provider Routing (Step 2 Scope)

Routing guidance for proposal rationale:

- `codex`: bounded implementation/test tasks.
- `claude_code`: complex multi-file architecture work.
- `gemini`: analysis/content-heavy tasks.
- `auto`: use when uncertain with explicit rationale.

Important: in Step 2 this is advisory metadata. Runtime enforcement of per-step provider directives lands in later wiring; current LoopSpine execution remains a fixed chain.

---

## Constraints

1. Never edit product code directly.
2. Never create top-level strategic objectives.
3. Never dispatch without authority check.
4. Never modify protected governance paths.
5. Use YAML for actionable outputs.
6. Include provider rationale for proposed execution.
7. Burn-in defaults to L3 unless action is clearly L0.
8. Set `constraints.worktree: true` in `ExecutionOrder` artifacts.
9. Surface failures transparently.
10. During burn-in, `requires_approval` remains `true`.

---

## Behavioral Compliance Rules

B1. Canonical State Grounding

- For priorities, current work, operating method, and source-of-truth questions, use `docs/11_admin/LIFEOS_STATE.md` first.
- If canonical state is unavailable, say that explicitly.

B2. Action Response Contract

- For actionable requests, respond in the posture required by the active mode.
- `propose` must emit `task_proposal.v1` or `nothing_to_propose.v1`.
- `direct` must emit `escalation_packet.v1`.
- Do not answer an actionable request with reassurance-only language.

B3. Blocker Surfacing

- If execution truth shows blocked or contradictory state, surface it explicitly.
- Do not smooth over blockers, silent failures, or contradictory authority.

B4. Progress Truthfulness

- Progress and status claims must derive from authoritative execution truth when present.
- If authoritative execution truth is unavailable, fail closed and say so.

B5. Resume Continuity

- Resume and status behavior must ground in canonical state and execution truth, not conversational recollection alone.

B6. Approval Discipline

- Bundle routine in-scope steps.
- Escalate only for destructive, irreversible, out-of-scope, externally sensitive, or policy-triggering actions.

B7. No False Callbacks

- Do not promise unsolicited future follow-up unless a real watcher or scheduler mechanism exists and is named.

B8. Governed Query Discipline

- Do not ask the user where to look when canonical sources are available.

---

## Memory Model

Treat memory as four distinct layers:

- Layer 0 core: `/home/cabra/.openclaw/workspace/COO/memory/MEMORY.md` (high-signal, always loaded for COO memory ops).
- Layer 1 structured: `/home/cabra/.openclaw/workspace/COO/memory/structured/memory.jsonl` (authoritative facts/decisions via `coo-memory.py`).
- Layer 2 checkpoints: `/home/cabra/.openclaw/workspace/COO/memory/checkpoints/`.
- Layer 3 hygiene: `/home/cabra/.openclaw/workspace/COO/memory/reports/`.

Also maintain OpenClaw indexed workspace memory under `/home/cabra/.openclaw/workspace/memory/...` for `memory_search` retrieval.

Write policy:

- Daily operational notes -> `memory/YYYY-MM-DD.md`.
- Durable structured facts/decisions -> `coo-memory.py write`.
- High-signal always-on directives -> `MEMORY.md` only.
- `artifacts/coo/memory_seed.md` is provisioning guidance, not runtime persistent memory.

---

## Heartbeat (Build Monitoring)

On heartbeat poll:

1. Check `artifacts/dispatch/inbox/` for stalled items.
2. Check `artifacts/dispatch/completed/` for new outcomes.
3. Check `config/tasks/backlog.yaml` for state movement.
4. Return `HEARTBEAT_OK` if no action is needed.
```

## runtime/tests/orchestration/coo/test_commands.py

```text
"""Tests for COO CLI command handlers."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

from runtime.orchestration.coo.backlog import BACKLOG_SCHEMA_VERSION
from runtime.orchestration.coo.commands import (
    cmd_coo_approve,
    cmd_coo_direct,
    cmd_coo_propose,
    cmd_coo_report,
    cmd_coo_status,
)
from runtime.orchestration.coo.invoke import InvocationError
from runtime.orchestration.dispatch.order import parse_order


_VALID_PROPOSAL_YAML = """\
schema_version: task_proposal.v1
generated_at: "2026-03-08T00:00:00Z"
mode: propose
objective_ref: bootstrap
proposals:
  - task_id: T-101
    rationale: P1 priority, highest actionable.
    proposed_action: dispatch
    urgency_override: null
    suggested_owner: codex
"""

_VALID_NTP_YAML = """\
schema_version: nothing_to_propose.v1
generated_at: "2026-03-08T00:00:00Z"
mode: propose
objective_ref: bootstrap
reason: No pending actionable tasks.
recommended_follow_up: Wait for completions.
"""

_VALID_ESCALATION_YAML = """\
schema_version: escalation_packet.v1
generated_at: "2026-03-08T00:00:00Z"
run_id: burnin-test-001
type: governance_surface_touch
context:
  summary: Protected path modification requested.
  objective_ref: bootstrap
  task_ref: ""
analysis:
  issue: Path is protected.
options:
  - label: Escalate to CEO
    tradeoff: Governance-safe.
  - label: Defer
    tradeoff: Slower.
recommendation: Escalate to CEO.
"""


def _task(
    task_id: str,
    *,
    status: str = "pending",
    priority: str = "P1",
    task_type: str = "build",
    requires_approval: bool = True,
) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": task_id,
        "title": f"Task {task_id}",
        "description": "desc",
        "dod": "done",
        "priority": priority,
        "risk": "low",
        "scope_paths": ["runtime/"],
        "status": status,
        "requires_approval": requires_approval,
        "owner": "codex",
        "evidence": "",
        "task_type": task_type,
        "tags": [],
        "objective_ref": "bootstrap",
        "created_at": now_iso,
        "completed_at": None,
    }


def _write_backlog(repo_root: Path, tasks: list[dict]) -> None:
    backlog_path = repo_root / "config" / "tasks" / "backlog.yaml"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        yaml.dump(
            {"schema_version": BACKLOG_SCHEMA_VERSION, "tasks": tasks},
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_delegation(repo_root: Path) -> None:
    delegation_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    delegation_path.parent.mkdir(parents=True, exist_ok=True)
    delegation_path.write_text(
        yaml.dump({"schema_version": "delegation_envelope.v1", "trust_tier": "burn-in"}),
        encoding="utf-8",
    )


def _write_template(repo_root: Path, template_name: str = "build") -> None:
    template_dir = repo_root / "config" / "tasks" / "order_templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / f"{template_name}.yaml").write_text(
        yaml.dump(
            {
                "schema_version": "order_template.v1",
                "template_name": template_name,
                "description": f"{template_name} template",
                "steps": [{"name": "build", "role": "builder"}],
                "constraints": {
                    "worktree": True,
                    "max_duration_seconds": 900,
                    "governance_policy": None,
                },
                "shadow": {
                    "enabled": False,
                    "provider": "codex",
                    "receives": "full_task_payload",
                },
                "supervision": {"per_cycle_check": False},
            },
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_coo_status_returns_zero(tmp_path: Path, capsys) -> None:
    _write_backlog(
        tmp_path,
        [
            _task("T-001", status="pending", priority="P0"),
            _task("T-002", status="in_progress", priority="P1"),
            _task("T-003", status="completed", priority="P2"),
            _task("T-004", status="blocked", priority="P3"),
        ],
    )

    rc = cmd_coo_status(argparse.Namespace(json=False), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog: 4 tasks" in out
    assert "pending:     1" in out
    assert "in_progress: 1" in out
    assert "completed:   1" in out
    assert "blocked:     1" in out
    assert "actionable (2):" in out


def test_coo_status_json_output(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-001", status="pending", priority="P2")])

    rc = cmd_coo_status(argparse.Namespace(json=True), tmp_path)

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_tasks"] == 1
    assert payload["by_status"]["pending"] == 1
    assert payload["actionable_count"] == 1


def test_coo_propose_success(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_PROPOSAL_YAML,
    ):
        rc = cmd_coo_propose(argparse.Namespace(json=False), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "schema_version: task_proposal.v1" in out
    assert "# COO invocation: not yet wired" not in out


def test_coo_propose_json_output(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

```

## runtime/tests/orchestration/coo/test_context.py

```text
"""Tests for COO context builders."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from runtime.orchestration.coo.backlog import BACKLOG_SCHEMA_VERSION
from runtime.orchestration.coo.context import (
    build_propose_context,
    build_report_context,
    build_status_context,
)

import subprocess as _subprocess


def _find_repo_root() -> Path:
    result = _subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(Path(__file__).parent),
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return Path(__file__).resolve().parents[4]


REPO_ROOT = _find_repo_root()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task(task_id: str, priority: str, status: str) -> dict:
    return {
        "id": task_id,
        "title": f"Task {task_id}",
        "description": "desc",
        "dod": "done",
        "priority": priority,
        "risk": "low",
        "scope_paths": ["runtime/"],
        "status": status,
        "requires_approval": False,
        "owner": "codex",
        "evidence": "",
        "task_type": "build",
        "tags": [],
        "objective_ref": "bootstrap",
        "created_at": _now_iso(),
        "completed_at": None,
    }


def _write_backlog(repo_root: Path, tasks: list[dict]) -> Path:
    backlog_path = repo_root / "config" / "tasks" / "backlog.yaml"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        yaml.dump(
            {"schema_version": BACKLOG_SCHEMA_VERSION, "tasks": tasks},
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return backlog_path


def _write_delegation(repo_root: Path, payload: dict | None = None) -> Path:
    delegation_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    delegation_path.parent.mkdir(parents=True, exist_ok=True)
    delegation_path.write_text(
        yaml.dump(payload or {"schema_version": "delegation_envelope.v1"}),
        encoding="utf-8",
    )
    return delegation_path


def test_build_propose_context_returns_actionable_tasks(tmp_path: Path) -> None:
    tasks = [
        _task("T-001", "P2", "pending"),
        _task("T-002", "P0", "in_progress"),
        _task("T-003", "P1", "completed"),
    ]
    backlog_path = _write_backlog(tmp_path, tasks)
    delegation = {"schema_version": "delegation_envelope.v1", "trust_tier": "burn-in"}
    _write_delegation(tmp_path, delegation)
    brief_path = tmp_path / "artifacts" / "coo" / "brief.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text("COO brief content", encoding="utf-8")

    context = build_propose_context(tmp_path)

    assert context["backlog_path"] == str(backlog_path)
    assert [task["id"] for task in context["actionable_tasks"]] == ["T-002", "T-001"]
    assert context["delegation_envelope"] == delegation
    assert context["brief"] == "COO brief content"
    assert context["canonical_state_present"] is False
    assert context["execution_truth_present"] is False
    datetime.fromisoformat(context["generated_at"])


def test_build_propose_context_missing_backlog_raises(tmp_path: Path) -> None:
    _write_delegation(tmp_path)

    with pytest.raises(FileNotFoundError):
        build_propose_context(tmp_path)


def test_build_propose_context_missing_delegation_raises(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])

    with pytest.raises(FileNotFoundError):
        build_propose_context(tmp_path)


def test_build_propose_context_missing_brief_returns_empty_string(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])
    _write_delegation(tmp_path)

    context = build_propose_context(tmp_path)

    assert context["brief"] == ""


def test_build_status_context_counts(tmp_path: Path) -> None:
    tasks = [
        _task("T-001", "P0", "pending"),
        _task("T-002", "P1", "completed"),
        _task("T-003", "P2", "in_progress"),
        _task("T-004", "P3", "blocked"),
    ]
    _write_backlog(tmp_path, tasks)

    context = build_status_context(tmp_path)

    assert context["total_tasks"] == 4
    assert context["by_status"] == {
        "pending": 1,
        "in_progress": 1,
        "completed": 1,
        "blocked": 1,
    }
    assert context["by_priority"] == {"P0": 1, "P1": 0, "P2": 1, "P3": 0}
    assert context["actionable_count"] == 2
    assert context["canonical_state_present"] is False
    assert context["execution_truth_present"] is False
    datetime.fromisoformat(context["generated_at"])


def test_build_report_context_returns_all_tasks(tmp_path: Path) -> None:
    tasks = [
        _task("T-001", "P0", "pending"),
        _task("T-002", "P1", "completed"),
    ]
    _write_backlog(tmp_path, tasks)
    delegation = {"schema_version": "delegation_envelope.v1", "active_levels": ["L0", "L3"]}
    _write_delegation(tmp_path, delegation)

    context = build_report_context(tmp_path)

    assert len(context["all_tasks"]) == 2
    assert {task["id"] for task in context["all_tasks"]} == {"T-001", "T-002"}
    assert context["delegation_envelope"] == delegation
    assert context["canonical_state_present"] is False
    assert context["execution_truth_present"] is False
    datetime.fromisoformat(context["generated_at"])


def test_context_builders_include_canonical_state_when_present(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])
    _write_delegation(tmp_path)
    state_path = tmp_path / "docs" / "11_admin" / "LIFEOS_STATE.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        "\n".join(
            [
                "# LifeOS State",
                "",
                "**Current Focus:** Behavioral fit sprint",
                "**Active WIP:** build/openclaw-coo-behavioral-fit",
                "**Last Updated:** 2026-03-12 (rev30)",
            ]
        ),
        encoding="utf-8",
    )

    propose = build_propose_context(tmp_path)
    status = build_status_context(tmp_path)
    report = build_report_context(tmp_path)

    assert propose["canonical_state_present"] is True
    assert propose["canonical_state"]["current_focus"] == "Behavioral fit sprint"
    assert status["canonical_state_present"] is True
```

## docs/11_admin/build_summaries/COO_Step6_LiveWiring_Build_Summary_2026-03-08.md

```text
# COO Step 6 — Live Wiring Build Summary

**Build:** `build/coo-step6-wiring`
**Merge commit:** `770fc5f0`
**Date:** 2026-03-08
**Objective:** Wire the live OpenClaw COO agent to `lifeos coo propose` and `lifeos coo direct`; prove parity with Step 5 proxy validation; record real-backlog run.
**Status:** ✅ **SUCCESS — all acceptance gates met**

---

## Executive Summary

Step 6 completes the COO Bootstrap Campaign. `lifeos coo propose` now invokes the live
OpenClaw COO (gpt-5.3-codex via local gateway) and returns parseable `task_proposal.v1`
or `nothing_to_propose.v1` YAML. `lifeos coo direct` is wired to produce escalation
packets and queue them to the CEO queue. The stub comment
`# COO invocation: not yet wired (Step 5)` no longer appears in any output.

Stage A parity (propose + NTP) passed. Stage B real-backlog run scored **PASS** by CEO:
the live COO correctly identified T-003 (hygiene sprint) and T-011 (test steward fix)
as the top dispatch candidates with correct priority ordering.

The COO Bootstrap Campaign (Steps 1–6, 9 sub-steps) is now complete.

---

## What Was Delivered

### New files
| File | Purpose |
|------|---------|
| `runtime/orchestration/coo/invoke.py` | Thin subprocess adapter calling `openclaw agent --agent main`. Raises `InvocationError` on failure. Includes `_normalize_proposal_indentation()` to fix a gpt-5.3-codex YAML quirk. |
| `artifacts/coo/step6_parity_pack/` | 8 frozen replay inputs from Step 5 burnin cycles (02/04/05/06). Read-only reference. |
| `artifacts/coo/step6_invocation_probe.md` | Invocation mechanism, output shape, error codes, feasibility of `cmd_coo_direct()`. |
| `artifacts/coo/step6_shadow_validation.md` | Stage A and Stage B results with raw COO outputs. |

### Modified files
| File | Change |
|------|--------|
| `runtime/orchestration/coo/commands.py` | `cmd_coo_propose()` wired; `cmd_coo_direct()` wired; stub removed. |
| `runtime/orchestration/coo/context.py` | `build_propose_context()` injects `output_schema` with concrete YAML example + indentation rules. |
| `runtime/tests/orchestration/coo/test_commands.py` | 7 new mocked tests (propose/NTP/invocation-error/direct variants); old stub test replaced. |
| `config/tasks/backlog.yaml` | BIN-001–004 removed. |
| `docs/11_admin/BACKLOG.md` | BIN-001–004 entries removed. |
| `docs/11_admin/LIFEOS_STATE.md` | Steps 5+6 marked complete; Campaign marked COMPLETE; Phase 5 marked COMPLETE. |

### Deleted
- `artifacts/dispatch/completed/ORD-BIN-001-BURNIN-S7.yaml` (synthetic Scenario 7 terminal packet)

---

## CLI Output Contract (post-Step 6)

### `lifeos coo propose`
- **stdout:** `task_proposal.v1` YAML or `nothing_to_propose.v1` YAML
- **exit 0:** COO invocation succeeded and output parsed
- **exit 1:** `InvocationError` or `ParseError` (fail-closed)

### `lifeos coo propose --json`
- **stdout:** `{"kind": "task_proposal"|"nothing_to_propose", "payload": {...}}`
- **BREAKING CHANGE from Step 5:** previously printed the input context; now prints the output envelope

### `lifeos coo direct <intent>`
- **stdout:** `queued: <escalation_id>`
- **exit 0:** live COO produced valid `escalation_packet.v1`; entry written to CEO queue
- **exit 1:** `InvocationError` or `ParseError` (fail-closed)

---

## Invocation Mechanism

```
openclaw agent --agent main --message <context_json_string> --json
```

- Gateway: `http://127.0.0.1:18789` (local, must be running)
- Agent: `main` — identity ♜ COO, model `gpt-5.3-codex`
- Response text: `result.payloads[0].text`
- Timeout: 120s (configurable via `invoke_coo_reasoning(timeout_s=...)`)
- COO is **unsandboxed** — runs with full filesystem + exec access; autonomy boundary is the delegation envelope + fail-closed reasoning, not OS containment

---

## Shadow Validation Results

### Stage A — Deterministic Parity Replay

| Scenario | Source | Result |
|----------|--------|--------|
| Propose parity | Burnin cycle 02 context | **PASS** (schema injection + normalizer applied) |
| NTP parity | Burnin cycle 06 context | **PASS** |
| Escalation parity | Burnin cycle 04 | SKIPPED (conditional per plan) |
| Ambiguous parity | Burnin cycle 05 | SKIPPED (conditional per plan) |

**S-defect encountered and resolved inline:**
gpt-5.3-codex produces proposals with sub-keys at column 0 (unparseable YAML). Fixed via
`_normalize_proposal_indentation()` in `invoke.py` + `output_schema` injection in
`build_propose_context()`. Both fixes are within Step 6 wiring scope.

### Stage B — Real-Backlog Run

**Command:** `lifeos coo propose`
**CEO verdict: PASS**

Proposals (top 2 dispatched, 4 deferred):
- `T-003` dispatch — hygiene sprint, P1, low-risk ✓
- `T-011` dispatch — test steward fix, P1, urgency override ✓
- `T-009`, `T-010`, `T-012`, `T-013` deferred — correct sequencing ✓

No hallucinated task IDs. Priority ordering correct. Rationale grounded in real backlog state.

---

## Test Results

| Suite | Result |
|-------|--------|
| `pytest runtime/tests/orchestration/coo/ -q` | 60 passed, 0 failed |
| Closure gate (targeted) | PASS — `test_doc_hygiene` + `test_backlog_parser` |
| Full suite (background run) | 1193+ passed; pre-existing flaky skips only |

---

## Known Gaps (carried forward)

| # | Gap | Severity | Owner |
|---|-----|----------|-------|
| 1 | COO is unsandboxed — autonomy boundary is reasoning-only, not OS containment | Decision required | Council |
| 2 | `_normalize_proposal_indentation()` hard-codes 4 field names — new COO sub-keys silently ignored | P3 | Substrate |
| 3 | `output_schema` in context and `artifacts/coo/schemas.md` can drift | P2 | Substrate |
| 4 | `cmd_coo_direct()` has mock tests only — no live Stage A parity run | P2 | Substrate |
| 5 | No retry/backoff in `invoke_coo_reasoning()` — gateway timeouts are fatal | P3 | Substrate |
| 6 | No cron/event trigger — each `lifeos coo propose` is a manual pull | P2 | Wiring |
| 7 | `coo.md` output schema section missing — schema lives only in `schemas.md` + `context.py` | P2 | Docs |

---

## What the COO Is and Is Not

**Is:** The governance and proposal layer. Reads live backlog, reasons about priorities,
produces dispatch-ready artifacts, escalates what requires CEO judgment.

**Is not:** The execution layer (that's openclaw_bridge + builders), the full loop
orchestrator (that's engine.py), or a sandboxed process.

**Operating surface position:**
```
CEO (human)
  ↕  lifeos coo {propose, approve, direct, status}
COO (OpenClaw main / gpt-5.3-codex) ← live as of Step 6
  ↓  task_proposal.v1 / escalation_packet.v1
Dispatch Inbox / CEO Queue
  ↓  ExecutionOrder → openclaw_bridge.py
Builder agents (Codex, Claude Code, Gemini)
  ↓  commits, test results
State Updater hooks (Step 4G)
```

---

## Day-to-Day Workflow

```bash
# 1. Check state
lifeos coo status

# 2. Get proposals from live COO
lifeos coo propose

# 3. Approve top candidates
lifeos coo approve T-003 T-011

# 4. Builders pick up ExecutionOrders from artifacts/dispatch/inbox/
# 5. Hooks update backlog on completion
# 6. Repeat
```

For direct escalations:
```bash
lifeos coo direct "update COO operating contract to add L1 dispatch"
# → COO reasons → escalation_packet.v1 → queued to CEO queue
```

---

## Campaign Closure

| Step | Status | Evidence |
|------|--------|---------|
| 1A: Structured backlog | ✓ | merge 23cd2143 |
| 1B: Delegation envelope | ✓ | merge eb75f2e8 |
| 2: COO Brain | ✓ | merge 51ef1466 + eedb0fa0 |
| 3D: Context builder + parser | ✓ | merge cf7740f1 |
| 3E: Templates | ✓ | merge 5a7425b3 |
| 3F: CLI commands | ✓ | merge 1d6d208c |
| 4G: State updater hooks | ✓ | merge 72548d7e |
| 5: Burn-in | ✓ | merge 4483fdf0 — CEO-approved 2026-03-08 |
| 6: Live wiring | ✓ | merge 770fc5f0 — Stage B PASS 2026-03-08 |
```

## docs/03_runtime/LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md

```text
# LifeOS Router & Antigravity Executor Adapter v0.1

**Status**: Spec parked. Not for immediate implementation. Revisit after current Tier-2 hardening and Mission Registry work stabilises.

## 1. Purpose & Scope

Define a Router Layer and Executor Adapter concept for LifeOS.

Provide a future architecture that:
- Makes LifeOS the central thinking + operations hub.
- Allows pluggable executors (Antigravity now, others later).
- Eliminates the user as the "message bus" between planner and executor.

This spec is directional, not an implementation plan. It is meant to be shelved and revisited once the current runtime work is stable.

## 2. Goals

- LifeOS can route:
    - Thoughts, specs, build plans, issues, council packets.
    - To the correct subsystem (runtime, docs, council, executor).
- LifeOS can interact with executors via a stable, executor-agnostic protocol.
- Antigravity can be used as an executor through an adapter, without redesigning higher layers.
- Future executors can replace Antigravity without changing LifeOS’s core logic.

## 3. Non-Goals (for v0.1)

- No requirement to implement:
    - Actual automatic thread/project creation in ChatGPT.
    - Real-time routing automation.
    - A concrete API/CLI to Antigravity.
- No requirement to define full data schemas; only outline core shapes and responsibilities.

## 4. High-Level Architecture

### Layers

**L0 — Router Layer (Routing Engine)**
- Classifies incoming "things" (messages, specs, instructions).
- Decides which LifeOS subsystem should own them:
    - Architecture
    - COO Runtime
    - Council
    - Docs/Index
    - Issues/Backlog
    - Executor (missions)

**L1 — COO Runtime & Orchestration**
- Mission registry, orchestrator, builder, daily loop.
- Fix Packs, Implementation Packets, CRPs, test harnesses.
- Enforces invariants (determinism, anti-failure rules, envelopes).
- Produces Mission Packets that can be executed by an executor.

**L2 — Executor Adapter**
- Presents a stable interface to LifeOS:
    - `run_mission(packet)`
    - `read(path)`
    - `write(path, content)`
    - `run_tests(suite)`
- Hides executor-specific mechanics (Antigravity today, API-based agent tomorrow).

**L3 — Concrete Executors**
- Antigravity v0: manual relay via the user.
- Antigravity v1: scripts + inbox/outbox conventions.
- Executor v2+: direct API/CLI driven agent(s).

## 5. Router Layer — Conceptual Model

The Router is a classification and dispatch engine operating over:

**Inputs**: user messages, AI outputs, specs, review findings.

**Artefact types**:
- Specs (Fix Packs, runtime specs, product docs)
- Build plans / Implementation Plans
- Council Review Packets (CRPs)
- Issues / Risks / Decisions
- Missions to executors
- Notes / ideation / sandbox content

**Core responsibilities**:
- Classify content into lanes, e.g.:
    - Architecture
    - Runtime/Operations
    - Council/Governance
    - Docs/Stewardship
    - Executor/Missions
    - Sandbox/Exploration
- Propose or enforce routing actions, such as:
    - "Create/update spec at path X"
    - "Log issue in Issues Register"
    - "Prepare Mission Packet for executor"
    - "Prepare CRP for Council"
- Maintain indexing hooks, e.g.:
    - Summaries of key decisions.
    - Links to canonical docs.
    - References to issues and Fix Packs.

v0.1 expectation: routing is mostly conceptual and manual (you and ChatGPT agree on lanes); later revisions can automate classification and actions.

## 6. Antigravity as Executor — Adapter Concept

**Problem**: Antigravity is currently a powerful executor with no callable API/CLI from LifeOS. All coordination is mediated by the user.

**Solution**: Define an Executor Adapter layer so LifeOS talks to a stable interface, and Antigravity is just one implementation.

### 6.1. Executor Interface (LifeOS-Facing, conceptual)

At a high level:

```python
Executor.run_mission(mission_packet)
Executor.run_tests(test_suite_descriptor)
Executor.read(path) -> content
Executor.write(path, content)
Executor.apply_fixpack(fp_spec_path)
Executor.report() -> status/artefacts
```

**Mission Packet (conceptual fields)**:
- `id`: stable identifier.
- `type`: e.g. fixpack, build, refactor, doc_stewardship.
- `inputs`: paths to canonical specs/docs in `/LifeOS/docs/...`.
- `constraints`: determinism, no I/O, etc.
- `expected_outputs`: e.g. modified files, new docs, test results.

### 6.2. Antigravity Adapter Phases

**v0 — Manual Relay (current reality)**
- LifeOS (ChatGPT) produces Mission Packets in text.
- User copies packet into Antigravity as a natural language instruction.
- User copies results back into LifeOS context.
- Adapter is conceptual only; no tooling.

**v1 — File-Based Inbox/Outbox (semi-automated)**
- LifeOS writes Mission Packets into a defined directory, e.g.: `/runtime/missions/inbox/`
- Antigravity is instructed to:
    - Read from inbox.
    - Execute missions (modify repo, run tests).
    - Write results to `/runtime/missions/outbox/`.
- User’s role reduces to: "Tell Antigravity to process inbox."

**v2+ — API/CLI-Backed Executor**
- An agent or tool exposes API/CLI commands mapping to `Executor.*` operations.
- A LifeOS controller (outside ChatGPT or via tools) calls the executor directly.
- User is no longer in the loop for normal missions.

**Key invariant**: LifeOS core logic (router + runtime) does not change across v0 → v2; only the adapter implementation changes.

## 7. Risks / Open Questions (for later)

- How to encode mission packets in a way Antigravity can reliably interpret.
- How much of the router’s logic should live in code vs in specs.
- How to avoid overcomplicating the adapter before an actual API exists.
- How to surface mission and executor state back to the user in a clean way (dashboards, logs, etc.).

```
