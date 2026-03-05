# Council Review Report: COO Bootstrap Plan
**Date:** 2026-03-05
**Plan under review:** `artifacts/plans/2026-03-05-coo-bootstrap-plan.md`
**Review topology:** Codex (Architecture lens) + Gemini (Risk/Pragmatism lens)

---

## Overall Verdict

| Reviewer | Model | Verdict |
|----------|-------|---------|
| Architecture | Codex (gpt-5.3-codex) | APPROVE_WITH_CONDITIONS |
| Risk/Pragmatism | Gemini | APPROVE_WITH_CONDITIONS |

**Combined: APPROVE_WITH_CONDITIONS — 5 conditions, 2 blockers that must be resolved before execution.**

---

## Raw Findings: Codex (Architecture Lens)

**Summary:** "The plan is architecturally aligned with existing ExecutionOrder/Dispatch primitives and appropriately reuses core infrastructure, but several control-flow and enforcement seams are underspecified and would otherwise make COO autonomy mostly advisory."

**Complexity budget:** 18 new files — NOT justified at once. Recommends phased delivery (foundation → burn-in → campaign/advanced).

### Claims

| ID | Category | Severity | Description |
|----|----------|----------|-------------|
| A1 | data_flow | **BLOCKER** | Dispatch execution control-flow owner undefined — who drains inbox? |
| A2 | interface | **MAJOR** | OpenClaw not a CLIProvider — CLIProvider enum supports only codex/gemini/claude_code |
| A3 | failure_mode | **MAJOR** | 5-level autonomy model not mechanically enforceable — no envelope gate in dispatch path |
| A4 | architecture | **MAJOR** | Backlog fragmentation — 3 parallel task sources (BACKLOG.md, config/backlog.yaml, nightly_queue.yaml) without migration contract |
| A5 | over_engineering | minor | Campaign/objective tracking premature before core loop reliability proven |
| A6 | architecture | observation | ExecutionOrder reuse is correct and minimizes integration risk (positive finding) |

**Full A1 detail:**
> Plan expects `propose → approve → dispatch → spine executes` (Step 3F), but current CLI only has `dispatch submit`/`dispatch status`. `DispatchEngine` has `poll_inbox()` but no runner loop wired. Nobody drains the inbox.
>
> Recommendation: Define canonical dispatch runner (run-once or daemon) that drains inbox via DispatchEngine. COO `approve` must call this contract explicitly.

**Full A2 detail:**
> Plan says COO invoked as OpenClaw via `cli_dispatch`, but `CLIProvider` enum is `{codex, gemini, claude_code}` — no `openclaw`. `config/models.yaml` `cli_providers` section matches. The OpenClaw bridge at `runtime/agents/openclaw_bridge.py` exists separately.
>
> Recommendation: Either add first-class `openclaw` CLIProvider (enum + command builder + models.yaml + tests) or explicitly use the existing OpenClaw bridge path.

**Full A4 detail:**
> Three overlapping task sources will exist simultaneously:
> - `docs/11_admin/BACKLOG.md` parsed by `recursive_kernel/backlog_parser.py`
> - `config/backlog.yaml` used by `run-mission` in `runtime/cli.py:595`
> - `artifacts/dispatch/nightly_queue.yaml` consumed FIFO
> - (New) `config/tasks/backlog.yaml` proposed by plan
>
> Recommendation: Define one canonical schema + adapters or explicit one-time migration with deprecation checkpoints.

**Conditions from Codex:**
1. Specify dispatch execution contract end-to-end (inbox producer, consumer, trigger) before `lifeos coo approve` is considered complete.
2. Autonomy/delegation enforcement must be mechanical (not prompt-only): envelope parser, action→escalation mapping, fail-closed gate, tests.
3. Resolve OpenClaw runtime integration path and align plan text with actual invocation architecture.
4. Establish single canonical backlog source with migration/deprecation rules.

---

## Raw Findings: Gemini (Risk/Pragmatism Lens)

**Summary:** "The plan is architecturally sound and leverages existing infrastructure well, but carries high operational risk due to aggressive deprecation and potential over-engineering of the autonomy levels."

**Complexity budget:** 15 new files — justified (modularity required for testability). But recommends phasing.

### Claims

| ID | Category | Severity | Description |
|----|----------|----------|-------------|
| R1 | failure_mode | **MAJOR** | LLM YAML output unreliable — no validation/retry/escalate path in parser |
| R2 | over_engineering | minor | 5-level autonomy model too complex for v1 — simplify to L0/L3/L4 |
| R3 | failure_mode | **MAJOR** | Aggressive deprecation of markdown files without rollback plan creates "blind flight" risk |
| R4 | missing_dependency | minor | `objective_ref` field required by Step 1A backlog but objectives defined in Step 2 (later) |
| R5 | assumption | minor | OpenClaw persistent memory format TBD — implementation stall risk |

**Full R1 detail:**
> `parser.py` is the orchestration bridge. If OpenClaw produces malformed YAML, the loop hangs silently.
>
> Recommendation: Implement retry-on-error or escalate-on-error in the parser. Fail to CEO queue if LLM output is invalid after N retries.

**Full R3 detail:**
> The plan deprecates `BACKLOG.md`, `LIFEOS_STATE.md`, `INBOX.md`, and `.context/project_state.md`. No explicit rollback plan specified (though git provides one implicitly).
>
> Recommendation: Maintain auto-generated "shadow" markdown views from structured backlog during burn-in phase. Only delete manual files after Step 6 (Live COO) is verified and stable.

**Full R4 detail:**
> Step 1A creates `TaskEntry` schema with `objective_ref` field. But objectives are only defined in Step 2 (later, sequential, CEO-dependent). Early tasks created in Step 1 will have empty/placeholder `objective_ref`.
>
> Recommendation: Move "set top-level objectives" to Pre-Step 1 activity, or use a `bootstrap` placeholder objective.

**Conditions from Gemini:**
1. Simplify autonomy model to L0/L3/L4 for initial bootstrap; add L1/L2 after Early Trust phase.
2. Auto-generate "shadow" markdown backlog during burn-in — do not delete manual files until Live COO is verified.
3. Parser must include retry-on-error or escalate-on-error path for invalid LLM YAML output.

---

## Synthesis

### Confirmed Good (Both Reviewers Agree)

- **Core architecture direction is correct** — reusing ExecutionOrder/DispatchEngine is the right choice
- **File-based communication is right** — no new plumbing needed
- **Campaign tracker should stay deferred** — consistent across both reviewers
- **COO system prompt (Step 2) is the highest-value artifact** — correctly identified as sequential/CEO-dependent

### Issues Requiring Resolution Before Execution

**Blocker-level (must fix):**

1. **A1: Define dispatch execution loop** — Who runs the dispatch inbox? The propose→approve→dispatch→execute flow is currently incomplete. The plan needs to specify whether this is `lifeos dispatch run` (run-once), a daemon, or triggered by `coo approve`. This is a fundamental architecture gap.

2. **A2: OpenClaw provider integration path** — The plan says "COO invoked as OpenClaw via cli_dispatch" but OpenClaw isn't in the CLIProvider enum. Clarify: use existing OpenClaw bridge (`runtime/agents/openclaw_bridge.py`) or add a new CLIProvider entry. The plan text must match the actual invocation path.

**Condition-level (required before execution):**

3. **Simplify autonomy model for v1** — Both reviewers flag L0-L4 as too complex for bootstrap. Recommended: start with L0 (autonomous reads/state updates), L3 (propose-and-wait for everything else), L4 (escalate for protected paths). Add L1/L2 after burn-in establishes trust.

4. **Don't delete markdown files during burn-in** — Keep BACKLOG.md, LIFEOS_STATE.md as auto-generated shadow views from structured backlog. Don't delete until Step 6 is verified.

5. **Parser must have fail-safe path** — parser.py needs retry-on-error + escalate-to-CEO-queue if LLM output is invalid. This prevents silent loop hangs.

6. **Resolve backlog fragmentation** — Define migration plan for 3→1 task source. BACKLOG.md → config/tasks/backlog.yaml migration must be explicit, with adapters for anything currently reading the old sources.

7. **objective_ref bootstrapping** — Use `bootstrap` placeholder in Step 1A or move objective-setting to before Step 1A.

**OK as-is (defer):**

- Campaign tracker/objectives register — both reviewers agree deferred is correct
- Revenue content track — independent, no architectural concerns raised
- OpenClaw memory format TBD — acceptable for Step 2 to define
- All Phase 2+ features

### Recommended Plan Adjustments

The following changes to the plan would address all conditions:

1. **Part 3, Step 1A:** Note that `objective_ref` will use `bootstrap` placeholder for tasks created before Step 2 completes.

2. **Part 3, Step 3F:** Add that `lifeos coo approve` must trigger the dispatch execution loop (either call `lifeos dispatch run` or wire the engine directly). Specify who runs the inbox drainer.

3. **Part 1, Section 1.1:** Clarify OpenClaw invocation path — via `OpenClaw bridge` (`runtime/agents/openclaw_bridge.py`) not via CLIDispatch directly. Update the reuse table accordingly.

4. **Part 1, Section 1.3:** Simplify to 3 levels for v1 (L0/L3/L4). Mark L1/L2 as "Phase 2 trust expansion."

5. **Part 1, Section 1.5:** Change deprecation plan — files become "shadow views auto-generated by COO" not deleted until Live COO (Step 6) is verified.

6. **Part 3, Step 3D:** Add explicit retry/escalate logic to parser.py spec.

7. **New item:** Add explicit backlog migration plan: single canonical schema, adapters for existing readers, deprecation timeline.

---

## Decision Required from CEO

The plan is approved with conditions. Reviewers agree the direction is correct. Before execution starts, the CEO should decide:

1. **Dispatch execution loop** (A1): How should the inbox be drained? Options:
   - A) `lifeos coo approve` auto-triggers `lifeos dispatch run` (inline)
   - B) `lifeos dispatch run` is a separate manual step CEO runs
   - C) Cron/daemon runs dispatch loop periodically

2. **Autonomy simplification** (both reviewers): Accept the L0/L3/L4 simplification for v1, or keep 5 levels with the understanding that L1/L2 are advisory during burn-in?

3. **Shadow markdown views**: Accept the "auto-generate shadow views, don't delete originals until Step 6" approach?

If the CEO accepts the recommended adjustments above, execution can proceed with the plan updated to reflect conditions 1-7.

---

## Files in This Review

```
artifacts/reviews/2026-03-05-coo-bootstrap/
├── context_pack_architecture.md    (input sent to Codex)
├── context_pack_risk.md            (input sent to Gemini)
├── codex_architecture_review.yaml  (raw Codex output, 5534 bytes)
├── gemini_risk_review.yaml         (raw Gemini output, 3359 bytes)
└── review_report.md                (this file)
```

**Test baseline:** 2303 passed, 7 skipped (verified before review session started).
