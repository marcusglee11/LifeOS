# LifeOS Master Execution Plan v1.1 (Superseding, Canonical)

**Status:** IN PROGRESS — W0/W4/W5/W7 core stabilization complete; W5-T02 DONE, W6 pending
**Last Updated:** 2026-02-19 (rev5)

## 0. Authority and Scope

This plan is the canonical execution authority for near-term LifeOS runtime work and supersedes:

- `artifacts/plans/LifeOS_Master_Execution_Plan_v1.0.md`
- `artifacts/plans/LifeOS Status and Decision-Complete.md`
- `artifacts/plans/Grand Plan LifeOS Spine Unification.md`
- `artifacts/plans/LifeOS Reliability-First Spine Consolidation and Multi-Agent Adapter Architecture V1 202060212.md`

Stateless agents must execute this plan exactly and report deviations as blockers.

## 1. Locked Ground Truth (Do Not Re-litigate During Execution)

1. OpenClaw install and acceptance are complete (verified 2026-02-11).
2. LoopSpine is the production execution controller (`runtime/orchestration/loop/spine.py`).
3. `autonomous_build_cycle` remains callable and must be blocked for new runs.
4. Canonical contracts already exist (`MissionResult`, `MissionContext`, `BaseMission`, `AgentCall`).
5. `ReviewMission` is LLM-backed (MVP-thin) and no longer hardcoded approval.
6. Budget eligibility logic still contains a stub at `runtime/orchestration/loop/configurable_policy.py:538`.
7. Token usage needed for budgeting is upstream-dependent: current agent flow can surface zero usage values until OpenCode response parsing is corrected.
8. Manual doc audits are too frequent; doc freshness must be automated and enforced.

## 2. Operating Principles

1. Extend existing contracts; do not introduce parallel core contract systems.
2. Fail closed on missing policy, missing usage evidence, missing packet evidence, unknown mission types.
3. Keep BACKLOG as canonical queue (`docs/11_admin/BACKLOG.md`).
4. Use OpenClaw as operator/orchestration surface; use Spine as execution core.
5. Every task emits machine-checkable artifacts and explicit pass/fail evidence.

## 3. Owner Split

1. CEO/OpenClaw owner:
- OpenClaw runtime configuration, keys, channel stability, host environment readiness.
2. Builder agents:
- Repo code changes, tests, docs stewardship, packet artifacts, commit evidence.

## 4. Execution Status Summary

| Package | Task | Status | Date | Notes |
|---------|------|--------|------|-------|
| W0 | T01 | ✅ DONE | 2026-02-12 | State/backlog reconciled |
| W0 | T02 | ✅ DONE | 2026-02-12 | Plan authority registered |
| W0 | T03 | ✅ DONE | 2026-02-12 | Runtime status artifacts exist |
| W0 | T04 | ✅ DONE | 2026-02-13 | Deprecated path guarded |
| W0 | T05 | ✅ DONE | 2026-02-14 | Test debt stabilized (test_e2e_smoke passes, test_steward_runner skipped on WSL) |
| W0 | T06 | ✅ DONE | 2026-02-14 | Doc stewardship gate integrated |
| W4 | T01 | ✅ DONE | 2026-02-13 | openclaw_bridge.py schema mapping |
| W4 | T02 | ✅ DONE | 2026-02-13 | Evidence routing integrated |
| W4 | T03 | ✅ DONE | 2026-02-18 | Worktree dispatch wired into Spine run path + clean-worktree enforcement |
| W4 | T04 | ✅ DONE | 2026-02-18 | Lifecycle hooks enforced across OpenClaw->Spine path via bridged execution command |
| W5 | T01 | ✅ DONE | 2026-02-14 | E2E proof run_20260214_053357 complete |
| W5 | T02 | ⏸️ OPEN | — | Checkpoint/resume needs E2E environment |
| W5 | T03 | ✅ DONE | 2026-02-13 | Budget controller has real enforcement (W5-T04 landed) |
| W5 | T04 | ✅ DONE | 2026-02-13 | Token plumbing fail-closed, integrated |
| W6 | T00-T02 | ⏸️ DEFERRED | — | Codemoot spike deferred pending W7 stabilization |
| W7 | T01 | ✅ DONE | 2026-02-16 | Ledger hash-chain hardened (commit 558c375) |
| W7 | T02 | ✅ DONE | 2026-02-16 | Freshness check wired into CI (warn mode) + close-build gate |
| W7 | T03 | ✅ DONE | 2026-02-16 | All 5 protocol docs finalized (ACTIVE, no TODO markers) |

**Current Focus:** W5-T02 Checkpoint/Resume E2E Proof COMPLETE. Next: W6 Codemoot spike

## 5. Execution Work Packages

## W0: Truth Alignment and Path Guarding (Immediate, This Week) — ✅ COMPLETE

### W0-T01: Canonical state/backlog reconciliation

- Scope:
- Update `docs/11_admin/LIFEOS_STATE.md` and `docs/11_admin/BACKLOG.md` to match verified runtime reality.
- Actions:
1. Mark OpenClaw install as completed item.
2. Promote E2E Spine real-run verification to current P0 focus.
3. Set canonical-plan authority pointer to this file.
- Artifacts:
- Updated state/backlog docs.
- DoD:
- No stale OpenClaw blocker language remains in canonical state docs.

### W0-T02: Plan authority register and indexing

- Scope:
- Establish a single source of planning authority.
- Actions:
1. Maintain `docs/11_admin/Plan_Supersession_Register.md`.
2. Update `docs/INDEX.md` timestamp and links.
3. Regenerate `docs/LifeOS_Strategic_Corpus.md`.
- Artifacts:
- Updated register/index/corpus.
- DoD:
- Register names v1.1 as active canonical plan.

### W0-T03: Runtime checkpoint report artifact

- Scope:
- Produce machine-generated runtime truth artifact on each doc stewardship cycle.
- Actions:
1. Generate `artifacts/status/runtime_status.json`.
2. Generate dated checkpoint report at `artifacts/packets/status/checkpoint_report_<YYYYMMDD>.json`.
3. Use this schema for both files:
- `generated_at_utc`
- `repo_root`
- `facts`
- `contradictions`
- `status`
- DoD:
- Both artifacts exist and validate against same shape.

### W0-T04: Guard legacy autonomous path

- Scope:
- Prevent split-brain new-run execution paths.
- Actions:
1. In `runtime/cli.py`, block `mission run autonomous_build_cycle` with migration guidance to `lifeos spine run`.
2. In `runtime/orchestration/missions/autonomous_build_cycle.py`, add deprecation guard for CLI mission-run entry path while preserving historical replay/test compatibility.
3. Keep registry entry but mark deprecated intent in mission metadata/docs.
- DoD:
- New autonomous runs are blocked outside Spine path.

### W0-T05: Targeted test debt stabilization

- Scope:
- Repair immediate failing recursive suites.
- Actions:
1. Fix `tests_recursive/test_e2e_smoke_timeout.py` import/path assumptions.
2. Fix `tests_recursive/test_steward_runner.py` interpreter assumptions and fixture brittleness.
3. Record residual environment-coupled failures as explicit xfail/triage if needed.
- DoD:
- Target suites are green or intentionally triaged with reasons.

### W0-T06: Doc stewardship gate and OpenCode dogfood run

- Scope:
- Execute doc stewardship checks, then attempt OpenCode-backed steward path.
- Actions:
1. Run `python3 scripts/claude_doc_stewardship_gate.py` and require pass.
2. Attempt `scripts/delegate_to_doc_steward.py` in OpenCode path if dependencies/environment are ready.
3. If OpenCode path cannot run, capture blocker and keep CI-safe fallback (gate pass + status artifact).
- DoD:
- Stewardship gate passes and run result is captured in status docs.

## W1-W2: OpenClaw Orchestrator Readiness

### W4-T01: Central schema mapping module

- Scope:
- Define one mapping implementation location (not scattered scripts).
- Actions:
1. Create/maintain `runtime/orchestration/openclaw_bridge.py`.
2. Centralize all conversions:
- OpenClaw job payload -> Spine invocation payload.
- Spine terminal/checkpoint artifacts -> OpenClaw result payload.
3. Add unit tests for round-trip mapping coverage.
- DoD:
- Mapping logic is isolated and tested in one module.

### W4-T02: Evidence routing contract

- Scope:
- Deterministic evidence locations for OpenClaw-submitted jobs.
- Actions:
1. Route evidence to `artifacts/evidence/openclaw/jobs/<job_id>/`.
2. Store packet refs, ledger refs, and hash manifest.
3. Add verification checks for missing evidence.
- DoD:
- OpenClaw job has discoverable, complete evidence bundle.

### W4-T03: Worktree dispatch governance

- Scope:
- Enforce isolated worktree execution for orchestrated jobs.
- Actions:
1. Wire worktree create/use/cleanup lifecycle.
2. Reject execution when isolation preconditions fail.
3. Add tests based on existing isolation patterns.
- DoD:
- Worktree lifecycle is deterministic and fail-closed.

### W4-T04: Validator lifecycle hooks

- Scope:
- Guarantee pre/post governance checks in orchestrated runs.
- Actions:
1. Pre-run: policy hash, envelope constraints, protected paths.
2. Post-run: evidence completeness, packet presence, ledger append success.
3. Block success state if any required check is missing.
- DoD:
- Governance checks enforce fail-closed behavior across OpenClaw -> Spine execution.

## W1-W2 (Parallel): E2E Spine Validation and Budget Hardening

### W5-T01: Real E2E task run

- Scope:
- Prove end-to-end chain on one non-trivial real task.
- Actions:
1. Select one low-risk backlog item.
2. Execute via `lifeos spine run`.
3. Capture packets, ledger trail, and commit evidence.
- DoD:
- One real task completes through hydrate -> policy -> design -> build -> review -> steward.

### W5-T02: Checkpoint/resume proof ✅ DONE (2026-02-19)

- Scope:
- Validate resume semantics and policy-hash continuity.
- Actions:
1. Trigger checkpoint case intentionally.
2. Resume using `lifeos spine resume <checkpoint_id>`.
3. Verify continuation and hash checks.
- DoD:
- Resume proceeds from correct state with policy integrity checks.
- Evidence: `artifacts/evidence/W5_T02_checkpoint_resume_proof.txt` (6/6 tests PASS)

### W5-T03: Budget controller stub replacement

- Scope:
- Replace permissive budget stub with enforced logic.
- Actions:
1. Replace `eligible=True` stub in `runtime/orchestration/loop/configurable_policy.py`.
2. Enforce run-level budget totals and threshold checks.
3. Emit explicit fail-closed reason codes on violations.
- DoD:
- Budget policy blocks out-of-budget runs.

### W5-T04: Token usage upstream plumbing (prerequisite to trusted budgeting)

- Scope:
- Ensure usage values are real, not zeros.
- Actions:
1. Update OpenCode client parsing to return actual token usage when provider supplies it.
2. Ensure agent API surfaces usage values downstream.
3. Fail closed with `TOKEN_ACCOUNTING_UNAVAILABLE` when usage is absent where required.
- DoD:
- Budget controller consumes real usage or safely blocks.

## W2-W4: Codemoot Spike (Evidence-First)

### W6-T00: Discovery gate (must pass before scheduling commitment)

- Scope:
- Confirm Codemoot API/docs are available and usable in this environment.
- Actions:
1. Validate documentation access, auth method, and basic request shape.
2. If inaccessible, file blocker and re-sequence timeline.
- DoD:
- Integration timeline starts only after discovery gate pass.

### W6-T01: Mission-level Codemoot integration

- Scope:
- Integrate without destabilizing canonical transport layer.
- Actions:
1. Add mission-level Codemoot-backed executor path.
2. Map outputs into canonical `MissionResult`.
3. Keep `call_agent` transport unchanged during spike.
- DoD:
- Codemoot runs produce contract-compliant mission outcomes.

### W6-T02: Comparative reliability run

- Scope:
- Compare Codemoot against baseline on same ticket class.
- Actions:
1. Execute matched tickets through baseline and Codemoot paths.
2. Compare success rate, failure modes, governance compliance, run cost.
- DoD:
- Promotion decision input is evidence-backed.

## W2-W4 (Parallel): Stabilization and Anti-Stale Automation

### W7-T01: Ledger hash-chain hardening

- Scope:
- Add tamper-evident chaining to ledger writes.
- Actions:
1. Implement hash-link fields in `runtime/orchestration/loop/ledger.py`.
2. Add verification and tamper tests.
- DoD:
- Ledger tampering is detectable.

### W7-T02: Doc freshness CI enforcement transition

- Scope:
- Move from warning-only to blocking doc contradiction gate.
- Actions:
1. Keep warning mode active immediately.
2. Flip to blocking at end of Week 2 (explicit date in CI config).
3. Emit weekly drift artifact and backlog feed.
- DoD:
- Contradictory state docs fail CI after switch date.

### W7-T03: Pending protocol doc finalization

- Scope:
- Close known pending docs to reduce stale churn.
- Actions:
1. Finalize backlog-listed pending docs.
2. Remove WIP markers/TODO placeholders.
3. Re-run index/corpus regeneration.
- DoD:
- Pending protocol docs are no longer partial drafts.

## 6. Test and Evidence Policy

1. Minimum checks per work package:
- Targeted tests for modified surfaces.
- Relevant runtime tests before/after phase batch.
2. Required evidence outputs:
- Updated docs and status artifacts.
- Command logs / packet references.
- Review packet with changed-file flat content.
3. No silent degradation:
- Any blocked test/tool must be recorded as blocker in state/status docs.

## 7. Public Interfaces and Artifact Contracts

### Runtime status schema (v1.1 execution)

All status artifacts in this plan use:

```json
{
  "generated_at_utc": "string (ISO-8601 UTC)",
  "repo_root": "string",
  "facts": "object",
  "contradictions": ["string"],
  "status": "ok|warn|fail"
}
```

### Canonical artifact paths

1. `artifacts/status/runtime_status.json`
2. `artifacts/packets/status/checkpoint_report_<YYYYMMDD>.json`
3. `artifacts/review_packets/Review_Packet_<Mission>_vX.Y.md`

## 8. Key Files Reference

| File | Role |
|---|---|
| `runtime/orchestration/loop/spine.py` | Canonical execution controller |
| `runtime/orchestration/missions/base.py` | Canonical mission contracts |
| `runtime/agents/api.py` | Agent invocation and usage surfacing |
| `runtime/agents/opencode_client.py` | Upstream usage parsing and provider response mapping |
| `runtime/orchestration/openclaw_bridge.py` | OpenClaw mapping module target |
| `runtime/orchestration/missions/autonomous_build_cycle.py` | Deprecated path guard target |
| `runtime/cli.py` | CLI block for deprecated path |
| `runtime/orchestration/loop/configurable_policy.py` | Budget gate logic |
| `runtime/orchestration/loop/ledger.py` | Hash-chain hardening target |
| `scripts/generate_runtime_status.py` | Runtime/doc truth artifact generator |
| `docs/11_admin/LIFEOS_STATE.md` | Canonical state narrative |
| `docs/11_admin/BACKLOG.md` | Canonical execution queue |
| `docs/11_admin/PROJECT_STATUS_v1.0.md` | Information-only status summary |
| `docs/11_admin/Plan_Supersession_Register.md` | Plan authority register |
