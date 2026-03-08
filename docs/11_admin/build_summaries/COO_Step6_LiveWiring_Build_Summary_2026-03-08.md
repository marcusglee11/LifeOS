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
