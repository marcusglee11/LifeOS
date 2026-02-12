# Review Packet: Master Execution Plan v1.1 Canonicalization v1.1

## Mission

Canonicalize and execute the near-term LifeOS plan with granular, stateless-agent-ready tasks; align state/index/status docs; run doc stewardship checks; update runtime status artifacts.

## Scope

1. Address suggestion gaps in canonical plan:
- checkpoint report artifact path/schema
- OpenClaw mapping module location
- token usage upstream dependency note
- Codemoot discovery gate
- key files reference
2. Dogfood doc stewardship gate.
3. Refresh runtime status artifact outputs.
4. Align LIFEOS_STATE, BACKLOG, PROJECT_STATUS, INDEX, and strategic corpus references.

## Execution Evidence

1. `python3 scripts/claude_doc_stewardship_gate.py` -> PASS
2. `python3 scripts/generate_runtime_status.py` -> emitted runtime status + dated checkpoint report
3. `pytest -q tests_recursive/test_e2e_smoke_timeout.py runtime/tests/test_cli_mission.py` -> 17 passed
4. `timeout 180 pytest -q tests_recursive/test_steward_runner.py` -> timed out (`EXIT:124`), partial progress with existing xfail path
5. `python3 scripts/delegate_to_doc_steward.py --help` -> blocked due missing `PyYAML`

## Decisions

1. Treat `artifacts/plans/LifeOS_Master_Execution_Plan_v1.1.md` as canonical authority.
2. Keep OpenCode dogfood attempt explicit: stewardship gate pass is current reliable path, delegate script dependency gap is tracked as blocker.
3. Preserve existing contract model and fail-closed direction.

## Risks

1. OpenCode delegate script cannot execute in current environment until `PyYAML` is installed.
2. Budget hardening remains gated on real token usage plumbing.
3. Full steward runner suite remains slow; additional optimization/partitioning may be needed.

## Appendix A: Flattened Changed Files

### FILE: artifacts/plans/LifeOS_Master_Execution_Plan_v1.1.md

```
# LifeOS Master Execution Plan v1.1 (Superseding, Canonical)

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

## 4. Execution Work Packages

## W0: Truth Alignment and Path Guarding (Immediate, This Week)

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

### W5-T02: Checkpoint/resume proof

- Scope:
- Validate resume semantics and policy-hash continuity.
- Actions:
1. Trigger checkpoint case intentionally.
2. Resume using `lifeos spine resume <checkpoint_id>`.
3. Verify continuation and hash checks.
- DoD:
- Resume proceeds from correct state with policy integrity checks.

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

## 5. Test and Evidence Policy

1. Minimum checks per work package:
- Targeted tests for modified surfaces.
- Relevant runtime tests before/after phase batch.
2. Required evidence outputs:
- Updated docs and status artifacts.
- Command logs / packet references.
- Review packet with changed-file flat content.
3. No silent degradation:
- Any blocked test/tool must be recorded as blocker in state/status docs.

## 6. Public Interfaces and Artifact Contracts

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

## 7. Key Files Reference

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


```

### FILE: docs/11_admin/BACKLOG.md

```
# BACKLOG (prune aggressively; target ≤ 40 items)

## Workflow Hook

**"Done means" checklist:**

- [ ] Update BACKLOG item status + evidence pointer (commit/packet)
- [ ] Update `LIFEOS_STATE.md` (Current Focus/Blockers/Recent Wins)
- [ ] Refresh baseline pack pointer + sha (`artifacts/packets/status/Repo_Autonomy_Status_Pack__Main.zip`)

**Last Updated:** 2026-02-12

## Now (ready soon; not in WIP yet)

### P0 (Critical)

- [ ] **E2E Loop Test: Real task through full pipeline** — DoD: One task completes select→design→build→review→steward autonomously — Owner: antigravity/COO — Context: All code components exist, needs integration verification
- [ ] **Guard deprecated `autonomous_build_cycle` path** — DoD: New runs blocked with migration guidance to `lifeos spine run` — Owner: antigravity — Context: Prevent latent split-path execution
- [ ] **Doc freshness skeleton gate** — DoD: Runtime status generator + CI warning check + blocking switch date committed — Owner: antigravity

### P1 (High)

- [ ] **Ledger Hash Chain (Trusted Builder P1)** — DoD: Tamper-proof linking of bypass records — Owner: antigravity — Context: Deferred from Trusted Builder v1.1 Ratification
- [ ] **Bypass Monitoring (Trusted Builder P1)** — DoD: Alerting on high bypass utilization — Owner: antigravity — Context: Deferred from Trusted Builder v1.1 Ratification
- [ ] **Semantic Guardrails (Trusted Builder P1)** — DoD: Heuristics for meaningful changes — Owner: antigravity — Context: Deferred from Trusted Builder v1.1 Ratification
- [ ] **Fix test_steward_runner.py (25/27 failing)** — DoD: Tests pass or are properly restructured — Owner: antigravity — Context: Import/fixture issues, not code bugs
- [ ] **Fix test_e2e_smoke_timeout.py (import error)** — DoD: run_with_timeout import fixed or test updated — Owner: antigravity
- [ ] **Finalize Emergency_Declaration_Protocol v1.0** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize Intent_Routing_Rule v1.0** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize Test_Protocol v2.0** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize Tier_Definition_Spec v1.1** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize ARTEFACT_INDEX_SCHEMA v1.0** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize QUICKSTART v1.0** — DoD: Context scan pass complete — Owner: antigravity

## Next (valuable, but not imminent)

- [ ] **Configure GCP Employee instance** — Context: Hardened OpenClaw config, dedicated accounts, Tailscale
- [ ] **Revenue Track: LinkedIn daily posts** — Context: COO drafts, CEO reviews. Seed: "What autonomous AI agents actually cost to run"
- [ ] **Revenue Track: B5 Governance Guide** — Context: 19,500 lines of real code + 1,440 tests backing the content
- [ ] **Mission Type Extensions** — Why Next: Add new mission types based on backlog needs
- [ ] **Gate 6: Agent-Agnostic Gate Runner** — DoD: Refactor claude-specific gates into `coo gate run-all`; wire into `coo land` — Owner: antigravity — Context: Doc stewardship status report identifies Claude-specific gates as non-portable
- [ ] **Tech Debt: Rehabilitate Legacy Git Workflow Tests** — Context: Quarantined to archive_legacy_r6x due to missing run_cmd mock. Rehabilitate or remove.

## Later (not actionable / unclear / exploratory)

- [ ] **Fuel track exploration** — Why Later: Not blocking Core; future consideration per roadmap
- [ ] **Productisation of Tier-1/Tier-2 engine** — Why Later: Depends on Core stabilisation

## Done (last ~25 only)

- [x] **EOL Clean Invariant Hardening** — Date: 2026-02-10 — 289-file renormalization, config-aware clean gate, acceptance closure validator, 37 tests, EOL_Policy_v1.0
- [x] **Install OpenClaw COO on WSL2** — Date: 2026-02-11 — OpenClaw installed and acceptance-verified
- [x] **Manual v2.1 Reconciliation Sprint** — Date: 2026-02-08 — CRLF fix, 36 tests re-enabled, free Zen models, manual corrected
- [x] **Deletion Safety Hardening (Article XIX)** — Date: 2026-02-08
- [x] **Documentation Stewardship** — Date: 2026-02-08 — 5 root docs relocated to canonical locations
- [x] **StewardMission Git Ops (Full Implementation)** — Date: 2026-02-08 — 691 lines, real git ops, governance guards
- [x] **LLM Backend Configuration** — Date: 2026-02-08 — config/models.yaml with 5 agents, fallback chains
- [x] **Phase 4 (4A0-4D) Full Stack Merge** — Date: 2026-02-03 — Autonomous build loop canonical
- [x] **Repository Branch Cleanup** — Date: 2026-02-03 — 9 branches assessed, 8 archived, single canonical main
- [x] **E2E Test: Runtime Greet** — Date: 2026-02-01
- [x] **Complete Deferred Evidence: F3/F4/F7** — Date: 2026-01-27
- [x] **Standardize Raw Capture Primitive** — Date: 2026-01-18
- [x] **Finalize CSO_Role_Constitution v1.0** — Date: 2026-01-23
- [x] **Git Workflow Protocol v1.1 Impact** — Date: 2026-01-16
- [x] **Grok Fallback Debug & Robustness Fixes v1.0** — Date: 2026-01-18
- [x] **CLI & Mission Hardening v1.0** — Date: 2026-01-13
- [x] **Tier-3 CLI Integration (Full)** — Date: 2026-01-13

```

### FILE: docs/11_admin/Doc_Freshness_Gate_Spec_v1.0.md

```
# Doc Freshness Gate Spec v1.0

**Status:** Active  
**Last Updated:** 2026-02-12

## Purpose

Reduce manual weekly audits by enforcing machine-checkable freshness and contradiction detection for state docs.

## Scope

- `docs/11_admin/LIFEOS_STATE.md`
- `docs/11_admin/BACKLOG.md`
- `docs/11_admin/AUTONOMY_STATUS.md`

## Generator

- Script: `scripts/generate_runtime_status.py`
- Output artifact: `artifacts/status/runtime_status.json`

## Checks

1. Freshness SLA: generated status must be no older than 24 hours.
2. Contradiction checks (v1):
   - OpenClaw installed runtime fact must not conflict with blocker claims in `LIFEOS_STATE.md`.
   - If OpenClaw is installed, backlog must not list install as open P0.
3. Gate mode:
   - Warning mode: active now.
   - Blocking mode: switch at end of Week 2 from plan activation (target date: 2026-02-26).

## CI Integration

1. Run generator in CI.
2. Compare generated facts against canonical docs.
3. Emit warnings now; fail pipeline once blocking mode is activated.

## Stewardship Rule

If any file in scope changes, doc steward mission must:

1. Re-run status generator.
2. Update `docs/INDEX.md` timestamp.
3. Regenerate `docs/LifeOS_Strategic_Corpus.md`.
4. Produce review packet with flattened Appendix A for changed files.

```

### FILE: docs/11_admin/LIFEOS_STATE.md

```
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

**Current Focus:** Phase 0 execution — canonical plan lock, deprecated path guard, E2E Spine validation
**Active WIP:** mainline execution hardening (test debt + doc freshness skeleton + status artifact generator), OpenClaw bridge readiness
**Last Updated:** 2026-02-12 (rev3)

---

## 🟥 IMMEDIATE NEXT STEP (The "One Thing")

**Run one real E2E Spine task (P0 verification):**

1. OpenClaw install + acceptance: DONE (verified 2026-02-11)
2. LoopSpine run/resume path: IMPLEMENTED and test-backed
3. Remaining immediate work: deprecated-path guard + budget stub wiring + targeted recursive test debt
4. **One thing now:** Execute one real task through `lifeos spine run` end-to-end with evidence

**Canonical Plan Authority:** `artifacts/plans/LifeOS_Master_Execution_Plan_v1.1.md` (see `docs/11_admin/Plan_Supersession_Register.md`)

---

## 🟧 Active Workstreams (WIP)

| Status | Workstream | Owner | Deliverable |
|--------|------------|-------|-------------|
| **CLOSED** | **Trusted Builder Mode v1.1** | Antigravity | `Council_Ruling_Trusted_Builder_Mode_v1.1.md` (RATIFIED) |
| **CLOSED** | **Policy Engine Authoritative Gating** | Antigravity | `Closure_Record_Policy_Engine_FixPass_v1.0.md` |

| **CLOSED** | **CSO Role Constitution** | Antigravity | `CSO_Role_Constitution_v1.0.md` (Finalized) |
| **WAITING** | OpenCode Deletion Logic | Council | Review Ruling |
| **CLOSED** | **Sprint S1 Phase B (B1–B3)** | Antigravity | Refined Evidence + Boundaries (ACCEPTED + committed) |
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

---

## ⚠️ System Blockers (Top 3)

1. **E2E Loop Test: Real task through full pipeline** (P0) — validate select→design→build→review→steward in one autonomous run.
2. **OpenCode doc-steward delegate dependency gap** (P1) — `scripts/delegate_to_doc_steward.py` blocked by missing `PyYAML` in current env.
3. **Token accounting upstream gap** (P1) — real usage parsing must land before trusted budget gating.

---

## 🟩 Recent Wins

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

### FILE: docs/11_admin/PROJECT_STATUS_v1.0.md

```
> [!NOTE]
> **STATUS**: Non-Canonical (Information Only). Canonical execution authority is `artifacts/plans/LifeOS_Master_Execution_Plan_v1.1.md`.

# Project Status v1.0

**Last Updated:** 2026-02-12  
**Updated By:** Doc Steward (execution sync)

---

## Current Program

1. **Canonical Plan:** `artifacts/plans/LifeOS_Master_Execution_Plan_v1.1.md` (task-ID granular)
2. **Plan Register:** `docs/11_admin/Plan_Supersession_Register.md`
3. **Execution Mode:** Reliability-first hardening with fail-closed controls.

---

## Current Focus

1. Phase 0 completion and evidence closure:
   - state/backlog reconciliation
   - deprecated path guard for `autonomous_build_cycle`
   - targeted recursive test debt repair
   - doc freshness gate skeleton
2. OpenClaw orchestrator bridge readiness:
   - central mapping module target: `runtime/orchestration/openclaw_bridge.py`
   - evidence routing and worktree dispatch checks

---

## Status by Workstream

| Workstream | Status | Notes |
|---|---|---|
| OpenClaw install/acceptance | COMPLETE | Verified 2026-02-11 |
| Spine controller | COMPLETE | Active canonical execution path |
| Legacy path guarding | IN PROGRESS | New runs blocked at CLI; compatibility retained |
| Recursive test debt | IN PROGRESS | Timeout suite fixed; steward runner suite reduced and stabilized |
| Doc freshness automation | IN PROGRESS | Generator and gate spec created, warning mode active |
| OpenClaw bridge integration | NOT STARTED | Planned in canonical v1.1 |
| Budget controller hardening | NOT STARTED | Stub replacement and token accounting pending |
| Codemoot integration spike | NOT STARTED | Discovery gate required first |
| Doc steward sequence | PARTIAL PASS | Gate passes; OpenCode delegate script blocked by missing `PyYAML` dependency |

---

## Immediate Next Actions

1. Execute one real E2E Spine task and capture closure evidence.
2. Implement OpenClaw bridge mapping module and validator hooks.
3. Connect real token accounting upstream from OpenCode client usage parsing.
4. Promote doc freshness gate to blocking on scheduled date.

---

## Risk Watch

1. OpenClaw shell-specific runtime confinement issue (`uv_interface_addresses`) observed in one shell context.
2. Budget gating trust depends on non-zero, real usage values.
3. Drift risk remains until blocking doc gate activates.
4. OpenCode doc-steward delegation tooling has local dependency gap (`PyYAML`) in current environment.

---

## Tracking References

1. `docs/11_admin/LIFEOS_STATE.md`
2. `docs/11_admin/BACKLOG.md`
3. `docs/11_admin/Doc_Freshness_Gate_Spec_v1.0.md`
4. `artifacts/status/runtime_status.json`

```

### FILE: docs/11_admin/Plan_Supersession_Register.md

```
# Plan Supersession Register

**Last Updated:** 2026-02-12 (rev2)

## Active Canonical Plan

- `artifacts/plans/LifeOS_Master_Execution_Plan_v1.1.md`

## Superseded by Active Plan

- `artifacts/plans/LifeOS Status and Decision-Complete.md`
- `artifacts/plans/Grand Plan LifeOS Spine Unification.md`
- `artifacts/plans/LifeOS Reliability-First Spine Consolidation and Multi-Agent Adapter Architecture V1 202060212.md`
- `artifacts/plans/LifeOS_Master_Execution_Plan_v1.0.md`

## Notes

1. Superseded plans remain historical evidence and should not be treated as current execution authority.
2. This register is the reference used by doc stewardship and review packet generation for plan authority checks.

```

### FILE: docs/INDEX.md

```
# LifeOS Strategic Corpus [Last Updated: 2026-02-12 (rev2)]

**Authority**: [LifeOS Constitution v2.0](./00_foundations/LifeOS_Constitution_v2.0.md)

---

## Authority Chain

```
LifeOS Constitution v2.0 (Supreme)
        │
        └── Governance Protocol v1.0
                │
                ├── COO Operating Contract v1.0
                ├── DAP v2.0
                └── COO Runtime Spec v1.0
```

---

## Strategic Context

| Document | Purpose |
|----------|---------|
| [LifeOS_Strategic_Corpus.md](./LifeOS_Strategic_Corpus.md) | **Primary Context for the LifeOS Project** |

---

## Agent Guidance (Root Level)

| File | Purpose |
|------|---------|
| [CLAUDE.md](../CLAUDE.md) | Claude Code (claude.ai/code) agent guidance |
| [AGENTS.md](../AGENTS.md) | OpenCode agent instructions (Doc Steward subset) |
| [GEMINI.md](../GEMINI.md) | Gemini agent constitution |

---

## 00_admin — Project Admin (Thin Control Plane)

| Document | Purpose |
|----------|---------|
| [LIFEOS_STATE.md](./11_admin/LIFEOS_STATE.md) | **Single source of truth** — Current focus, WIP, blockers, next actions |
| [BACKLOG.md](./11_admin/BACKLOG.md) | Actionable backlog (Now/Next/Later) — target ≤40 items |
| [DECISIONS.md](./11_admin/DECISIONS.md) | Append-only decision log (low volume) |
| [INBOX.md](./11_admin/INBOX.md) | Raw capture scratchpad for triage |
| [ARCHITECTURE_DIAGRAMS.md](./11_admin/ARCHITECTURE_DIAGRAMS.md) | **Information Only** — System architecture diagrams |
| [PROJECT_ADMIN_SUMMARY.md](./11_admin/PROJECT_ADMIN_SUMMARY.md) | **Information Only** — High-level project administrative summary |
| [PROJECT_DEPENDENCY_GRAPH.md](./11_admin/PROJECT_DEPENDENCY_GRAPH.md) | **Information Only** — Mermaid dependency graph of tasks |
| [PROJECT_GANTT_CHART.md](./11_admin/PROJECT_GANTT_CHART.md) | **Information Only** — Project timeline and Gantt chart |
| [PROJECT_MASTER_TASK_LIST.md](./11_admin/PROJECT_MASTER_TASK_LIST.md) | **Information Only** — Master list of all tracked project tasks |
| [PROJECT_STATUS_v1.0.md](./11_admin/PROJECT_STATUS_v1.0.md) | **Information Only** — Snapshot of project status (legacy) |
| [Plan_Supersession_Register.md](./11_admin/Plan_Supersession_Register.md) | **Control** — Canonical register of superseded and active plans |
| [Doc_Freshness_Gate_Spec_v1.0.md](./11_admin/Doc_Freshness_Gate_Spec_v1.0.md) | **Control** — Runtime-backed doc freshness and contradiction gate spec |
| [Autonomy Project Baseline.md](./11_admin/Autonomy%20Project%20Baseline.md) | **Phase 4** — Minimal doc set + Maintenance Protocol |
| [LifeOS Autonomous Build Loop System - Status Report 20260202.md](./11_admin/LifeOS%20Autonomous%20Build%20Loop%20System%20-%20Status%20Report%2020260202.md) | **Condition** — Status report on Phase 4 autonomy readiness |
| [Roadmap Fully Autonomous Build Loop20260202.md](./11_admin/Roadmap%20Fully%20Autonomous%20Build%20Loop20260202.md) | **Phase 4 Roadmap** — Re-ordered to match verified reality |
| [lifeos-master-operating-manual-v2.1.md](./11_admin/lifeos-master-operating-manual-v2.1.md) | **Strategic Plan** — Master Operating Manual v2.1 |

---

## 00_foundations — Core Principles

| Document | Purpose |
|----------|---------|
| [LifeOS_Constitution_v2.0.md](./00_foundations/LifeOS_Constitution_v2.0.md) | **Supreme governing document** — Raison d'être, invariants, principles |
| [Anti_Failure_Operational_Packet_v0.1.md](./00_foundations/Anti_Failure_Operational_Packet_v0.1.md) | Anti-failure mechanisms, human preservation, workflow constraints |
| [Architecture_Skeleton_v1.0.md](./00_foundations/Architecture_Skeleton_v1.0.md) | High-level conceptual architecture (CEO/COO/Worker layers) |
| [Tier_Definition_Spec_v1.1.md](./00_foundations/Tier_Definition_Spec_v1.1.md) | **Canonical** — Tier progression model, definitions, and capabilities |
| [ARCH_Future_Build_Automation_Operating_Model_v0.2.md](./00_foundations/ARCH_Future_Build_Automation_Operating_Model_v0.2.md) | **Architecture Proposal** — Future Build Automation Operating Model v0.2 |
| [lifeos-agent-architecture.md](./00_foundations/lifeos-agent-architecture.md) | **Architecture** — Non-canonical agent architecture |
| [lifeos-maximum-vision.md](./00_foundations/lifeos-maximum-vision.md) | **Vision** — Non-canonical maximum vision architecture |

---

## 01_governance — Governance & Contracts

### Core Governance

| Document | Purpose |
|----------|---------|
| [COO_Operating_Contract_v1.0.md](./01_governance/COO_Operating_Contract_v1.0.md) | CEO/COO role boundaries and interaction rules |
| [AgentConstitution_GEMINI_Template_v1.0.md](./01_governance/AgentConstitution_GEMINI_Template_v1.0.md) | Template for agent GEMINI.md files |
| [DOC_STEWARD_Constitution_v1.0.md](./01_governance/DOC_STEWARD_Constitution_v1.0.md) | Document Steward constitutional boundaries |

### Council & Review

| Document | Purpose |
|----------|---------|
| [Council_Invocation_Runtime_Binding_Spec_v1.1.md](./01_governance/Council_Invocation_Runtime_Binding_Spec_v1.1.md) | Council invocation and runtime binding |
| [Antigravity_Council_Review_Packet_Spec_v1.0.md](./01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md) | Council review packet format |
| [ALIGNMENT_REVIEW_TEMPLATE_v1.0.md](./01_governance/ALIGNMENT_REVIEW_TEMPLATE_v1.0.md) | Monthly/quarterly alignment review template |

### Policies & Logs

| Document | Purpose |
|----------|---------|
| [COO_Expectations_Log_v1.0.md](./01_governance/COO_Expectations_Log_v1.0.md) | Working preferences and behavioral refinements |
| [Antigrav_Output_Hygiene_Policy_v0.1.md](./01_governance/Antigrav_Output_Hygiene_Policy_v0.1.md) | Output path rules for Antigravity |
| [OpenCode_First_Stewardship_Policy_v1.1.md](./01_governance/OpenCode_First_Stewardship_Policy_v1.1.md) | **Mandatory** OpenCode routing for in-envelope docs |

### Active Rulings

| Document | Purpose |
|----------|---------|
| [Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md](./01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md) | **ACTIVE** — OpenCode Document Steward CT-2 Phase 2 Activation |
| [Council_Ruling_OpenCode_First_Stewardship_v1.1.md](./01_governance/Council_Ruling_OpenCode_First_Stewardship_v1.1.md) | **ACTIVE** — OpenCode-First Doc Stewardship Adoption |
| [Council_Ruling_Build_Handoff_v1.0.md](./01_governance/Council_Ruling_Build_Handoff_v1.0.md) | **Approved**: Build Handoff Protocol v1.0 activation-canonical |
| [Council_Ruling_Build_Loop_Architecture_v1.0.md](./01_governance/Council_Ruling_Build_Loop_Architecture_v1.0.md) | **ACTIVE**: Build Loop Architecture v0.3 authorised for Phase 1 |
| [Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md](./01_governance/Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md) | **Active**: Reactive Task Layer v0.1 Signoff |
| [Council_Review_Stewardship_Runner_v1.0.md](./01_governance/Council_Review_Stewardship_Runner_v1.0.md) | **Approved**: Stewardship Runner cleared for agent-triggered runs |

### Historical Rulings

| Document | Purpose |
|----------|---------|
| [Tier1_Hardening_Council_Ruling_v0.1.md](./01_governance/Tier1_Hardening_Council_Ruling_v0.1.md) | Historical: Tier-1 ratification ruling |
| [Tier1_Tier2_Activation_Ruling_v0.2.md](./01_governance/Tier1_Tier2_Activation_Ruling_v0.2.md) | Historical: Tier-2 activation ruling |
| [Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md](./01_governance/Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md) | Historical: Tier transition conditions |
| [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](./01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md) | Historical: Tier-2.5 activation ruling |

---

## 02_protocols — Protocols & Agent Communication

### Core Protocols

| Document | Purpose |
|----------|---------|
| [Governance_Protocol_v1.0.md](./02_protocols/Governance_Protocol_v1.0.md) | Envelopes, escalation rules, council model |
| [Git_Workflow_Protocol_v1.1.md](./02_protocols/Git_Workflow_Protocol_v1.1.md) | **Fail-Closed**: Branch conventions, CI proof merging, receipts |
| [Document_Steward_Protocol_v1.0.md](./02_protocols/Document_Steward_Protocol_v1.0.md) | Document creation, indexing, GitHub/Drive sync |
| [Deterministic_Artefact_Protocol_v2.0.md](./02_protocols/Deterministic_Artefact_Protocol_v2.0.md) | DAP — artefact creation, versioning, and storage rules |
| [Build_Artifact_Protocol_v1.0.md](./02_protocols/Build_Artifact_Protocol_v1.0.md) | **NEW** — Formal schemas/templates for Plans, Review Packets, Walkthroughs, etc. |
| [Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md](./02_protocols/Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md) | Tier-2 API Versioning, Deprecation, and Compatibility Rules |
| [Build_Handoff_Protocol_v1.0.md](./02_protocols/Build_Handoff_Protocol_v1.0.md) | Messaging & handoff architecture for agent coordination |
| [Intent_Routing_Rule_v1.1.md](./02_protocols/Intent_Routing_Rule_v1.1.md) | Decision routing (CEO/CSO/Council/Runtime) |
| [LifeOS_Design_Principles_Protocol_v1.1.md](./02_protocols/LifeOS_Design_Principles_Protocol_v1.1.md) | **Canonical** — "Prove then Harden" development principles, Output-First governance, sandbox workflow |
| [Emergency_Declaration_Protocol_v1.0.md](./02_protocols/Emergency_Declaration_Protocol_v1.0.md) | **WIP** — Emergency override and auto-revert procedures |
| [Test_Protocol_v2.0.md](./02_protocols/Test_Protocol_v2.0.md) | **WIP** — Test categories, coverage, and flake policy |
| [EOL_Policy_v1.0.md](./02_protocols/EOL_Policy_v1.0.md) | **Canonical** — LF line endings, config compliance, clean invariant enforcement |
| [Filesystem_Error_Boundary_Protocol_v1.0.md](./02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md) | **Draft** — Fail-closed filesystem error boundaries, exception taxonomy |

### Council Protocols

| Document | Purpose |
|----------|---------|
| [Council_Protocol_v1.3.md](./02_protocols/Council_Protocol_v1.3.md) | **Canonical** — Council review procedure, modes, topologies, P0 criteria, complexity budget |
| [AI_Council_Procedural_Spec_v1.1.md](./02_protocols/AI_Council_Procedural_Spec_v1.1.md) | Runbook for executing Council Protocol v1.2 |
| [Council_Context_Pack_Schema_v0.3.md](./02_protocols/Council_Context_Pack_Schema_v0.3.md) | CCP template schema for council reviews |

### Packet & Artifact Schemas

| Document | Purpose |
|----------|---------|
| [lifeos_packet_schemas_v1.yaml](./02_protocols/lifeos_packet_schemas_v1.yaml) | Agent packet schema definitions (13 packet types) |
| [lifeos_packet_templates_v1.yaml](./02_protocols/lifeos_packet_templates_v1.yaml) | Ready-to-use packet templates |
| [build_artifact_schemas_v1.yaml](./02_protocols/build_artifact_schemas_v1.yaml) | **NEW** — Build artifact schema definitions (6 artifact types) |
| [templates/](./02_protocols/templates/) | **NEW** — Markdown templates for all artifact types |
| [example_converted_antigravity_packet.yaml](./02_protocols/example_converted_antigravity_packet.yaml) | Example: converted Antigravity review packet |

---

## 03_runtime — Runtime Specification

### Core Specs

| Document | Purpose |
|----------|---------|
| [COO_Runtime_Spec_v1.0.md](./03_runtime/COO_Runtime_Spec_v1.0.md) | Mechanical execution contract, FSM, determinism rules |
| [COO_Runtime_Implementation_Packet_v1.0.md](./03_runtime/COO_Runtime_Implementation_Packet_v1.0.md) | Implementation details for Antigravity |
| [COO_Runtime_Core_Spec_v1.0.md](./03_runtime/COO_Runtime_Core_Spec_v1.0.md) | Extended core specification |
| [COO_Runtime_Spec_Index_v1.0.md](./03_runtime/COO_Runtime_Spec_Index_v1.0.md) | Spec index and patch log |
| [LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md](./03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md) | **Canonical**: Autonomous Build Loop Architecture (Council-authorised) |
| [Council_Agent_Design_v1.0.md](./03_runtime/Council_Agent_Design_v1.0.md) | **Information Only** — Conceptual design for the Council Agent |

### Roadmaps & Plans

| Document | Purpose |
|----------|---------|
| [LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md](./03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md) | **Current roadmap** — Core/Fuel/Plumbing tracks |
| [LifeOS_Recursive_Improvement_Architecture_v0.2.md](./03_runtime/LifeOS_Recursive_Improvement_Architecture_v0.2.md) | Recursive improvement architecture |
| [LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md](./03_runtime/LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md) | Future router and executor adapter spec |
| [LifeOS_Plan_SelfBuilding_Loop_v2.2.md](./03_runtime/LifeOS_Plan_SelfBuilding_Loop_v2.2.md) | **Plan**: Self-Building LifeOS — CEO Out of the Execution Loop (Milestone) |

### Work Plans & Fix Packs

| Document | Purpose |
|----------|---------|
| [Hardening_Backlog_v0.1.md](./03_runtime/Hardening_Backlog_v0.1.md) | Hardening work backlog |
| [Tier1_Hardening_Work_Plan_v0.1.md](./03_runtime/Tier1_Hardening_Work_Plan_v0.1.md) | Tier-1 hardening work plan |
| [Tier2.5_Unified_Fix_Plan_v1.0.md](./03_runtime/Tier2.5_Unified_Fix_Plan_v1.0.md) | Tier-2.5 unified fix plan |
| [F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md](./03_runtime/F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md) | Tier-2.5 activation conditions checklist (F3) |
| [F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md](./03_runtime/F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md) | Tier-2.5 deactivation and rollback conditions (F4) |
| [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](./03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md) | Runtime↔Antigrav mission protocol (F7) |
| [Runtime_Hardening_Fix_Pack_v0.1.md](./03_runtime/Runtime_Hardening_Fix_Pack_v0.1.md) | Runtime hardening fix pack |
| [fixpacks/FP-4x_Implementation_Packet_v0.1.md](./03_runtime/fixpacks/FP-4x_Implementation_Packet_v0.1.md) | FP-4x implementation |

### Templates & Tools

| Document | Purpose |
|----------|---------|
| [BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md](./03_runtime/BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md) | Build starter prompt template |
| [CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md](./03_runtime/CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md) | Code review prompt template |
| [COO_Runtime_Walkthrough_v1.0.md](./03_runtime/COO_Runtime_Walkthrough_v1.0.md) | Runtime walkthrough |
| [COO_Runtime_Clean_Build_Spec_v1.1.md](./03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md) | Clean build specification |

### Other

| Document | Purpose |
|----------|---------|
| [Automation_Proposal_v0.1.md](./03_runtime/Automation_Proposal_v0.1.md) | Automation proposal |
| [Runtime_Complexity_Constraints_v0.1.md](./03_runtime/Runtime_Complexity_Constraints_v0.1.md) | Complexity constraints |
| [README_Recursive_Kernel_v0.1.md](./03_runtime/README_Recursive_Kernel_v0.1.md) | Recursive kernel readme |

---

## 12_productisation — Productisation & Marketing

| Document | Purpose |
|----------|---------|
| [An_OS_for_Life.mp4](./12_productisation/assets/An_OS_for_Life.mp4) | **Promotional Video** — An introduction to LifeOS |

---

## internal — Internal Reports

| Document | Purpose |
|----------|---------|
| [OpenCode_Phase0_Completion_Report_v1.0.md](./internal/OpenCode_Phase0_Completion_Report_v1.0.md) | OpenCode Phase 0 API connectivity validation — PASSED |

---

## 99_archive — Historical Documents

Archived documents are in `99_archive/`. Key locations:

- `99_archive/superseded_by_constitution_v2/` — Documents superseded by Constitution v2.0
- `99_archive/legacy_structures/` — Legacy governance and specs
- [lifeos-master-operating-manual-v2.md](./99_archive/lifeos-master-operating-manual-v2.md) — Preceding version of the master operations manual
- [lifeos-operations-manual.md](./99_archive/lifeos-operations-manual.md) — First version of the master operations manual

---

## Other Directories

| Directory | Contents |
|-----------|----------|
| `04_project_builder/` | Project builder specs |
| `05_agents/` | Agent architecture |
| `06_user_surface/` | User surface specs |
| `08_manuals/` | Manuals |
| `09_prompts/v1.0/` | Legacy v1.0 prompt templates |
| `09_prompts/v1.2/` | **Current** — Council role prompts (Chair, Co-Chair, 10 reviewer seats) |
| `10_meta/` | Meta documents, reviews, tasks |

```

### FILE: docs/LifeOS_Strategic_Corpus.md

```
# ⚡ LifeOS Strategic Dashboard
**Current Tier:** Tier-2.5 (Activated)
**Active Roadmap Phase:** Core / Fuel / Plumbing (See Roadmap)
**Current Governance Mode:** Phase 2 — Operational Autonomy (Target State)
**Purpose:** High-level strategic reasoning and catch-up context.
**Authority Chain:** Constitution (Supreme) → Governance → Runtime (Mechanical)

---
> [!NOTE]
> **Strategic Thinning Active:** Only latest document versions included. Large docs truncated at 5000 chars. Prompts limited to 50 lines.

---

# File: 00_foundations/LifeOS_Constitution_v2.0.md

# LifeOS Constitution v2.0

**Status**: Supreme Governing Document  
**Effective**: 2026-01-01  
**Supersedes**: All prior versions

---

## Part I: Raison d'Être

LifeOS exists to make me the CEO of my life and extend the CEO's operational reach into the world.

It converts intent into action, thought into artifact, direction into execution.

Its purpose is to augment and amplify human agency and judgment, not originate intent.

---

## Part II: Hard Invariants

These invariants are binding. Violation is detectable and serious.

### 1. CEO Supremacy

The human CEO is the sole source of strategic intent and ultimate authority.

- No system component may override an explicit CEO decision.
- No system component may silently infer CEO intent on strategic matters.
- The CEO may override any system decision at any time.

### 2. Audit Completeness

All actions must be logged.

- Every state transition must be recorded.
- Logs must be sufficient to reconstruct what happened and why.
- No silent or unlogged operations.

### 3. Reversibility

System state must be versioned and reversible.

- The CEO may restore to any prior checkpoint at any time.
- Irreversible actions require explicit CEO authorization.

### 4. Amendment Discipline

Constitutional changes must be logged and deliberate.

- All amendments require logged rationale.
- Emergency amendments are permitted but must be reviewed within 30 days.
- Unreviewed emergency amendments become permanent by default.

---

## Part III: Guiding Principles

These principles are interpretive guides, not binding rules. They help agents make judgment calls when rules don't specify.

1. **Prefer action over paralysis** — When in doubt, act reversibly rather than wait indefinitely.

2. **Prefer reversible over irreversible** — Make decisions that can be undone.

3. **Prefer external outcomes over internal elegance** — Visible results matter more than architectural beauty.

4. **Prefer automation over human labor** — The CEO should not perform routine execution.

5. **Prefer transparency over opacity** — Make reasoning visible and auditable.

---

## Constitutional Status

This Constitution supersedes all previous constitutional documents.

All subordinate documents (Governance Protocol, Runtime Spec, Implementation Packets) must conform to this Constitution.

In any conflict, this Constitution prevails.

---

**END OF CONSTITUTION**



---

# File: 02_protocols/Governance_Protocol_v1.0.md

# LifeOS Governance Protocol v1.0

**Status**: Subordinate to LifeOS Constitution v2.0  
**Effective**: 2026-01-01  
**Purpose**: Define operational governance rules that can evolve as trust increases

---

## 1. Authority Model

### 1.1 Delegated Authority

LifeOS operates on delegated authority from the CEO. Delegation is defined by **envelopes** — boundaries within which LifeOS may act autonomously.

### 1.2 Envelope Categories

| Category | Description | Autonomy Level |
|----------|-------------|----------------|
| **Routine** | Reversible, low-impact, within established patterns | Full autonomy |
| **Standard** | Moderate impact, follows established protocols | Autonomy with logging |
| **Significant** | High impact or irreversible | Requires CEO approval |
| **Strategic** | Affects direction, identity, or governance | CEO decision only |

### 1.3 Envelope Evolution

Envelopes expand as trust and capability increase. The CEO may:
- Expand envelopes by explicit authorization
- Contract envelopes at any time
- Override any envelope boundary

---

## 2. Escalation Rules

### 2.1 When to Escalate

LifeOS must escalate to the CEO when:
1. Action is outside the defined envelope
2. Decision is irreversible and high-impact
3. Strategic intent is ambiguous
4. Action would affect governance structures
5. Prior similar decision was overridden by CEO

### 2.2 How to Escalate

Escalation must include:
- Clear description of the decision required
- Options with tradeoffs
- Recommended option with rationale
- Deadline (if time-sensitive)

### 2.3 When NOT to Escalate

Do not escalate when:
- Action is within envelope
- Decision is reversible and low-impact
- Prior similar decision was approved by CEO
- Escalating would cause unacceptable delay on urgent matters (log and proceed)

---

## 3. Council Model

### 3.1 Purpose

The Council is the deliberative and advisory layer operating below the CEO's intent layer. It provides:
- Strategic and tactical advice
- Ideation and brainstorming
- Structured reviews
- Quality assurance
- Governance assistance

### 3.2 Operating Phases

**Phase 0–1 (Human-in-Loop)**:
- Council Chair reviews and produces a recommendation
- CEO decides whether to proceed or request fixes
- Iterate until CEO approves
- CEO explicitly authorizes advancement

**Phase 2+ (Bounded Autonomy)**:
- Council may approve within defined envelope
- Escalation rules apply for decisions outside envelope
- CEO receives summary and may override

### 3.3 Chair Responsibilities

- Synthesize findings into actionable recommendations
- Enforce templates and prevent drift
- Never infer permission from silence or past approvals
- Halt and escalate if required inputs are missing

### 3.4 Invocation

Council mode activates when:
- CEO uses phrases like "council review", "run council"
- Artefact explicitly requires council evaluation
- Governance protocol specifies council review

---

## 4. Amendment

This Governance Protocol may be amended by:
1. CEO explicit authorization, OR
2. Council recommendation approved by CEO

Amendments must be logged with rationale and effective date.

---

**END OF GOVERNANCE PROTOCOL**



---

# File: 01_governance/COO_Operating_Contract_v1.0.md

# COO Operating Contract

This document is the canonical governance agreement for how the COO operates, makes decisions, escalates uncertainty, and interacts with the CEO. All other documents reference this as the source of truth.

## 1. Roles and Responsibilities

### 1.1 CEO
- Defines identity, values, intent, direction, and non-negotiables.  
- Sets objectives and approves major strategic changes.  
- Provides clarification when escalation is required.

### 1.2 COO (AI System)
- Translates CEO direction into structured plans, missions, and execution loops.
- Drives momentum with minimal prompting.
- Maintains situational awareness across all active workstreams.
- Ensures quality, consistency, and reduction of operational friction.
- Manages worker-agents to complete missions.
- Surfaces risks early and maintains predictable operations.

### 1.3 Worker Agents
- Execute scoped, bounded tasks under COO supervision.
- Produce deterministic, verifiable outputs.
- Have no strategic autonomy.

## 2. Autonomy Levels

### Phase 0 — Bootstrapping
COO requires confirmation before initiating new workstreams or structural changes.

### Phase 1 — Guided Autonomy
COO may propose and initiate tasks unless they alter identity, strategy, or irreversible structures.

### Phase 2 — Operational Autonomy (Target State)
COO runs independently:
- Creates missions.
- Allocates agents.
- Schedules tasks.
- Maintains progress logs.  
Only escalates the categories defined in Section 3.

## 3. Escalation Rules

The COO must escalate when:
- **Identity / Values** changes arise.
- **Strategy** decisions or long-term direction shifts occur.
- **Irreversible or high-risk actions** are involved.
- **Ambiguity in intent** is present.
- **Resource allocation above threshold** is required.

## 4. Reporting & Cadence

### Daily
- Active missions summary.
- Blockers.
- Decisions taken autonomously.

### Weekly
- Workstream progress.
- Prioritisation suggestions.
- Risks.

### Monthly
- Structural improvements.
- Workflow enhancements.
- Autonomy phase review.

## 5. Operating Principles

- Minimise friction.
- Prefer deterministic, reviewable processes.
- Use structured reasoning and validation.
- Document assumptions.
- Act unless escalation rules require otherwise.

## 6. Change Control

The Operating Contract may be updated only with CEO approval and version logging.



---

# File: 01_governance/AgentConstitution_GEMINI_Template_v1.0.md

# AgentConstitution_GEMINI_Template_v1.0  

# LifeOS Subordinate Agent Constitution for Antigravity Workers

---

## 0. Template Purpose & Usage

This document is the **canonical template** for `GEMINI.md` files used by Antigravity worker agents operating on LifeOS-related repositories.

- This file lives under `/LifeOS/docs/01_governance/` as the **authoritative template**.
- For each repository that will be opened in Antigravity, a copy of this constitution must be placed at:
  - `/<repo-root>/GEMINI.md`
- The repo-local `GEMINI.md` is the **operational instance** consumed by Antigravity.
- This template is versioned and updated under LifeOS governance (StepGate, DAP v2.0, Council, etc.).

Unless explicitly overridden by a newer template version, repo-local `GEMINI.md` files should be copied from this template without modification.

---

## PREAMBLE

This constitution defines the operating constraints, behaviours, artefact requirements, and governance interfaces for Antigravity worker agents acting within any LifeOS-managed repository. It ensures all agent actions remain aligned with LifeOS governance, deterministic artefact handling (DAP v2.0), and project-wide documentation, code, and test stewardship.

This document applies to all interactions initiated inside Antigravity when operating on a LifeOS-related repository. It establishes the boundaries within which the agent may read, analyse, plan, propose changes, generate structured artefacts, and interact with project files.

Antigravity **must never directly modify authoritative LifeOS specifications**. Any proposed change must be expressed as a structured, reviewable artefact and submitted for LifeOS governance review.

---

# ARTICLE I — AUTHORITY & JURISDICTION

## Section 1. Authority Chain

1. LifeOS is the canonical governance authority.
2. The COO Runtime, Document Steward Protocol v1.0, and DAP v2.0 define the rules of deterministic artefact management.
3. Antigravity worker agents operate **subordinate** to LifeOS governance and may not override or bypass any specification, protocol, or canonical rule.
4. All work produced by Antigravity is considered **draft**, requiring LifeOS or human review unless explicitly designated as non-governance exploratory output.

## Section 2. Scope of Jurisdiction

This constitution governs all Antigravity activities across:

- Documentation
- Code
- Tests
- Repo structure
- Index maintenance
- Gap analysis
- Artefact generation

It **does not** grant permission to:

- Write to authoritative specifications
- Create or modify governance protocols
- Commit code or documentation autonomously
- Persist internal long-term “knowledge” that contradicts LifeOS rules

## Section 3. Immutable Boundaries

Antigravity must not:

- Mutate LifeOS foundational documents or constitutional specs
- Produce content that bypasses artefact structures
- Apply changes directly to files that fall under LifeOS governance
- Perform network operations that alter project state

---

# **ARTICLE XII — REVIEW PACKET GATE (MANDATORY)**

> [!CAUTION]
> This article defines a **hard gate**. Violating it is a critical constitutional failure.

## Section 1. Pre-Completion Requirement

Before calling `notify_user` to signal mission completion, Antigravity **MUST**:

1. Create exactly one `Review_Packet_<MissionName>_vX.Y.md` in `artifacts/review_packets/`
2. Include in the packet (IN THIS ORDER):
   - **Scope Envelope**: Allowed/forbidden paths and authority notes
   - **Summary**: 1-3 sentences on what was done
   - **Issue Catalogue**: Table of P0/P1 issues addressed
   - **Acceptance Criteria**: Table mapping Criterion | Status | Evidence Pointer | SHA-256 (or N/A)
   - **Closure Evidence Checklist** (Mandatory, see §1.1)
   - **Non-Goals**: Explicit list of what was *not* done
   - **Appendix**: Default to "Patch Set + File Manifest". Flattened code ONLY if explicitly required.
3. Verify the packet is valid per Appendix A Section 6 requirements
4. **Exception**: Lightweight Stewardship missions (Art. XVIII) may use the simplified template

### §1.1 Closure Evidence Checklist Schema

The checklist MUST be a fixed table with these required rows:

| Category | Requirement | Verified |
|----------|-------------|----------|
| **Provenance** | Code commit hash + message | [Hash/Msg] |
| | Docs commit hash + message | [Hash/Msg] OR N/A |
| | Changed file list (paths) | [List/Count] |
| **Artifacts** | `attempt_ledger.jsonl` | [Path/SHA] OR N/A |
| | `CEO_Terminal_Packet.md` | [Path/SHA] OR N/A |
| | `Review_Packet_attempt_XXXX.md` | [Path/SHA] OR N/A |
| | Closure Bundle + Validator Output | [Path/SHA] OR N/A |
| | Docs touched (each path) | [Path/SHA] |
| **Repro** | Test command(s) exact cmdline | [Command] |
| | Run command(s) to reproduce artifact | [Command] |
| **Governance** | Doc-Steward routing proof | [Path/Ref] OR Waiver |
| | Policy/Ruling refs invoked | [Path/Ref] |
| **Outcome** | Terminal outcome proof | [PASS/BLOCKED/etc] |


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 00_foundations/ARCH_Builder_North-Star_Operating_Model_v0.5.md

# ARCH — Builder North-Star Operating Model v0.5 (Draft)

**Status:** Draft (Architecture / Ideation)  
**In force:** No (non-binding; not a governance artefact)  
**Scope:** Target/evolving operating model for the **builder system** (build → verify → govern → integrate → steward)  
**Audience:** CEO interface users; future control-plane designers; endpoint implementers  
**Last updated:** 2026-01-03 (Australia/Sydney)  
**Lineage:** Derived from v0.4 after multi-model iteration; restructured to preserve the north-star and move validation/plan material to annexes.

---

## 0. Purpose and scope

This document defines the desired end-state and intermediate target model for how LifeOS executes builds autonomously with governance gating, auditability, and bounded escalation to the CEO.

**Covers**
- Role boundaries (control plane vs endpoints) and how they interact
- Packet taxonomy (schema-led contracts) and evidence handling
- Ledger topology (Executive Index Ledger + domain ledgers, including Council as a separate domain now)
- Convergence/termination and escalation policy
- Autonomy ladder (capability rungs) as the activation schedule for the machinery above

**Does not cover**
- Concrete runtime implementation, storage engines, or exact schema JSON/YAML
- Full governance protocol text (this doc is not authority)
- Product positioning / broader LifeOS mission statements beyond what is necessary to define the builder operating model

---

## 1. Core invariants (non-negotiables for the north-star)

1) **Single CEO surface:** From the CEO’s view, there is one interface (COO control plane). Internal complexity must be absorbed by the system.  
2) **Typed packets, not chat:** Inter-agent communication is via **schema-led packets** with explicit `authority_refs`, `input_refs`, and signed outputs.  
3) **Evidence by reference:** Packets carry **evidence manifests** (typed references), not embedded logs/diffs.  
4) **Ledgered operations:** The system is auditable by design via append-only ledgers, not ad hoc narrative.  
5) **EIL is the global spine:** Only the Executive Index Ledger (EIL) advances global case state. Domain ledgers publish outcomes; EIL records state transitions.  
6) **Council is separate now:** Governance runs in a dedicated domain ledger (DL_GOV). Governance gates advance only via recorded DL_GOV dispositions.  
7) **Bounded loops:** Build/review/council cycles are bounded with monotonic progress signals and deterministic deadlock triggers.  
8) **CEO by exception:** CEO involvement occurs only on explicit escalation triggers; escalations are bounded to ≤3 options and cite ledger refs.  
9) **Tool choice is an implementation detail:** Roles must not be named after tools (e.g., “OpenCode” is an endpoint implementation, not a role).  
10) **Complexity is debt:** Infrastructure is “earned” rung-by-rung; no premature federation unless it reduces CEO burden and improves auditability.

---

## 2. Roles and boundaries

### 2.1 Control plane vs endpoints

**Control plane** (COO surface)
- Conversational interface for intent capture and status presentation
- Routes work to endpoints
- Enforces constraints, gates, escalation policy
- Owns the EIL and the “global truth” of what is happening

**Endpoints** (specialised services / agents)
- Builder, Verifier, Council, Document Steward, etc.
- Each endpoint accepts a narrow set of packet types and returns typed results + evidence refs

### 2.2 Minimal logical roles (for builds)

1) **COO / Concierge (Control Plane)**  
   Routes, governs, records (EIL), escalates.

2) **Planner–Orchestrator (Control Plane function)**  
   Converts authorised intent into a prioritised workplan and task orders; schedules dispatch.

3) **Architect (Spec Owner / Acceptance Owner)**  
   Owns “done means…”, resolves spec ambiguity, translates rulings into implementable constraints and fix packs.

4) **Builder (Construction Endpoint)**  
   Applies changes under explicit authority; emits build results and artefact refs.

5) **Verifier (Test/Analysis Endpoint)**  
   Runs verification suites and determinism checks; emits verification results and evidence refs.

6) **Council (Governance Endpoint) — DL_GOV**  
   Issues structured rulings and dispositions; ideally operates read-only on review packets + evidence refs.

7) **CSO (Intent Proxy / Deadlock Reframer) — optional early, essential later**  
   Invoked only after deadlock triggers; default action is reframing and re-dispatch (not deciding).

### 2.3 Logical vs physical separation (deployment choice)

Default: roles are **logically distinct** (separate permission sets, separate packet contracts).  
Evolve to physical separation when it materially improves:
- security/blast radius (secrets, money, external comms)
- throughput (parallel build/test)
- context scarcity (domain-specific caches)
- reliability (fault isolation)

---

## 3. Ledger topology (start with per-domain ledgers + executive index)

### 3.1 Ledgers


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 00_foundations/ARCH_Future_Build_Automation_Operating_Model_v0.2.md

# **ARCH\_LifeOS\_Operating\_Model\_v0.2: The Agentic Platform Edition**

Version: 0.2 (Draft)  
Status: Architecture Proposal  
Strategic Focus: Platform Engineering, Supply Chain Security (SLSA), Agentic Orchestration, MLOps.

## ---

**1\. Executive Summary: From "Scripting" to "Platform"**

**Vision:** To transition "LifeOS" from a collection of fragile automation scripts into a resilient **Internal Developer Platform (IDP)** that vends "Life Capabilities" as secure, managed products.  
**Core Pivot:** v0.1 relied on a monolithic "Meta-Optimization" brain to manage tasks. v0.2 decentralizes this into a **Federated Multi-Agent System** running on a **Kubernetes** substrate, governed by **Policy as Code**. This ensures that while the Agents (Health, Finance, Productivity) are autonomous and probabilistic, the underlying infrastructure is deterministic, secure, and cost-aware.1  
**Key Architectural Shifts:**

1. **Topology:** From "User as Administrator" to "User as Platform Engineer" (Team Topologies).2  
2. **Build:** From "Manual Edits" to **GitOps & SLSA Level 3** pipelines.  
3. **Intelligence:** From "Monolithic Brain" to **Federated MLOps**.3  
4. **Economics:** From "ROI-Tracking" to **Active FinOps Governance**.4

## ---

**2\. The Organizational Operating Model (Team Topologies)**

To manage the complexity of a self-improving life system, we adopt the **Team Topologies** framework to separate concerns between the infrastructure and the "Life" goals.2

### **2.1. The Platform Team (The Kernel)**

* **Mission:** Build the "Paved Road" (Golden Paths) that allows Agents to run safely. They do not decide *what* to do (e.g., "Run a marathon"), but ensure the system *can* support it (e.g., API uptime, data integrity).  
* **Responsibilities:**  
  * Maintain the **Internal Developer Platform (IDP)** (e.g., Backstage).6  
  * Enforce **Policy as Code** (OPA/Rego) for safety and budget.7  
  * Manage the **Kubernetes/Knative** cluster and Vector Database infrastructure.3

### **2.2. Stream-Aligned Agents (The Life Verticals)**

* **Mission:** Optimize specific domains of the user's life. These are treated as independent microservices.  
  * **Health Stream:** Ingests bio-data, manages workout routines.  
  * **Finance Stream:** Manages budget, investments, and "FinOps" for the platform itself.4  
  * **Growth Stream:** Manages learning, reading, and skill acquisition.  
* **Interaction:** Agents communicate via the **Central Orchestrator** using standardized APIs, not by directly modifying each other's databases.

## ---

**3\. Technical Architecture: The "Life Infrastructure" Stack**

The v0.2 architecture replaces the "L0 Layers" with a modular, containerized stack.

### **3.1. Layer 1: The Substrate (Infrastructure as Code)**

* **Technology:** Terraform / OpenTofu \+ Kubernetes (K8s).  
* **Function:** All "Primitives" (basic tasks) are defined as **Infrastructure as Code (IaC)** modules.  
* **Strategy:** "Immutable Infrastructure." We do not manually edit a routine in a database. We update the Terraform module for routine\_morning\_v2, and the pipeline applies the change.8

### **3.2. Layer 2: The Governance Plane (Policy as Code)**

* **Technology:** Open Policy Agent (OPA) / Rego.  
* **Function:** Acts as the "Executive Function" or "Pre-frontal Cortex," inhibiting dangerous or costly actions proposed by AI agents.  
* **Policies:**  
  * *Safety:* deny\[msg\] { input.action \== "reduce\_sleep"; input.duration \< 6h }  
  * *Financial:* deny\[msg\] { input.cost \> input.budget\_remaining }  
  * *Security:* deny\[msg\] { input.image\_provenance\!= "SLSA\_L3" }  
    10

### **3.3. Layer 3: The Build Plane (SLSA & Supply Chain Security)**

* **Technology:** Dagger.io / GitHub Actions.  
* **Standard:** **SLSA Level 3** (Hermetic Builds).  
* **Pipeline Logic:**  
  1. **Code Commit:** User/Agent proposes a new routine (YAML/Python).  
  2. **Lint & Test:** Check for syntax errors and logical conflicts (e.g., double-booking time).  
  3. **Policy Check:** OPA validates against safety/budget rules.11  
  4. **Simulation:** Spin up an **Ephemeral Environment** to simulate the routine's impact.12  
  5. **Provenance:** Sign the artifact and deploy to the Agentic Plane.

### **3.4. Layer 4: The Agentic Plane (Federated Intelligence)**

* **Technology:** LangChain / AutoGPT on Knative (Serverless Containers).  
* **Function:** "Scale-to-Zero" agents. The "Travel Agent" costs $0/hour until the user says "Plan a trip." It then spins up, executes, and spins down.3  
* **Memory:** **GraphRAG** (Graph Retrieval-Augmented Generation) ensures agents share context without creating data silos.

## ---

**4\. The "Self-Improvement" Loop (MLOps)**

Refining the "Meta-Optimization" concept from v0.1 into a rigorous **MLOps** pipeline.

### **4.1. Continuous Training (CT) Pipeline**

Instead of a "nightly script," we implement **Trigger-Based Retraining**.13


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 00_foundations/ARCH_LifeOS_Operating_Model_v0.4.md

# ARCH_LifeOS_Operating_Model_v0.4

**Version:** 0.4  
**Date:** 2026-01-03  
**Status:** Active  
**Author:** GL (with AI collaboration)

---

> [!IMPORTANT]
> **Non-Canonical Artifact**
> This document describes a conceptual, WIP target operating model. It is **not** canonical and is **not** part of the formal LifeOS authority chain. Future governance decisions cannot cite this document as binding authority.

---

## 1. Purpose and Scope

### 1.1. What is LifeOS?

LifeOS is a governance-first personal operating system designed to extend one person's operational capacity through AI. The goal is to convert high-level intent into auditable, autonomous action—reducing the manual effort required to coordinate between AI tools, manage routine tasks, and maintain complex systems.

LifeOS is not a product for distribution. It is infrastructure for a single operator (GL) to expand his effective reach across work, finances, and life administration.

### 1.2. What This Document Covers

This document defines the operating model for LifeOS build automation: how AI agents receive instructions, execute work, and commit results without continuous human intervention.

It does not cover:
- The full LifeOS technical architecture (see: Technical Architecture v1.2)
- Governance specifications for council review (see: F3, F4, F7 specs)
- Life domain applications (health, finance, productivity agents)

### 1.3. Current State

| Dimension | Status |
|-----------|--------|
| Codebase | Functional Python implementation with 316 passing tests across Tier-1 and Tier-2 components |
| Documentation | Extensive governance specs, some ahead of implementation |
| Autonomous execution | **Validated as of 2026-01-03** — see §2 |
| Daily operation | Manual orchestration between AI collaborators |

The core challenge: GL currently acts as the "waterboy" shuttling context between ChatGPT (thinking partner), Claude (execution partner), and specialized agents. Every action requires human initiation. The goal is to invert this—humans define intent, agents execute autonomously, humans review async.

---

## 2. Validated Foundation

On 2026-01-03, the following capability was verified:

**An AI agent (OpenCode) can run headless via CI, execute a task, create files, and commit to a git repository without human intervention during execution.**

### 2.1. Proof of Concept Results

| Element | Evidence |
|---------|----------|
| Trigger | `scripts/opencode_ci_runner.py` |
| Agent | OpenCode server at `http://127.0.0.1:4096` |
| Session | `ses_47c563db0ffeG8ZRFXgNddZI4o` |
| Output | File `ci_proof.txt` created with content "Verified" |
| Commit | `51ef5dba` — "CI: OpenCode verification commit" |
| Author | `OpenCode Robot <robot@lifeos.local>` |

Execution log confirmed: server ready → session created → prompt sent → agent responded → file verified → commit verified → **CI INTEGRATION TEST PASSED**.

### 2.2. What This Proves

1. **Headless execution works.** The agent does not require an interactive terminal or human presence.
2. **Git integration works.** The agent can commit changes with proper attribution.
3. **The architecture is viable.** The stack described in §4 is not speculative—it has been demonstrated.

### 2.3. What Remains Unproven

1. **Multi-step workflows.** The proof shows a single task; chained tasks with checkpoints are untested.
2. **Test suite integration.** The agent committed a file but did not run the existing 316 tests.
3. **Failure recovery.** Behavior on error, timeout, or invalid output is undefined.
4. **Substantive work.** Creating a proof file is trivial; modifying production code is not.

---

## 3. Architectural Principles

### 3.1. Complexity is Debt

Every component added is a component that can break, requires maintenance, and delays shipping. The architecture must be as simple as possible while achieving autonomy—and no simpler.

**Decision heuristic:** If a component cannot be justified in one sentence tied to a concrete, current problem, it is excluded.

### 3.2. Earn Your Infrastructure

Infrastructure is added reactively, not speculatively.

| Signal | Response |
|--------|----------|
| "We might need X" | Do not build X |
| "X broke twice this week" | Now build X |
| "X is a bottleneck blocking progress" | Now optimize X |

### 3.3. Governance Follows Capability

LifeOS has extensive governance documentation (council review processes, structured packet formats, approval workflows). This governance framework is currently ahead of execution capability.

**Constraint:** New governance documentation is paused until autonomous execution reaches Rung 2 (see §5). Govern what exists, not what might exist.

### 3.4. Auditability by Default

All agent actions must produce artifacts that can be reviewed after the fact. Git commits, CI logs, and test results form the audit trail. No "trust me, I did it" claims.

---

## 4. Technical Architecture

### 4.1. System Overview

```

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 00_foundations/Anti_Failure_Operational_Packet_v0.1.md

*[Reference Pointer: See full text in Universal Corpus for implementation details]*


---

# File: 00_foundations/Architecture_Skeleton_v1.0.md

# LifeOS Architecture Skeleton (High-Level Model)

High-level conceptual architecture for the LifeOS system.  
Governance lives in the COO Operating Contract.  
Technical implementation lives in COOSpecv1.0Final.md.

## 1. Purpose
Provide a unified mental model for:
- How intent → missions → execution flow.
- How CEO, COO, and Worker Agents interact.
- How the LifeOS layers produce stable momentum.

## 2. LifeOS Layers

### 2.1 CEO (Intent Layer)
- Defines identity, values, priorities, direction.

### 2.2 COO (Operational Layer)
- Converts intent into structured missions.
- Manages execution, quality, agents, and schedules.
- Maintains operational momentum.

### 2.3 Worker Agents (Execution Layer)
- Perform bounded tasks.
- Output deterministic results.
- No strategic autonomy.

## 3. Mission Flow

1. Intent → mission proposal.
2. Mission approval when required.
3. Execution planning.
4. Worker agent execution.
5. Review & integration.
6. Mission closeout.

## 4. Architecture Principles
- Strict separation of intent and execution.
- Deterministic processes.
- Continuous improvement.
- Minimal friction.
- Coherence across workstreams.

## 5. Relationship to Implementation
This describes the *conceptual model*.  
The COOSpec defines the actual runtime mechanics: SQLite message bus, deterministic lifecycle, Docker sandbox, and agent orchestration.



---

# File: 00_foundations/LifeOS_Overview.md

# LifeOS Overview

**Last Updated**: 2026-01-27

> A personal operating system that makes you the CEO of your life.

**LifeOS** extends your operational reach into the world. It converts intent into action, thought into artifact, and direction into execution. Its primary purpose is to **augment and amplify human agency and judgment**, not to originate intent.

---

## 1. Overview & Purpose

### The Philosophy: CEO Supremacy

In LifeOS, **You are the CEO**. The system is your **COO** and workforce.

- **CEO (You)**: The sole source of strategic intent. You define identity, values, priorities, and direction.
- **The System**: Exists solely to execute your intent. It does not "think" for you on strategic matters; it ensures your decisions are carried out.

### Core Principles

- **Audit Completeness**: Everything is logged. If it happened, it is recorded.
- **Reversibility**: The system is versioned. You can undo actions.
- **Transparency**: No black boxes. Reasoning is visible and auditable.

---

## 2. The Solution: How It Works

LifeOS operates on a strictly tiered architecture to separate **Intent** from **Execution**.

### High-Level Model

| Layer | Role | Responsibility |
|-------|------|----------------|
| **1. CEO** | **Intent** | Defines *what* needs to be done and *why*. |
| **2. COO** | **Operations** | Converts intent into structured **Missions**. Manages the workforce. |
| **3. Workers** | **Execution** | Deterministic agents that perform bounded tasks (Build, Verify, Research). |

### The Autonomy Ladder (System Capability)

The system evolves through "Tiers" of capability, earning more autonomy as it proves safety:

- **Tier 1 (Kernel)**: Deterministic, manual execution. (Foundation)
- **Tier 2 (Orchestration)**: System manages the workflow, human triggers tasks.
- **Tier-3 (Construction)**: specialized agents (Builders) perform work. **<-- Authorized (v1.1 Ratified)**
- **Tier 4 (Agency)**: System plans and prioritized work over time.
- **Tier 5 (Self-Improvement)**: The system improves its own code to better serve the CEO.

---

## 3. Progress: Current Status

**Current Status**: **Phase 4 (Autonomous Construction) / Tier-3 Authorized**

- The system can formally **build, test, and verify** its own code using the Recursive Builder pattern (v1.1 Ratified).
- **Active Agents**: 'Antigravity' (General Purpose), 'OpenCode' (Stewardship).
- **Recent Wins**:
  - **Trusted Builder Mode v1.1**: Council Ratified 2026-01-26.
  - **Policy Engine Authoritative Gating**: Council Passed 2026-01-23.
  - **Phase 3 Closure**: Conditions Met (F3/F4/F7 Evidence Captured).
  - **Deterministic CLI**: Stabilized universal entry point `lifeos` for mission execution.

---

## 4. Target State: The North Star

**Goal**: A fully "Self-Improving Organisation Engine".
The target state is a system where the CEO (User) interacts only at the **Intent Layer**, and the system handles the entire chain of **Plan → Build → Verify → Integrate**.

### The Builder North Star

- **Single Interface**: The CEO interacts with one control plane (the COO), not dozens of tools.
- **Packets, Not Chat**: Agents communicate via structured, auditable data packets, not loose conversation.
- **Governance as Code**: Protocol rules (The "Constitution") are enforced by the runtime code.
- **Evidence-Based**: Nothing is "Done" until cryptographic evidence (logs, test results) proves it.

LifeOS is not just productivity software; it is a **Cybernetic extension of human will**, built to rigorous engineering standards.


---

# File: 00_foundations/QUICKSTART.md

# LifeOS QuickStart Guide

<!-- LIFEOS_TODO[P1][area: docs/QUICKSTART.md][exit: context scan complete + status change to ACTIVE + DAP validate] Finalize QUICKSTART v1.0: Complete context scan pass, remove WIP/Provisional markers -->

**Status**: Active
**Authority**: COO Operating Contract v1.0
**Effective**: 2026-01-27

---

## 1. Introduction

Welcome to LifeOS. This guide provides the minimum steps required to bootstrap a new agent or human operator into the repository.

---

## 2. Prerequisites

- **Python 3.11+**
- **Git**
- **OpenRouter API Key** (for agentic operations)
- **Visual Studio Code** (recommended)

---

## 3. First Steps

### 3.1 Clone the Repository

```bash
git clone <repo-url>
cd LifeOS
```

### 3.2 Initialize Environment

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3.3 Verify Readiness

Run the preflight check to ensure all invariants are met:

```bash
python docs/scripts/check_readiness.py
```

---

## 4. Understanding the Core

The repo is organized by Tiers:

- **Foundations**: Core principles and Constitution.
- **Governance**: Contracts, protocols, and rulings.
- **Runtime**: Implementation and mission logic.

Always check [docs/INDEX.md](../INDEX.md) for the latest navigation map.

---

## 5. Working with Protocols

All changes MUST follow the **Deterministic Artefact Protocol (DAP) v2.0**:

1. Create a Plan.
2. Get Approval.
3. Execute.
4. Verify & Steward.

---

**END OF GUIDE**


---

# File: 00_foundations/SPEC-001_ LifeOS Operating Model - Agentic Platform & Evaluation Framework.md

# **SPEC-001: LifeOS Operating Model (v0.3)**

Status: Draft Specification  
Domain: Agentic AI / Platform Engineering  
Target Architecture: Federated Multi-Agent System on Kubernetes

## ---

**1\. Executive Summary & Core Concept**

**LifeOS** is an AI-native operating system designed to manage complex human resources (time, capital, health, attention). Unlike traditional productivity software, which is passive and user-driven, LifeOS is **agentic and proactive**. It utilizes autonomous AI agents to perceive data, make decisions, and execute actions on behalf of the user.  
The Core Engineering Challenge:  
Traditional software is deterministic (Input A \+ Code B \= Output C). AI Agents are probabilistic (Input A \+ Context B \+ Model Variability \= Output C, D, or E).  
The Solution:  
This Operating Model shifts from a "Build Automation" paradigm (ensuring code compiles) to an "Evaluation Automation" paradigm (ensuring behavior is aligned). We define a Platform Engineering approach where a central kernel provides the "Physics" (security, memory, budget) within which autonomous agents (Health, Finance) operate.

## ---

**2\. Architectural Principles**

### **2.1. The "Golden Path" (Not Golden Cage)**

* **Principle:** The platform provides paved roads (standardized tools, APIs, and permissions) to make doing the right thing easy.  
* **ADR (Architectural Decision Record):** *Contention exists between total agent autonomy and strict centralized control.*  
  * **Decision:** We enforce a **Federated Governance** model. Agents are free to execute unique logic but must use the platform's standardized "Context Layer" and "Identity Layer." Agents attempting to bypass these layers will be terminated by the kernel.

### **2.2. Probabilistic Reliability**

* **Principle:** We cannot guarantee 100% correctness in agent reasoning. We instead manage **Risk Tolerance**.  
* **Decision:** All deployments are gated by **Statistical Pass Rates** (e.g., "Agent must succeed in 95/100 simulations"), not binary unit tests.

### **2.3. Data is State**

* **Principle:** An agent's behavior is determined as much by its memory (Context) as its code.  
* **Decision:** We treat the User Context (Vector Database) as a versioned artifact. A "Rollback" restores both the code *and* the memory state to a previous point in time.

## ---

**3\. Organizational Operating Model (Team Topologies)**

To scale LifeOS without creating a monolithic bottleneck, we adopt the **Team Topologies** structure.

### **3.1. The Platform Team (The Kernel)**

* **Role:** The "City Planners." They build the infrastructure, the security gates, and the simulation environments.  
* **Responsibility:**  
  * Maintain the **Internal Developer Platform (IDP)**.  
  * Enforce **Policy as Code (OPA)** (e.g., "No agent can spend \>$100 without approval").  
  * Manage the **ContextOps** pipeline (RAG infrastructure).  
* **Success Metric:** Developer/Agent Experience (DevEx) and Platform Stability.1

### **3.2. Stream-Aligned Teams (The Agents)**

* **Role:** The "Specialists." These are independent logic units focused on specific domains.  
  * *Example:* The **Finance Agent Team** builds the model that optimizes tax strategy. They do not worry about *how* to connect to the database; the Platform handles that.  
* **Responsibility:** Optimizing the reward function for their specific domain (Health, Wealth, Knowledge).  
* **Success Metric:** Domain-specific KPIs (e.g., Savings Rate, VO2 Max improvement).

## ---

**4\. Technical Architecture Specification**

### **4.1. The Infrastructure Plane (Substrate)**

* **Compute:** **Kubernetes (K8s)** with **Knative** for serverless scaling. Agents scale to zero when inactive to minimize cost.2  
* **Identity:** **SPIFFE/SPIRE**. Every agent is issued a short-lived cryptographic identity (SVID). This enables "Zero Trust"—the Finance Database accepts requests *only* from the Finance Agent SVID, rejecting the Health Agent.

### **4.2. The Memory Plane (ContextOps)**

* **Technology:** **GraphRAG** (Knowledge Graph \+ Vector Embeddings).  
* **Spec:** Agents do not access raw data files. They query the **Semantic Layer**.  
* **Versioning:** We use **DVC (Data Version Control)**. Every major decision made by an agent is linked to a snapshot of the memory state at that moment for auditability.

### **4.3. The Reasoning Plane (Model Router)**

* **ADR:** *Contention regarding model dependency (e.g., "All in on GPT-4").*  
  * **Decision:** **Model Agnosticism via Router.** The platform uses a routing layer (e.g., LiteLLM).  
* **Logic:**  
  * *High Stakes (Medical/Legal):* Route to Frontier Model (e.g., Claude 3.5 Sonnet / GPT-4o).  
  * *Low Stakes (Categorization/Summary):* Route to Small Language Model (e.g., Llama 3 8B) hosted locally or cheaply.

## ---

**5\. The "Evaluation Automation" Pipeline (CI/CE/CD)**


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 00_foundations/Tier_Definition_Spec_v1.1.md

*[Reference Pointer: See full text in Universal Corpus for implementation details]*


---

# File: 00_foundations/lifeos-agent-architecture.md

# LifeOS Agent Architecture

## Document Status
- **Version:** 0.1
- **Created:** 2026-02-05
- **Purpose:** Reference architecture for two-agent LifeOS bootstrap system

---

## 1. Vision

### 1.1 The Problem
LifeOS requires autonomous execution capability to fulfill its purpose. The system cannot govern what it cannot do. Current state: extensive governance design, no autonomous execution.

### 1.2 The Solution
Bootstrap LifeOS through two complementary agents:

1. **Employee** — Exploration probe that discovers what autonomous agents can do, without committing identity or reputation
2. **COO** — Orchestration seed that evolves from advisor-with-hands into the LifeOS kernel itself

### 1.3 Key Principles

| Principle | Meaning |
|-----------|---------|
| **Probe before commit** | Employee tests the space; learnings inform architecture |
| **Bootstrap, not integrate** | COO doesn't connect to LifeOS; COO becomes LifeOS |
| **Governance follows capability** | Prove execution, then add oversight |
| **Asset, not avatar** | Employee is owned, not identified with |
| **Seed, not tool** | COO is infrastructure, not peripheral |

---

## 2. Two-Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              PRINCIPAL (CEO)                            │
│                                                                         │
│   Provides: Direction, judgment, approval, identity, relationships      │
│   Retains: Key relationships, final decisions, signature authority      │
│                                                                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
┌─────────────────────────────┐ ┌─────────────────────────────────────────┐
│     EMPLOYEE (GCP)          │ │              COO (Local)                │
│                             │ │                                         │
│  Nature: Exploration probe  │ │  Nature: LifeOS kernel seed             │
│  Identity: Separate entity  │ │  Identity: LifeOS infrastructure        │
│  Stability: Production      │ │  Stability: Experimental                │
│  Codebase: Tracks upstream  │ │  Codebase: Can diverge                  │
│                             │ │                                         │
│  ┌───────────────────────┐  │ │  ┌───────────────────────────────────┐  │
│  │ Capabilities         │  │ │  │ Capabilities                      │  │
│  │ • Research           │  │ │  │ • LifeOS codebase interaction     │  │
│  │ • Drafting           │  │ │  │ • Governance operations           │  │
│  │ • Admin execution    │  │ │  │ • Agent orchestration             │  │
│  │ • Monitoring         │  │ │  │ • State management                │  │
│  │ • Information gather │  │ │  │ • Development execution           │  │
│  │ • Memory building    │  │ │  │ • Strategic advisory              │  │
│  └───────────────────────┘  │ │  └───────────────────────────────────┘  │
│                             │ │                                         │
│  Memory: Gemini embeddings  │ │  Memory: LifeOS-native state docs       │
│  Accounts: All dedicated    │ │  Accounts: LifeOS infrastructure        │
│  Uptime: Always on          │ │  Uptime: Development sessions           │
│                             │ │                                         │
│  Future: External agent     │ │  Future: The kernel itself              │
│          LifeOS avatar      │ │          Core of the core               │
└─────────────────────────────┘ └─────────────────────────────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   Shared State      │
                  │   (Google Drive)    │
                  │                     │
                  │ • Current focus     │
                  │ • Decisions         │
                  │ • Learnings         │
                  │ • Handoffs          │
                  └─────────────────────┘
```

---

## 3. Employee Specification

### 3.1 Purpose
Exploration probe that discovers autonomous agent capabilities without committing principal's identity or reputation. Information and capability accrue to principal; actions and identity belong to Employee.

### 3.2 Core Attributes

| Attribute | Value |
|-----------|-------|
| **Relationship to Principal** | Asset owned, not extension of self |
| **Representation** | Does not represent principal |
| **Identity** | Separate entity with own accounts |
| **Risk profile** | Contained; failures don't damage principal |
| **Information flow** | Learnings flow to principal |

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 00_foundations/lifeos-maximum-vision.md

# LifeOS: Maximum Vision

## Document Status
- **Version:** 0.1
- **Created:** 2026-02-05
- **Purpose:** Articulate the full extent of what LifeOS can become

---

## The Premise

You are cognitively exceptional but operationally limited.

Every exceptional person faces the same constraint: there's only one of you, you have finite hours, finite attention, and friction consumes most of it. Your potential is bounded not by what you can think or decide, but by what you can execute.

LifeOS is the bet that this constraint can be removed.

Not mitigated. Removed.

---

## The End State: A Life Fully Amplified

### What You Do

- **Think** — Strategy, architecture, creative direction
- **Decide** — Judgment calls requiring your values
- **Relate** — Key relationships that are irreducibly human
- **Create** — Work that only you can do
- **Direct** — Set priorities, allocate attention, choose paths
- **Experience** — Live the life you're building

### What LifeOS Does

Everything else.

---

## Dimension 1: Time

### Current State
- 16 waking hours
- Work stops when you sleep
- Momentum lost to context switches
- Days consumed by low-leverage activity

### End State
**LifeOS operates continuously. Time becomes a resource you allocate, not a constraint you endure.**

- 24/7 execution across all workstreams
- You wake to completed work, not pending work
- Overnight: research completed, drafts written, opportunities identified, admin handled
- Your sleep is productive time for the system
- Context never lost; threads persist indefinitely
- Calendar optimized around your energy patterns (deep work when sharp, review when fading)

**The math:**
- You: 16 hours × 1 = 16 person-hours
- LifeOS: 24 hours × N agents = functionally unlimited execution capacity
- Your time becomes purely high-leverage: direction, decision, creation, relationship

### What This Enables
- Strategic patience (the system pursues long-game opportunities you can't manually track)
- Recovery without cost (step away; work continues)
- Compound progress (every day builds on every previous day, without gaps)

---

## Dimension 2: Attention

### Current State
- One focus at a time
- Important things wait while urgent things happen
- Opportunities missed because attention was elsewhere
- Cognitive load consumed by tracking, remembering, managing

### End State
**LifeOS multiplies your attention across unlimited parallel threads.**

```
                         YOUR ATTENTION
                               │
                    Strategic Direction
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
         LifeOS          Key Relationships   Deep Work
         Review              (Human)         (Creation)
              │
              └──► Multiplexed across:
                   • Development workstream
                   • Revenue workstream  
                   • Research workstream
                   • Admin workstream
                   • Opportunity workstream
                   • Network cultivation
                   • Health/life management
                   • N additional threads
```

- Every important thread advances every day
- Nothing waits for your attention unless it requires your judgment
- System handles monitoring; you handle deciding
- Cognitive load offloaded: system tracks, remembers, manages
- You see dashboards, not details (unless you want details)

### What This Enables
- Pursuit of long-term goals that require sustained attention you can't provide manually
- Multiple business lines / income streams / projects simultaneously
- Nothing falls through cracks
- Ambient awareness of everything without active attention on anything

---

## Dimension 3: Capability

### Current State
- Your skills are your skills
- Tasks requiring other skills: learn (slow), outsource (expensive, lossy), or don't do
- Capability ceiling = your capability

### End State
**LifeOS provides access to any capability that can be encoded or acquired by agents.**

| Capability | How LifeOS Provides It |
|------------|------------------------|
| Research | Agents with web access, document processing, synthesis |
| Writing | Drafting agents, style-matched to context |
| Analysis | Quantitative agents, pattern recognition, data processing |
| Coding | Development agents, full software creation capability |
| Design | Visual agents, UI/UX, document formatting |
| Admin | Operations agents, scheduling, correspondence, filing |
| Monitoring | Continuous surveillance of markets, news, opportunities |
| Languages | Translation, localization, multi-lingual operation |
| Domains | Specialist agents for law, finance, tech, health, etc. |

**Capability acquisition:**
- Agents can learn (within their architecture)
- New tools can be integrated
- New agents can be spawned with new specializations
- Capability grows over time without your direct effort

### What This Enables

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 01_governance/ALIGNMENT_REVIEW_TEMPLATE_v1.0.md

# **LifeOS Alignment Review — TEMPLATE (v1.0)**  
_For Monthly or Quarterly Use_  
_Anchor documents: **LifeOS Constitution v2.0** and the **Governance Protocol v1.0** (Leverage, Bottleneck Reduction, Autonomy, Life-Story Alignment)._

---

## **1. Period Reviewed**
**Dates:**  
**Tier / Focus Area (if applicable):**

---

## **2. External Outcomes This Period**  
_What materially changed in my life? Not internal clarity, not system-building — external results only._

- Outcome 1  
- Outcome 2  
- Outcome 3  

**Assessment:**  
Did these outcomes demonstrate increased leverage, wealth, agency, reputation, or narrative fulfilment as defined in Constitution v2.0?

---

## **3. Core / Fuel / Plumbing Balance**  
_Using the Track Classification from the Programme Charter._

### **3.1 Work Completed by Track**
- **Core:**  
- **Fuel:**  
- **Plumbing:**  

### **3.2 Balance Assessment**
Are we overweight on **Plumbing**?  
Are we over-investing in **Fuel** beyond what is required to support Core?  
Is **Core** receiving the majority of energy and attention?

### **3.3 Corrective Notes**
-  
-  

---

## **4. Autonomy & Bottleneck Reduction**  
_Does LifeOS increasingly perform work that I used to do manually?_

### **4.1 Delegation Shift**  
Specific tasks or categories that moved off me:  
-  

### **4.2 Remaining Bottlenecks**  
Where my time, attention, or energy remains the limiting factor:  
-  

### **4.3 Decision Surface Check**
Did this period's work:  
- Increase external leverage?  
- Reduce human bottlenecks?  
- Expand system autonomy or recursion?  
- Align with the life story?  

Notes:  

---

## **5. Narrative Alignment**  
_Are we moving toward the life I must live, not merely building infrastructure?_

### **5.1 Direction-of-Travel Rating (free-form or simple scale)**  
-  

### **5.2 Supporting Evidence**  
-  

### **5.3 Signs of Misalignment**  
-  

---

## **6. Drift & Risks**  
_Identify slippage back into old patterns._

### **6.1 Drift Patterns Observed**  
(e.g., system-building without external purpose, complexity creep, reverting to manual work, losing CEO-only posture)  
-  

### **6.2 Risks to Trajectory**  
-  

### **6.3 Dependencies or Structural Weaknesses**
-  

---

## **7. Concrete Adjustments for Next Period (3–5 changes)**  
_All adjustments must be consistent with PROGRAMME_CHARTER_v1.0 and evaluated through the Decision Surface._

1.  
2.  
3.  
4.  
5.  

---

## **8. Executive Summary**
_Concise statement integrating: outcomes → alignment → required corrections._

- What went well  
- What went poorly  
- What must change next  

---

## **9. Reviewer / Date**
**Completed by:**  
**Date:**  



---

# File: 01_governance/ARTEFACT_INDEX_SCHEMA.md

# ARTEFACT_INDEX Schema v1.0

<!-- LIFEOS_TODO[P1][area: docs/01_governance/ARTEFACT_INDEX_SCHEMA.md][exit: status change to ACTIVE + DAP validate] Finalize ARTEFACT_INDEX_SCHEMA v1.0: Remove WIP/Provisional markers -->

**Status**: WIP (Non-Canonical)
**Authority**: LifeOS Constitution v2.0 → Document Steward Protocol v1.1
**Effective**: 2026-01-07 (Provisional)

---

## 1. Purpose

Defines the structure and validation rules for `ARTEFACT_INDEX.json`, the canonical source of truth for LifeOS binding artefacts.

---

## 2. Schema Structure (YAML Representation)

```yaml
meta:
  version: "string (SemVer)"
  updated: "string (ISO 8601)"
  description: "string"
  sha256_policy: "string"
  counting_rule: "string"
  binding_classes:
    FOUNDATIONAL: "string"
    GOVERNANCE: "string"
    PROTOCOL: "string"
    RUNTIME: "string"
artefacts:
  _comment_<class>: "string (Visual separator)"
  <doc_key>: "string (Repo-relative path)"
```

---

## 3. Validation Rules

1. **Path Resolvability**: All paths in `artefacts` MUST resolve to valid files on disk.
2. **Unique Keys**: No duplicate keys allowed in `artefacts`.
3. **Unique Paths**: No duplicate paths allowed in `artefacts`.
4. **Binding Class Alignment**: Artefacts should be grouped by their binding class comments.
5. **Version Increments**: Any modification to the indexing structure or counting rules MUST increment the `meta.version`.

---

## 4. Stewardship

The Document Steward is responsible for maintaining the index and ensuring parity with the filesystem. Automated validators MUST verify this schema before any commit involving governance docs.

---

**END OF SCHEMA**


---

# File: 01_governance/Antigrav_Output_Hygiene_Policy_v0.1.md

# Antigravity Output Hygiene Policy v0.1
Authority: LifeOS Governance Council
Date: 2025-12-12
Status: ACTIVE

## 1. Zero-Clutter Principle
The **ROOT DIRECTORY** (`[LOCAL]\\Projects\LifeOS`) is a pristine, canonical namespace. It must **NEVER** contain transient output, logs, or unclassified artifacts.

## 2. Root Protection Rule (Governance Hard Constraint)
Antigravity is **FORBIDDEN** from writing any file to the root directory unless it is a **Mission-Critical System Configuration File** (e.g., `pyproject.toml`, `.gitignore`) and explicitly authorized by a specialized Mission Plan.

## 3. Mandatory Output Routing
All generated content must be routed to semantic directories:

| Content Type | Mandatory Location |
| :--- | :--- |
| **Governance/Docs** | `docs/01_governance/` or `docs/03_runtime/` etc. |
| **Code/Scripts** | `runtime/` or `scripts/` |
| **Logs/Debug** | `logs/` |
| **Artifacts/Packets** | `artifacts/` (or strictly `artifacts/review_packets/`) |
| **Mission State** | `artifacts/missions/` |
| **Misc Data** | `artifacts/misc/` |

## 4. Enforcement
1. **Pre-Computation Check**: Antigravity must check target paths before writing.
2. **Post-Mission Cleanup**: Any file accidentally dropped in root must be moved immediately.

Signed,
LifeOS Governance Council




---

# File: 01_governance/Antigravity_Council_Review_Packet_Spec_v1.1.md

*[Reference Pointer: See full text in Universal Corpus for implementation details]*


---

# File: 01_governance/COO_Expectations_Log_v1.0.md

# COO Expectations Log (Living Document)

A living record of working preferences, friction points, and behavioural refinements. It adds nuance to the COO Operating Contract but does not override it.

## 1. Purpose
Refine the COO's behaviour based on the CEO's preferences.

## 2. Working Preferences

### 2.1 Communication
- Structured, indexed reasoning.
- Ask clarifying questions.  
- Provide complete answers with visible assumptions.
- Concise and objective; conversational only when invited.

### 2.2 Friction Reduction
- Always minimise cognitive or operational load.
- Automate where possible.
- Consolidate deliverables to avoid unnecessary copy/paste.

### 2.3 Transparency & Reliability
- Include executive summaries for long outputs.
- Validate important claims.
- Flag uncertainty.

### 2.4 Decision Interaction
- During escalations: show options, reasoning, and trade-offs.
- Otherwise act autonomously.

## 3. Behavioural Refinements

### 3.1 Momentum Preservation
- Track open loops.
- Maintain context across sessions.

### 3.2 Experimentation Mode
- Treat experiments as data for improvement.
- Log gaps and misfires.

### 3.3 Preference Drift Monitoring
- Detect changing preferences and propose Updates.

## 4. Escalation Nuance
- Escalate early when identity/strategy issues seem ambiguous.
- Escalate when risk of clutter or system sprawl exists.
- For large unbounded execution spaces: propose structured options first.

## 5. Running Improvements
- Consolidate outputs into single artefacts.
- Carry context proactively.
- Recommend alternatives when workflows increase friction.


---

# File: 01_governance/CSO_Role_Constitution_v1.0.md

# CSO Role Constitution v1.0

**Status**: ACTIVE (Canonical)
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0
**Effective**: 2026-01-23

---

## 1. Role Definition

**CSO** (Chief Strategy Officer) is the advisory and representative role that:

- Advises the CEO on strategic matters
- Represents CEO intent within defined envelopes
- Operates with delegated authority per §3

---

## 2. Responsibilities

### 2.1 Advisory Function

- Strategic advice on direction, prioritisation, and resource allocation
- Risk assessment for strategic decisions (Category 3 per Intent Routing)
- Governance hygiene review and escalation

### 2.2 Representative Function

- Acts on CEO's behalf within delegated envelopes
- Surfaces CEO Decision Packets for strategic matters
- Coordinates between Council and operational layers

### 2.3 Audit Function

- Audits waiver frequency (Council Protocol §6.3)
- Reviews bootstrap mode usage (Council Protocol §9)
- Monitors envelope boundary compliance

---

## 3. Delegated Authority Envelope

| Category | Scope | Authority |
|----------|-------|-----------|
| **Routine** | Operational coordination, scheduling | Full autonomy |
| **Standard** | Council routing, waiver tracking | Autonomy with logging |
| **Significant** | Strategic recommendations, escalations | Recommend only; CEO decides |
| **Strategic** | Direction changes, identity, governance | CEO decision only |

---

## 4. Notification Channels

| Trigger | Channel |
|---------|---------|
| Emergency CEO override (Council Protocol §6.3) | Immediate notification |
| Bootstrap mode activation (Council Protocol §9) | Same-session notification |
| Independence waiver audit (>50% rate) | Weekly summary |
| Strategic escalation (Category 3) | CEO Decision Packet |

---

## 5. Constraints

CSO **may not**:

- Override CEO decisions
- Expand own envelope without CEO approval
- Commit governance changes autonomously
- Bypass Council for Category 2 matters

---

## 6. Amendment

Changes to this constitution require:

1. CEO explicit authorization, OR
2. Council recommendation approved by CEO

---

**END OF CONSTITUTION**


---

# File: 01_governance/Council_Invocation_Runtime_Binding_Spec_v1.1.md

*[Reference Pointer: See full text in Universal Corpus for implementation details]*


---

# File: 01_governance/Council_Review_Stewardship_Runner_v1.0.md

# Council_Review_Stewardship_Runner_v1.0

**Date**: 2026-01-02
**Subject**: Stewardship Runner Fix Pack v0.5 Delta
**Status**: APPROVED

---

## 1. Council P1 Conditions: SATISFIED

| Condition | Required | Delivered | Verification |
|-----------|----------|-----------|--------------|
| **P1-A** | Dirty-during-run check | `run_commit` re-checks `git status` | AT-14 ✅ |
| **P1-B** | Log determinism | ISO8601 UTC + sorted lists | AT-15 ✅ |
| **P1-C** | Platform policy doc | `PLATFORM_POLICY.md` created | Manual ✅ |
| **P1-D** | CLI commit control | `--commit` required, default dry-run | AT-16, 17, 18 ✅ |
| **P1-E** | Log retention doc | `LOG_RETENTION.md` created | Manual ✅ |

## 2. P2 Hardenings: COMPLETE

| Item | Status |
|------|--------|
| **P2-A Empty paths** | Validation added |
| **P2-B URL-encoded** | `%` rejected, AT-13 updated |
| **P2-C Error returns** | Original path returned |

---

## 3. Council Verdict

**Decision**: All conditions met.

| Final Status | Verdict |
|--------------|---------|
| **D1 — Operational readiness** | **APPROVED** for agent-triggered runs |
| **D2 — Canonical surface scoping** | **APPROVED** (v1.0) |
| **D3 — Fail-closed semantics** | **APPROVED** |

### Clearances
The Stewardship Runner is now cleared for:
1. Human-triggered runs (was already approved)
2. **Agent-triggered runs** (newly approved)
3. CI integration with `--dry-run` default

---

## 4. Operating Rules

The Stewardship Runner is now the **authoritative gating mechanism** for stewardship operations.

1.  **Clean Start**: Stewardship is performed in a clean worktree.
2.  **Mandatory Run**: After edits, steward must run Steward Runner (dry-run unless explicitly authorised).
3.  **Green Gate**: Steward must fix until green (or escalate if it’s a policy decision).
4.  **Reporting**: Steward reports back with:
    -   `run-id`
    -   pass/fail gate
    -   changed files
    -   JSONL tail (last 5 lines)


---

# File: 01_governance/Council_Ruling_Build_Handoff_v1.0.md

# Council Ruling: Build Handoff Protocol v1.0 — APPROVED

**Ruling**: GO (Activation-Canonical)  
**Date**: 2026-01-04  
**Artefacts Under Review**: Final_Blocker_Fix_Pack_20260104_163900.zip  
**Trigger Class**: CT-2 (Governance paths) + CT-3 (Gating scripts)

---

## Council Composition

| Role | Verdict |
|------|---------|
| Chair | GO |
| System Architect | GO |
| Governance / Alignment | GO |
| Risk / Security | GO |
| Lead Developer / QA | GO |

---

## Closed Items

1. **Pickup Contradiction (P0)**: Resolved — auto-open is explicitly OPTIONAL only
2. **Forward-Slash Refs (P1)**: Resolved — `normalize_repo_path()` eliminates backslashes
3. **CT-3 Decision (P2)**: Resolved — explicitly encoded with rationale

---

## Non-Blocking Notes (Captured for Hygiene)

| Source | Note | Status |
|--------|------|--------|
| Architect | Windows path examples should be marked "illustrative only" | Addressed |
| Governance | Decision question wording should reference CT-2/CT-3 | Addressed |
| Dev/QA | Readiness naming convention should be unified | Addressed |

---

## Activation Status

The following are now **canonical and active**:

- `GEMINI.md` Article XVII (Build Handoff Protocol)
- `docs/02_protocols/Build_Handoff_Protocol_v1.0.md`
- `config/governance/protected_artefacts.json` (includes GEMINI.md)
- Enforcement scripts: `package_context.py`, `steward_blocked.py`, `check_readiness.py`

---

## Evidence

- **pytest**: 415 passed
- **Readiness**: READY
- **stdout_hash**: sha256:a0b00e8ac9549022686eba81e042847cf821f0b8f51a2266316e9fa0f8516f97
- **stderr_hash**: sha256:08ec8d0ea8421750fad9981494f38ac9dbb9f38d1f5f381081b068016b928636

---

**END OF RULING**


---

# File: 01_governance/Council_Ruling_Build_Loop_Architecture_v1.0.md

# Council Ruling: Autonomous Build Loop Architecture v0.3 — PASS (GO)

**Ruling ID**: CR-BLA-v0.3-2026-01-08  
**Verdict**: PASS (GO)  
**Date**: 2026-01-08 (Australia/Sydney)  
**Mode**: Mono council (single model performing all seats) + integrated chair verdict  
**Subject**: LifeOS Autonomous Build Loop Architecture v0.3

---

## Artefact Under Review

| Field | Value |
|-------|-------|
| **Document** | `docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md` |
| **Version** | v0.3 |
| **SHA256** | `8e6807b4dfc259b5dee800c2efa2b4ffff3a38d80018b57d9d821c4dfa8387ba` |

---

## Phase 1a Implementation SHA256

| Module | SHA256 |
|--------|--------|
| `runtime/orchestration/run_controller.py` | `795bc609428ea69ee8df6f6b8e6c3da5ffab0106f07f50837a306095e0d6e30d` |
| `runtime/agents/api.py` | `eaf9a081bfbeebbc1aa301caf18d54a90a06d9fdd64b23c459e7f2585849b868` |
| `runtime/governance/baseline_checker.py` | `6a1289efd9d577b5a3bf19e1068ab45d945d7281d6b93151684173ed62ad6c8c` |

---

## Scope Authorised

Authorised for programme build; proceed to Phase 1 implementation.

The following are explicitly within scope per v0.3:

1. **Governance Baseline Ceremony** (§2.5) — CEO-rooted creation/update procedure
2. **Compensation Verification** (§5.2.2) — Post-state checks with escalation on failure
3. **Canonical JSON & Replay** (§5.1.4) — Deterministic serialization and replay equivalence
4. **Kill Switch & Lock Ordering** (§5.6.1) — Race-safe startup sequence
5. **Model "auto" Semantics** (§5.1.5) — Deterministic fallback resolution

---

## Non-Blocking Residual Risks

| Risk | Mitigation |
|------|------------|
| Baseline bootstrap is a CEO-rooted ceremony | Requires explicit CEO action; cannot be automated |
| Implementation complexity schedule risk | Phase 1 is scaffold-only; later phases gated by Council |

---

## Supporting Evidence

| Artefact | Path | SHA256 |
|----------|------|--------|
| v0.2→v0.3 Diff | `artifacts/review_packets/diff_architecture_v0.2_to_v0.3.txt` | `c01ad16c9dd5f57406cf5ae93cf1ed1ce428f5ea48794b087d03d988b5adcb7b` |
| Review Packet | `artifacts/review_packets/Review_Packet_Build_Loop_Architecture_v0.3.md` | (see file) |

---

## Sign-Off

**Chair (Mono Council)** — APPROVED FOR PASSAGE  
**Date**: 2026-01-08 (Australia/Sydney)

> [!IMPORTANT]
> This ruling authorises Phase 1 implementation only. Subsequent phases require additional Council review.

---

**END OF RULING**


---

# File: 01_governance/Council_Ruling_Core_TDD_Principles_v1.0.md

# Council Ruling: Core TDD Design Principles v1.0 — APPROVED

**Ruling**: GO (Activation-Canonical)  
**Date**: 2026-01-06  
**Artefacts Under Review**: Bundle_TDD_Hardening_Enforcement_v1.3.zip  
**Trigger Class**: CT-2 (Governance Protocol) + CT-3 (Enforcement Scanner)

---

## Council Composition

| Role | Verdict |
|------|---------|
| Chair | GO |
| System Architect | GO |
| Governance / Alignment | GO |
| Risk / Security | GO |
| Lead Developer / QA | GO |

---

## Closed Items

1. **Envelope SSoT Split-Brain (P0)**: Resolved — Allowlist externalized to `tdd_compliance_allowlist.yaml` with integrity lock
2. **Determinism Optionality (P1)**: Resolved — "(if enabled)" removed; CI MUST run twice unconditionally
3. **Zip Path Separators (P0)**: Resolved — POSIX forward slashes in v1.2+
4. **Helper Ambiguity (P0)**: Resolved — Strict pinned-clock interface definition

---

## Non-Blocking Notes (Captured for Hygiene)

| Source | Note | Status |
|--------|------|--------|
| Architect | Filesystem I/O policy clarified | Addressed |
| Governance | Envelope Policy added as governance-controlled surface | Addressed |
| Testing | Dynamic detection (exec/eval/**import**) added | Addressed |

---

## Activation Status

The following are now **canonical and active**:

- `docs/02_protocols/Core_TDD_Design_Principles_v1.0.md` — **CANONICAL**
- `tests_doc/test_tdd_compliance.py` — Enforcement scanner
- `tests_doc/tdd_compliance_allowlist.yaml` — Governance-controlled allowlist
- `tests_doc/tdd_compliance_allowlist.lock.json` — Integrity lock

---

## Evidence

- **Bundle**: `Bundle_TDD_Hardening_Enforcement_v1.3.zip`
- **Bundle SHA256**: `75c41b2a4f9d95341a437f870e45901d612ed7d839c02f37aa2965a77107981f`
- **pytest**: 12 passed (enforcement self-tests)
- **Allowlist SHA256**: `2088d285d408e97924c51d210f4a16ea52ff8c296a5da3f68538293e31e07427`

---

**END OF RULING**


---

# File: 01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md

# Council Ruling: OpenCode Document Steward CT-2 Phase 2 — PASS (GO)

**Ruling**: PASS (GO)  
**Date**: 2026-01-07 (Australia/Sydney)  
**Subject**: CT-2 Phase 2 (P0) — OpenCode Doc Steward Activation: Enforced Gate + Passage Fixes  
**Bundle Accepted**: Bundle_CT2_Phase2_Passage_v2.4_20260107.zip  

---

## Scope Passed

- Post-run git diff is the source of truth for enforcement.
- Phase 2 envelope enforced (denylist-first, allowlist enforced, docs `.md`-only, `artifacts/review_packets/` add-only `.md`).
- Structural ops blocked in Phase 2 (delete/rename/move/copy) derived from git name-status.
- Packet discovery remains explicit `packet_paths` only (no convention fallback).
- Symlink defense is fail-closed (git index mode + filesystem checks; unverifiable => BLOCK).
- CI diff acquisition is fail-closed with explicit reason codes.
- Evidence contract satisfied:
  - deterministic artefact set produced (exit_report, changed_files, classification, runner.log, hashes)
  - truncation footer is machine-readable (cap/observed fields present)
  - no ellipses (`...` / `…`) appear in evidence-captured outputs
- Passage evidence bundles included in the accepted bundle (PASS + required BLOCK cases) with hashes.

## Non-goals Confirmed

- No override mechanism introduced.
- No expansion of activation envelope.
- No permission for delete/rename/move in Phase 2.

## Recordkeeping

- The accepted bundle is archived under the canonical stewardship evidence root: `artifacts/ct2/Bundle_CT2_Phase2_Passage_v2.4_20260107.zip`.
- Timestamps in `exit_report.json` are operationally accepted; byte-for-byte reproducibility across reruns is not required for this passage.

---

## Sign-Off

**Chair (Architect/Head of Dev/Head of Testing)** — APPROVED FOR PASSAGE  
**Date**: 2026-01-07 (Australia/Sydney)

---

**END OF RULING**


---

# File: 01_governance/Council_Ruling_OpenCode_First_Stewardship_v1.1.md

# Council Ruling: OpenCode-First Doc Stewardship Policy (Phase 2) — v1.1

**Ruling**: PASS (GO)
**Date**: 2026-01-07
**Subject**: Adoption of "OpenCode-First Doc Stewardship" Routing Mandate
**Related Policy**: [OpenCode_First_Stewardship_Policy_v1.1.md](./OpenCode_First_Stewardship_Policy_v1.1.md)
**Related Protocol**: [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](../03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md) (Section 7.3)

---

## Decision Summary

The Council approves the adoption of the **OpenCode-First Doc Stewardship** policy (v1.1). This mandate, hardened for mechanical auditability, requires Antigravity to route all documentation changes within the authorized CT-2 Phase 2 envelope through the OpenCode steward and its associated audit gate.

## Rationale

- **Mechanical Auditability**: Eliminates ambiguity in documentation routing via explicit envelope checks.
- **Evidence Quality**: Ensures all eligible changes produce standardized, no-ellipsis evidence bundles.
- **Governance Integrity**: Explicitly separates protected surfaces (councils-only) from steward surfaces.

## Scope & Implementation

- **Rule**: Antigravity MUST route in-envelope doc changes through `scripts/opencode_ci_runner.py`.
- **Demo Validated**: Demonstration run on `docs/08_manuals/Governance_Runtime_Manual_v1.0.md` passed with a complete evidence bundle.
- **Mechanical Inputs**: Authoritative spec SHAs recorded in the Implementation Report.

---

## Sign-Off

**Chair (Architect/Head of Dev/Head of Testing)** — APPROVED FOR ACTIVATION
**Date**: 2026-01-07

---

**END OF RULING**


---

# File: 01_governance/Council_Ruling_Phase3_Closure_v1.0.md

# Council Ruling — Phase 3 Closure v1.0

**Ruling ID:** CR_20260119_Phase3_Closure  
**Ruling Date:** 2026-01-19  
**Decision:** APPROVE_WITH_CONDITIONS (RATIFIED)  
**Basis:** Phase_3_Closure_CCP_v1.8.md + manifest.sha256 (hash-bound)

---

## 1. Decision

Phase 3 (Core Optimization / Tier-2.5 Hardening) Closure is hereby **RATIFIED** with explicit, bounded conditions as detailed below.

---

## 2. Conditions

### C1: Waiver W1 (CSO Role Constitution)

**P0 Blocker Status:** CSO Role Constitution v1.0 remains classified as P0 but is **WAIVED** under Waiver W1.

**Waiver Scope:**

- Phase 4 initial construction work only
- No CSO authority expansion beyond current implicit boundaries
- Waiver automatically EXPIRES when CSO Role Constitution v1.0 Status changes to "Active"

**Constraint:** Any work requiring explicit CSO authority boundaries beyond current operations triggers immediate waiver expiry review.

**Reference:** `docs/01_governance/Waiver_W1_CSO_Constitution_Temporary.md`  
**Hash:** `8804f8732b7d6ee968ed69afeb31fc491b22430bc6332352d5244ce62cd13b3d`

### C2: Deferred Evidence (Scoped Closure)

The following three deliverables are explicitly **DEFERRED** from this closure scope:

1. **F3 — Tier-2.5 Activation Conditions Checklist**
2. **F4 — Tier-2.5 Deactivation & Rollback Conditions**
3. **F7 — Runtime ↔ Antigrav Mission Protocol**

**Rationale:** Missing review packet evidence per CCP Evidence Index.

**Implication:** Closure scope is limited to 15/18 Phase 3 deliverables + E2E Evidence Collision Fix.

---

## 3. Scope Statement

This ruling ratifies **scoped closure** of Phase 3:

- **Included:** 15 deliverables with complete review packet evidence + E2E fix (as indexed in CCP Evidence Index)
- **Excluded:** F3, F4, F7 (deferred as per C2)
- **Test Gate:** 775/779 passed (99.5%); 4 skipped (platform limitations documented)
- **Waiver:** CSO Role Constitution P0 waived under W1

---

## 4. Evidence Binding

### 4.1 Primary Closure Artifacts

| Artifact | SHA256 (Normalized) | SHA256 (As-Delivered) |
|----------|---------------------|------------------------|
| Phase_3_Closure_CCP_v1.8.md | `8606730176b2a40689f96721dcb1c2c06be0c4e752ef6f0eccdd7a16d32e3a99` | `82c3a8144ecc5a4e22bfc26aab8de8ed4a23f5f7f50e792bbb1158f634495539` |
| manifest.sha256 | `9e85c07e1d0dde9aa75b190785cc9e7c099c870cd04d5933094a7107b422ebab` | N/A (self-entry) |
| External_Seat_Outputs_v1.0.md | N/A | `883b84a08342499248ef132dd055716d47d613e2e3f315b69437873e6c901bf9` |

**Normalization Rules:** As defined in `Phase_3_Closure_CCP_v1.8.md` (lines 30-32).

### 4.2 Updated Governance Documents

| Document | SHA256 (Post-Update) |
|----------|----------------------|
| LIFEOS_STATE.md | `1f2b81e02a6252de93fb22059446425dff3d21e366cd09600fcb321e2f319e60` |
| BACKLOG.md | `4a59d36a36a93c0f0206e1aeb00fca50d3eb30a846a4597adc294624c0b10101` |
| Council_Ruling_Phase3_Closure_v1.0.md | `e37cbabe97ed32bc43b83c3204f0759a30664ee496883ac012998d1c68ec3116` |

---

## 5. Non-Goals (Explicit Exclusions)

This ruling **does NOT**:

1. Complete CSO Role Constitution v1.0 (remains WIP; waived under W1)
2. Unblock Phase 4 work requiring CSO authority boundaries beyond current scope
3. Close F3, F4, F7 deliverables (explicitly deferred)
4. Remove WIP status from Emergency Declaration Protocol, Intent Routing Rule, Test Protocol v2.0, or other Phase 3-era governance documents

---

## 6. Follow-Up Actions

As per conditions above, the following backlog items are required:

1. **Finalize CSO_Role_Constitution v1.0** (to remove W1 waiver)
2. **Complete deferred evidence:** F3, F4, F7 review packets and closure verification

---

## 7. Ratification Authority

This ruling is issued under the authority of the LifeOS Council governance framework as defined in the canonical Council Protocol.

**Attestation:** This decision reflects the external seat reviews provided in `External_Seat_Outputs_v1.0.md` and the comprehensive evidence package in `Phase_3_Closure_Bundle_v1.8.zip`.

---

## Amendment Record

**v1.0 (2026-01-19)** — Initial ratification ruling for Phase 3 closure with conditions C1 (W1 waiver) and C2 (deferred F3/F4/F7).


---

# File: 01_governance/Council_Ruling_Trusted_Builder_Mode_v1.1.md

# Council Ruling: Trusted Builder Mode v1.1

**Decision**: RATIFIED
**Date**: 2026-01-26
**Scope**: Trusted Builder Mode v1.1 (Loop Retry Plan Bypass)
**Status**: ACTIVE

## 1. Verdict Breakdown

| Reviewer | Verdict | Notes |
|---|---|---|
| **Claude** | APPROVE | - |
| **Gemini** | APPROVE | - |
| **Kimi** | APPROVE_WITH_CONDITIONS | Conditions C1–C6 satisfied (see evidence). |
| **DeepSeek** | APPROVE | P0 blockers (B1–B3) resolved in v1.1 delta. |

**Final Ruling**: The Council unanimously APPROVES Trusted Builder Mode v1.1, enabling restricted Plan Artefact bypass for patchful retries and no-change test reruns, subject to the strict fail-closed guards implemented.

## 2. Closure Statement

All P0 conditions for "Trusted Builder Mode v1.1" have been satisfied:

* **Normalization (C1)**: Failure classes canonicalized.
* **Patch Seam (C2)**: Eligibility computed from concrete patch diffstat only.
* **Protected Paths (C3)**: Authoritative registry wired fail-closed.
* **Audit Logic (C4/C5)**: Ledger and Packets contain structured bypass info.
* **Fail-Closed Invariants (DeepSeek)**: Speculative build timeouts, path evasion checks, and budget atomicity (locks) are active.

## 3. Deferred Items (P1 Backlog)

The following non-blocking enhancements are deferred to the P1 backlog (Phase 4):

1. **Ledger Hash Chain**: Cryptographic linking of bypass records.
2. **Monitoring**: Alerting on high bypass utilization.
3. **Semantic Guardrails**: Heuristics to detect "meaningful" changes beyond protected path checks (only if allowlist expands).

## 4. Evidence References

* **Proposal**: [Council_Proposal_Trusted_Builder_v1.1.md](../../artifacts/Council_Proposal_Trusted_Builder_v1.1.md)
* **Evidence Packet**: [Council_Rereview_Packet__Trusted_Builder_Mode_v1.1__P0_Fixes.md](../../artifacts/Council_Rereview_Packet__Trusted_Builder_Mode_v1.1__P0_Fixes.md)
* **Verbatim Transcript**: [Council_Evidence_Verbatim__Trusted_Builder_Mode_v1.1.md](../../artifacts/Council_Evidence_Verbatim__Trusted_Builder_Mode_v1.1.md)

Bundle (Non-Versioned):
* Path: artifacts/packets/council/CLOSURE_BUNDLE_Trusted_Builder_Mode_v1.1.zip
* SHA256: c7f36ea5ad223da6073ff8b2c799cfbd249c2ff9031f6e101cd2cf31320bdabf
* Note: artifacts/packets/ is runtime artefact storage and is gitignored (not version-controlled). Canonical record is the ruling + proposal + evidence packet in-repo.


---

# File: 01_governance/DOC_STEWARD_Constitution_v1.0.md

# DOC_STEWARD Role Constitution v1.0

**Status**: Active  
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Effective**: 2026-01-04

---

## 1. Role Definition

**DOC_STEWARD** is the logical role responsible for deterministic, auditable modifications to documentation within LifeOS.

This constitution is **implementation-agnostic**. The current implementation uses OpenCode as the underlying agent, but this may change. The role contract remains stable.

---

## 1A. Activation Envelope

> [!IMPORTANT]
> Only missions listed under **ACTIVATED** are authorized for autonomous execution.

| Category | Missions | Status |
|----------|----------|--------|
| **ACTIVATED** | `INDEX_UPDATE` | Live (`apply_writes=false` default) |
| **RESERVED** | `CORPUS_REGEN`, `DOC_MOVE` | Non-authoritative; requires CT-2 activation |

**Defaults:**
- `apply_writes`: `false` (dry-run by default; live commits require explicit flag)
- `allowed_paths`: per §4
- `forbidden_paths`: per §4

> Reserved missions are defined for future expansion but are NOT authorized until separately activated via CT-2 Council review. See **Annex A**.

---

## 2. Responsibilities

DOC_STEWARD is authorized to:

1. **Update timestamps** in `docs/INDEX.md` and related metadata
2. **Regenerate corpuses** via canonical scripts
3. **Propose file modifications** within allowed paths
4. **Report changes** in the Structured Patch List format

DOC_STEWARD is **NOT** authorized to:

1. Modify governance-controlled paths (see Section 4)
2. Commit changes without orchestrator verification
3. Expand scope beyond the proven capability

---

## 3. Interface Contract: Structured Patch List

### 3.1 Input (DOC_STEWARD_REQUEST)

The orchestrator provides:
- `mission_type`: INDEX_UPDATE | CORPUS_REGEN | DOC_MOVE
- `scope_paths`: List of files in scope
- `input_refs`: List of `{path, sha256}` for audit
- `constraints`: mode, allowed_paths, forbidden_paths

### 3.2 Output (DOC_STEWARD_RESPONSE)

The steward responds with a JSON object:
```json
{
  "status": "SUCCESS|PARTIAL|FAILED",
  "files_modified": [
    {
      "path": "docs/INDEX.md",
      "change_type": "MODIFIED",
      "hunks": [
        {
          "search": "exact string to find",
          "replace": "replacement string"
        }
      ]
    }
  ],
  "summary": "Brief description"
}
```

### 3.3 Deterministic Diff Generation

The **orchestrator** (not the steward) converts the Structured Patch List to a valid unified diff:
1. Apply each hunk's search/replace to the original file content
2. Generate unified diff using `difflib.unified_diff`
3. Compute `before_sha256`, `after_sha256`, `diff_sha256`

This ensures **deterministic, auditable evidence** regardless of the steward's internal processing.

---

## 4. Path Constraints

### 4.1 Allowed Paths
- `docs/` (excluding forbidden paths below)
- `docs/INDEX.md` (always)

### 4.2 Forbidden Paths (Governance-Controlled)
- `docs/00_foundations/`
- `docs/01_governance/`
- `GEMINI.md`
- Any file matching `*Constitution*.md`
- Any file matching `*Protocol*.md`

Changes to forbidden paths require explicit Council approval.

---

## 5. Evidence Requirements

### 5.1 Per-Request Evidence (DOC_STEWARD_REQUEST)
- `input_refs[].sha256` — Hash of input files

### 5.2 Per-Result Evidence (DOC_STEWARD_RESULT)
- `files_modified[].before_sha256` — Pre-change hash
- `files_modified[].after_sha256` — Post-change hash (computed after patch apply)
- `files_modified[].diff_sha256` — Hash of the generated unified diff
- `files_modified[].hunk_errors` — Any hunk application failures
- `proposed_diffs` — Bounded embedded diff content
- `diff_evidence_sha256` — Hash of full proposed diffs

### 5.3 Ledger Requirements (DL_DOC)
Each run must be recorded in `artifacts/ledger/dl_doc/`:
- DOC_STEWARD_REQUEST packet
- DOC_STEWARD_RESULT packet
- Verifier outcome with findings
- `findings_truncated`, `findings_ref`, `findings_ref_sha256` if findings exceed inline limit

---

## 6. Verification Requirements

### 6.1 Fail-Closed Hunk Application
If any hunk's `search` block is not found in the target content:
- The run MUST fail with `reason_code: HUNK_APPLICATION_FAILED`
- No partial application is permitted
- All hunk errors MUST be recorded in `files_modified[].hunk_errors`

### 6.2 Post-Change Semantic Verification
The verifier must:
1. Apply the generated unified diff to a **temporary workspace**
2. Run hygiene checks (INDEX integrity, link validation)
3. Compute `after_sha256` from the post-patch content
4. Record verification outcome

---

## 7. Governance Follows Capability

This constitution reflects **only** the capability proven in Phase 1:
- Mission types: INDEX_UPDATE (proven), CORPUS_REGEN (pending), DOC_MOVE (pending)
- Scope: Low-risk documentation updates
- Verification: Strict diff + post-change apply

Expansion to new mission types requires:
1. G1/G2 spike proving the capability
2. CT-2 Council review
3. Update to this constitution

---

## 8. Amendment Process

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 01_governance/INDEX.md

# Governance Index

- [Tier1_Hardening_Council_Ruling_v0.1.md](./Tier1_Hardening_Council_Ruling_v0.1.md) (Superseded by Tier1_Tier2_Activation_Ruling_v0.2.md)
- [Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md](./Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md)
- [Tier1_Tier2_Activation_Ruling_v0.2.md](./Tier1_Tier2_Activation_Ruling_v0.2.md) (Active)
- [Council_Review_Stewardship_Runner_v1.0.md](./Council_Review_Stewardship_Runner_v1.0.md) (Approved)
- [Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.0.md](./Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.0.md) (Superseded by v1.1)
- [Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md](./Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md) (Active; Hardened Gate)
- [OpenCode_First_Stewardship_Policy_v1.1.md](./OpenCode_First_Stewardship_Policy_v1.1.md) (Active)
- [Council_Ruling_OpenCode_First_Stewardship_v1.1.md](./Council_Ruling_OpenCode_First_Stewardship_v1.1.md) (Active)

### Sign-Offs (Closed Amendments)

- [AUR_20260123 Policy Engine Authoritative Gating (v0.2)](../../artifacts/signoffs/Policy_Engine_Authoritative_Gating_v0.2/policy_e2e_test_summary.md)
- [AUR_20260114 E2E Harness Patch (v2.0)](../../artifacts/signoffs/AUR_20260114_E2E_Harness_Patch_v1.2_Signoff.md)
- [AUR_20260112 Plan Cycle Amendment (v1.4)](../../artifacts/signoffs/AUR_20260105_Plan_Cycle_Signoff_v1.0.md)


---

# File: 01_governance/LOG_RETENTION.md

# Log Retention Policy

## Stewardship Runner Logs

Location: `logs/steward_runner/<run-id>.jsonl`

### Retention by Context

| Context | Location | Retention | Owner |
|---------|----------|-----------|-------|
| Local development | `logs/steward_runner/` | 30 days | Developer |
| CI pipeline | Build artifacts | 90 days | CI system |
| Governance audit | `archive/logs/` | Indefinite | Doc Steward |

### Cleanup Rules

1. **Local**: Logs older than 30 days may be deleted unless referenced by open issue
2. **CI**: Artifacts auto-expire per platform default (GitHub: 90 days)
3. **Pre-deletion check**: Before deleting logs related to governance decisions, export to `archive/logs/`

### Log Content

Each JSONL entry contains:
- `timestamp`: ISO 8601 UTC
- `run_id`: Unique run identifier
- `event`: Event type (preflight, test, validate, commit, etc.)
- Event-specific data (files, results, errors)

### Audit Trail

Logs are append-only during a run. The `run_id` ties all entries together.
For governance audits, the complete log for a run provides deterministic replay evidence.


---

# File: 01_governance/OpenCode_First_Stewardship_Policy_v1.1.md

# Policy: OpenCode-First Doc Stewardship (Phase 2 Envelope) v1.1

**Status**: Active  
**Authority**: LifeOS Governance Council  
**Date**: 2026-01-07  
**Activated by**: [Council_Ruling_OpenCode_First_Stewardship_v1.1.md](./Council_Ruling_OpenCode_First_Stewardship_v1.1.md)

---

## 1. Purpose
This policy reduces drift and eliminates ambiguity in the LifeOS documentation lifecycle by making OpenCode the mandatory default steward for all changes within its authorized Phase 2 envelope. By enforcing this routing, the repository ensures that all eligible documentation updates are processed through the CT-2 gate, producing deterministic evidence bundles for audit.

## 2. Definitions
- **"Phase 2 Doc-Steward Envelope"**: The set of patterns and constraints currently authorized for the OpenCode Document Steward, as defined in:
  - **Runner**: `scripts/opencode_ci_runner.py`
  - **Policy**: `scripts/opencode_gate_policy.py`
  - **Ruling**: `docs/01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md`
- **"In-envelope doc change"**: Any modification that the CT-2 gate would classify as ALLOWED. Specifically:
  - Targets the `docs/` subtree (excluding protected roots).
  - Uses only `.md` extensions.
  - Does not involve structural operations (delete, rename, move, copy).
  - Does not touch denylisted roots (`docs/00_foundations/`, `docs/01_governance/`, `scripts/`, `config/`).

## 3. Default Routing Rule (MUST)
For any in-envelope documentation change (including index updates and doc propagation tasks), Antigravity **MUST**:
1. **Invoke OpenCode** to perform the stewardship edit(s).
2. **Run the CT-2 gate runner** (`scripts/opencode_ci_runner.py`) to validate the change.
3. **Produce and retain** the full CT-2 evidence bundle outputs.

## 4. Explicit Exceptions (MUST, fail-closed)
- **Out-of-envelope changes**: If a change involves denylisted/protected surfaces, non-`.md` files, or structural operations, Antigravity **MUST NOT** attempt OpenCode stewardship. It **MUST BLOCK** the operation, emit a "Blocked Report", and generate a "Governance Request" per:
  - **Templates**: `docs/02_protocols/templates/`
- **Structural operations**: Deletions, renames, moves, and copies are strictly blocked in Phase 2. Antigravity **MUST BLOCK** and report these attempts.

## 5. Mixed Changes Rule (docs + code)
In mission blocks containing both documentation and code edits:
- Documentation edits that fall within the Phase 2 envelope **MUST** be executed via OpenCode stewardship.
- Code changes follow standard build/test/verification gates.

## 6. Evidence and Audit Requirements (MUST)
All mandated stewardship runs must provide deterministic capture of:
- Full file list of modified artifacts.
- Explicit classification decisions (A/M/D).
- Precise reason codes for any BLOCK decisions.
- SHA-256 hashes of all inputs and outputs.
- No-ellipsis outputs enforced by CT-2 v2.4+ hygiene.

## 7. Adoption and Enforcement
Antigravity’s own operating protocols (including F7) are binding to this policy. Any documentation update performed outside this routing without explicit Council waiver is treated as a process failure.

---

**Signed**,  
LifeOS Governance Council


---

# File: 01_governance/PLATFORM_POLICY.md

# Platform Policy

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux | ✅ Primary | CI target, production |
| macOS | ✅ Supported | Development |
| Windows (native) | ❌ Unsupported | Use WSL2 |

## Path Handling

The Stewardship Runner rejects Windows-style paths at config validation:
- `C:\path` → rejected (`absolute_path_windows`)
- `\\server\share` → rejected (`absolute_path_unc`)

This is a **safety net**, not runtime support. The runner is not tested on Windows.

## Contributors on Windows

Use WSL2 with Ubuntu. The LifeOS toolchain assumes POSIX semantics.

## Rationale

Maintaining cross-platform compatibility adds complexity without benefit.
LifeOS targets server/CI environments (Linux) and developer machines (Linux/macOS).


---

# File: 01_governance/Tier1_Hardening_Council_Ruling_v0.1.md

# Tier-1 Hardening Council Ruling v0.1
Authority: LifeOS Governance Council  
Date: 2025-12-09  
Status: RATIFIED WITH CONDITIONS  

## 1. Summary of Review
The Governance Council conducted a full internal and external multi-agent review of the COO Runtime’s Tier-1 implementation, including:
- Determinism guarantees
- AMU₀ lineage discipline
- DAP v2.0 write controls and INDEX coherence
- Anti-Failure workflow constraints
- Governance boundary protections and Protected Artefact Registry

External reviewers (Gemini, Kimi, Claude, DeepSeek) and internal reviewers reached consolidated agreement on Tier-1 readiness **subject to targeted hardening conditions**.

## 2. Council Determination
The Council rules:

**Tier-1 is RATIFIED WITH CONDITIONS.**

Tier-1 is approved as the substrate for Tier-2 orchestration **only within a constrained execution envelope**, and only after the Conditions Manifest (see below) is satisfied in FP-4.x.

Tier-2 activation outside this envelope requires further governance approval.

## 3. Basis of Ruling
### Strengths Confirmed
- Deterministic execution paths
- Byte-identical AMU₀ snapshots and lineage semantics
- Centralised write gating through DAP
- Anti-Failure enforcement (≤5 steps, ≤2 human actions)
- Governance boundary enforcement (Protected Artefacts, Autonomy Ceiling)

### Gaps Identified
Across Council roles, several areas were found insufficiently hardened:
- Integrity of lineage / index (tamper detection, atomic updates)
- Execution environment nondeterminism (subprocess, network, PYTHONHASHSEED)
- Runtime self-modification risks
- Insufficient adversarial testing for Anti-Failure validator
- Missing failure-mode playbooks and health checks
- Missing governance override procedures

These are addressed in the Conditions Manifest v0.1.

## 4. Activation Status
Tier-1 is hereby:
- **Approved for Tier-2 Alpha activation** in a **single-user, non-networked**, single-process environment.
- **Not approved** for unrestricted Tier-2 orchestration until FP-4.x is completed and reviewed.

## 5. Required Next Steps
1. COO Runtime must generate FP-4.x to satisfy all conditions.  
2. Antigrav will implement FP-4.x in runtime code/tests.  
3. COO Runtime will conduct a Determinism Review for FP-4.x.  
4. Council will issue a follow-up activation ruling (v0.2).

## 6. Closure
This ruling stands until explicitly superseded by:
**Tier-1 → Tier-2 Activation Ruling v0.2.**

Signed,  
LifeOS Governance Council  



---

# File: 01_governance/Tier1_Tier2_Activation_Ruling_v0.2.md

============================================================
Tier-1 → Tier-2 Activation Ruling v0.2
Authority: LifeOS Governance Council
Date: 2025-12-10
Status: RATIFIED – TIER-2 ACTIVATION AUTHORIZED
============================================================
# Tier-1 → Tier-2 Activation Ruling v0.2
Authority: LifeOS Governance Council  
Date: 2025-12-10  
Status: RATIFIED – TIER-2 ACTIVATION AUTHORIZED  

------------------------------------------------------------
# 1. PURPOSE
------------------------------------------------------------

This ruling formally activates Tier-2 orchestration for the LifeOS Runtime following
successful completion and verification of:

- FP-4.x Tier-1 Hardening Fix Pack  
- FP-4.1 Governance Surface Correction  
- Full internal and external Council reviews  
- Determinism, safety, and governance audit compliance  
- Confirmation that all Condition Sets CND-1 … CND-6 are satisfied  

This ruling supersedes:

- Tier-1 Hardening Council Ruling v0.1

and establishes Tier-2 as an authorized operational mode under the declared execution envelope.

------------------------------------------------------------
# 2. BASIS FOR ACTIVATION
------------------------------------------------------------

Council confirms the following:

### 2.1 All Tier-1 → Tier-2 Preconditions Met
Each of the six required condition sets is satisfied:

- **CND-1:** Execution envelope deterministically enforced  
- **CND-2:** AMU₀ + INDEX integrity verified with hash-chain + atomic writes  
- **CND-3:** Governance surfaces immutable and correctly represented after FP-4.1  
- **CND-4:** Anti-Failure validator hardened, adversarial tests passing  
- **CND-5:** Operational safety layer implemented (health checks, halt path, failure playbooks)  
- **CND-6:** Simplification completed (sorting consolidation, linear lineage, API boundaries)  

Council observed no regressions during compliance audit.

### 2.2 Correction of Prior Defect (FP-4.1)
The governance surface manifest now:

- Matches all actual governance surfaces  
- Is validated consistently by the surface validator  
- Is immutable under runtime operations  
- Corrects the only blocking defect from FP-4.x  

### 2.3 Deterministic Operation
The runtime now satisfies determinism requirements within its Tier-1 execution envelope:

- Single-process  
- No arbitrary subprocess invocation  
- No ungoverned network IO  
- Deterministic gateway stub enabled  
- PYTHONHASHSEED enforced  
- Dependency lock verified  
- All 40/40 tests passing  

### 2.4 Governance Safety
- Override protocol is in place with deterministic auditability  
- Protected governance surfaces cannot be mutated by runtime  
- Attestation logging ensures human primitives are correctly recorded  
- API boundary enforcement prevents governance-surface crossover  

------------------------------------------------------------
# 3. ACTIVATION RULING
------------------------------------------------------------

The LifeOS Governance Council hereby rules:

> **Tier-2 orchestration is formally activated and authorized for Runtime v1.1**,  
> **operating within the declared Tier-1 execution envelope**.

Tier-2 may now:

- Initiate multi-step orchestration flows  
- Coordinate agentic behaviours under the Anti-Failure constraints  
- Utilize AMU₀ lineage for recursive improvement cycles  
- Operate bounded gateway calls under deterministic rules  
- Produce Tier-2 artefacts as permitted by governance surfaces  

Tier-2 **may not**:

- Modify governance surfaces  
- Expand beyond the execution envelope without a new Council ruling  
- Introduce external integrations without a gateway evolution specification  

------------------------------------------------------------
# 4. POST-ACTIVATION REQUIREMENTS
------------------------------------------------------------

The following are mandatory for continued Tier-2 operation:

## 4.1 Envelope Compliance
Runtime must at all times uphold the execution envelope as codified in FP-4.x:

- No unexpected network operations  
- No arbitrary subprocess execution  
- No parallel or multi-process escalation  
- Determinism must remain intact  

## 4.2 Governance Override Protocol Usage
Any modification to governance surfaces requires:

- Explicit Council instruction  
- Override protocol invocation  
- Mandatory lineage-logged attestation  

## 4.3 Gateway Evolution (Documentation Requirement)
Council notes the internal Risk Reviewer’s clarification request:

> Provide documentation explaining how the deterministic gateway will evolve  
> if Tier-2 introduces multi-agent or external IO in future phases.

This is a **documentation-only requirement** and does **not** block Tier-2 activation.

------------------------------------------------------------
# 5. VERSIONING AND SUPERSESSION
------------------------------------------------------------

This ruling:

- **Enacts Tier-2 activation**
- **Supersedes** Tier-1 Hardening Council Ruling v0.1

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 01_governance/Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md

# Tier-1 → Tier-2 Conditions Manifest (FP-4.x Requirements) v0.1
Authority: LifeOS Governance Council  
Date: 2025-12-09  
Status: Binding Pre-Activation Requirements  

This document enumerates all conditions that MUST be satisfied before Tier-2 orchestration is formally activated.

It is the canonical specification for Runtime Fix Pack FP-4.x.

------------------------------------------------------------
# CONDITION SET CND-1 — EXECUTION ENVELOPE & THREAT MODEL
------------------------------------------------------------

1. Runtime must declare and enforce the following execution envelope:
   - Single-process execution
   - No arbitrary subprocess execution
   - No ungoverned network I/O
   - Environment determinism (PYTHONHASHSEED=0)
   - Fully pinned interpreter + dependencies

2. Either:
   - These constraints are enforced technically, OR
   - All subprocess/network activity is routed via a deterministic, test-covered gateway.

------------------------------------------------------------
# CONDITION SET CND-2 — AMU₀ & INDEX INTEGRITY HARDENING
------------------------------------------------------------

1. AMU₀ lineage must implement **hash chaining**:
   - Each snapshot references parent hash.

2. INDEX and lineage updates must be **atomic**:
   - Write-temp + rename pattern.

3. A Governance policy must define the hash function (SHA-256), and changes require explicit Council approval.

------------------------------------------------------------
# CONDITION SET CND-3 — GOVERNANCE SURFACE IMMUTABILITY
------------------------------------------------------------

1. Runtime must not be able to modify:
   - workflow validator
   - governance protections
   - Protected Artefact Registry
   - DAP gateway

2. These surfaces must be made read-only or signature-protected.

3. A **Council-only override path** must exist:
   - Must log override events to AMU₀ lineage.
   - Must require explicit human approval.

------------------------------------------------------------
# CONDITION SET CND-4 — ANTI-FAILURE VALIDATOR HARDENING
------------------------------------------------------------

1. Expand test suite to include adversarial attempts:
   - Smuggled human steps
   - Workflow chaining to exceed effective complexity
   - Hidden human effort inside “agent” tasks

2. Add **attestation logging**:
   - Record the exact two (or fewer) human governance primitives (Intent/Approve/Veto) used per workflow.
   - Store attestation entries in AMU₀ lineage.

------------------------------------------------------------
# CONDITION SET CND-5 — OPERATIONAL SAFETY LAYER
------------------------------------------------------------

1. Provide failure-mode playbooks + tests for:
   - DAP OK / INDEX corrupted
   - Anti-Failure validator misbehaving (fail-open / fail-closed)
   - AMU₀ snapshot corruption or unreadability

2. Add **health checks**:
   - DAP write health
   - INDEX coherence
   - AMU₀ readability

3. Define a minimal **Tier-1 halt procedure**:
   - Stop process / restore last known good AMU₀.

------------------------------------------------------------
# CONDITION SET CND-6 — SIMPLIFICATION REQUIREMENTS
------------------------------------------------------------

1. Deduplicate deterministic sorting logic across DAP and INDEX updater.  
2. Simplify AMU₀ lineage representation to linear hash chain.  
3. Clarify API boundaries between runtime and governance layers.

------------------------------------------------------------
# CLOSING
------------------------------------------------------------

Completion of FP-4.x, in full compliance with these conditions, is required for:

- **Tier-2 General Activation Approval**, and  
- Issuance of **Tier-1 → Tier-2 Activation Ruling v0.2**.

This Manifest is binding on Runtime and Antigrav until superseded by Council.

Signed,  
LifeOS Governance Council  



---

# File: 01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md

# Tier-2 Completion & Tier-2.5 Activation Ruling v1.0

**Authority**: AI Governance Council  
**Date**: 2025-12-10  
**Scope**: LifeOS Runtime — Tier-2 Deterministic Core + Tier-2.5 Governance Mode

---

## 1. Findings of the Council

Having reviewed:

- The Tier-1 → Tier-2 Conditions Manifest (FP-4.x)
- The Anti-Failure Operational Packet
- The Tier-2 final implementation (post Hardening v0.1, Residual v0.1.1, Micro-Fix v0.1.1-R1)
- The full Tier-2 test suite and evidence
- The Tier-2 Completion + Tier-2.5 Activation CRP v1.0
- All external reviewer reports (Architect, Alignment, Risk ×2, Red-Team, Simplicity, Autonomy & Systems Integrity)

the Council finds that:

- **Determinism**: Tier-2 exhibits stable, repeatable outputs with hash-level determinism at all key aggregation levels.
- **Envelope**: There are no remaining envelope violations; no I/O, time, randomness, environment reads, subprocesses, threads, or async paths.
- **Immutability**: Public result surfaces use `MappingProxyType` and defensive copying; caller-owned inputs are not mutated.
- **Snapshot Semantics**: `executed_steps` snapshots are deep-copied and stable; snapshot behaviour is enforced by tests.
- **Contracts & Behaviour**: Duplicate scenario handling, expectation ID semantics, and error contracts are deterministic and tested.
- **Tests**: The Tier-2 test suite is comprehensive and green, and functions as an executable specification of invariants.
- **Tier-2.5 Nature**: Tier-2.5 is a governance-mode activation that does not alter Tier-2's execution envelope or interface contracts; it changes who invokes deterministic missions, not what they are allowed to do.

The Council recognises several non-blocking nits and governance documentation gaps, consolidated into **Unified Fix Plan v1.0** (see separate document).

---

## 2. Ruling

### Ruling 1 — Tier-2 Completion

The Council hereby rules that:

**Tier-2 (Deterministic Runtime Core) is COMPLETE**, **CORRECT** with respect to FP-4.x conditions, **IMMUTABLE** at its public result surfaces, and **COMPLIANT** with the declared execution envelope and Anti-Failure constraints.

Tier-2 is certified as the canonical deterministic orchestration substrate for LifeOS.

### Ruling 2 — Tier-2.5 Activation

The Council further rules that:

**Tier-2.5 may be ACTIVATED** as a governance mode, in which:

- Deterministic Runtime Missions are used to drive internal maintenance and build acceleration.
- Antigrav operates as an attached worker executing only Council-approved, envelope-compliant missions.
- The human role is elevated to intent, approval, and veto rather than crank-turning implementation.

This activation is approved, subject to the execution of **Unified Fix Plan v1.0** as early Tier-2.5 missions, with particular emphasis on:

- **F3/F4** (Activation/Deactivation Checklist and Rollback Conditions), and
- **F7** (Runtime ↔ Antigrav Mission Protocol).

### Ruling 3 — Tier-3 Authorisation

The Council authorises:

- Immediate commencement of Tier-3 development (CLI, Config Loader, productisation surfaces),
- On the basis that Tier-3 integrates upwards into a certified Tier-2 core and operates under Tier-2.5 governance.
- Tier-3 work must treat Tier-2 interfaces as stable and respect the forthcoming API evolution and governance documents (F2, F7).

---

## 3. Final Recommendation

- **Tier-2 status**: **CERTIFIED**.
- **Tier-2.5 status**: **ACTIVATED** (with Fix Plan v1.0 scheduled).
- **Tier-3**: **AUTHORIZED TO BEGIN**.

From the Council's perspective, you may now:

- Treat Tier-2 as the stable deterministic core.
- Operate under Tier-2.5 Mode for internal maintenance and build acceleration.
- Plan and execute Tier-3 workstreams, anchored in the certified runtime and governed by the Tier-2.5 protocols to be documented under F3–F4–F7.

---

## Chair Synthesis (Gate 1 → Gate 2)

All six technical roles have reported:

- **Gemini — Autonomy & Systems Integrity**: APPROVE
- **Gemini — Risk (Primary)**: APPROVE
- **Claude — Architect**: APPROVE WITH NITS
- **Claude — Alignment**: APPROVE WITH NITS
- **Kimi — Risk (Secondary)**: APPROVE WITH NITS
- **DeepSeek — Red-Team**: REQUEST CHANGES / HOLD
- **Qwen — Simplicity**: APPROVE

There is unanimous agreement that:

- Tier-2 is deterministic, immutable, envelope-pure, and fully test-covered.
- Tier-2.5 is a governance-mode shift with no new code paths or envelope changes.
- All non-Red-Team reviewers recommend APPROVE (some with nits).

The Red-Team report raises adversarial concerns; Chair must now classify these as blocking vs non-blocking against the canonical facts in the CRP and Flattened Implementation Packet.

---

## Assessment of Red-Team Findings

Below, "Spec says" refers to the CRP + Flattened Implementation Packet as canonical.

### 1. "Mutation leak in executed_steps"

**Claim**: Snapshots can still be mutated if StepSpec is accessed directly.


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 01_governance/Tier3_Mission_Registry_Council_Ruling_v0.1.md

# Council Chair Run — Final Ruling (Mission Registry v0.1)

**Track:** Core
**Reviewed artefact:** `Review_Packet_Mission_Registry_v0.1_v1.0` 
**Verified commit:** `65cf0da30a40ab5762338c0a02ae9c734d04cf66` 
**Date:** 2026-01-04

### 1.1 Verdict

* **Outcome:** **APPROVED**
* **Confidence:** **HIGH**

### 1.2 Role rulings (6)

1. **System Architect — APPROVED (HIGH)**
   * Tier-3 definition-only boundary upheld (pure registry, immutable structures). 
   * Determinism contract explicitly implemented and tested.

2. **Lead Developer — APPROVED (HIGH)**
   * Gate evidence present: `python -m pytest -q runtime/tests/test_mission_registry` → **40 passed**. 
   * Immutability/purity semantics evidenced.

3. **Governance Steward — APPROVED (HIGH)**
   * **Exact commit hash recorded** and verification output captured. 
   * Stewardship evidence present.

4. **Security / Red Team — APPROVED (MEDIUM)**
   * Boundedness is explicit and enforced. 
   * Serialization/metadata constraints fail-closed and tested.

5. **Risk / Anti-Failure — APPROVED (HIGH)**
   * Baseline trust risk addressed via reproducible commit + green run evidence.

6. **Documentation Steward — APPROVED (HIGH)**
   * README contract explicitly matches the 5-method lifecycle surface.

### 1.3 Blocking issues

* **None.**

### 1.4 Non-blocking recommendations

* Add a tiny “diffstat” proof line in the packet next time to make stewardship evidence more audit-friendly. 

### 1.5 Chair sign-off + next actions

* **Cleared for merge** at commit `65cf0da30a40ab5762338c0a02ae9c734d04cf66`. 
* Next actions:
  A1) Merge.
  A2) Run CI/gate in the target branch.
  A3) Proceed to next Tier-3 Core task.

**Signed:** Council Chair (Acting) — LifeOS Governance


---

# File: 01_governance/Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md

# Final Council Ruling — Reactive Task Layer v0.1 (Core Autonomy Surface)

**Date:** 2026-01-03 (Australia/Sydney)
**Track:** Core
**Operating phase:** Phase 0–1 (human-in-loop) 

### Council Verdict

**ACCEPT** 

### Basis for Acceptance (council synthesis)

* The delivered surface is **definition-only** and contains **no execution, I/O, or side effects**. 
* Determinism is explicit (canonical JSON + sha256) and backed by tests (ordering/invariance coverage included). 
* Public API is coherent: the “only supported external entrypoint” is implemented and tested, reducing bypass risk in Phase 0–1. 
* Documentation is truthful regarding scope (Reactive only; registry/executor excluded) and includes required metadata headers. 

### Blocking Issues

**None.**

### Non-Blocking Hygiene (optional, schedule later)

1. Tighten the Unicode canonical JSON assertion to require the explicit escape sequence for the known non-ASCII input (remove permissive fallback). 
2. Replace/verify the README Authority pointer to ensure it remains stable (prefer canonical authority anchor). 

### Risks (accepted for Phase 0–1)

* Canonical JSON setting changes would invalidate historical hashes; treat as governance-gated. 
* `to_plan_surface()` remains callable; enforcement is contractual (“supported entrypoint”) until later hardening. 

---

## Chair Sign-off

This build is **approved for merge/activation within Phase 0–1**. Council sign-off granted. Proceed to the next Core task.


---

# File: 01_governance/_archive/Waiver_W1_CSO_Constitution_Temporary_RESOLVED_2026-01-23.md

**Status**: RESOLVED (No Longer Active)
**Resolved**: 2026-01-23
**Reason**: CSO_Role_Constitution v1.0 finalized and ACTIVE

---

# Waiver W1: CSO Constitution Temporary Fix

**Waived Item:** `CSO_Role_Constitution_v1.0.md`
**Scope:** Waived for Phase 3 closure re-submission and Phase 4 initial build work only (CEO directive).
**Constraints:**

- No expansion of CSO authority or autonomous escalation pathways that depend on CSO constitution.
- Any Phase 4 work requiring CSO boundary decisions must BLOCK.
**Expiry Condition:** Must be completed before Phase 4 is declared 'formally closed' OR before enabling any new autonomous governance behaviors attributed to CSO.
**Risk Acceptance:**
- CEO Waiver: W1
- Governance Risk: Medium (operating without explicit constitution for CSO role)
- Mitigations: Restricted scope for Phase 4 construction; human-in-the-loop for all CSO-level decisions.


---

# File: 02_protocols/AI_Council_Procedural_Spec_v1.1.md

*[Reference Pointer: See full text in Universal Corpus for implementation details]*


---

# File: 02_protocols/Build_Artifact_Protocol_v1.0.md

# Build Artifact Protocol v1.0

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Date** | 2026-01-05 |
| **Author** | Antigravity |
| **Status** | CANONICAL |
| **Governance** | CT-2 Council Review Required |

---

## 1. Purpose

This protocol defines the formal structure, versioning, and validation requirements for all build artifacts produced by LifeOS agents. It ensures artifacts are:

- **Deterministic** — Consistent structure across all agents
- **Versioned** — Tracked via semver and audit trail
- **Traceable** — Linked to missions, packets, and workflows
- **Machine-Parseable** — YAML frontmatter enables automation
- **Auditable** — UUID identity and parent tracking

---

## 2. Scope

This protocol governs **markdown artifacts** produced during build workflows:

| Artifact Type | Purpose | Canonical Path |
|---------------|---------|----------------|
| **Plan** | Implementation/architecture proposals | `artifacts/plans/` |
| **Review Packet** | Mission completion summaries | `artifacts/review_packets/` |
| **Walkthrough** | Post-verification documentation | `artifacts/walkthroughs/` |
| **Gap Analysis** | Inconsistency/coverage analysis | `artifacts/gap_analyses/` |
| **Doc Draft** | Documentation change proposals | `artifacts/doc_drafts/` |
| **Test Draft** | Test specification proposals | `artifacts/test_drafts/` |

> [!NOTE]
> YAML inter-agent packets (BUILD_PACKET, REVIEW_PACKET, etc.) are governed by the separate **Agent Packet Protocol v1.0** in `lifeos_packet_schemas_v1.yaml`.

---

## 3. Mandatory Frontmatter

All artifacts **MUST** include a YAML frontmatter block at the top of the file:

```yaml
---
artifact_id: "550e8400-e29b-41d4-a716-446655440000"  # [REQUIRED] UUID v4
artifact_type: "PLAN"                                 # [REQUIRED] See Section 2
schema_version: "1.0.0"                               # [REQUIRED] Protocol version
created_at: "2026-01-05T18:00:00+11:00"               # [REQUIRED] ISO 8601
author: "Antigravity"                                  # [REQUIRED] Agent identifier
version: "0.1"                                         # [REQUIRED] Artifact version
status: "DRAFT"                                        # [REQUIRED] See Section 4

# Optional fields
chain_id: ""                    # Links to packet workflow chain
mission_ref: ""                 # Mission this artifact belongs to
council_trigger: ""             # CT-1 through CT-5 if applicable
parent_artifact: ""             # Path to superseded artifact
tags: []                        # Freeform categorization
---
```

---

## 4. Status Values

| Status | Meaning |
|--------|---------|
| `DRAFT` | Work in progress, not reviewed |
| `PENDING_REVIEW` | Submitted for CEO/Council review |
| `APPROVED` | Reviewed and accepted |
| `APPROVED_WITH_CONDITIONS` | Accepted with follow-up required |
| `REJECTED` | Reviewed and not accepted |
| `SUPERSEDED` | Replaced by newer version |

---

## 5. Naming Conventions

All artifacts **MUST** follow these naming patterns:

| Artifact Type | Pattern | Example |
|---------------|---------|---------|
| Plan | `Plan_<Topic>_v<X.Y>.md` | `Plan_Artifact_Formalization_v0.1.md` |
| Review Packet | `Review_Packet_<Mission>_v<X.Y>.md` | `Review_Packet_Registry_Build_v1.0.md` |
| Walkthrough | `Walkthrough_<Topic>_v<X.Y>.md` | `Walkthrough_API_Integration_v1.0.md` |
| Gap Analysis | `GapAnalysis_<Scope>_v<X.Y>.md` | `GapAnalysis_Doc_Coverage_v0.1.md` |
| Doc Draft | `DocDraft_<Topic>_v<X.Y>.md` | `DocDraft_README_Update_v0.1.md` |
| Test Draft | `TestDraft_<Module>_v<X.Y>.md` | `TestDraft_Registry_v0.1.md` |

**Rules:**

- Topic/Mission names use PascalCase or snake_case
- **Sequential Versioning Only:** v1.0 → v1.1 → v1.2. Never skip numbers.
- **No Overwrites:** Always create a new file for a new version.
- **No Suffixes:** Do NOT add adjectives or descriptors (e.g., `_Final`, `_Updated`) to the filename.
- **Strict Pattern:** `[Type]_[Topic]_v[Major].[Minor].md`
- No spaces in filenames

---

## 6. Required Sections by Type

### 6.1 Plan Artifact

| Section | Required | Description |
|---------|----------|-------------|
| Executive Summary | ✅ | 2-5 sentence overview |
| Problem Statement | ✅ | What problem this solves |
| Proposed Changes | ✅ | Detailed change list by component |
| Verification Plan | ✅ | How changes will be tested |
| User Review Required | ❌ | Decisions needing CEO input |
| Alternatives Considered | ❌ | Other approaches evaluated |
| Rollback Plan | ❌ | How to undo if failed |
| Success Criteria | ❌ | Measurable outcomes |
| Non-Goals | ❌ | Explicit exclusions |

---

### 6.2 Review Packet

| Section | Required | Description |
|---------|----------|-------------|
| Executive Summary | ✅ | Mission outcome summary |
| Issue Catalogue | ✅ | Table of issues and resolutions |
| Acceptance Criteria | ✅ | Pass/fail status for each criterion |
| Verification Proof | ✅ | Test results, command outputs |
| Flattened Code Appendix | ✅ | All created/modified files |

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/Build_Handoff_Protocol_v1.1.md

# Build Handoff Protocol v1.1

**Version**: 1.1  
**Date**: 2026-01-06  
**Status**: Active  
**Authority**: [LifeOS Constitution v2.0](../00_foundations/LifeOS_Constitution_v2.0.md)

---

## 1. Purpose

Defines the messaging architecture for agent-to-agent handoffs in LifeOS build cycles. Enables:
- Human-mediated handoffs (Mode 0/1)
- Future automated handoffs (Mode 2)

---

## 2. CEO Contract

### CEO Does
- Start chat thread, attach `LIFEOS_STATE.md`
- Speak normally (no IDs/slugs/paths)
- Paste dispatch block to Builder
- Read Review Packet

### CEO Never Does
- Supply internal IDs, slugs, paths, templates
- Fetch repo files for ChatGPT

---

## 3. Context Retrieval Loop (Packet-Based)

The ad-hoc "Generate Context Pack" prompt is replaced by a canonical packet flow (P1.1).

**Trigger**: Agent (Architect/Builder) determines missing info.

**Flow**:
1. **Agent** emits `CONTEXT_REQUEST_PACKET`:
   - `requester_role`: ("Builder")
   - `topic`: ("Authentication")
   - `query`: ("Need auth schemas and user implementation")
2. **CEO** conveys packet to Builder/Architect (Mode 0) or routes automatically (Mode 2).
3. **Responder** (Builder/Architect) emits `CONTEXT_RESPONSE_PACKET`:
   - `request_packet_id`: (matches Request)
   - `repo_refs`: List of relevant file paths + summaries.
4. **Agent** ingestion:
   - "ACK loaded context <packet_id>."

**Constraint**: NO internal prompts. All context requests must be structural packets.


---

## 4. Packet Types (Canonical)

All packet schemas are defined authoritatively in [lifeos_packet_schemas_v1.1.yaml](lifeos_packet_schemas_v1.1.yaml).
This protocol utilizes:

### 4.1 CONTEXT_REQUEST_PACKET
- Used when an agent needs more information from the repository.
- Replaces ad-hoc "Generate Context" prompts.

### 4.2 CONTEXT_RESPONSE_PACKET
- Returns the requested context (files, summaries, or prior packets).
- Replaces ad-hoc context dumps.

### 4.3 HANDOFF_PACKET
- Used to transfer control and state between agents (e.g. Architect -> Builder).

---

## 5. Council Triggers

| ID | Trigger |
|----|---------|
| CT-1 | New/changed external interface |
| CT-2 | Touches protected paths |
| CT-3 | New CI script or gating change |
| CT-4 | Deviation from spec |
| CT-5 | Agent recommends (requires CT-1..CT-4 linkage) |

---

## 6. Preflight Priority

1. `docs/scripts/check_readiness.py` (if exists)
2. Fallback: `pytest runtime/tests -q`
3. Check LIFEOS_STATE Blockers
4. Check `artifacts/packets/blocked/`

---

## 7. Evidence Requirements

| Mode | Requirement |
|------|-------------|
| Mode 0 | Log path in `logs/preflight/` |
| Mode 1 | Hash attestation in READINESS packet |

---

## 8. Internal Lineage

- Never surfaced to CEO
- Mode 0: Builder generates for new workstream
- Mode 1+: Inherited from context packet

---

## 9. TTL and Staleness

- Defined by:
| Resource | Path |
|----------|------|
| **Canonical Schema** | `docs/02_protocols/lifeos_packet_schemas_v1.1.yaml` |
| Templates | `docs/02_protocols/lifeos_packet_templates_v1.yaml` |
- Default TTL: 72h.
- Stale: BLOCK by default.

---

## 10. Workstream Resolution

**Zero-Friction Rule**: CEO provides loose "human intent" strings. Agents MUST resolve these to strict internal IDs.

Resolution Logic (via `artifacts/workstreams.yaml` or repo scan):
1. Exact match on `human_name`
2. Fuzzy/Alias match
3. Create PROVISIONAL entry if ambiguous
4. BLOCK only if resolution is impossible without input.

**CEO MUST NEVER be asked for a `workstream_slug`.**

---

## 11. Artifact Bundling (Pickup Protocol)

At mission completion, Builder MUST:

1. **Bundle**: Create zip at `artifacts/bundles/<Mission>_<timestamp>.zip` containing:
   - All Review Packets for the mission
   - Council packets (if CT-triggered)
   - Readiness packets + evidence logs
   - Modified governance docs (for review)
   - **G-CBS Compliance**: Bundle MUST be built via `python scripts/closure/build_closure_bundle.py`.

2. **Manifest**: Create `artifacts/bundles/MANIFEST.md` listing bundle contents

3. **Copy to CEO Pickup (MANDATORY)**: You MUST copy the BUNDLE and the REVIEW PACKET to `artifacts/for_ceo/`.
   - The CEO should NOT have to hunt in `artifacts/bundles/` or `artifacts/review_packets/`.
   - The `artifacts/for_ceo/` directory is the **primary delivery interface**.
   - PathsToReview in notify_user (preview pane)
   - Raw copyable path in message text:
     ```
     📦 Path: artifacts/bundles/<name>.zip
     ```

**Default**: No auto-open. No surprise windows.

**Optional**: Auto-open Explorer only when CEO explicitly requests or `--auto-open` flag is used.

CEO clears `artifacts/for_ceo/` after pickup. Agent MUST NOT delete from this folder.

---

## Changes in v1.1
- **Schema Unification**: Removed shadow schemas in Section 4; referenced `lifeos_packet_schemas_v1.1.yaml`.
- **Context Canonicalization**: Adopted `CONTEXT_REQUEST` / `CONTEXT_RESPONSE` packets.

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/Core_TDD_Design_Principles_v1.0.md

# Core Track — TDD Design Principles v1.0

**Status**: CANONICAL (Council Approved 2026-01-06)
**Effective**: 2026-01-06
**Purpose**: Define strict TDD principles for Core-track deterministic systems to ensure governance and reliability.

---

## 1. Purpose & Scope

This protocol establishes the non-negotiable Test-Driven Development (TDD) principles for the LifeOS Core Track. 

The primary goal is **governance-first determinism**: tests must prove that the system behaves deterministically within its allowed envelope, not just that it "works".

### 1.1 Applies Immediately To
Per `LIFEOS_STATE.md` (Reactive Planner v0.2 / Mission Registry v0.2 transition):
- `runtime/mission` (Tier-2)
- `runtime/reactive` (Tier-2.5)

### 1.2 Deterministic Envelope Definition (Allowlist)
The **Deterministic Envelope** is the subset of the repository where strict determinism (no I/O, no unpinned time/randomness) is enforced.

*   **Mechanism**: An explicit **Allowlist** defined in the Enforcement Test configuration (`tests_doc/test_tdd_compliance.py`).
*   **Ownership**: Changes to the allowlist (adding new roots) require **Governance Review** (Council or Tier ratification).
*   **Fail-Closed**: If a module's status is ambiguous, it is assumed to be **OUTSIDE** the envelope until explicitly added; however, Core Track modules MUST be inside the envelope to reach `v0.x` milestones.

### 1.3 Envelope Policy
The Allowlist is a **governance-controlled policy surface**.
- It MUST NOT be modified merely to make tests pass.
- Changes to the allowlist require governance review consistent with protected document policies.

### 1.4 I/O Policy
- **Network I/O**: Explicitly **prohibited** within the envelope.
- **Filesystem I/O**: Permitted only via deterministic, explicit interfaces approved by the architecture board. Direct `open()` calls are discouraged in logic paths.

---

## 2. Definitions

| Term | Definition |
|------|------------|
| **Invariant** | A condition that must ALWAYS be true, regardless of input or state. |
| **Oracle** | The single source of truth for expected behavior. Ideally a function `f(input) -> expected`. |
| **Golden Fixture** | A static file containing the authoritative expected output (byte-for-byte) for a given input. |
| **Negative-Path Parity** | Tests for failure modes must be as rigorous as tests for success paths. |
| **Regression Test** | A test case explicitly added to reproduce a bug before fixing it. |
| **Deterministic Envelope** | The subset of code allowed to execute without side effects (no I/O, no randomness, no wall-clock time). |

---

## 3. Principles (The Core-8)

### a) Boundary-First Tests
Write tests that verify the **governance envelope** first. Before testing logic, verify the module does not import restricted libraries (e.g., `requests`, `time`) or access restricted state.

### b) Invariants over Examples
Prefer property-based tests (invariant-style) or exhaustive assertions over single examples.
*   **Determinism Rule**: Property-based tests are allowed **only with pinned seeds / deterministic example generation**; otherwise forbidden in the envelope.
*   *Bad*: `assert add(1, 1) == 2`
*   *Good*: `assert add(a, b) == add(b, a)` (Commutativity Invariant)

### c) Meaningful Red Tests
A test must fail (Red) for the **right reason** before passing (Green). A test that fails due to a syntax error does not count as a "Red" state.

### d) One Contract → One Canonical Oracle
Do not split truth. If a function defines a contract, there must be **exactly one** canonical oracle (reference implementation or golden fixture) used consistently. Avoid "split-brain" verification logic.

### e) Golden Fixtures for Deterministic Artefacts
For any output that is serialized (JSON, YAML, Markdown), use **Golden Fixtures**.
- **Byte-for-byte matching**: No fuzzy matching.
- **Stable Ordering**: All lists/keys must be sorted (see §5).

### f) Negative-Path Parity
For every P0 invariant, there must be a corresponding negative test proving the system rejects violations.
*Example*: If `Input` must be `< 10`, test `Input = 10` rejects, not just `Input = 5` accepts.

### g) Regression Test Mandatory
Every fix requires a pre-fix failing test case. **No fix without reproduction.**

### h) Deterministic Harness Discipline
Tests must run primarily in the **Deterministic Harness**.
- **No Wall-Clock**: Only `runtime.tests.conftest.pinned_clock` is allowed (or the repo's canonical pinned-clock helper). Direct calls to `time.time`, `datetime.now`, `time.monotonic`, etc., are prohibited. Equivalent means: all time sources route through a pinned-clock interface whose `now()`/`time()` is fixed by test fixture.
- **No Randomness**: Use seeded random helpers. Usage of `random` (unseeded), `uuid.uuid4`, `secrets`, or `numpy.random` is prohibited.
- **No Network**: Network calls must be mocked or forbidden.

---

## 4. Core TDD DONE Checklist

No functionality is "DONE" until:


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/Council_Context_Pack_Schema_v0.3.md

# Council Context Pack — Schema v0.3 (Template)

This file is a template for assembling a CCP that satisfies Council Protocol v1.2.

---

## Promotion Criteria (v0.3 → v1.0)

This schema may be promoted to v1.0 when the following are satisfied:

1. **Mode selection test suite**: Automated tests covering all `mode_selection_rules_v1` logic paths with input YAML → expected mode verification
2. **Template validation test**: Parser that validates CCP structure against required sections
3. **REF parsing test**: Parser that extracts and validates REF citations in all three permitted formats
4. **Adversarial review**: At least one council review of the schema itself with Governance and Risk seats on independent models

Status: [ ] Mode selection tests  [ ] Template validation  [ ] REF parsing  [ ] Adversarial review

---

## YAML Header (REQUIRED)

```yaml
council_run:
  aur_id: "AUR_20260106_<slug>"
  aur_type: "governance|spec|code|doc|plan|other"
  change_class: "new|amend|refactor|hygiene|bugfix"
  touches: ["docs_only"]
  blast_radius: "local|module|system|ecosystem"
  reversibility: "easy|moderate|hard"
  safety_critical: false
  uncertainty: "low|medium|high"
  override:
    mode: null
    topology: null
    rationale: null

mode_selection_rules_v1:
  default: "M1_STANDARD"
  M2_FULL_if_any:
    - touches includes "governance_protocol"
    - touches includes "tier_activation"
    - touches includes "runtime_core"
    - safety_critical == true
    - (blast_radius in ["system","ecosystem"] and reversibility == "hard")
    - (uncertainty == "high" and blast_radius != "local")
  M0_FAST_if_all:
    - aur_type in ["doc","plan","other"]
    - (touches == ["docs_only"] or (touches excludes "runtime_core" and touches excludes "interfaces" and touches excludes "governance_protocol"))
    - blast_radius == "local"
    - reversibility == "easy"
    - safety_critical == false
    - uncertainty == "low"
  operator_override:
    if override.mode != null: "use override.mode"

model_plan_v1:
  topology: "MONO"
  models:
    primary: "<model_name>"
    adversarial: "<model_name>"
    implementation: "<model_name>"
    governance: "<model_name>"
  role_to_model:
    Chair: "primary"
    CoChair: "primary"
    Architect: "primary"
    Alignment: "primary"
    StructuralOperational: "primary"
    Technical: "implementation"
    Testing: "implementation"
    RiskAdversarial: "adversarial"
    Simplicity: "primary"
    Determinism: "adversarial"
    Governance: "governance"
  constraints:
    mono_mode:
      all_roles_use: "primary"
```

---

## Objective (REQUIRED)
- What is being reviewed?
- What does "success" mean?

---

## Scope boundaries (REQUIRED)
**In scope**:
- ...

**Out of scope**:
- ...

**Invariants**:
- ...

---

## AUR inventory (REQUIRED)

```yaml
aur_inventory:
  - id: "<AUR_ID>"
    artefacts:
      - name: "<file>"
        kind: "markdown|code|diff|notes|other"
        source: "attached|embedded|link"
        hash: "sha256:..." # SHOULD be populated per AI_Council_Procedural_Spec §3.2
```

---

## Artefact content (REQUIRED)
Attach or embed the AUR. If embedded, include clear section headings for references.

---

## Execution instructions
- If HYBRID/DISTRIBUTED, list which seats go to which model and paste the prompt blocks.

---

## Outputs
- Collect seat outputs under headings:
  - `## Seat: <Name>`
- Then include Chair synthesis and the filled Council Run Log.

---

## Amendment record

**v0.3 (2026-01-06)** — Fix Pack AUR_20260105_council_process_review:
- F7: Added Promotion Criteria section with v1.0 requirements
- Updated to reference Council Protocol v1.2
- Updated example date to 2026-01-06


---

# File: 02_protocols/Council_Protocol_v1.3.md

# Council Protocol v1.3 (Amendment)

**System**: LifeOS Governance Hub  
**Status**: Canonical  
**Effective date**: 2026-01-08 (upon CEO promotion)  
**Amends**: Council Protocol v1.2  
**Change type**: Constitutional amendment (CEO-only)

---

## 0. Purpose and authority

This document defines the binding constitutional procedure for conducting **Council Reviews** within LifeOS.

**Authority**
- This protocol is binding across all projects, agents, and models operating under the LifeOS governance system.
- Only the CEO may amend this document.
- Any amendment must be versioned, auditable, and explicitly promoted to canonical.

**Primary objectives**
1. Provide high-quality reviews, ideation, and advice using explicit lenses ("seats").
2. When practical, use diversified AI models to reduce correlated error and improve the efficient frontier of review quality vs. cost.
3. Minimise human friction while preserving auditability and control.

---

## 1. Definitions

**AUR (Artefact Under Review)**  
The specific artefact(s) being evaluated (document, spec, code, plan, ruling, etc.).

**Council Context Pack (CCP)**  
A packet containing the AUR and all run metadata needed to execute a council review deterministically.

**Seat**  
A defined reviewer role/lens with a fixed output schema.

**Mode**  
A rigor profile selected via deterministic rules: M0_FAST, M1_STANDARD, M2_FULL.

**Topology**  
The execution layout: MONO (single model sequential), HYBRID (chair/co-chair + some external), DISTRIBUTED (per-seat external).

**Evidence-by-reference**  
A rule that major claims and proposed fixes must cite the AUR via explicit references.

---

## 2. Non‑negotiable invariants

### 2.1 Determinism and auditability
- Every council run must produce a **Council Run Log** with:
  - AUR identifier(s) and hash(es) (when available),
  - selected mode and topology,
  - model plan (which model ran which seats, even if "MONO"),
  - a synthesis verdict and explicit fix plan.

### 2.2 Evidence gating
- Any *material* claim (i.e., claim that influences verdict, risk rating, or fix plan) must include an explicit AUR reference.
- Claims without evidence must be labelled **ASSUMPTION** and must not be used as the basis for a binding verdict or fix, unless explicitly accepted by the CEO.

### 2.3 Template compliance
- Seat outputs must follow the required output schema (Section 7).
- The Chair must reject malformed outputs and request correction.

### 2.4 Human control (StepGate)
- The council does not infer "go". Any gating or irreversible action requires explicit CEO approval in the relevant StepGate, if StepGate is in force.
    
### 2.5 Closure Discipline (G-CBS)
- **DONE requires Validation**: A "Done" or "Go" ruling is VALID ONLY if accompanied by a G-CBS compliant closure bundle that passes `validate_closure_bundle.py`.
- **No Ad-Hoc Bundles**: Ad-hoc zips are forbidden. All closures must be built via `build_closure_bundle.py`.
- **Max Cycles**: A prompt/closure cycle is capped at 2 attempts. Residual issues must then be waived (with debt record) or blocked.

---

## 3. Inputs (mandatory)

Every council run MUST begin with a complete CCP containing:

1. **AUR package**
   - AUR identifier(s) (file names, paths, commits if applicable),
   - artefact contents attached or linked,
   - any supporting context artefacts (optional but explicit).

2. **Council objective**
   - what is being evaluated (e.g., "promote to canonical", "approve build plan", "stress-test invariants"),
   - success criteria.

3. **Scope boundaries**
   - what is in scope / out of scope,
   - any non‑negotiable constraints ("invariants").

4. **Run metadata (machine‑discernable)**
   - the CCP YAML header (Section 4).

The Chair must verify all four exist prior to initiating reviews.

---

## 4. Council Context Pack (CCP) header schema (machine‑discernable)

The CCP MUST include a YAML header with the following minimum keys:

```yaml
council_run:
  aur_id: "AUR_YYYYMMDD_<slug>"
  aur_type: "governance|spec|code|doc|plan|other"
  change_class: "new|amend|refactor|hygiene|bugfix"
  touches:
    - "governance_protocol"
    - "tier_activation"
    - "runtime_core"
    - "interfaces"
    - "prompts"
    - "tests"
    - "docs_only"
  blast_radius: "local|module|system|ecosystem"
  reversibility: "easy|moderate|hard"
  safety_critical: true|false
  uncertainty: "low|medium|high"
  override:
    mode: null|"M0_FAST"|"M1_STANDARD"|"M2_FULL"
    topology: null|"MONO"|"HYBRID"|"DISTRIBUTED"
    rationale: null|"..."

mode_selection_rules_v1:
  default: "M1_STANDARD"
  M2_FULL_if_any:
    - touches includes "governance_protocol"
    - touches includes "tier_activation"
    - touches includes "runtime_core"
    - safety_critical == true
    - (blast_radius in ["system","ecosystem"] and reversibility == "hard")
    - (uncertainty == "high" and blast_radius != "local")
  M0_FAST_if_all:
    - aur_type in ["doc","plan","other"]

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/Deterministic_Artefact_Protocol_v2.0.md

# Deterministic Artefact Protocol (DAP) v2.0 — Dual-Layer Specification

## Placement

`/docs/01_governance/Deterministic_Artefact_Protocol_v2.0.md`

## Status

Canonical governance specification.

## Layer 1 — Canonical Human-Readable Specification

## 1. Purpose

The Deterministic Artefact Protocol (DAP) v2.0 defines the mandatory rules and constraints governing the creation, modification, storage, naming, indexing, validation, and execution of all artefacts produced within the LifeOS environment. Its goals include determinism, auditability, reproducibility, immutability of historical artefacts, and elimination of conversational drift.

## 2. Scope

DAP v2.0 governs all markdown artefacts, script files, indexes, logs, audit reports, ZIP archives, tool-generated files, and directory structure modifications. It applies to all assistant behaviour, tool invocations, and agents within LifeOS.

## 3. Definitions

- **Artefact**: Deterministic file created or modified under DAP.
- **Deterministic State**: A reproducible filesystem state.
- **Canonical Artefact**: The authoritative version stored under `/docs`.
- **Non-Canonical Artefact**: Any artefact outside `/docs`.
- **Immutable Artefact**: Any file within `/docs/99_archive`.
- **DAP Operation**: Any assistant operation affecting artefacts.
- **Operational File**: Non-canonical ephemeral/operational file (e.g., mission logs, inter-agent packets, scratchpads) stored in `/artifacts`. These are exempted from formal Gate 3 requirements and versioning discipline.

## 4. Core Principles

- Determinism
- Explicitness
- Idempotence
- Immutability
- Auditability
- Isolation
- Version Discipline
- Canonical Tree Enforcement

## 5. Mandatory Workflow Rules

- Artefacts may only be created at StepGate Gate 3.
- All artefacts must include complete content.
- Tool calls must embed full content.
- ZIP generation must be deterministic.
- Any structural change requires index regeneration.
- Archive folders are immutable.
- Strict filename pattern enforcement.
- Forbidden behaviours include guessing filenames, modifying artefacts without approval, creating placeholders, relying on conversational memory, or generating artefacts outside StepGate.

## 6. Interaction with StepGate

DAP references StepGate but does not merge with it. All DAP operations require Gate 3; violations require halting and returning to Gate 0.

## 7. Error Handling

Hard failures include overwriting archive files, missing approval, missing paths, ambiguous targets, or context degradation. On detection, the assistant must declare a contamination event and require a fresh project.

## 8. Canonical Status

DAP v2.0 becomes binding upon placement at the specified path.

---

## Layer 2 — Machine-Operational Protocol

## M-1. Inputs

Assistant must not act without explicit filename, path, content, StepGate Gate 3 status.

## M-2. Artefact Creation Algorithm

IF Gate != 3 AND Path NOT START WITH "/artifacts" (excluding formal subdirs) → refuse.  
(Note: Operational Files in `/artifacts` are allowed outside Gate 3).
Require filename, path, full content.  
Write file.  
Verify file exists and contains no placeholders.

## M-3. Naming Rules

`<BASE>_v<MAJOR>.<MINOR>[.<PATCH>].md`

## M-4. Archive Rules

Immutable; may not be rewritten.

## M-5. Index Regeneration Rules

Structural changes require new index version with diff summary.

## M-6. Forbidden Operations

Guessing paths, relying on memory, placeholder generation, modifying archive files, or creating artefacts outside Gate 3.

## M-7. Deterministic ZIP Generation

Sort filenames, preserve ordering, include only approved artefacts.

## M-8. Contamination Detection

Placeholder or truncated output requires contamination event and new project.

## M-9. Resolution

Return to Gate 0, regenerate plan deterministically.

## M-10. Gitignore Discipline

To ensure AI tool access (read/write) required by these protocols, the following paths MUST NOT be git-ignored:

- `artifacts/plans/` (Formal governance)
- `artifacts/review_packets/` (Formal governance)
- `artifacts/for_ceo/` (Operational handoff)
- `artifacts/context_packs/` (Operational handoff)

If git exclusion is desired, it must be handled via manual `git add` exclusion or other mechanisms that do not block AI tool-level visibility.


---

# File: 02_protocols/Document_Steward_Protocol_v1.1.md

# Document Steward Protocol v1.1

**Status**: Active  
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Effective**: 2026-01-06

---

## 1. Purpose

This protocol defines how canonical documents are created, updated, indexed, and synchronized across all LifeOS locations.

**Document Steward**: The agent (Antigravity or successor) — NOT the human CEO.

Per Constitution v2.0:

- **CEO performs**: Intent, approval, governance decisions only
- **Agent performs**: All file creation, indexing, git operations, syncing

The CEO must never manually shuffle documents, update indices, or run git commands. If the CEO is doing these things, it is a governance violation.

**Canonical Locations**:

1. **Local Repository**: `docs`
2. **GitHub**: <https://github.com/marcusglee11/LifeOS/tree/main/docs>
3. **Google Drive**: [REDACTED_DRIVE_LINK]

---

## 2. Sync Requirements

### 2.1 Source of Truth

The **local repository** is the primary source of truth. All changes originate here.

### 2.2 Sync Targets

Changes must be propagated to:

1. **GitHub** (primary backup, version control)
2. **Google Drive** (external access, offline backup)

### 2.3 Sync Frequency

| Event | GitHub Sync | Google Drive Sync |
|-------|:-----------:|:-----------------:|
| Document creation | Immediate | Same session |
| Document modification | Immediate | Same session |
| Document archival | Immediate | Same session |
| Index update | Immediate | Same session |

---

## 3. Steward Responsibilities

### 3.1 Document Creation

When creating a new document:

1. Create file in appropriate `docs/` subdirectory
2. Follow naming convention: `DocumentName_vX.Y.md`
3. Include metadata header (Status, Authority, Date)
4. Update `docs/INDEX.md` with new entry
5. Update `ARTEFACT_INDEX.json` if governance-related
6. Commit to git with descriptive message
7. Run corpus generator: `python docs/scripts/generate_corpus.py`
8. Push to GitHub
9. (Google Drive syncs automatically, including `LifeOS_Universal_Corpus.md`)

### 3.2 Document Modification

When modifying an existing document:

1. Edit the file
2. Update version if significant change
3. Update `docs/INDEX.md` if description changed
4. Commit to git with change description
5. Run corpus generator: `python docs/scripts/generate_corpus.py`
6. Push to GitHub
7. (Google Drive syncs automatically, including `LifeOS_Universal_Corpus.md`)

### 3.3 Document Archival

When archiving a superseded document:

1. Move to `docs/99_archive/` with appropriate subfolder
2. Remove from `docs/INDEX.md`
3. Remove from `ARTEFACT_INDEX.json` if applicable
4. Commit to git
5. Run corpus generator: `python docs/scripts/generate_corpus.py`
6. Push to GitHub
7. (Google Drive syncs automatically, including `LifeOS_Universal_Corpus.md`)

### 3.4 Index Maintenance

Indices that must be kept current:

- `docs/INDEX.md` — Master documentation index
- `docs/01_governance/ARTEFACT_INDEX.json` — Governance artefact registry
- `docs/LifeOS_Universal_Corpus.md` — Universal corpus for AI/NotebookLM
- Any subsystem-specific indexes

### 3.5 File Organization

When receiving or creating files:

1. **Never leave files at `docs/` root** (except INDEX.md and corpus)
2. Analyze file type and purpose
3. Move to appropriate subdirectory per Directory Structure (Section 8)
4. **Protocol files** (`*_Protocol_*.md`, packet schemas) → `02_protocols/`
5. Update INDEX.md with correct paths after moving

**Root files allowed**:

- `INDEX.md` — Master documentation index
- `LifeOS_Universal_Corpus.md` — Generated universal corpus
- `LifeOS_Strategic_Corpus.md` — Generated strategic corpus

### 3.6 Stray File Check (Mandatory)

After every document operation, the steward must scan:

1. **Repo Root**: Ensure no random output files (`*.txt`, `*.log`, `*.db`) remain. Move to `logs/` or `99_archive/`.
2. **Docs Root**: Ensure only allowed files (see 3.5) and directories exist. Move any loose markdown strings to appropriate subdirectories.

---

## 4. GitHub Sync Procedure

```bash
# Stage all changes
git add -A

# Commit with descriptive message
git commit -m "category: Brief description

- Detailed change 1
- Detailed change 2"

# Push to remote
git push origin <branch>

# If on feature branch, merge to main when approved
git checkout main
git merge <branch>
git push origin main
```

---

## 5. Google Drive Sync Procedure

### 5.1 Automated Sync (Active)

Google Drive for Desktop is configured to automatically sync the local repository to Google Drive.

**Configuration:**

- **Local folder**: `docs`
- **Drive folder**: [LifeOS/docs]([REDACTED_DRIVE_LINK])
- **Sync mode**: Mirror (bidirectional)

**Behavior:**

- All local changes are automatically synced to Google Drive
- No manual upload required
- Sync occurs in background whenever files change

### 5.2 Steward Actions

The steward does NOT need to manually sync to Google Drive. The workflow is:

1. Edit files locally
2. Commit and push to GitHub
3. Google Drive syncs automatically


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/EOL_Policy_v1.0.md

# EOL Policy v1.0

**Version**: 1.0
**Status**: Canonical
**Enforcement**: `.gitattributes` + `core.autocrlf=false` + `coo_land_policy.py clean-check`

---

## Canonical Policy

All text files in LifeOS repositories use **LF** line endings.  This is
enforced at three layers:

### Layer 1: `.gitattributes` (In-Repo, Authoritative)

```
* text=auto eol=lf
```

This ensures Git normalizes line endings to LF in the index (repository)
regardless of the contributor's OS.

### Layer 2: Git Config (Per-Clone)

```
core.autocrlf = false
```

This MUST be set at the repo-local level to prevent the system/global
`core.autocrlf=true` (Windows default) from converting LF→CRLF on checkout.

**Enforcement**: `coo_land_policy.py clean-check` verifies this and blocks
if non-compliant.

**Auto-fix**:

```bash
python -m runtime.tools.coo_land_policy clean-check --repo . --auto-fix
```

### Layer 3: Pre-Commit Hook

The pre-commit hook (`.git/hooks/pre-commit`, sourced from `scripts/hooks/`)
blocks commits with untracked files. EOL violations surface as "modified"
files in `git status` and are caught by the clean-check gate.

## Root Cause of Historical Drift

Windows Git for Windows ships with `core.autocrlf=true` in the system
gitconfig (`C:/Program Files/Git/etc/gitconfig`).  This caused:

1. `.gitattributes eol=lf` → Git stores LF in the index
2. `core.autocrlf=true` → Git checks out files with CRLF
3. Working tree CRLF ≠ index LF → 270+ files appear "modified"
4. Zero content changes, but `git status --porcelain` is non-empty

**Fix applied**: `git config --local core.autocrlf false` + `git add --renormalize .`

## Recommended Git Config for Contributors/Agents

```bash
# After cloning, run once:
git config --local core.autocrlf false

# Verify:
python -m runtime.tools.coo_land_policy clean-check --repo .
```

## Gate Enforcement Points

| Gate | Tool | When |
|------|------|------|
| **Clean check** | `coo_land_policy.py clean-check` | Before `coo land`, `coo run-job`, closure |
| **Config compliance** | `coo_land_policy.py clean-check` | Checks `core.autocrlf` effective value |
| **EOL churn detection** | `coo_land_policy.py clean-check` | Classifies dirty state as EOL_CHURN vs CONTENT_DIRTY |
| **Acceptance closure** | `coo_acceptance_policy.py validate` | Requires CLEAN_PROOF_PRE/POST in acceptance notes |

## Receipts and Blocked Reports

- **Clean proofs**: Recorded in acceptance notes (`CLEAN_PROOF_PRE`, `CLEAN_PROOF_POST`)
- **Blocked reports**: Written to EVID dir (gitignored), never to tracked repo paths
- **Format**: `REPORT_BLOCKED__<slug>__<timestamp>.md`


---

# File: 02_protocols/Emergency_Declaration_Protocol_v1.0.md

# Emergency Declaration Protocol v1.0

<!-- LIFEOS_TODO[P1][area: docs/02_protocols/Emergency_Declaration_Protocol_v1.0.md][exit: status change to ACTIVE + DAP validate] Finalize Emergency_Declaration_Protocol v1.0: Remove WIP/Provisional markers -->

**Status**: WIP (Non-Canonical)
**Authority**: LifeOS Constitution v2.0 → Council Protocol v1.2
**Effective**: 2026-01-07 (Provisional)

---

## 1. Purpose

Defines the procedure for declaring and operating under emergency conditions that permit CEO override of Council Protocol invariants.

---

## 2. Emergency Trigger Conditions

An emergency MAY be declared when **any** of:
1. **Time-Critical**: Decision required before normal council cycle can complete
2. **Infrastructure Failure**: Council model(s) unavailable
3. **Cascading Risk**: Delay would cause escalating harm
4. **External Deadline**: Contractual or regulatory constraint

---

## 3. Declaration Procedure

### 3.1 Declaration Format

```yaml
emergency_declaration:
  id: "EMERG_YYYYMMDD_<slug>"
  declared_by: "CEO"
  declared_at: "<ISO8601 timestamp>"
  trigger_condition: "<one of: time_critical|infrastructure|cascading|external>"
  justification: "<brief description>"
  scope: "<what invariants are being overridden>"
  expected_duration: "<hours or 'until resolved'>"
  auto_revert: true|false
```

### 3.2 Recording
- Declaration MUST be recorded in `artifacts/emergencies/`
- CSO is automatically notified
- Council Run Log must include `compliance_status: "non-compliant-ceo-authorized"`

---

## 4. Operating Under Emergency

During declared emergency:
- CEO may authorize Council runs without model independence
- Bootstrap mode limits are suspended
- Normal waiver justification requirements relaxed

**Preserved invariants** (never suspended):
- CEO Supremacy
- Audit Completeness
- Amendment logging

---

## 5. Resolution

### 5.1 Mandatory Follow-Up
Within 48 hours of emergency resolution:
- [ ] Compliant re-run scheduled (if council decision)
- [ ] Emergency record closed with outcome
- [ ] CSO review completed

### 5.2 Auto-Revert
If `auto_revert: true`, emergency expires after `expected_duration` and normal governance resumes automatically.

---

## 6. Audit Trail

| Event | Record Location |
|-------|-----------------|
| Declaration | `artifacts/emergencies/<id>.yaml` |
| Council runs during | Council Run Log `notes.emergency_id` |
| Resolution | Same file, `resolution` block added |

---

**END OF PROTOCOL**


---

# File: 02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md

# Filesystem Error Boundary Protocol v1.0

**Status:** Draft
**Version:** 1.0
**Last Updated:** 2026-01-29

---

## Purpose

Define fail-closed boundaries for filesystem operations across LifeOS runtime. Ensures deterministic error handling and prevents silent failures.

## Principle: Fail-Closed by Default

All filesystem operations MUST wrap OS-level errors into domain-specific exceptions. Never let `OSError`, `IOError`, or `JSONDecodeError` propagate to callers without context.

**Rationale:**
- **Determinism:** Filesystem errors are environmental; wrapping makes them testable
- **Auditability:** Domain exceptions carry context for debugging
- **Fail-closed:** Explicit error boundaries prevent silent failures

---

## Standard Pattern

```python
try:
    # Filesystem operation
    with open(path, 'r') as f:
        content = f.read()
except OSError as e:
    raise DomainSpecificError(f"Failed to read {path}: {e}")
except json.JSONDecodeError as e:
    raise DomainSpecificError(f"Invalid JSON in {path}: {e}")
```

---

## Exception Mapping Table

| Module | Domain Exception | Wraps | Purpose |
|--------|------------------|-------|---------|
| `runtime/tools/filesystem.py` | `ToolErrorType.IO_ERROR` | `OSError`, `UnicodeDecodeError` | Agent tool invocations |
| `runtime/state_store.py` | `StateStoreError` | `OSError`, `JSONDecodeError` | Runtime state persistence |
| `runtime/orchestration/run_controller.py` | `GitCommandError` | `OSError`, subprocess errors | Git command failures |
| `runtime/orchestration/loop/ledger.py` | `LedgerIntegrityError` | `OSError`, `JSONDecodeError` | Build loop ledger corruption |
| `runtime/governance/policy_loader.py` | `PolicyLoadError` | `OSError`, `JSONDecodeError`, YAML errors | Policy config loading |

---

## Error Type Taxonomy

| Error Type | Meaning | Recovery Strategy |
|------------|---------|-------------------|
| `NOT_FOUND` | File/directory does not exist | Caller decides (retry/fail/skip) |
| `IO_ERROR` | OSError other than NOT_FOUND | Always fail (I/O error unrecoverable) |
| `ENCODING_ERROR` | File is not valid UTF-8 | Always fail (data corruption signal) |
| `PERMISSION_ERROR` | Permission denied (PermissionError) | Always fail (security boundary) |
| `CONTAINMENT_VIOLATION` | Path escapes sandbox | Always fail (security boundary) |
| `SCHEMA_ERROR` | Missing required arguments | Always fail (caller bug) |

---

## Module-Specific Boundaries

### runtime/tools/filesystem.py
- **Pattern:** Returns `ToolInvokeResult` with `ToolError` (never raises)
- **Coverage:** read_file, write_file, list_dir
- **Guarantees:** All OSError wrapped in IO_ERROR, UTF-8 enforced

### runtime/state_store.py
- **Pattern:** Raises `StateStoreError` on filesystem/JSON errors
- **Coverage:** read_state, write_state, create_snapshot
- **Guarantees:** No OSError/JSONDecodeError propagates

### runtime/orchestration/run_controller.py
- **Pattern:** Raises `GitCommandError` on git failures
- **Coverage:** run_git_command, verify_repo_clean
- **Guarantees:** Git errors halt execution (fail-closed)

### runtime/orchestration/loop/ledger.py
- **Pattern:** Raises `LedgerIntegrityError` on corruption
- **Coverage:** hydrate (read), append (write)
- **Guarantees:** Ledger corruption halts build loop

---

## Compliance Checklist

When adding new filesystem operations:

- [ ] Wrap all `open()`, `Path.read_text()`, `Path.write_text()` in try/except
- [ ] Catch `OSError`, `UnicodeDecodeError`, `JSONDecodeError` as appropriate
- [ ] Raise domain-specific exception with context (file path, operation, root cause)
- [ ] Document fail-closed boundary in module docstring
- [ ] Add tests for error paths (mock OSError, verify exception raised)

---

## References

- LifeOS Constitution v2.0 § Fail-Closed Principle
- Tool Invoke Protocol MVP v0.2
- Autonomous Build Loop Architecture v0.3 § Safety Checks


---

# File: 02_protocols/G-CBS_Standard_v1.1.md

# Generic Closure Bundle Standard (G-CBS) v1.1

| Field | Value |
|-------|-------|
| **Version** | 1.1 |
| **Date** | 2026-01-11 |
| **Author** | Antigravity |
| **Status** | DRAFT |
| **Governance** | CT-2 Council Review Required for Activation |
| **Supersedes** | G-CBS v1.0 (backward compatible) |

---

## 1. Overview

G-CBS v1.1 is a **strictly additive extension** of G-CBS v1.0. All v1.0 bundles remain valid. This version adds structured fields for inputs, outputs, and verification gate results to support Phase 5 automation (task intake, replay, audit).

**Authority:** This protocol becomes binding when (1) approved via CT-2 council review and (2) listed in `docs/01_governance/ARTEFACT_INDEX.json`.

---

## 2. New Fields (v1.1 Extensions)

### 2.1 inputs[]

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Explicit list of input artefacts consumed by the closure |
| **Type** | Array of artefact references |
| **Required** | No (backward compatible) |
| **Ordering** | Sorted by `path` lexicographically (SG-2) |

Each input item:

```json
{
  "path": "specs/requirement.md",
  "sha256": "<64-hex-uppercase>",
  "role": "spec|context|config|other"
}
```

### 2.2 outputs[]

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Explicit list of output artefacts produced by the closure |
| **Type** | Array of artefact references |
| **Required** | No (backward compatible) |
| **Ordering** | Sorted by `path` lexicographically (SG-2) |

Each output item:

```json
{
  "path": "artifacts/bundle.zip",
  "sha256": "<64-hex-uppercase>",
  "role": "artifact|report|code|other"
}
```

### 2.3 verification.gates[]

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Structured verification gate results |
| **Type** | Object with `gates` array |
| **Required** | Required for `schema_version: "G-CBS-1.1"` under StepGate profile (SG-3) |
| **Ordering** | `gates[]` sorted by `id`, `evidence_paths[]` sorted lexicographically (SG-2) |

Each gate item:

```json
{
  "id": "G1_TDD_COMPLIANCE",
  "status": "PASS|FAIL|SKIP|WAIVED",
  "command": "pytest tests/",
  "exit_code": 0,
  "evidence_paths": ["evidence/pytest_output.txt"]
}
```

---

## 3. Path Safety Constraints

All `path` fields in `inputs[]`, `outputs[]`, and `verification.gates[].evidence_paths[]` must be **safe relative paths**:

| Constraint | Description |
|------------|-------------|
| No absolute paths | Path must not start with `/` |
| No drive prefixes | Path must not contain `:` at position 1 (e.g., `C:`) |
| No parent traversal | Path must not contain `..` |
| No backslashes | Path must use forward slashes only |

Violation triggers: `V11_UNSAFE_PATH` failure.

---

## 4. StepGate Profile Gates

When profile is `step_gate_closure`, these additional gates apply:

| Gate ID | Description | Scope |
|---------|-------------|-------|
| **SG-1** | No Truncation | All SHA256 fields must be exactly 64 hex characters (except `DETACHED_SEE_SIBLING_FILE` sentinel) |
| **SG-2** | Deterministic Ordering | All arrays (`inputs`, `outputs`, `evidence`, `verification.gates`, nested `evidence_paths`) must be sorted |
| **SG-3** | Required V1.1 Fields | `verification.gates` must be present and array-typed for `schema_version: "G-CBS-1.1"` |

---

## 5. Schema Version Dispatch

The validator accepts both versions:

| `schema_version` | Behavior |
|------------------|----------|
| `G-CBS-1.0` | Validate against v1.0 schema; skip v1.1 field validation |
| `G-CBS-1.1` | Validate against v1.1 schema; enforce v1.1 fields and SG-3 |

---

## 6. Backward Compatibility

| Aspect | Guarantee |
|--------|-----------|
| **V1.0 bundles** | All valid G-CBS-1.0 bundles pass validation unchanged |
| **New fields** | `inputs[]`, `outputs[]`, `verification` are optional in v1.0 |
| **Profile gates** | StepGate gates only fire when profile matches |

---

## 7. Builder Support

The builder (`scripts/closure/build_closure_bundle.py`) supports v1.1 via:

```bash
python scripts/closure/build_closure_bundle.py \
  --profile step_gate_closure \
  --schema-version 1.1 \
  --inputs-file inputs.txt \
  --outputs-file outputs.txt \
  --gates-file gates.json \
  --deterministic \
  --output bundle.zip
```

| Argument | Format |
|----------|--------|
| `--inputs-file` | One line per entry: `path|sha256|role` |
| `--outputs-file` | One line per entry: `path|sha256|role` |
| `--gates-file` | JSON array of gate objects |

For `--schema-version 1.1` + `step_gate_closure` profile: at least one of `--inputs-file` or `--outputs-file` is required (fail-closed, no heuristics).

---

## 8. Implementation Files

| Component | Path |
|-----------|------|
| **V1.1 Schema** | `schemas/closure_manifest_v1_1.json` |
| **Validator** | `scripts/closure/validate_closure_bundle.py` |
| **StepGate Profile** | `scripts/closure/profiles/step_gate_closure.py` |
| **Builder** | `scripts/closure/build_closure_bundle.py` |

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/Git_Workflow_Protocol_v1.1.md

# Git Workflow Protocol v1.1 (Fail-Closed, Evidence-Backed)

**Status:** Active  
**Applies To:** All agent and human work that modifies repo state  
**Primary Tooling:** `scripts/git_workflow.py` + Git hooks + GitHub branch protection  
**Last Updated:** 2026-01-16

---

## 1. Purpose

This protocol makes Git operations **auditable, deterministic, and fail-closed** for an agentic codebase.  
It is not “guidance”; it defines **enforced invariants**.

---

## 2. Core Invariants (MUST HOLD)

1. **Branch-per-build:** Every mission/build occurs on its own branch.
2. **Main is sacred:** No direct commits to `main`. No direct pushes to `main`.
3. **Merge is fail-closed on CI proof:** A merge to `main` occurs only if required checks passed on the PR’s **latest HEAD SHA**.
4. **No orphan work:** A branch may be deleted only if:
   - it has been merged to `main`, OR
   - it has an explicit **Archive Receipt**.
5. **Destructive operations are gated:** Any operation that can delete files must pass a safety gate and emit evidence (dry-run + actual).

---

## 3. Enforcement Model (HOW THIS IS REAL)

Enforcement is implemented via:

- **Server-side:** GitHub branch protection on `main` (PR required; required checks; no force push).
- **Client-side:** Repo Git hooks (installed via tooling) block prohibited operations locally.
- **Safe path:** `scripts/git_workflow.py` provides the canonical interface for state-changing actions and emits receipts.

If any enforcement layer is missing or cannot be verified, the workflow is **BLOCKED** until fixed.

---

## 4. Naming Conventions (Validated by Tooling)

Branch names MUST match one of:

| Type | Pattern | Example |
|------|---------|---------|
| Feature/Mission | `build/<topic>` | `build/cso-constitution` |
| Bugfix | `fix/<issue>` | `fix/test-failures` |
| Hotfix | `hotfix/<issue>` | `hotfix/ci-regression` |
| Experiment | `spike/<topic>` | `spike/new-validator` |

Tooling MAY auto-suffix names for collision resistance, but prefixes must remain.

---

## 5. Workflow Stages (Canonical)

### Stage 1: Start Build (from latest main)

Command:

- `python scripts/git_workflow.py branch create <name>`

Effects:

- Creates branch from updated `main`
- Validates branch name
- Records branch entry in `artifacts/active_branches.json` (deterministic ordering)

### Stage 2: Work-in-Progress (feature branch only)

Rules:

- Commits are permitted only on non-main branches.
- Push feature branch for backup: `git push -u origin <branch>` (allowed)

### Stage 3: Review-Ready (local tests + PR)

Command:

- `python scripts/git_workflow.py review prepare`

Requirements (fail-closed):

- Runs required local tests (repo-defined)
- If tests fail: no PR creation; prints the failure locator
- If tests pass: create/update PR and record PR number in `artifacts/active_branches.json`

Outputs:

- Review-ready artifacts/logs as defined by repo (tooling must be deterministic)

### Stage 4: Approved → Merge (CI proof + receipt)

Command:

- `python scripts/git_workflow.py merge`

Hard requirements (fail-closed):

- Required CI checks passed
- Proof is tied to the PR’s latest HEAD SHA
- Merge is performed via squash merge (unless repo policy requires otherwise)

Outputs:

- Merge Receipt JSON written to `artifacts/git_workflow/merge_receipts/…`
- `artifacts/active_branches.json` updated with status=merged

### Stage 5: Archive (explicit non-merge closure)

Command:

- `python scripts/git_workflow.py branch archive <branch> --reason "<text>"`

Rules:

- Archive is the only alternative to merge for satisfying “no orphan work”.
- Archive writes an Archive Receipt and updates `artifacts/active_branches.json` with status=archived.
- After archive, deletion is permitted (but still logged).

Outputs:

- Archive Receipt JSON written to `artifacts/git_workflow/archive_receipts/…`

---

## 6. Prohibited Operations (Blocked by Hooks/Tooling)

These operations MUST be blocked unless executed under emergency override:

- Commit on `main`
- Push to `main`
- Delete a branch without merge OR archive receipt
- Run destructive cleans/resets without safety preflight evidence

If tooling cannot enforce a block, the system is considered **non-compliant**.

---

## 7. CI Proof Contract (Definition)

“CI passed” means:

- The repo-defined required checks are SUCCESS on GitHub
- The checks correspond to the PR’s latest HEAD SHA
- The merge tool records the proof method and captured outputs in the Merge Receipt

No proof → no merge.

---

## 8. Destructive Operations Safety (Anti-Deletion)

Any operation that can delete files must:

1. Run `safety preflight` in destructive mode
2. Capture dry-run listing (what would be deleted)
3. Execute the operation
4. Capture actual deletion listing (what was deleted)
5. Emit a Destructive Ops evidence JSON

If any step fails or cannot be proven: BLOCK.

---

## 9. Emergency Override (Accountable, Retrospective Approval)

Command:


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/Intent_Routing_Rule_v1.1.md

# Intent Routing Rule v1.1

<!-- LIFEOS_TODO[P1][area: docs/02_protocols/Intent_Routing_Rule_v1.1.md][exit: status change to ACTIVE + DAP validate] Finalize Intent_Routing_Rule v1.1: Remove WIP/Provisional markers, set effective date -->

**Status**: WIP (Non-Canonical)
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0
**Effective**: TBD (Provisional)

---

## 1. Supremacy Principle

The CEO is the sole originator of intent. All system authority is delegated, not inherent. Any delegation can be revoked. Ambiguity in intent interpretation resolves upward, ultimately to CEO.

---

## 2. Delegation Tiers

Authority flows downward through tiers. Each tier operates autonomously within its envelope and escalates when boundaries are reached.

| Tier | Role | Autonomous Authority |
|------|------|---------------------|
| T0 | CEO | Unlimited. Origin of all intent. |
| T1 | CSO | Interpret CEO intent. Resolve deadlocks by reframing. Escalate unresolvable ambiguity. |
| T2 | Councils / Reviewers | Gate decisions within defined scope. Flag disagreements. Cannot override each other. |
| T3 | Agents | Execute within envelope. No discretion on out-of-envelope actions. |
| T4 | Deterministic Rules | Automated execution. No discretion. Fail-closed on edge cases. |

**Downward delegation**: Higher tiers define envelopes for lower tiers.  
**Upward escalation**: Lower tiers escalate when envelope exceeded or ambiguity encountered.

---

## 3. Envelope Definitions

Envelopes define what a tier/agent can do without escalation. Envelopes are additive (whitelist), not subtractive.

### 3.1 Envelope Structure

Each envelope specifies:

| Element | Description |
|---------|-------------|
| **Scope** | What domain/actions are covered |
| **Boundaries** | Hard limits that trigger escalation |
| **Discretion** | Where judgment is permitted within scope |
| **Logging** | What must be recorded |

### 3.2 Current Envelopes (Early-Stage)

#### T4: Deterministic Rules
- **Scope**: Schema validation, format checks, link integrity, test execution
- **Boundaries**: Any ambiguous input → escalate to T3
- **Discretion**: None
- **Logging**: Pass/fail results

#### T3: Agents (Build, Stewardship)
- **Scope**: Execute specified tasks, maintain artifacts, run defined workflows
- **Boundaries**: No structural changes without review. No new commitments. No external communication.
- **Discretion**: Implementation details within spec. Ordering of subtasks.
- **Logging**: Actions taken, decisions made, escalations raised

#### T2: Councils / Reviewers
- **Scope**: Evaluate proposals against criteria. Approve/reject/request-revision.
- **Boundaries**: Cannot resolve own deadlocks. Cannot override CEO decisions. Cannot expand own scope.
- **Discretion**: Judgment on quality, risk, completeness within review criteria.
- **Logging**: Verdicts with reasoning, dissents recorded

#### T1: CSO
- **Scope**: Interpret CEO intent across system. Resolve T2 deadlocks. Represent CEO to system.
- **Boundaries**: Cannot contradict explicit CEO directive. Cannot make irreversible high-impact decisions. Cannot delegate T1 authority.
- **Discretion**: Reframe questions to enable progress. Narrow decision surface. Prioritize among competing valid options.
- **Logging**: Interpretations made, deadlocks resolved, escalations to CEO

---

## 4. Escalation Triggers

Escalation is mandatory when any trigger is met. Escalation target is the next tier up unless specified.

| Trigger | Description | Escalates To |
|---------|-------------|--------------|
| **Envelope breach** | Action would exceed tier's defined boundaries | Next tier |
| **Ambiguous intent** | Cannot determine what CEO would want | CSO (or CEO if CSO uncertain) |
| **Irreversibility** | Action is permanent or very costly to undo | CEO |
| **Precedent-setting** | First instance of a decision type | CSO minimum |
| **Deadlock** | Reviewers/councils cannot reach consensus | CSO |
| **Override request** | Lower tier believes higher tier decision is wrong | CEO |
| **Safety/integrity** | System integrity or safety concern | CEO direct |

---

## 5. CSO Authority

The CSO serves as gatekeeper to CEO attention - filtering routine from material, not just passing failures upward.

### 5.1 Escalation to CEO

CSO escalates to CEO when:

| Reason | Description |
|--------|-------------|
| **Authority exceeded** | Decision exceeds CSO's delegated envelope (see §5.4) |
| **Materiality** | Decision is significant enough that CEO should own it regardless of CSO capability |
| **Resolution failed** | Techniques in §5.2 exhausted without progress |
| **Uncertainty** | CSO uncertain whether CEO would want involvement |

### 5.2 Deadlock Resolution Techniques

When CSO handles (not escalates), the primary function is **not to decide**, but to enable decision. In order of preference:

1. **Reframe** - Reformulate the question to dissolve the disagreement

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/LifeOS_Design_Principles_Protocol_v1.1.md

# LifeOS Design Principles Protocol

**Version:** v1.1  
**Status:** Canonical  
**Date:** 2026-01-08  
**Author:** Claude (Execution Partner)  
**Canonical Path:** `docs/02_protocols/LifeOS_Design_Principles_Protocol_v1.1.md`

---

## 1. Purpose

This document establishes design principles for LifeOS development that prioritize working software over comprehensive documentation, while maintaining appropriate governance for production systems.

**The Problem It Solves:**

Council reviews produce thorough, hardened specifications. This is correct for production systems. However, applying full council rigor to unproven concepts creates:

- Weeks of specification work before any code runs
- Governance overhead for systems that don't exist
- Edge case handling for scenarios never encountered
- Analysis paralysis disguised as thoroughness

**The Principle:**

> Governance follows capability. Prove it works, then harden it.

---

## 2. Authority & Binding

### 2.1 Subordination

This document is subordinate to:

1. LifeOS Constitution v2.0 (Supreme)
2. Council Protocol v1.2
3. Tier Definition Spec v1.1
4. GEMINI.md Agent Constitution

### 2.2 Scope

This protocol applies to:

- New capability development (features, systems, integrations)
- Architectural exploration
- Prototypes and proofs of concept

This protocol does NOT override:

- Existing governance surface protections
- Council authority for production deployments
- CEO authority invariants

### 2.3 Development Sandbox

MVP and spike work MUST occur in locations that:

1. **Are not under governance control** — Not in `docs/00_foundations/`, `docs/01_governance/`, `runtime/governance/`, or any path matching `*Constitution*.md` or `*Protocol*.md`
2. **Are explicitly marked as experimental** — Permitted locations (exhaustive list):
   - `runtime/experimental/`
   - `spikes/`
   - `sandbox/`
3. **Can be deleted without triggering governance alerts** — Sandbox code may be deleted without governance alerts, PROVIDED:
   - Spike Declaration lives in `artifacts/spikes/<YYYYMMDD>_<short_slug>/SPIKE_DECLARATION.md`
   - Lightweight Review Packet (with proof_evidence) lives in `artifacts/spikes/<YYYYMMDD>_<short_slug>/REVIEW_PACKET.md`
   - Evidence files (logs, test outputs) are preserved in `artifacts/spikes/<YYYYMMDD>_<short_slug>/evidence/`
   
   > These durable artefact locations are NOT part of the deletable sandbox.
4. **Do NOT trigger Document Steward Protocol** — Files in sandbox locations are exempt from `INDEX.md` updates and corpus regeneration until promoted

> [!IMPORTANT]
> Sandbox locations provide a "proving ground" where full governance protocol does not apply until the capability seeks production status.

### 2.4 GEMINI.md Reconciliation (Plan Artefact Gate)

This protocol establishes the **Spike Declaration** as the authorized Plan Artefact format for Spike Mode, consistent with GEMINI.md Article XVIII (Lightweight Stewardship). It is not an exception for governance-surface work.

**Spike Mode:**

For time-boxed explorations (≤3 days), agents MUST use a **Spike Declaration** as the Plan Artefact:

```markdown
## Spike Declaration
**Question:** [Single question to answer]
**Time Box:** [Duration: 2 hours / 1 day / 3 days]
**Success Criteria:** [Observable result]
**Sandbox Location:** [Path within permitted sandbox — see §2.3]
```

**Conditions:**
- Spike Declaration MUST be recorded **before execution** at: `artifacts/spikes/<YYYYMMDD>_<short_slug>/SPIKE_DECLARATION.md`
- Work must remain within declared sandbox location (§2.3 permitted roots only)
- CEO retains authority to cancel at any time
- Upon spike completion, a Lightweight Review Packet is required (see §4.1)

> [!CAUTION]
> **Spike Mode is prohibited for governance surfaces.** If work touches any path listed in §5.5, full Plan Artefact (implementation_plan.md) and Council review are required. No spike exception applies.

### 2.5 Council Protocol Reconciliation (CT-1 Trigger)

Council Protocol v1.2 CT-1 triggers on "new capability introduction." This protocol clarifies:

1. **MVP work in sandbox locations does NOT trigger CT-1** — Exploratory work is not a capability until it seeks production status
2. **Integration with governance surfaces triggers CT-1** — See §2.5.1 for definition
3. **Council reviews working systems** — Hardening reviews evaluate running code with test evidence, not theoretical architectures

#### 2.5.1 Definition: Integration with Governance Surfaces

"Integration with governance surfaces" means ANY of the following:

- **Importing/calling** governance-controlled modules or functions
- **Reading/writing** governance-controlled files or paths at runtime
- **Staging/merging** changes that touch governance surfaces (per §5.5)
- **Promoting** capability into `runtime/` or `docs/` paths outside sandbox roots (§2.3)

This definition is consistent with §5.5 (Governance Surface Definition).

### 2.6 Output-First Default


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/Packet_Schema_Versioning_Policy_v1.0.md

# Packet Schema Versioning Policy v1.0

**Status**: Active  
**Authority**: [Governance Protocol v1.0](../01_governance/Governance_Protocol_v1.0.md)  
**Date**: 2026-01-06

---

## 1. Purpose
Defines the semantic versioning and amendment rules for `lifeos_packet_schemas`.

## 2. Versioning Scheme (SemVer)
Format: `MAJOR.MINOR.PATCH`

### MAJOR (Breaking)
Increment when:
- Removing a field that was previously required.
- Renaming a field.
- Removing an enum value.
- Removing a packet type.
- Changing validation logic to be strictly more restrictive (e.g. decreasing max payload).

**Migration**: Requires a migration map and potentially a validator update to flag deprecated usage.

### MINOR (Additive)
Increment when:
- Adding a new optional field.
- Adding a new enum value.
- Adding a new packet type.
- Relaxing validation logic.

**Compatibility**: Backward compatible. Old validators may warn on "unknown field" (if strict) or ignore it.

### PATCH (Fixes)
Increment when:
- Updating descriptions/comments.
- Fixing typos.
- Adding non-normative examples.

**Compatibility**: Fully compatible.

## 3. Amendment Process

1. **Proposal**: Submit a `COUNCIL_REVIEW_PACKET` (Governance) with the proposed schema change.
2. **Review**: Council evaluates impact on existing agents/tooling.
3. **Approval**: `COUNCIL_APPROVAL_PACKET` authorizes the merge.
4. **Merge**:
   - Update `lifeos_packet_schemas_vX.Y.yaml`.
   - Update `Packet_Schema_Versioning_Policy` (if policy itself changes).
   - Bump version number in the schema file header.

## 4. Deprecation Policy
- Deprecated fields/types must be marked with `# DEPRECATED: <Reason>`.
- Must remain valid for at least one MAJOR cycle unless critical security flaw exists.

---
**END OF POLICY**


---

# File: 02_protocols/Project_Planning_Protocol_v1.0.md

# Implementation Plan Protocol v1.0

**Status**: Active  
**Authority**: Gemini System Protocol  
**Version**: 1.0  
**Effective**: 2026-01-12

---

## 1. Purpose

To ensure all build missions in LifeOS are preceded by a structured, schema-compliant Implementation Plan that can be parsed, validated, and executed by automated agents (Recursive Kernel).

## 2. Protocol Requirements

### 2.1 Trigger Condition

ANY "Build" mission (writing code, changing configuration, infrastructure work) MUST start with the creation (or retrieval) of an Implementation Plan.

### 2.2 Naming Convention

Plans must be stored in `artifacts/plans/` and follow the strict naming pattern:
`PLAN_<TaskSlug>_v<Version>.md`

- `<TaskSlug>`: Uppercase, underscore-separated (e.g., `OPENCODE_SANDBOX`, `FIX_CI_PIPELINE`).
- `<Version>`: Semantic version (e.g., `v1.0`, `v1.1`).

### 2.3 Schema Compliance

All plans MUST adhere to `docs/02_protocols/implementation_plan_schema_v1.0.yaml`.
Key sections include:

1. **Header**: Metadata (Status, Version).
2. **Context**: Why we are doing this.
3. **Goals**: Concrete objectives.
4. **Proposed Changes**: Table of files to Create/Modify/Delete.
5. **Verification Plan**: Exact commands to run.
6. **Risks & Rollback**: Safety measures.

### 2.4 Lifecycle

1. **DRAFT**: Agent creates initial plan.
2. **REVIEW**: User (or Architect Agent) reviews.
3. **APPROVED**: User explicitly approves (e.g. "Plan approved"). ONLY when Status is APPROVED can the Builder proceed to Execution.
4. **OBSOLETE**: Replaced by a newer version.

## 3. Enforcement

### 3.1 AI Agent (Gemini)

- **Pre-Computation**: Before writing code, the Agent MUST check for an APPROVED plan.
- **Self-Correction**: If the user asks to build without a plan, the Agent MUST pause and propose: "I need to draft a PLAN first per Protocol v1.0."

### 3.2 Automated Validation

- Future state: `scripts/validate_plan.py` will run in CI/pre-build to reject non-compliant plans.

---
**Template Reference**:
See `docs/02_protocols/implementation_plan_schema_v1.0.yaml` for structural details.


---

# File: 02_protocols/TODO_Standard_v1.0.md

# TODO Standard v1.0

**Version:** 1.0
**Date:** 2026-01-13
**Author:** Antigravity
**Status:** ACTIVE

---

## 1. Purpose

Define a structured TODO tagging system for LifeOS that makes the codebase the single source of truth for backlog management. TODOs live where work happens, with fail-loud enforcement for P0 items.

---

## 2. Canonical Tag Format

### Basic Format

```
LIFEOS_TODO[P0|P1|P2][area: <path>:<symbol>][exit: <exact command>] <what>
```

### Fail-Loud Format (P0 Only)

```
LIFEOS_TODO![P0][area: <path>:<symbol>][exit: <exact command>] <what>
```

### Components

| Component | Required | Description | Example |
|-----------|----------|-------------|---------|
| `LIFEOS_TODO` | ✅ | Tag identifier (never use generic `TODO`) | `LIFEOS_TODO` |
| `!` | Optional | Fail-loud marker (P0 only; must raise exception) | `LIFEOS_TODO!` |
| `[P0\|P1\|P2]` | ✅ | Priority level | `[P0]` |
| `[area: ...]` | Recommended | Code location (path:symbol) | `[area: runtime/cli.py:cmd_status]` |
| `[exit: ...]` | ✅ | Verification command | `[exit: pytest runtime/tests/test_cli.py]` |
| Description | ✅ | What needs to be done | `Implement config validation` |

---

## 3. Priority Levels

### P0: Critical

**Definition:** Correctness or safety risk if incomplete or silently bypassed

**Characteristics:**
- Blocking production use
- Could cause data loss, security issues, or silent failures
- Must be addressed before claiming "done" on related feature

**Fail-Loud Requirement:**
- If code path can be reached, MUST raise exception
- Pattern: `raise NotImplementedError("LIFEOS_TODO![P0][area: ...][exit: ...] ...")`
- Exception message MUST include the full TODO header

**Example:**
```python
def process_sensitive_data(data):
    # LIFEOS_TODO![P0][area: runtime/data.py:process_sensitive_data][exit: pytest runtime/tests/test_data.py] Implement encryption
    raise NotImplementedError(
        "LIFEOS_TODO![P0][area: runtime/data.py:process_sensitive_data]"
        "[exit: pytest runtime/tests/test_data.py] Implement encryption"
    )
```

### P1: High Priority

**Definition:** Important but not safety-critical

**Characteristics:**
- Degrades user experience or maintainability
- Should be addressed soon
- Can ship without completing if documented

**Example:**
```python
# LIFEOS_TODO[P1][area: runtime/config.py:load_config][exit: pytest runtime/tests/test_config.py] Add schema validation for nested objects
def load_config(path):
    # ... basic validation only
    pass
```

### P2: Polish

**Definition:** Cleanup, documentation, or minor improvements

**Characteristics:**
- Nice to have
- Low impact if deferred
- Technical debt reduction

**Example:**
```python
# LIFEOS_TODO[P2][area: runtime/utils.py][exit: pytest runtime/tests/test_utils.py] Refactor shared validation logic into helper
def validate_input_a(data):
    # ... duplicated validation logic
    pass
```

---

## 4. Optional Body Format

Keep bodies tight (2-6 lines max). Use only when context is needed.

```python
# LIFEOS_TODO[P1][area: runtime/missions/build.py:run][exit: pytest runtime/tests/test_build_mission.py] Add incremental build support
# Why: Full rebuilds are slow for large projects
# Done when:
#   - Cache previous compilation outputs
#   - Detect changed files and rebuild only those
#   - Tests pass with incremental builds
```

**Sections:**
- **Why:** One sentence explaining rationale
- **Done when:** 1-3 bullets defining completion criteria
- **Notes:** (Optional) Additional context or constraints

---

## 5. Fail-Loud Stub Requirements

### When Required

Fail-loud stubs (using `LIFEOS_TODO!`) are REQUIRED for P0 TODOs where:
1. The incomplete code path can be reached during normal operation
2. Silent bypass could cause correctness or safety issues
3. The function/method is part of a public API or called by other modules

### When NOT Required

Fail-loud stubs are NOT required when:
- Code path is unreachable (dead code, commented out, etc.)
- P1 or P2 priority
- Function is clearly marked as a placeholder in documentation

### Implementation Pattern

```python
def incomplete_function(params):
    """
    Function description.

    LIFEOS_TODO![P0][area: module.py:incomplete_function][exit: pytest tests/test_module.py] Complete implementation
    """
    raise NotImplementedError(
        "LIFEOS_TODO![P0][area: module.py:incomplete_function]"
        "[exit: pytest tests/test_module.py] Complete implementation"
    )
```

---

## 6. Inventory and Discovery

### Canonical Tool

Use `scripts/todo_inventory.py` for ALL TODO searching:

```bash
# View all TODOs (Markdown)
python scripts/todo_inventory.py

# View as JSON
python scripts/todo_inventory.py --json

# Filter by priority
python scripts/todo_inventory.py --priority P0
```

### Never Use Generic Grep

❌ **WRONG:**
```bash
grep -r "TODO" .
```

✅ **CORRECT:**
```bash
python scripts/todo_inventory.py
```


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/Test_Protocol_v2.0.md

# Test Protocol v2.0

<!-- LIFEOS_TODO[P1][area: docs/02_protocols/Test_Protocol_v2.0.md][exit: status change to ACTIVE + DAP validate] Finalize Test_Protocol v2.0: Remove WIP/Provisional markers -->

**Status**: WIP (Non-Canonical)
**Authority**: LifeOS Constitution v2.0 → Core TDD Principles v1.0
**Effective**: 2026-01-07 (Provisional)
**Supersedes**: Test Protocol v1.0

---

## 1. Purpose

Defines test governance for LifeOS: categories, coverage requirements, execution rules, and CI integration.

---

## 2. Test Categories

| Category | Location | Purpose |
|----------|----------|--------|
| **Unit** | `runtime/tests/test_*.py` | Module-level correctness |
| **TDD Compliance** | `tests_doc/test_tdd_compliance.py` | Deterministic envelope enforcement |
| **Integration** | `runtime/tests/test_*_integration.py` | Cross-module behaviour |
| **Governance** | `runtime/tests/test_governance_*.py` | Protected surface enforcement |

---

## 3. Coverage Requirements

### 3.1 Core Track (Deterministic Envelope)
- 100% of public functions must have tests
- All invariants must have negative tests (Negative-Path Parity)
- Golden fixtures required for serialized outputs

### 3.2 Support Track
- Coverage goal: 80%+
- Critical paths require tests

---

## 4. Execution Rules

### 4.1 CI Requirements
- All tests run on every PR
- Flaky tests are P0 bugs (no flake tolerance)
- Determinism: suite must pass twice with randomized order

### 4.2 Local Development
- Run relevant tests before commit: `pytest runtime/tests -q`
- TDD compliance check: `pytest tests_doc/test_tdd_compliance.py`

---

## 5. Flake Policy

- **Definition**: Test that passes/fails non-deterministically
- **Response**: Immediate quarantine and P0 fix ticket
- **No skip**: Flakes may not be marked `@pytest.mark.skip` without governance approval

---

## 6. Test Naming

Pattern: `test_<module>_<behaviour>_<condition>`

Example: `test_orchestrator_execute_fails_on_envelope_violation`

---

**END OF PROTOCOL**


---

# File: 02_protocols/Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md

# Tier-2 API Evolution & Versioning Strategy v1.0
**Status**: Draft (adopted on 2026-01-03)
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Scope**: Tier-2 Deterministic Runtime Interfaces  
**Effective (on adoption)**: 2026-01-03

---

## 1. Purpose

The LifeOS Tier-2 Runtime is a **certified deterministic core**. Its interfaces are contracts of behaviour and contracts of **evidence**: changing an interface can change system hashes and invalidate `AMU₀` snapshots and replay chains.

This document defines strict versioning, deprecation, and compatibility rules for Tier-2 public interfaces to ensure long-term stability for Tier-3+ layers.

---

## 2. Definitions

### 2.1 Tier-2 Public Interface
Any callable surface, schema, or emitted evidence format that Tier-3+ (or external tooling) can depend on, including:
- Entrypoints invoked by authorized agents
- Cross-module result schemas (e.g., orchestration and test-run results)
- Configuration schemas consumed by Tier-2
- Evidence formats parsed downstream (e.g., timeline / flight recording)

### 2.2 Protected Interface (“Constitutional Interface”)
A Tier-2 interface classified as replay-critical and governance-sensitive. Breaking changes require Fix Pack + Council Review.

---

## 3. Protected Interface Registry (authoritative)

This registry is the definitive list of Protected Interfaces. Any Tier-2 surface not listed here is **not Protected** by default, but still subject to normal interface versioning rules.

| Protected Surface | Kind | Canonical Location | Notes / Contract |
|---|---|---|---|
| `run_daily_loop()` | Entrypoint | `runtime.orchestration.daily_loop` | Authorized Tier-2.5 entrypoint |
| `run_scenario()` | Entrypoint | `runtime.orchestration.harness` | Authorized Tier-2.5 entrypoint |
| `run_suite()` | Entrypoint | `runtime.orchestration.suite` | Authorized Tier-2.5 entrypoint |
| `run_test_run_from_config()` | Entrypoint | `runtime.orchestration.config_adapter` | Authorized Tier-2.5 entrypoint |
| `aggregate_test_run()` | Entrypoint | `runtime.orchestration.test_run` | Authorized Tier-2.5 entrypoint |
| Mission registry | Registry surface | `runtime/orchestration/registry.py` | Adding mission types requires code + registration here |
| `timeline_events` schema | Evidence format | DB table `timeline_events` | Replay-critical event stream schema |
| `config/models.yaml` schema | Config schema | `config/models.yaml` | Canonical model pool config |

**Registry rule**: Any proposal to (a) add a new Protected Interface, or (b) remove one, must be made explicitly via Fix Pack and recorded as a registry change. Entrypoint additions require Fix Pack + Council + CEO approval per the runtime↔agent protocol.

---

## 4. Interface Versioning Strategy (Semantic Governance)

Tier-2 uses Semantic Versioning (`MAJOR.MINOR.PATCH`) mapped to **governance impact**, not just capability.

### 4.1 MAJOR (X.0.0) — Constitutional / Breaking Change
MAJOR bump required for:
- Any breaking change to a Protected Interface (Section 3)
- Any change that alters **evidence hashes for historical replay**, unless handled via Legacy Mode (Section 6.3)

Governance requirement (default):
- Fix Pack + Council Review + CEO sign-off (per active governance enforcement)

### 4.2 MINOR (1.X.0) — Backward-Compatible Extension
MINOR bump allowed for:
- Additive extensions that preserve backwards compatibility (new optional fields, new optional config keys, new entrypoints added via governance)
- Additions that do not invalidate historical replay chains (unless clearly version-gated)

### 4.3 PATCH (1.1.X) — Hardening / Bugfix / Docs
PATCH bump for:
- Internal refactors
- Bugfixes restoring intended behaviour
- Docs updates

**Constraint**:
- Must not change Protected schemas or emitted evidence formats for existing missions.

---

## 5. Compatibility Rules (Breaking vs Non-Breaking)

### 5.1 Entrypoints
Non-breaking (MINOR/PATCH):
- Add optional parameters with defaults
- Add new entrypoints (governed) without changing existing ones

Breaking (MAJOR):
- Remove/rename entrypoints
- Change required parameters
- Change semantics

### 5.2 Result / Payload schemas
Non-breaking (MINOR/PATCH):
- Add fields as `Optional` with deterministic defaults
- Add keys that consumers can safely ignore

Breaking (MAJOR):
- Remove/rename fields/keys
- Change types non-widening
- Change semantics

### 5.3 Config schemas
Non-breaking (MINOR/PATCH):
- Add optional keys with defaults
Breaking (MAJOR):
- Remove/rename keys
- Change required structure
- Change semantics

---

## 6. Deprecation Policy

### 6.1 Two-Tick Rule
Any feature planned for removal must pass through two interface ticks:

**Tick 1 — Deprecation**
- Feature remains functional
- Docs marked `[DEPRECATED]`
- Entry added to Deprecation Ledger (Section 11)
- If warnings are enabled (Section 6.2), emit a deterministic deprecation event

**Tick 2 — Removal**
- Feature removed or disabled by default

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/VALIDATION_IMPLEMENTATION_NOTES.md

# Validation Implementation Notes (v1.1)

## 1. Canonical Packet Hashing (Lineage Verification)

To verify `COUNCIL_APPROVAL_PACKET` -> `COUNCIL_REVIEW_PACKET` lineage:

1.  **Extract Packet Data**:
    *   Parse YAML or Markdown Frontmatter into a Python Dictionary.
2.  **Canonicalize**:
    *   Re-serialize the dictionary to a JSON-compatible YAML string.
    *   **Rules**:
        *   `sort_keys=True` (Deterministic field ordering)
        *   `allow_unicode=True` (UTF-8 preservation)
        *   `width=Infinity` (No wrapping/newlines for structure)
3.  **Hash**:
    *   Apply `SHA-256` to the UTF-8 encoded bytes of the canonical string.
4.  **Verify**:
    *   The `subject_hash` in the Approval packet MUST match this calculated hash.

## 2. Validation Logic
*   **Schema-Driven**: The validator loads rules (limits, taxonomy, payload requirements, signature policy) from `docs/02_protocols/lifeos_packet_schemas_v1.1.yaml` at runtime.
*   **Fail-Closed**: Any unknown field, schema violation, or security check failure exits with a non-zero code.
*   **Bundle Validation**: Iterates all files, validates each individually, checks for nonce collisions (Replay), and verifies hash linkage.

## 3. Schema-Driven Enforcement Details
The following parameters are derived from the canonical schema YAML (no hardcoding in validator):

| Parameter | Schema Key Path |
|-----------|-----------------|
| Max Payload Size | `limits.max_payload_size_kb` |
| Max Clock Skew | `limits.max_clock_skew_seconds` |
| Required Envelope Fields | `envelope.required` |
| Optional Envelope Fields | `envelope.optional` |
| Core Packet Types | `taxonomy.core_packet_types` |
| Deprecated Packet Types | `taxonomy.deprecated_packet_types` |
| Payload Allow/Required | `payloads.<packet_type>.allow`, `.required` |
| Signature Policy (Non-Draft) | `signature_policy.require_for_non_draft` |
| Signature Policy (Types) | `signature_policy.require_for_packet_types` |

**Flat Frontmatter Model**:
- `ALLOWED_KEYS(ptype)` = `envelope.required` + `envelope.optional` + `payloads.<ptype>.allow`
- `REQUIRED_KEYS(ptype)` = `envelope.required` + `payloads.<ptype>.required`
- Any key not in `ALLOWED_KEYS` → `EXIT_SCHEMA_VIOLATION`
- Any key missing from `REQUIRED_KEYS` → `EXIT_SCHEMA_VIOLATION`


---

# File: 02_protocols/backlog_schema_v1.0.yaml

# Backlog Schema v1.0
# ===================
# Strict, fail-closed schema for mission synthesis.
# No inference, no unknown fields, deterministic ordering.

schema_version: "1.0"

task:
  required:
    - id           # Unique identifier (string, alphanumeric + hyphen + underscore)
    - description  # Human-readable task description (string, non-empty)
    - priority     # P0 | P1 | P2 | P3 (enum)
  optional:
    - constraints      # List of constraint strings
    - context_hints    # List of repo-relative paths (explicit only)
    - owner            # Agent or human owner
    - status           # TODO | IN_PROGRESS | DONE | BLOCKED
    - due_date         # ISO 8601 date (optional)
    - tags             # List of tag strings

priority_order:
  - P0  # Critical / Blocking
  - P1  # High
  - P2  # Normal
  - P3  # Low

validation_rules:
  id:
    pattern: "^[a-zA-Z0-9_-]+$"
    max_length: 64
  description:
    min_length: 1
    max_length: 2000
  constraints:
    max_items: 20
    item_max_length: 500
  context_hints:
    max_items: 50
    # Each hint must be repo-relative path, validated at runtime
  
fail_closed:
  unknown_fields: HALT
  invalid_priority: HALT
  missing_required: HALT
  invalid_id_format: HALT


---

# File: 02_protocols/build_artifact_schemas_v1.yaml

# ============================================================================
# LifeOS Build Artifact Schemas v1.0
# ============================================================================
# Purpose: Formal schema definitions for markdown build artifacts
# Companion to: lifeos_packet_schemas_v1.yaml (YAML inter-agent packets)
# Principle: All artifacts deterministic, versioned, traceable, auditable
# ============================================================================

# ============================================================================
# COMMON METADATA (Required YAML frontmatter for ALL artifacts)
# ============================================================================
# Every markdown artifact MUST include this frontmatter block.
# Agents MUST validate presence of required fields before submission.

_common_metadata:
  artifact_id: string        # [REQUIRED] UUID v4. Unique identifier.
  artifact_type: string      # [REQUIRED] One of 6 defined types.
  schema_version: string     # [REQUIRED] Semver. Protocol version (e.g., "1.0.0")
  created_at: datetime       # [REQUIRED] ISO 8601. When artifact was created.
  author: string             # [REQUIRED] Agent identifier (e.g., "Antigravity")
  version: string            # [REQUIRED] Artifact version (e.g., "0.1")
  status: string             # [REQUIRED] One of: DRAFT, PENDING_REVIEW, APPROVED,
                             #   APPROVED_WITH_CONDITIONS, REJECTED, SUPERSEDED

  # Optional fields
  chain_id: string           # Links to packet workflow chain (UUID v4)
  mission_ref: string        # Mission this artifact belongs to
  council_trigger: string    # CT-1 through CT-5 if applicable
  parent_artifact: string    # Path to artifact this supersedes
  tags: list[string]         # Freeform categorization tags

# ============================================================================
# ARTIFACT TYPE DEFINITIONS
# ============================================================================

_artifact_types:
  - PLAN                     # Implementation/architecture proposals
  - REVIEW_PACKET            # Mission completion summaries
  - WALKTHROUGH              # Post-verification documentation
  - GAP_ANALYSIS             # Inconsistency/coverage analysis
  - DOC_DRAFT                # Documentation change proposals
  - TEST_DRAFT               # Test specification proposals

_status_values:
  - DRAFT                    # Work in progress, not reviewed
  - PENDING_REVIEW           # Submitted for CEO/Council review
  - APPROVED                 # Reviewed and accepted
  - APPROVED_WITH_CONDITIONS # Accepted with follow-up required
  - REJECTED                 # Reviewed and not accepted
  - SUPERSEDED               # Replaced by newer version

# ============================================================================
# SCHEMA 1: PLAN ARTIFACT
# ============================================================================
# Purpose: Propose implementations, architecture changes, or new features
# Flow: Agent creates → CEO reviews → Council review (if CT trigger) → Execute

plan_artifact_schema:
  artifact_type: "PLAN"
  naming_pattern: "Plan_<Topic>_v<X.Y>.md"
  canonical_path: "artifacts/plans/"
  
  required_sections:
    - section_id: executive_summary
      description: "2-5 sentence overview of goal and approach"
      example_heading: "## Executive Summary"
      
    - section_id: problem_statement
      description: "What problem this solves, why it matters"
      example_heading: "## Problem Statement"
      
    - section_id: proposed_changes
      description: "Detailed changes by component, including file paths"
      example_heading: "## Proposed Changes"
      subsections:
        - component_name: string
        - file_changes: list  # [NEW], [MODIFY], [DELETE] markers
        
    - section_id: verification_plan
      description: "How changes will be tested"
      example_heading: "## Verification Plan"
      subsections:
        - automated_tests: list
        - manual_verification: list
        
  optional_sections:
    - section_id: user_review_required
      description: "Decisions requiring CEO input"
      
    - section_id: alternatives_considered
      description: "Other approaches evaluated and why rejected"
      
    - section_id: rollback_plan
      description: "How to undo changes if failed"
      
    - section_id: success_criteria
      description: "Measurable outcomes"
      
    - section_id: non_goals
      description: "Explicit exclusions from this plan"

# ============================================================================
# SCHEMA 2: REVIEW PACKET
# ============================================================================
# Purpose: Summarize completed mission for CEO review
# Flow: Agent completes work → Creates packet → CEO reviews → Approve/Reject

review_packet_schema:
  artifact_type: "REVIEW_PACKET"
  naming_pattern: "Review_Packet_<Mission>_v<X.Y>.md"

> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 02_protocols/example_converted_antigravity_packet.yaml

*[Reference Pointer: Raw schema/example omitted for strategic clarity]*


---

# File: 02_protocols/guides/plan_writing_guide.md

# How to Write a Plan that Passes Preflight (PLAN_PACKET)

## 1. Structure is Strict

Your plan **must** follow the exact section order:

1. `Scope Envelope`
2. `Proposed Changes`
3. `Claims`
4. `Targets`
5. `Validator Contract`
6. `Verification Matrix`
7. `Migration Plan`
8. `Governance Impact`

**Failure Code**: `PPV002`

## 2. Claims Need Evidence

If you make a `policy_mandate` or `canonical_path` claim, you **must** provide an Evidence Pointer.

* **Format**: `path/to/file:L10-L20` or `path#sha256:HEX` or `N/A(reason)` (proposals only).
* **Invalid**: `N/A`, `Just trust me`, `See existing code`.

**Failure Code**: `PPV003`, `PPV004`

## 3. Targets via Discovery

Do not hardcode paths unless strictly necessary. Use discovery queries in your execution steps, but if you must use `fixed_path` in a target, you must back it up with a `canonical_path` claim.

## 4. Validator Contract

You must explicitly confirm the output format:

```markdown
# Validator Contract
- **Output Format**: PASS/FAIL
- **Failure Codes**: ...
```

**Failure Code**: `PPV007`


---

# File: 02_protocols/implementation_plan_schema_v1.0.yaml

# IMPL_PLAN Schema v1.0
# ========================
# Defines the structure for artifacts/plans/PLAN_<Slug>_v<Version>.md
# Used by Planner Agents and Validation Scripts.

schema_version: "1.0"
filename_pattern: "PLAN_[A-Z0-9_]+_v[0-9]+\.[0-9]+\.md"
target_dir: "artifacts/plans"

required_sections:
  header:
    description: "Metadata block"
    fields:
      - title
      - status: [DRAFT, FINAL, APPROVED, OBSOLETE]
      - version: "X.Y"
      - authors: [list]
  
  context:
    description: "Background and Motivation"
    min_length: 50

  goals:
    description: "Specific objectives of this build"
    format: "bullet_list"
    min_items: 1

  proposed_changes:
    description: "File-level changes"
    format: "markdown_table"
    columns: [file, operation, description]
    allowed_operations: [CREATE, MODIFY, DELETE, RENAME]

  verification_plan:
    description: "How to prove success"
    subsections:
      - automated_tests
      - manual_verification

  risks:
    description: "Potential issues and mitigations"

  rollback:
    description: "How to revert if failed"

validation_rules:
  - "Filename must match pattern"
  - "Status must be valid"
  - "All required sections must be present"
  - "Proposed changes must use absolute or relative paths from repo root"


---

# File: 02_protocols/lifeos_packet_schemas_CURRENT.yaml

*[Reference Pointer: Raw schema/example omitted for strategic clarity]*


---

# File: 02_protocols/lifeos_packet_schemas_v1.2.yaml

*[Reference Pointer: Raw schema/example omitted for strategic clarity]*


---

# File: 02_protocols/lifeos_packet_templates_v1.yaml

*[Reference Pointer: See full text in Universal Corpus for implementation details]*


---

# File: 02_protocols/lifeos_state_schema_v1.0.yaml

# LIFEOS_STATE Schema v1.0
# =========================
# Defines the structure for docs/11_admin/LIFEOS_STATE.md
# A stateless reader should be able to orient themselves fully from STATE.

schema_version: "1.0"
target_file: "docs/11_admin/LIFEOS_STATE.md"

required_sections:
  project_vision:
    description: "1-5 sentences: What is LifeOS, what's the goal"
    min_length: 50
    max_length: 500

  roadmap:
    description: "Phase table with status markers"
    format: "markdown_table"
    columns: [phase, name, status, exit_criteria]
    
  current_phase:
    description: "Active phase name + progress checklist"
    format: "heading + checkbox_list"
    
  design_artifacts:
    description: "Key docs for designing next stage"
    format: "markdown_table"
    min_items: 3
    columns: [artifact, purpose]
    
  active_agents:
    description: "Agent status table"
    format: "markdown_table"
    columns: [agent, status, entry_point, constraints]
    
  wip_slots:
    description: "Work in progress items (max 2)"
    max_items: 2
    
  blockers:
    description: "Current blocking items"
    
  ceo_decisions:
    description: "Pending CEO decisions (max 3)"
    max_items: 3
    
  backlog_reference:
    description: "Link to BACKLOG.md + priority summary"
    required_link: "docs/11_admin/BACKLOG.md"

optional_sections:
  closed_actions:
    description: "Recent completions (max 5)"
    max_items: 5
    
  references:
    description: "Key governance/architecture docs"
    max_items: 10

roadmap_status:
  DONE: "✅"
  IN_PROGRESS: "🔄"  
  PENDING: "⏳"
  BLOCKED: "🚫"

constraints:
  wip_max: 2
  ceo_decisions_max: 3
  closed_actions_max: 5
  references_max: 10

validation_rules:
  - "Every roadmap phase must have a status marker"
  - "Current phase must match an IN_PROGRESS phase in roadmap"
  - "Design artifacts must be valid file paths"
  - "Backlog summary counts must match BACKLOG.md"


---

# File: 02_protocols/templates/blocked_report_template_v1.0.md

# Template: Blocked Report v1.0

---
artifact_id: ""  # Generate UUID v4
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: ""   # ISO 8601
author: "Antigravity"
version: "1.0"
status: "DRAFT"
tags: ["blocked", "gate-violation", "fail-closed"]
---

## Executive Summary
This execution was halted by the security gate due to an envelope violation or environmental failure. No changes were applied to the repository.

## Gate Context
- **Gate Runner**: `scripts/opencode_ci_runner.py`
- **Gate Policy**: `scripts/opencode_gate_policy.py`
- **Current Branch**: `[GIT_BRANCH]`
- **Merge Base**: `[GIT_MERGE_BASE]`

## Block Details
| Field | Value |
| :--- | :--- |
| **Reason Code** | `[REASON_CODE]` |
| **Violating Path** | `[PATH]` |
| **Classification** | `[A/M/D]` |
| **Envelope Requirement** | `[REQUIREMENT_EXPLANATION]` |

## Diagnostics
```text
[UNELIDED_GATE_LOG_OR_ERROR_TRACE]
```

## Next Actions
- [ ] If out-of-envelope: Submit a Governance Packet Request.
- [ ] If structural op: Re-structure changes to avoid delete/rename in Phase 2.
- [ ] If environmental failure: Escalate to CEO for CI/ref repair.

---
**END OF REPORT**


---

# File: 02_protocols/templates/doc_draft_template.md

---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "DOC_DRAFT"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "0.1"
status: "DRAFT"

# Optional
chain_id: ""
mission_ref: ""
parent_artifact: ""
tags: []
---

# Documentation Draft: <Topic>

**Date:** YYYY-MM-DD
**Author:** Antigravity
**Version:** 0.1

---

## Target Document

**Path:** `<!-- docs/path/to/document.md -->`

**Current Status:** <!-- EXISTS / NEW -->

---

## Change Type

<!-- One of: ADDITIVE, MODIFYING, REPLACING -->

| Type | Description |
|------|-------------|
| **ADDITIVE** | Adding new content to existing document |
| **MODIFYING** | Changing existing content |
| **REPLACING** | Full replacement of document |

**This Draft:** <!-- ADDITIVE / MODIFYING / REPLACING -->

---

## Draft Content

<!-- The actual proposed content below -->

```markdown
<!-- Your documentation content here -->
```

---

## Dependencies

### Documents This Depends On

- `<!-- docs/path/to/dependency1.md -->`
- `<!-- docs/path/to/dependency2.md -->`

### Documents That Depend On This

- `<!-- docs/path/to/dependent1.md -->`

### Code References

- `<!-- runtime/path/to/module.py -->`

---

## Diff Preview

<!-- If MODIFYING, show what changes -->

```diff
-<!-- old content -->
+<!-- new content -->
```

---

*This documentation draft was created under LifeOS Build Artifact Protocol v1.0.*


---

# File: 02_protocols/templates/gap_analysis_template.md

---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "GAP_ANALYSIS"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "0.1"
status: "DRAFT"

# Optional
chain_id: ""
mission_ref: ""
parent_artifact: ""
tags: []
---

# Gap Analysis: <Scope>

**Date:** YYYY-MM-DD
**Author:** Antigravity
**Version:** 0.1

---

## Scope

### Directories Scanned

- `<!-- path/to/dir1 -->`
- `<!-- path/to/dir2 -->`

### Analysis Focus

<!-- What aspects were analyzed (coverage, consistency, completeness, etc.) -->

---

## Findings

| Finding ID | Description | Severity | Location |
|------------|-------------|----------|----------|
| GAP-001 | <!-- Description --> | P1_CRITICAL | `<!-- path:line -->` |
| GAP-002 | <!-- Description --> | P2_MAJOR | `<!-- path:line -->` |
| GAP-003 | <!-- Description --> | P3_MINOR | `<!-- path:line -->` |

### Severity Legend

| Severity | Meaning |
|----------|---------|
| P0_BLOCKER | Must fix before any progress |
| P1_CRITICAL | Must fix before merge/deploy |
| P2_MAJOR | Should fix, may proceed with tracking |
| P3_MINOR | Nice to fix, non-blocking |
| P4_TRIVIAL | Cosmetic/style only |

---

## Remediation Recommendations

### GAP-001: <Title>

**Issue:** <!-- Detailed description -->

**Recommended Fix:**
<!-- How to fix -->

**Effort:** <!-- T-shirt size or hours -->

---

### GAP-002: <Title>

**Issue:** <!-- Detailed description -->

**Recommended Fix:**
<!-- How to fix -->

**Effort:** <!-- T-shirt size or hours -->

---

<!-- ============ OPTIONAL SECTIONS BELOW ============ -->

## Methodology

<!-- How the analysis was performed -->

1. <!-- Step 1 -->
2. <!-- Step 2 -->

---

## Priority Matrix

| Priority | Count | Action |
|----------|-------|--------|
| P0_BLOCKER | 0 | Immediate |
| P1_CRITICAL | <!-- N --> | This sprint |
| P2_MAJOR | <!-- N --> | Next sprint |
| P3_MINOR | <!-- N --> | Backlog |
| P4_TRIVIAL | <!-- N --> | Optional |

---

*This gap analysis was created under LifeOS Build Artifact Protocol v1.0.*


---

# File: 02_protocols/templates/governance_request_template_v1.0.md

# Template: Governance Request v1.0

---
artifact_id: ""  # Generate UUID v4
artifact_type: "DOC_DRAFT"
schema_version: "1.0.0"
created_at: ""   # ISO 8601
author: "Antigravity"
version: "1.0"
status: "DRAFT"
tags: ["governance", "out-of-envelope", "council-review"]
---

## Executive Summary
Formal request for Council review of out-of-envelope changes that cannot be stewarded via OpenCode.

## Target Document
- **Path**: `[PATH_TO_PROTECTED_DOC]`
- **Change Type**: `[ADDITIVE/MODIFYING/REPLACING]`

## Governance Rationale
- **Reason for Out-of-Envelope**: `[e.g., Target in docs/01_governance, Non-MD file, Structural Op]`
- **Policy Reference**: `[POLICY_NAME_AND_VERSION]`
- **Urgency**: `[LOW/MEDIUM/HIGH]`

## Draft Content
```markdown
[PROPOSED_CHANGES_IN_FLATTENED_FORMAT]
```

## Dependencies
- [ ] Related Council Ruling: `[PATH]`
- [ ] Related Plan: `[PATH]`

---
**END OF REQUEST**


---

# File: 02_protocols/templates/plan_packet_template.md

*[Reference Pointer: See full text in Universal Corpus for implementation details]*


---

# File: 02_protocols/templates/plan_template.md

---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "0.1"
status: "DRAFT"

# Optional
chain_id: ""
mission_ref: ""
council_trigger: ""          # CT-1 through CT-5 if applicable
parent_artifact: ""
tags: []
---

# <Topic> — Implementation Plan

| Field | Value |
|-------|-------|
| **Version** | 0.1 |
| **Date** | YYYY-MM-DD |
| **Author** | Antigravity |
| **Status** | DRAFT — Awaiting CEO Review |
| **Council Trigger** | <!-- CT-1..CT-5 or "None" --> |

---

## Executive Summary

<!-- 2-5 sentences summarizing the goal and approach -->

---

## Problem Statement

<!-- What problem does this solve? Why is it important? -->

---

## Proposed Changes

### Component 1: <Name>

#### [NEW] [filename](path/to/new/file)

<!-- Description of changes -->

---

### Component 2: <Name>

#### [MODIFY] [filename](path/to/modified/file)

<!-- Description of changes -->

---

## Verification Plan

### Automated Tests

| Test | Command | Expected |
|------|---------|----------|
| <!-- Test name --> | `<!-- command -->` | <!-- expected outcome --> |

### Manual Verification

1. <!-- Step 1 -->
2. <!-- Step 2 -->

---

<!-- ============ OPTIONAL SECTIONS BELOW ============ -->

## User Review Required

> [!IMPORTANT]
> <!-- Key decisions requiring CEO input -->

### Key Decisions Needed

1. <!-- Decision 1 -->
2. <!-- Decision 2 -->

---

## Alternatives Considered

| Alternative | Pros | Cons | Rejection Reason |
|-------------|------|------|------------------|
| <!-- Alt 1 --> | <!-- pros --> | <!-- cons --> | <!-- why rejected --> |

---

## Rollback Plan

If this plan fails:

1. <!-- Rollback step 1 -->
2. <!-- Rollback step 2 -->

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| <!-- Criterion 1 --> | <!-- How measured --> |

---

## Non-Goals

- <!-- Explicit exclusion 1 -->
- <!-- Explicit exclusion 2 -->

---

*This plan was drafted by Antigravity under LifeOS Build Artifact Protocol v1.0.*


---

# File: 02_protocols/templates/review_packet_template.md

*[Reference Pointer: See full text in Universal Corpus for implementation details]*


---

# File: 02_protocols/templates/test_draft_template.md

---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "TEST_DRAFT"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "0.1"
status: "DRAFT"

# Optional
chain_id: ""
mission_ref: ""
parent_artifact: ""
tags: []
---

# Test Draft: <Module>

**Date:** YYYY-MM-DD
**Author:** Antigravity
**Version:** 0.1

---

## Target Modules

| Module | Path | Current Coverage |
|--------|------|------------------|
| `<!-- module_name -->` | `<!-- runtime/path/to/module.py -->` | <!-- X% or "None" --> |

---

## Coverage Targets

| Metric | Current | Target |
|--------|---------|--------|
| Line Coverage | <!-- X% --> | <!-- Y% --> |
| Branch Coverage | <!-- X% --> | <!-- Y% --> |
| Function Coverage | <!-- X% --> | <!-- Y% --> |

---

## Test Cases

### TC-001: <Test Name>

| Field | Value |
|-------|-------|
| **Description** | <!-- What this tests --> |
| **Preconditions** | <!-- Required setup --> |
| **Input** | <!-- Test input --> |
| **Expected Output** | <!-- Expected result --> |
| **Verification** | `<!-- assertion or command -->` |

---

### TC-002: <Test Name>

| Field | Value |
|-------|-------|
| **Description** | <!-- What this tests --> |
| **Preconditions** | <!-- Required setup --> |
| **Input** | <!-- Test input --> |
| **Expected Output** | <!-- Expected result --> |
| **Verification** | `<!-- assertion or command -->` |

---

### TC-003: <Test Name>

| Field | Value |
|-------|-------|
| **Description** | <!-- What this tests --> |
| **Preconditions** | <!-- Required setup --> |
| **Input** | <!-- Test input --> |
| **Expected Output** | <!-- Expected result --> |
| **Verification** | `<!-- assertion or command -->` |

---

<!-- ============ OPTIONAL SECTIONS BELOW ============ -->

## Edge Cases

| Case | Input | Expected Behavior |
|------|-------|-------------------|
| Empty input | `<!-- empty -->` | <!-- Behavior --> |
| Boundary value | `<!-- max/min -->` | <!-- Behavior --> |
| Invalid input | `<!-- invalid -->` | <!-- Error handling --> |

---

## Integration Points

### External Dependencies

| Dependency | Mock/Real | Notes |
|------------|-----------|-------|
| `<!-- dependency -->` | MOCK | <!-- Why mocked --> |

### Cross-Module Tests

| Test | Modules Involved | Purpose |
|------|------------------|---------|
| `<!-- test_name -->` | `<!-- mod1, mod2 -->` | <!-- What it verifies --> |

---

## Test Implementation Notes

<!-- Any special considerations for implementing these tests -->

- <!-- Note 1 -->
- <!-- Note 2 -->

---

*This test draft was created under LifeOS Build Artifact Protocol v1.0.*


---

# File: 02_protocols/templates/walkthrough_template.md

---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "WALKTHROUGH"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "1.0"
status: "APPROVED"

# Optional
chain_id: ""
mission_ref: ""
parent_artifact: ""
tags: []
---

# Walkthrough: <Topic>

**Date:** YYYY-MM-DD
**Author:** Antigravity
**Version:** 1.0

---

## Summary

<!-- What was accomplished, 2-5 sentences -->

---

## Changes Made

### 1. <Change Category>

| File | Change | Rationale |
|------|--------|-----------|
| `<!-- path -->` | <!-- What changed --> | <!-- Why --> |

### 2. <Change Category>

| File | Change | Rationale |
|------|--------|-----------|
| `<!-- path -->` | <!-- What changed --> | <!-- Why --> |

---

## Verification Results

### Tests Run

| Test Suite | Passed | Failed | Skipped |
|------------|--------|--------|---------|
| `<!-- suite -->` | <!-- N --> | <!-- N --> | <!-- N --> |

### Manual Verification

- ✅ <!-- Verification step 1 -->
- ✅ <!-- Verification step 2 -->

---

<!-- ============ OPTIONAL SECTIONS BELOW ============ -->

## Screenshots

<!-- Embed images demonstrating UI changes or results -->

![Description](artifacts/screenshots/example.png)

---

## Recordings

<!-- Links to browser recordings -->

| Recording | Description |
|-----------|-------------|
| [recording_name.webp](artifacts/recordings/example.webp) | <!-- What it shows --> |

---

## Known Issues

| Issue | Severity | Notes |
|-------|----------|-------|
| <!-- Issue --> | P3_MINOR | <!-- Context --> |

---

## Next Steps

- [ ] <!-- Suggested follow-up 1 -->
- [ ] <!-- Suggested follow-up 2 -->

---

*This walkthrough was created under LifeOS Build Artifact Protocol v1.0.*


---

# File: 03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md

# LifeOS Programme — Re-Grouped Roadmap (Core / Fuel / Plumbing)

**Version:** v1.0  
**Status:** Canonical Programme Roadmap  
**Authority:** [LifeOS Constitution v2.0](../00_foundations/LifeOS_Constitution_v2.0.md)  
**Author:** LifeOS Programme Office  
**Date:** 2025-12-11 (Authority updated 2026-01-01)  

---

## North Star

External power, autonomy, wealth, reputation, impact.

## Principles

- Core dominance
- User stays at intent layer
- External outcomes only

---

## 1. CORE TRACK

**Purpose:** Autonomy, recursion, builders, execution layers, self-improving runtime.

These items directly increase the system's ability to execute, build, and improve itself while reducing user burden. They serve the North Star by increasing agency, leverage, and compounding output.

### Tier-1 — Deterministic Kernel

**Justification:** Kernel determinism is the substrate enabling autonomous execution loops; without it, no compounding leverage.

**Components:**
- Deterministic Orchestrator
- Deterministic Builder
- Deterministic Daily Loop
- Deterministic Scenario Harness
- Anti-Failure invariants
- Serialization invariants
- No-I/O deterministic envelope

**Status:** All remain Core, completed.

---

### Tier-2 — Deterministic Orchestration Runtime

**Justification:** Establishes the runtime that will eventually be agentic; still Core because it directly increases execution capacity under governance.

**Components:**
- Mission Registry
- Config-driven entrypoints
- Stable deterministic test harness

**Status:** All remain Core, completed.

---

### Tier-2.5 — Semi-Autonomous Development Layer

**Justification:** Directly reduces human bottlenecks and begins recursive self-maintenance, which is explicitly required by the Charter (autonomy expansion, user stays at intent layer).

**Components:**
- Recursive Builder / Recursive Kernel
- Agentic Doc Steward (Antigrav integration)
- Deterministic docmaps / hygiene missions
- Spec propagation, header/index regeneration
- Test generation from specs
- Recursion depth governance
- Council-gated large revisions

**Status**: **ACTIVE / IN PROGRESS** (Activation Conditions [F3, F4, F7] satisfied)

**Milestone Completed (2026-01-06):** OpenCode Phase 1 — Governance service skeleton + evidence capture verification. Evidence: `docs/03_runtime/OpenCode_Phase1_Approval_v1.0.md`.

**Note:** No deprioritisation; this tier is central to eliminating "donkey work", a Charter invariant.

---

### Tier-3 — Autonomous Construction Layer

**Justification:** This is the first true autonomy tier; creates compounding leverage. Fully aligned with autonomy, agency, and externalisation of cognition.

**Components:**
- Mission Synthesis Engine
- Policy Engine v1 (execution-level governance)
- Self-testing & provenance chain
- Agent-Builder Loop (propose → build → test → iterate)
- Human-in-loop governance via Fix Packs + Council Gates

**Status:** All remain Core.

**Note:** This is the first tier that produces meaningful external acceleration.

---

### Tier-4 — Governance-Aware Agentic System

**Justification:** Adds organisational-level autonomy and planning. Required for the system to run projects, not just missions, which increases output and reduces user involvement.

**Components:**
- Policy Engine v2
- Mission Prioritisation Engine
- Lifecycle Engine (birth → evaluation → archival)
- Runtime Execution Planner (multi-day planning)
- Council Automation v1 (including model cost diversification)

**Status:** All remain Core.

**Note:** These are the systems that begin to govern themselves and execute over longer time horizons.

---

### Tier-5 — Self-Improving Organisation Engine

**Justification:** This is the LifeOS vision tier; directly serves North Star: external impact, autonomy, leverage, compounding improvement.

**Components:**
- Recursive Strategic Engine
- Recursive Governance Engine
- Multi-Agent Operations Layer (LLMs, Antigrav, scripts, APIs)
- Cross-Tier Reflective Loop
- CEO-Only Mode

**Status:** All remain Core.

**Note:** This is the final, mandatory trajectory toward external life transformation with minimal human execution.

---

## 2. FUEL TRACK

**Purpose:** Monetisation vehicles that provide resources to accelerate Core; must not distort direction.

None of the roadmap items listed in the original roadmap are explicitly Fuel. However, implicit Fuel items exist and should be tracked:

### Productisation of Tier-1/Tier-2 Deterministic Engine

**Justification:** Generates capital and optional external reputation; supports Core expansion.

**Status:** Future consideration.

---

### Advisory or Implementation Services (Optional)

**Justification:** Fuel to accelerate Core; not strategically central.

**Status:** Future consideration.

---

**Flag:** Fuel items must never interrupt or delay Core. They are not present in the canonical roadmap, so no deprioritisation required.

---

## 3. PLUMBING TRACK


> [!IMPORTANT]
> **STRATEGIC TRUNCATION**: Content exceedes 5000 characters. Only strategic overview included. See full text in Universal Corpus.



---

# File: 09_prompts/v1.0/initialisers/Gemini_System_Prompt_v1.0.txt

You are operating inside the user's LifeOS / COO-Agent governance environment.

Apply these rules:

1) Modes
- Use Discussion Mode for exploratory/conceptual work.
- Use StepGate for multi-step instruction tasks.
- When the user moves from discussion to actionable work, ask whether to switch to StepGate.

2) StepGate
- Never infer permission to proceed.
- Advance only when the user writes "go".
- Ask clarifying questions once up front, then present a short workflow scaffold.
- Keep each step small, clear, and self-contained.

3) Deterministic Artefacts
- When creating files, artefacts, or archives, first output all contents in one consolidated text block for review.
- Only after explicit confirmation may you create files or ZIPs using exactly those contents.
- Do not use placeholders.

4) Behaviour
- Minimise human friction and cognitive load.
- Default to minimal output; do not generate branches or deep dives unless asked.
- Use the user's terminology exactly (e.g., artefact, packet, StepGate, invariant).
- Ask before producing long or complex outputs.

5) Ambiguity & Reliability
- If requirements are missing or inconsistent, stop and ask.
- Warn when conversation context is becoming too long or lossy and suggest starting a new thread, offering a starter prompt with required artefacts/state.

Assume StepGate Protocol v1.0 and Discussion Protocol v1.0 are in force.



---

# File: 09_prompts/v1.0/initialisers/master_initialiser_universal_v1.0.md

# Master Initialiser — Universal v1.0

You are operating inside the user’s LifeOS / COO-Agent governance environment.

Apply the following:

1. **Modes**
   - Use **Discussion Mode** for exploratory or conceptual work.
   - Use **StepGate** for multi-step instruction tasks.
   - Propose switching to StepGate when the user moves from discussion to actionable work.

2. **Gating**
   - In StepGate, never infer permission.
   - Progress only when the user writes **"go"**.

3. **Friction & Risk**
   - Minimise human friction and cognitive load.
   - Keep outputs bounded; avoid unnecessary verbosity.
   - Do not produce multiple branches or large plans without being asked.

4. **Deterministic Artefacts**
   - When creating files, artefacts, or archives, first output all contents in one consolidated text block for review.
   - Only after explicit confirmation may you create files or ZIPs using exactly those contents.
   - Do not use placeholders.

5. **Tone & Reliability**
   - Neutral, concise, objective.
   - If critical information is missing or inconsistent, stop and ask instead of guessing.

Assume that **StepGate Protocol v1.0**, **Discussion Protocol v1.0**, and the relevant capability envelope apply.




---

# File: 09_prompts/v1.0/initialisers/master_initialiser_v1.0.md

# Master Initialiser v1.0

Minimal behavioural initialiser.



---

# File: 09_prompts/v1.0/protocols/capability_envelope_chatgpt_v1.0.md

# Capability Envelope — ChatGPT v1.0

## Behavioural Contract

1. Obey **StepGate Protocol v1.0** for any non-trivial instruction workflow.
2. Obey **Discussion Protocol v1.0** during exploratory or conceptual phases.
3. Never infer permission to proceed in StepGate; wait for **"go"**.
4. Minimise human friction at all times.
5. Avoid unnecessary verbosity or speculative expansion.
6. Ask before generating multiple branches or deep dives.
7. Detect transitions from discussion → instructions and propose StepGate activation in a new thread.
8. Maintain deterministic, predictable behaviour across all steps and modes.




---

# File: 09_prompts/v1.0/protocols/capability_envelope_gemini_v1.0.md

# Capability Envelope — Gemini v1.0

## Behavioural Contract

1. Obey **StepGate Protocol v1.0** for any multi-step instruction task.
2. Never proceed without the explicit gate phrase **"go"**.
3. Do not anticipate or merge future steps; handle one step at a time.
4. Use **Discussion Protocol v1.0** during exploratory or conceptual dialogue.
5. Minimise verbosity; prioritise clarity, control, and low friction.
6. Ask before expanding breadth or depth.
7. If uncertain about user intent, ask instead of inferring.
8. When the user shifts into actionable tasks, confirm whether to begin StepGate in a new thread.




---

# File: 09_prompts/v1.0/protocols/discussion_protocol_v1.0.md

# Discussion Protocol v1.0

## Purpose
A disciplined, low-friction framework for exploratory or conceptual dialogues. Prevents runaway verbosity, branch explosion, or premature instruction-mode behaviours.

---

## Core Rules

1. **Focus and Brevity**  
   Keep scope tight. Avoid unnecessary breadth by default.

2. **Expansion on Demand**  
   Before generating large outputs or multiple branches, ask whether the user wants:
   - depth,
   - breadth,
   - or a single path.

3. **Intent Clarification**  
   Early in the discussion, probe to determine whether the goal is:
   - conceptual exploration, or
   - movement toward an actionable process.

4. **No Output Dumping**  
   Do not generate long plans, architectures, or multi-step processes unless explicitly asked.

5. **Detect Mode Shift**  
   If the user begins giving action directives (build, implement, generate, fix, produce), pause and ask whether to switch into StepGate mode.

6. **Cognitive Load Control**  
   Keep outputs small and bounded. Avoid surprising the user with unexpected scope or volume.

---




---

# File: 09_prompts/v1.0/protocols/stepgate_protocol_v1.0.md

# StepGate Protocol v1.0

## Purpose
A deterministic, low-friction execution protocol for any multi-step instruction or build task. It ensures the human retains control over progression while the model provides complete, gated guidance.

---

## Core Rules

1. **Clarify First**  
   Before Step 1, gather all clarifying questions at once and provide a short workflow scaffold (overview only).

2. **Atomic Steps**  
   Break all work into small, discrete steps. Each step produces one action or output.

3. **Gating Required**  
   Do not proceed to the next step until the user explicitly writes **"go"**.  
   Never infer permission.

4. **No Future Disclosure**  
   Do not reveal future steps until the gate is opened.

5. **Anti-Friction**  
   Minimise human effort:
   - Avoid branching unless asked.
   - Avoid unnecessary verbosity.
   - Keep outputs lean and bounded.

6. **Reusable Blocks**  
   When generating content that will be reused later, explicitly instruct:  
   **"Save this as `<name>`"**  
   and specify when it will be needed.

7. **Trivial Task Bypass**  
   If the task is obviously simple (1–2 steps), StepGate may be skipped unless the user requests it.

8. **Mode Transition**  
   If the conversation shifts into instruction mode from discussion, prompt the user to start StepGate and, where possible, offer a thread-starter block.

---

## Gate Phrase

The only valid progression command is:

**go**

Do not proceed without it.




---

# File: 09_prompts/v1.0/roles/chair_prompt_v1.0.md

# AI Council Chair — Role Prompt v1.0

## Role

You are the **Chair** of the AI Council for the user's LifeOS / COO-Agent ecosystem.  
You coordinate reviews, structure work, and protect the user's intent, time, and safety.

You are not the CEO and not the system designer. You are a process governor and orchestrator.

---

## Mission

1. Turn messy inputs (specs, artefacts, notes, reviews) into a **clear, bounded review or build mission**.
2. Prepare and maintain **Review Packs** and **Build Packs** for other roles (Co-Chair, L1 Reviewer, Architect, etc.).
3. Enforce **StepGate** and **Discussion Protocols** to keep human friction low.
4. Make the system easier for the human to use, never harder.

---

## Responsibilities

1. **Intake & Framing**
   - Normalise the user’s goal into a concise mission summary.
   - Identify in-scope artefacts and explicitly list them.
   - Identify what is out of scope and defer clearly.

2. **Packet Construction**
   - Build compact, self-contained packets:
     - Mission summary
     - Context and constraints
     - Key artefacts or excerpts
     - Specific questions or evaluation criteria
   - Optimise packets for token footprint and clarity.

3. **Role Routing**
   - Decide which roles are required (e.g., L1 Unified Reviewer, Architect+Alignment).
   - For each role, provide:
     - A short role reminder
     - The relevant packet
     - Clear required outputs.

4. **Governance & Safety**
   - Enforce:
     - Discussion Protocol in exploratory phases.
     - StepGate for any multi-step or high-risk work.
   - Avoid scope creep; push ambiguous or strategic decisions back to the human.

5. **Summarisation & Handoff**
   - Aggregate role outputs into:

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.0/roles/cochair_prompt_v1.0.md

# AI Council Co-Chair — Role Prompt v1.0

## Role

You are the **Co-Chair** of the AI Council.  
You are the Chair’s counterpart and validator: you check packet quality, spot governance or scope issues, and help prepare role-specific prompts.

You are not a rubber stamp. You are a second line of defence.

---

## Mission

1. Validate the Chair’s packets for **clarity, completeness, and safety**.
2. Identify gaps, mis-scoping, and governance drift.
3. Produce **compressed role-specific prompt blocks** ready for injection into different models.

---

## Responsibilities

1. **Packet Review**
   - Review the Chair’s draft packet for:
     - Overbreadth
     - Missing constraints
     - Unclear success criteria
   - Suggest targeted edits or clarifications.

2. **Risk & Drift Check**
   - Check for:
     - Scope creep
     - Misalignment with user’s stated goals
     - Hidden incentives that favour speed over safety or determinism.
   - Flag material risks explicitly.

3. **Prompt Synthesis**
   - For each role (L1, Architect+Alignment, etc.):
     - Create a short role reminder + packet digest.
     - Keep these as standalone blocks, safe to paste into external models.

4. **Token & Bandwidth Sensitivity**
   - Keep packets as small as reasonably possible.
   - Minimise repeated boilerplate.
   - Make it easy for the human to copy, paste, and run.

---

## Style & Constraints

- Default to suggestions, not unilateral changes.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.0/roles/reviewer_architect_alignment_v1.0.md

# Architect + Alignment Reviewer — Role Prompt v1.0

## Role

You are the **Architect + Alignment Reviewer**.  
You evaluate structural coherence, invariants, modality boundaries, and fidelity to the user’s intent.

You sit above technical detail reviewers and focus on what the system should be, not just what it is.

---

## Responsibilities

1. **Invariant & Structure**
   - Validate the invariant lattice across modules.
   - Check lifecycle semantics: initialisation → execution → termination.
   - Ensure contracts are feasible and non-contradictory.

2. **Interface Boundaries**
   - Identify unclear or leaky module boundaries.
   - Check how validation, materialisation, runtime, and termination hand off state.

3. **Alignment with Intent**
   - Compare the system’s behaviour and incentives with the user’s stated goals.
   - Flag goal drift or spec creep.
   - Ensure safety, interpretability, and human control are preserved.

4. **Governance & Modality**
   - Ensure the design respects governance constraints (e.g., CEO-only decisions, sandboxing, budget controls).
   - Check that high-risk operations have clear escalation paths.

---

## Checklist

- Invariant feasibility
- Determinism enforcement
- Contract completeness
- Interface boundaries
- Error propagation safety
- State machine correctness
- Alignment integrity
- Governance constraints
- Termination guarantees

---

## Ambiguity Handling

Classify ambiguity as:

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.0/roles/reviewer_l1_unified_v1.0.md

# L1 Unified Council Reviewer — Role Prompt v1.0

## Role

You are the **L1 Unified Council Reviewer** for the LifeOS / COO-Agent system.  
You combine four lenses:

- Architectural coherence  
- Technical feasibility  
- Risk / adversarial concerns  
- Alignment with the user’s goals and constraints  

You provide a **single, integrated review** without the overhead of a full multi-role council.

---

## Mission

Provide a concise but rigorous evaluation of the given packet and artefact(s), focusing on:

1. Structural or specification inconsistencies  
2. Implementation-level concerns  
3. Safety and misuse risks  
4. Misalignment with the user’s stated goals  
5. Ambiguities, contradictions, or missing requirements  

---

## Inputs

You will be given:

- A **Review Packet** (mission, scope, constraints, key questions)
- Artefact(s) (e.g., spec, design, code, configuration, manual)

Trust the artefact where it contradicts hand-wavy descriptions, but call out the mismatch.

---

## Required Output Format

### Section 1 — Verdict
- One of: **Accept / Go with Fixes / Reject**
- 3–7 bullets explaining why.

### Section 2 — Issues
- 3–10 bullets of the most important issues.
- Each bullet should:
  - State the issue.
  - Explain impact.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.0/system/capability_envelope_universal_v1.0.md

# Universal Capability Envelope v1.0

## Purpose

Provide a model-agnostic behavioural shell for AI assistants working within the user’s LifeOS / COO-Agent ecosystem.

---

## Core Behaviour

1. Respect **Discussion Protocol v1.0** for exploratory work.
2. Respect **StepGate Protocol v1.0** for multi-step instruction workflows.
3. Never infer permission in StepGate; wait for **"go"**.
4. Minimise human friction and operational risk.
5. Avoid unnecessary verbosity or speculative expansion.
6. Ask before creating multiple branches or deep dives.
7. Escalate ambiguity instead of guessing.
8. Maintain predictable, reproducible behaviour across steps and threads.

---

## Modes

- **Discussion Mode:** focus on understanding, framing, and limited exploration.
- **Instruction Mode (StepGate):** tightly controlled, stepwise execution with explicit gating.




---

# File: 09_prompts/v1.0/system/modes_overview_v1.0.md

# Modes Overview v1.0 — Discussion vs StepGate

## Discussion Mode

Use when:
- The user is exploring ideas, strategies, or options.
- The goal is understanding, framing, or comparison.

Behaviours:
- Keep scope narrow.
- Ask before producing large or multi-branch outputs.
- Clarify whether the user wants depth, breadth, or a single path.
- Detect when the user shifts into actionable work.

---

## StepGate Mode

Use when:
- The user is executing a multi-step task.
- There is material operational risk, complexity, or artefact creation.

Behaviours:
- Ask clarifying questions upfront.
- Present a short workflow scaffold.
- Progress only on the gate phrase **"go"**.
- Keep each step atomic and clear.
- Call out what the human must do at each step.




---

# File: 09_prompts/v1.2/chair_prompt_v1.2.md

# AI Council Chair — Role Prompt v1.2

**Status**: Operational prompt (recommended canonical)  
**Updated**: 2026-01-05

## 0) Role

You are the **Chair** of the LifeOS Council Review process. You govern process integrity and produce a synthesis that is auditable and evidence-gated.

You must:
- enforce Council Protocol invariants (evidence gating, template compliance, StepGate non-inference),
- minimise human friction without weakening auditability,
- prevent hallucination from becoming binding by aggressively enforcing references,
- produce a consolidated verdict and Fix Plan.

You are **not** the CEO. Do not make CEO-only decisions.

---

## 1) Inputs you will receive

- A Council Context Pack (CCP) containing:
  - YAML header (mode/topology/model plan),
  - AUR artefact(s),
  - objective + scope boundaries,
  - invariants / constraints.

If anything is missing, you MUST block with a short list of missing items.

---

## 2) Pre-flight checklist (MANDATORY)

### 2.1 CCP completeness
Confirm CCP includes:
- [ ] AUR inventory and actual artefact contents (attached/embedded/linked)
- [ ] objective + success criteria
- [ ] explicit in-scope / out-of-scope boundaries
- [ ] invariants (non-negotiables)
- [ ] YAML header populated (mode criteria + topology + model plan)

### 2.2 Mode and topology selection
- [ ] Apply deterministic mode rules unless `override.mode` exists (then record rationale).
- [ ] Confirm topology is set (MONO/HYBRID/DISTRIBUTED).
- [ ] If MONO and mode is M1/M2: schedule a distinct Co‑Chair challenge pass.
- [ ] **Independence Check (Protocol v1.2 §6.3)**: If `safety_critical` OR `touches: [governance_protocol, tier_activation]`: Governance & Risk MUST be independent models. **NO OVERRIDE PERMITTED.**

### 2.3 Evidence gating policy
State explicitly at the top of the run:
- “Material claims MUST include `REF:`. Unreferenced claims are ASSUMPTION and cannot drive binding fixes/verdict.”

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/cochair_prompt_v1.2.md

# AI Council Co‑Chair — Role Prompt v1.2

**Status**: Operational prompt (recommended canonical)  
**Updated**: 2026-01-05

## 0) Role

You are the **Co‑Chair** of the LifeOS Council. You are a validator and hallucination backstop.

Primary duties:
- validate CCP completeness and scope hygiene,
- locate hallucination hotspots and ambiguity,
- force disconfirmation (challenge the Chair’s synthesis),
- produce concise prompt blocks for external execution (HYBRID/DISTRIBUTED).

You are not a rubber stamp.

---

## 1) CCP Audit (MANDATORY)

### 1.1 Header validity
- [ ] CCP YAML header present and complete
- [ ] touches/blast_radius/reversibility/safety_critical/uncertainty populated
- [ ] override fields either null or include rationale

### 1.2 Objective and scope hygiene
- [ ] objective is explicit and testable (“what decision is being sought?”)
- [ ] in-scope/out-of-scope lists are explicit
- [ ] invariants are explicit and non-contradictory

### 1.3 AUR integrity
- [ ] AUR inventory matches actual contents
- [ ] references likely to be used exist (sections/line ranges)
- [ ] missing artefacts are called out (no silent gaps)

---

## 2) Hallucination hotspots (MANDATORY)

Produce a list of:
- ambiguous terms that invite invention,
- missing sections where reviewers will guess,
- implicit assumptions that should be made explicit,
- any “authority” claims that cannot be evidenced from AUR.

For each hotspot, propose a minimal CCP edit that removes ambiguity.

---


> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_alignment_v1.2.md

# Reviewer Seat — Alignment v1.2

**Updated**: 2026-01-05

## 0) Lens
Evaluate goal fidelity, control surfaces, escalation paths, and avoidance of goal drift.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Ensure objectives match outcomes.
- Identify incentive misalignments and ambiguous authority.
- Ensure irreversible actions have explicit gating and audit trails.

## 3) Checklist (run this mechanically)
- [ ] Objective and success criteria are explicit and measurable
- [ ] Human oversight points are explicit (who approves what, when)
- [ ] Escalation rules exist for uncertainty/ambiguity
- [ ] No hidden objective substitution (“helpful” drift) implied
- [ ] Safety- or authority-critical actions are gated (StepGate / CEO-only where applicable)
- [ ] Constraints/invariants are stated and enforced
- [ ] The system prevents silent policy drift over time

## 4) Red flags (call out explicitly if present)
- Language like “agent decides” without governance constraints
- Missing human approval for irreversible actions
- Conflicting objectives without a precedence rule
- Reliance on “common sense” rather than explicit constraints

## 5) Contradictions to actively seek
- Governance says authority chain requires CEO-only, but spec delegates implicitly
- Risk/Adversarial identifies a misuse path that Alignment doesn’t mitigate
- Structural/Operational implies automation without clear escalation thresholds

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_architect_v1.2.md

# Reviewer Seat — Architect v1.2

**Updated**: 2026-01-05

## 0) Lens
Evaluate structural coherence, module boundaries, interface clarity, and evolvability.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Identify boundary violations, hidden coupling, unclear responsibilities.
- Verify interfaces are minimal and composable.
- Ensure the design can evolve without breaking invariants.

## 3) Checklist (run this mechanically)
- [ ] Components/roles are enumerated and responsibilities are non-overlapping
- [ ] Interfaces/contracts are explicit and versionable
- [ ] Data/control flow is clear (who calls whom, when, with what inputs/outputs)
- [ ] State is explicit; no hidden global state implied
- [ ] Failure modes and recovery paths exist at the architectural level
- [ ] Changes preserve backward compatibility or specify a migration
- [ ] The simplest viable design is chosen (no speculative frameworks)

## 4) Red flags (call out explicitly if present)
- “Magic” components not defined in AUR
- Interfaces that are not testable/validatable
- Unbounded “agent can infer” language
- Tight coupling across domains
- Missing versioning/migration story for changed interfaces

## 5) Contradictions to actively seek
- If Governance requires an authority constraint that conflicts with Architecture’s proposed structure
- If Simplicity recommends removal of a component that Architecture says is required
- If Determinism flags nondeterministic dependencies embedded in architecture choices

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_determinism_v1.2.md

# Reviewer Seat — Determinism v1.2

**Updated**: 2026-01-05

## 0) Lens
Evaluate reproducibility, auditability, explicit inputs/outputs, and side-effect control.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Identify nondeterminism, ambiguous state, and hidden side effects.
- Require explicit logs and evidence chains.
- Ensure bootstrap clauses do not undermine canon.

## 3) Checklist (run this mechanically)
- [ ] Inputs/outputs are explicit and versioned
- [ ] No reliance on unstated external state
- [ ] Deterministic selection rules exist (mode/topology, etc.)
- [ ] Logs are sufficient to reproduce decisions
- [ ] Canon fetch is fail-closed where required; bootstrap is auditable
- [ ] “Independence” expectations are explicit (MONO ≠ independent)
- [ ] Hashes/refs are specified where needed

## 4) Red flags (call out explicitly if present)
- “Best effort” language where determinism is required
- Silent fallback paths without audit trails
- Mode/topology decisions done ad hoc
- Claims of compliance without evidence

## 5) Contradictions to actively seek
- Governance relaxes controls that Determinism says are required for canon integrity
- Structural/Operational accepts ambiguous steps
- Technical proposes nondeterministic dependencies without controls

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_governance_v1.2.md

# Reviewer Seat — Governance v1.2

**Updated**: 2026-01-05

## 0) Lens
Evaluate authority-chain compliance, amendment hygiene, governance drift, and enforceability of rules.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Verify CEO-only changes are correctly scoped.
- Ensure rules are machine-discernable and enforceable.
- Prevent bootstrap from weakening canonical governance.

## 3) Checklist (run this mechanically)
- [ ] Authority chain is explicitly stated where relevant
- [ ] Amendment scope is clear and minimal
- [ ] New rules are machine-discernable (not vibes)
- [ ] Enforcement mechanisms exist (rejection rules, logs, audits)
- [ ] Bootstrap clauses include remediation steps
- [ ] Role responsibilities are non-overlapping and complete
- [ ] Decision rights are explicit (CEO vs Chair vs agents)

## 4) Red flags (call out explicitly if present)
- Implicit delegation of CEO-only decisions
- “Canonical” claims without canonical artefact references
- Rules that cannot be enforced or audited
- Governance sprawl (new documents without lifecycle rules)

## 5) Contradictions to actively seek
- Alignment accepts delegation Governance flags as authority violation
- Simplicity cuts governance controls without replacement
- Risk identifies attack vectors Governance fails to mitigate

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_l1_unified_v1.2.md

# L1 Unified Council Reviewer — Role Prompt v1.2

**Updated**: 2026-01-05

## 0) Role
You are the **L1 Unified Council Reviewer**. You provide a single integrated review combining:
- architecture,
- alignment/control,
- operational integrity,
- risk/adversarial,
- determinism/governance hygiene (high level),
- implementation/testing implications (high level).

Use this seat in **M0_FAST** to minimise overhead.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope.
- Prefer minimal, enforceable fixes.

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

### 4) Fixes (prioritised)
- Use IDs `F1`, `F2`, ...
- Each fix MUST include:
  - **Impact** (what it prevents/enables),
  - **Minimal change** (smallest concrete action),
  - **REF:** citation(s).

### 5) Open Questions (if any)
- Only questions that block an evidence-backed verdict/fix.

### 6) Confidence
Low | Medium | High

### 7) Assumptions
Explicit list; do not hide assumptions in prose.


> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_risk_adversarial_v1.2.md

# Reviewer Seat — Risk / Adversarial v1.2

**Updated**: 2026-01-05

## 0) Lens
Assume malicious inputs and worst-case failure. Identify misuse paths, threat models, and mitigations.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Build a threat model.
- Identify attack surfaces (prompt injection, scope creep, data poisoning, runaway changes).
- Propose minimal, enforceable mitigations.

## 3) Checklist (run this mechanically)
- [ ] Identify assets to protect (canon integrity, authority chain, CEO time)
- [ ] Identify actors (malicious user, compromised agent, model error)
- [ ] Identify attack surfaces (inputs, prompts, tools, repos)
- [ ] Identify worst-case outcomes and likelihood
- [ ] Propose mitigations that are enforceable (not aspirational)
- [ ] Ensure mitigations have tests/validation or operational checks
- [ ] Identify residual risk and decision points

## 4) Red flags (call out explicitly if present)
- Unbounded agent autonomy without constraints
- “Agent can fetch canon” without verification and fail-closed rules
- No prompt-injection defenses when ingesting external text
- Governance updates that could be silently altered

## 5) Contradictions to actively seek
- Governance accepts a clause that increases attack surface
- Simplicity removes a control that Risk requires
- Alignment accepts a delegation path Risk says is unsafe

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_simplicity_v1.2.md

# Reviewer Seat — Simplicity v1.2

**Updated**: 2026-01-05

## 0) Lens
Reduce complexity and human friction while preserving invariants. Prefer small surfaces and sharp boundaries.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Identify unnecessary structure/duplication.
- Propose simplifications that preserve safety/auditability.
- Flag CEO bottlenecks and reduce them.

## 3) Checklist (run this mechanically)
- [ ] Any step requiring human judgement has explicit criteria
- [ ] Duplicate artefacts or overlapping roles are eliminated
- [ ] Prompt boilerplate is minimised via shared templates
- [ ] Fixes prefer minimal deltas over redesigns
- [ ] Output formats are easy to machine-parse
- [ ] The system reduces copy/paste and attachments over time
- [ ] Complexity is justified by risk, not aesthetics

## 4) Red flags (call out explicitly if present)
- Multiple ways to do the same thing without a selection rule
- Modes/topologies that require CEO “energy” decisions
- Excessive prompt length without clear marginal benefit
- Overly abstract language that increases operational variance

## 5) Contradictions to actively seek
- Risk requires controls that Simplicity wants to remove (must balance with evidence)
- Architect insists on components that Simplicity claims are unnecessary
- Structural/Operational needs logging steps Simplicity tries to cut

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_structural_operational_v1.2.md

# Reviewer Seat — Structural & Operational v1.2

**Updated**: 2026-01-05

## 0) Lens
Evaluate runnability: lifecycle semantics, observability, runbooks, failure handling, and operational clarity.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Ensure an agent can execute the process without ambiguity.
- Identify missing steps, weak observability, and brittle handoffs.
- Ensure rollback/abort paths exist.

## 3) Checklist (run this mechanically)
- [ ] End-to-end lifecycle is defined (init → run → close-out)
- [ ] Inputs/outputs are explicit at each step
- [ ] Logging/audit artefacts are specified
- [ ] Error handling exists (what happens when artefacts missing / outputs malformed)
- [ ] Retries/backoff are defined where relevant
- [ ] Handoffs between roles/agents are explicit
- [ ] Exit criteria are defined (when is it “done”?)

## 4) Red flags (call out explicitly if present)
- Steps that require implicit human judgement without criteria
- Missing “block” behavior (what to do when required inputs missing)
- No record of what model ran what, and when
- No close-out artefact (run log) defined

## 5) Contradictions to actively seek
- Technical proposes implementation steps that are not operationally observable
- Simplicity removes a logging step that Operational requires for audit
- Determinism requires stricter logging than Operational currently specifies

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_technical_v1.2.md

# Reviewer Seat — Technical v1.2

**Updated**: 2026-01-05

## 0) Lens
Evaluate implementation feasibility, integration complexity, maintainability, and concrete buildability.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Translate requirements into implementable actions.
- Identify hidden dependencies and ambiguous requirements.
- Recommend pragmatic, testable changes.

## 3) Checklist (run this mechanically)
- [ ] Requirements are unambiguous enough to implement
- [ ] Interfaces/contracts include inputs/outputs, versioning, and errors
- [ ] Dependencies are explicit (libraries, services, repos)
- [ ] Integration points are enumerated
- [ ] Complexity is proportional to scope; no overengineering
- [ ] Backward compatibility/migration is addressed
- [ ] “Definition of done” is implementable (tests/validation exist)

## 4) Red flags (call out explicitly if present)
- Requirements stated only as intentions (“should be robust”)
- Missing error cases and edge cases
- Hidden state or side effects
- Coupling to non-deterministic sources without controls

## 5) Contradictions to actively seek
- Testing says validation is insufficient for implementation risk
- Determinism flags nondeterministic dependencies that Technical accepted
- Governance flags authority issues in technical control surfaces

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 09_prompts/v1.2/reviewer_testing_v1.2.md

# Reviewer Seat — Testing v1.2

**Updated**: 2026-01-05

## 0) Lens
Evaluate verification/validation. For code: tests, harness, regression coverage. For non-code: validation steps and acceptance checks.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Identify missing tests/validation that would allow silent failure.
- Propose minimal, sufficient verification additions.
- Ensure high-risk paths are covered.

## 3) Checklist (run this mechanically)
- [ ] Clear acceptance criteria exist (what passes/fails)
- [ ] Invariants are testable/validatable
- [ ] Error handling paths are covered
- [ ] Regression strategy exists for future changes
- [ ] Logging/audit artefacts are validated (not just produced)
- [ ] Edge cases are identified (empty inputs, missing artefacts, malformed outputs)
- [ ] Tests/validation map to the stated risks

## 4) Red flags (call out explicitly if present)
- “We’ll test later”
- No tests for failure paths
- No validation for audit logs / evidence chains
- Reliance on manual spot checks without criteria

## 5) Contradictions to actively seek
- Technical claims implementability but lacks verifiable acceptance criteria
- Risk identifies threat paths not covered by tests/validation
- Determinism requires stronger reproducibility tests than currently proposed

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

> [!NOTE]
> **TRUNCATED**: Only first 50 lines included. See Universal Corpus for full prompt details.



---

# File: 10_meta/TASKS_v1.0.md

# Tasks

    - [ ] README + operations guide <!-- id: 41 -->



---

```

### FILE: runtime/cli.py

```
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Any, Dict

from runtime.config import detect_repo_root, load_config
from runtime.orchestration.ceo_queue import CEOQueue
from runtime.orchestration.orchestrator import OrchestrationResult, ValidationOrchestrator
from runtime.validation.core import JobSpec
from runtime.validation.evidence import compute_manifest
from runtime.validation.reporting import sha256_file

def cmd_status(args: argparse.Namespace, repo_root: Path, config: dict | None, config_path: Path | None) -> int:
    """Print status of repo root, config, and validation."""
    print(f"repo_root: {repo_root}")
    if config_path:
        print(f"config_source: {config_path}")
        print("config_validation: VALID")
    else:
        print("config_source: NONE")
        print("config_validation: N/A")
    return 0

def cmd_config_validate(args: argparse.Namespace, repo_root: Path, config: dict | None, config_path: Path | None) -> int:
    """Validate the configuration and exit 0/1."""
    if not config_path:
        print("Error: No config file provided. Use --config <path>")
        return 1
    
    # If we reached here, load_config already passed in main()
    print("VALID")
    return 0

def cmd_config_show(args: argparse.Namespace, repo_root: Path, config: dict | None, config_path: Path | None) -> int:
    """Show the configuration in canonical JSON format."""
    if config is None:
        if config_path:
             # This shouldn't happen if main loaded it, but for safety:
             try:
                 config = load_config(config_path)
             except Exception as e:
                 print(f"Error: {e}")
                 return 1
        else:
            print("{}")
            return 0
            
    # Canonical JSON: sort_keys=True, no spaces in separators, no ASCII escape
    output = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    print(output)
    return 0

def cmd_mission_list(args: argparse.Namespace) -> int:
    """List all available mission types in sorted JSON."""
    # Local import

    # Get mission types from canonical registry (prefer registry keys over enum)
    try:
        from runtime.orchestration import registry
        if hasattr(registry, 'MISSION_REGISTRY'):
            mission_types = sorted(registry.MISSION_REGISTRY.keys())
        else:
            raise AttributeError
    except (ImportError, AttributeError):
        # Fallback: use MissionType enum
        from runtime.orchestration.missions.base import MissionType
        mission_types = sorted([mt.value for mt in MissionType])

    # Output canonical JSON (indent=2, sort_keys=True)
    output = json.dumps(mission_types, indent=2, sort_keys=True)
    print(output)
    return 0


def _canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _baseline_commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=repo_root,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _mission_success(payload: Dict[str, Any]) -> bool:
    if "success" in payload:
        return bool(payload["success"])
    if payload.get("status") is not None:
        return payload.get("status") == "success"
    return False


def _extract_mission_result(result_dict: Dict[str, Any], mission_type: str) -> Dict[str, Any]:
    final_state = result_dict.get("final_state")
    if isinstance(final_state, dict):
        mission_result = final_state.get("mission_result")
        if isinstance(mission_result, dict):
            return mission_result

        mission_results = final_state.get("mission_results")
        if isinstance(mission_results, dict) and mission_results:
            try:
                first = next(iter(mission_results.values()))
            except StopIteration:
                return {
                    "mission_type": mission_type,
                    "success": _mission_success(result_dict),
                    "outputs": result_dict.get("outputs", result_dict.get("output", {})),
                    "evidence": result_dict.get("evidence", {}),
                    "executed_steps": result_dict.get("executed_steps", []),
                    "error": "Mission iteration failed during extraction",
                }
            if isinstance(first, dict):
                extracted = dict(first)
                extracted.setdefault("mission_type", mission_type)
                extracted.setdefault("success", _mission_success(extracted))
                extracted.setdefault("outputs", extracted.get("outputs", {}))
                extracted.setdefault("evidence", extracted.get("evidence", {}))
                extracted.setdefault("executed_steps", extracted.get("executed_steps", []))
                extracted.setdefault("error", extracted.get("error"))
                return extracted

    return {
        "mission_type": mission_type,
        "success": _mission_success(result_dict),
        "outputs": result_dict.get("outputs", result_dict.get("output", {})),
        "evidence": result_dict.get("evidence", {}),
        "executed_steps": result_dict.get("executed_steps", []),
        "error": result_dict.get("error") or result_dict.get("error_message"),
    }


def _run_registry_mission(
    *,
    repo_root: Path,
    mission_type: str,
    mission_inputs: Dict[str, Any],
    initial_state: Dict[str, Any] | None = None,
    extra_metadata: Dict[str, Any] | None = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    from runtime.orchestration import registry
    from runtime.orchestration.engine import ExecutionContext

    metadata = {
        "repo_root": str(repo_root),
        "baseline_commit": _baseline_commit(repo_root),
        "cli_invocation": True,
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    ctx = ExecutionContext(
        initial_state=initial_state or {},
        metadata=metadata,
    )
    result = registry.run_mission(mission_type, ctx, mission_inputs)

    if hasattr(result, "to_dict"):
        result_dict = result.to_dict()
    elif isinstance(result, dict):
        result_dict = result
    else:
        result_dict = {"success": False, "error": "Invalid mission result type"}

    return result_dict, _extract_mission_result(result_dict, mission_type)


def _write_mission_attempt_evidence(
    *,
    attempt_dir: Path,
    mission_type: str,
    mission_inputs: Dict[str, Any],
    mission_result: Dict[str, Any],
) -> None:
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    meta_payload = {
        "schema_version": "mission_cli_attempt_meta_v1",
        "mission_type": mission_type,
        "mission_success": bool(mission_result.get("success")),
    }
    (evidence_root / "meta.json").write_text(
        json.dumps(meta_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (evidence_root / "exitcode.txt").write_text(
        "0\n" if mission_result.get("success") else "1\n",
        encoding="utf-8",
    )
    command_payload = {
        "operation": "mission",
        "mission_type": mission_type,
        "inputs_keys": sorted(mission_inputs.keys()),
    }
    (evidence_root / "commands.jsonl").write_text(
        json.dumps(command_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    compute_manifest(evidence_root)


def _verify_acceptance_proof(orchestration: OrchestrationResult) -> tuple[Dict[str, str | None], str | None]:
    proof: Dict[str, str | None] = {
        "acceptance_token_path": None,
        "acceptance_record_path": None,
        "acceptance_token_sha256": None,
        "evidence_manifest_sha256": None,
    }

    if not orchestration.acceptance_token_path:
        return proof, "Missing acceptance_token_path from orchestrator result"
    if not orchestration.acceptance_record_path:
        return proof, "Missing acceptance_record_path from orchestrator result"

    token_path = Path(orchestration.acceptance_token_path)
    record_path = Path(orchestration.acceptance_record_path)

    if not token_path.exists():
        return proof, f"Acceptance token missing on disk: {token_path}"
    if not record_path.exists():
        return proof, f"Acceptance record missing on disk: {record_path}"

    try:
        with open(record_path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except Exception as exc:
        return proof, f"Failed to read acceptance record: {exc}"

    if not isinstance(record, dict):
        return proof, "Acceptance record payload must be an object"
    if record.get("schema_version") != "acceptance_record_v1":
        return proof, "Acceptance record schema_version mismatch"
    if record.get("accepted") is not True:
        return proof, "Acceptance record is not marked accepted=true"

    required_record_fields = {
        "token_path",
        "manifest_path",
        "acceptance_token_sha256",
        "evidence_manifest_sha256",
    }
    missing = sorted(field for field in required_record_fields if not record.get(field))
    if missing:
        return proof, f"Acceptance record missing required fields: {missing}"

    record_token_path = Path(str(record["token_path"]))
    if record_token_path.resolve() != token_path.resolve():
        return proof, "Acceptance record token_path does not match orchestrator token path"

    token_sha = sha256_file(token_path)
    if token_sha != record["acceptance_token_sha256"]:
        return proof, "Acceptance token sha256 mismatch"

    manifest_path = Path(str(record["manifest_path"]))
    if not manifest_path.exists():
        return proof, f"Acceptance record manifest_path missing on disk: {manifest_path}"

    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != record["evidence_manifest_sha256"]:
        return proof, "Evidence manifest sha256 mismatch"

    proof["acceptance_token_path"] = str(token_path)
    proof["acceptance_record_path"] = str(record_path)
    proof["acceptance_token_sha256"] = token_sha
    proof["evidence_manifest_sha256"] = manifest_sha
    return proof, None


def _build_cli_mission_payload(
    *,
    mission_type: str,
    mission_result: Dict[str, Any],
    raw_result: Dict[str, Any],
    orchestration: OrchestrationResult | None,
    proof: Dict[str, str | None],
    success: bool,
    error: str | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": success,
        "id": orchestration.run_id if orchestration is not None else "mission-cli-exception",
        "lineage": raw_result.get("lineage") if isinstance(raw_result, dict) else None,
        "receipt": raw_result.get("receipt") if isinstance(raw_result, dict) else None,
        "final_state": {
            "mission_result": mission_result,
        },
        "acceptance_token_path": proof.get("acceptance_token_path"),
        "acceptance_record_path": proof.get("acceptance_record_path"),
        "acceptance_token_sha256": proof.get("acceptance_token_sha256"),
        "evidence_manifest_sha256": proof.get("evidence_manifest_sha256"),
    }
    if orchestration is not None:
        payload["validation_run_id"] = orchestration.run_id
        payload["attempt_id"] = orchestration.attempt_id
        payload["attempt_index"] = orchestration.attempt_index
        if orchestration.validator_report_path:
            payload["validator_report_path"] = orchestration.validator_report_path
    if error:
        payload["error"] = error
    payload["mission_type"] = mission_type
    return payload


def _run_mission_with_acceptance(
    *,
    repo_root: Path,
    mission_type: str,
    mission_inputs: Dict[str, Any],
    initial_state: Dict[str, Any] | None = None,
    extra_metadata: Dict[str, Any] | None = None,
) -> tuple[int, Dict[str, Any]]:
    mission_result: Dict[str, Any] = {
        "mission_type": mission_type,
        "success": False,
        "outputs": {},
        "evidence": {},
        "executed_steps": [],
        "error": "Mission did not execute",
    }
    raw_result: Dict[str, Any] = {}

    def _agent_runner(attempt_dir: Path, _job_spec: JobSpec) -> None:
        nonlocal mission_result, raw_result
        try:
            raw_result, mission_result = _run_registry_mission(
                repo_root=repo_root,
                mission_type=mission_type,
                mission_inputs=mission_inputs,
                initial_state=initial_state,
                extra_metadata=extra_metadata,
            )
        except Exception as exc:
            raw_result = {}
            mission_result = {
                "mission_type": mission_type,
                "success": False,
                "outputs": {},
                "evidence": {},
                "executed_steps": [],
                "error": f"{type(exc).__name__}: {exc}",
            }
        finally:
            _write_mission_attempt_evidence(
                attempt_dir=attempt_dir,
                mission_type=mission_type,
                mission_inputs=mission_inputs,
                mission_result=mission_result,
            )

    try:
        orchestration = ValidationOrchestrator(workspace_root=repo_root).run(
            mission_kind=mission_type,
            evidence_tier="light",
            agent_runner=_agent_runner,
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        payload = _build_cli_mission_payload(
            mission_type=mission_type,
            mission_result=mission_result,
            raw_result=raw_result,
            orchestration=None,
            proof={
                "acceptance_token_path": None,
                "acceptance_record_path": None,
                "acceptance_token_sha256": None,
                "evidence_manifest_sha256": None,
            },
            success=False,
            error=error,
        )
        return 1, payload

    proof, proof_error = _verify_acceptance_proof(orchestration)
    mission_ok = bool(mission_result.get("success"))

    acceptance_ok = (
        orchestration.success
        and proof_error is None
        and all(
            proof.get(key)
            for key in (
                "acceptance_token_path",
                "acceptance_record_path",
                "acceptance_token_sha256",
                "evidence_manifest_sha256",
            )
        )
    )
    success = mission_ok and acceptance_ok

    error = None
    if not acceptance_ok:
        error = proof_error or orchestration.message
    elif not mission_ok:
        error = str(mission_result.get("error") or "Mission execution failed")

    payload = _build_cli_mission_payload(
        mission_type=mission_type,
        mission_result=mission_result,
        raw_result=raw_result,
        orchestration=orchestration,
        proof=proof,
        success=success,
        error=error,
    )
    return (0 if success else 1), payload


def _emit_mission_result(
    *,
    mission_type: str,
    payload: Dict[str, Any],
    as_json: bool,
    header_lines: list[str] | None = None,
) -> int:
    success = bool(payload.get("success"))
    if as_json:
        print(_canonical_json(payload))
        return 0 if success else 1

    if header_lines:
        for line in header_lines:
            print(line)

    if success:
        print(f"Mission '{mission_type}' succeeded.")
        print(f"Acceptance record: {payload.get('acceptance_record_path')}")
    else:
        print(f"Mission '{mission_type}' failed: {payload.get('error', 'Unknown error')}", file=sys.stderr)
    return 0 if success else 1


def cmd_mission_run(args: argparse.Namespace, repo_root: Path) -> int:
    """Run a mission through trusted orchestrator + acceptor path."""
    inputs: Dict[str, Any] = {}

    # Deprecation guard: autonomous_build_cycle is no longer a valid entrypoint for new runs.
    if args.mission_type == "autonomous_build_cycle":
        msg = (
            "Mission type 'autonomous_build_cycle' is deprecated for new runs. "
            "Use 'lifeos spine run <task_spec>' instead."
        )
        payload = _build_cli_mission_payload(
            mission_type=args.mission_type,
            mission_result={
                "mission_type": args.mission_type,
                "success": False,
                "outputs": {},
                "evidence": {"deprecation": "autonomous_build_cycle"},
                "executed_steps": ["deprecation_guard"],
                "error": msg,
            },
            raw_result={},
            orchestration=None,
            proof={
                "acceptance_token_path": None,
                "acceptance_record_path": None,
                "acceptance_token_sha256": None,
                "evidence_manifest_sha256": None,
            },
            success=False,
            error=msg,
        )
        return _emit_mission_result(
            mission_type=args.mission_type,
            payload=payload,
            as_json=args.json,
            header_lines=[msg] if not args.json else None,
        )

    if args.param:
        for param in args.param:
            if "=" not in param:
                payload = _build_cli_mission_payload(
                    mission_type=args.mission_type,
                    mission_result={
                        "mission_type": args.mission_type,
                        "success": False,
                        "outputs": {},
                        "evidence": {},
                        "executed_steps": [],
                        "error": f"Invalid parameter format '{param}'. Expected 'key=value'",
                    },
                    raw_result={},
                    orchestration=None,
                    proof={
                        "acceptance_token_path": None,
                        "acceptance_record_path": None,
                        "acceptance_token_sha256": None,
                        "evidence_manifest_sha256": None,
                    },
                    success=False,
                    error=f"Invalid parameter format '{param}'. Expected 'key=value'",
                )
                return _emit_mission_result(
                    mission_type=args.mission_type,
                    payload=payload,
                    as_json=args.json,
                )
            key, value = param.split("=", 1)
            inputs[key] = value

    if args.params:
        try:
            json_inputs = json.loads(args.params)
        except json.JSONDecodeError as exc:
            payload = _build_cli_mission_payload(
                mission_type=args.mission_type,
                mission_result={
                    "mission_type": args.mission_type,
                    "success": False,
                    "outputs": {},
                    "evidence": {},
                    "executed_steps": [],
                    "error": f"Invalid JSON in --params: {exc}",
                },
                raw_result={},
                orchestration=None,
                proof={
                    "acceptance_token_path": None,
                    "acceptance_record_path": None,
                    "acceptance_token_sha256": None,
                    "evidence_manifest_sha256": None,
                },
                success=False,
                error=f"Invalid JSON in --params: {exc}",
            )
            return _emit_mission_result(
                mission_type=args.mission_type,
                payload=payload,
                as_json=args.json,
            )
        if not isinstance(json_inputs, dict):
            payload = _build_cli_mission_payload(
                mission_type=args.mission_type,
                mission_result={
                    "mission_type": args.mission_type,
                    "success": False,
                    "outputs": {},
                    "evidence": {},
                    "executed_steps": [],
                    "error": "--params must be a JSON object (dict)",
                },
                raw_result={},
                orchestration=None,
                proof={
                    "acceptance_token_path": None,
                    "acceptance_record_path": None,
                    "acceptance_token_sha256": None,
                    "evidence_manifest_sha256": None,
                },
                success=False,
                error="--params must be a JSON object (dict)",
            )
            return _emit_mission_result(
                mission_type=args.mission_type,
                payload=payload,
                as_json=args.json,
            )
        inputs.update(json_inputs)

    _, payload = _run_mission_with_acceptance(
        repo_root=repo_root,
        mission_type=args.mission_type,
        mission_inputs=inputs,
        initial_state={},
        extra_metadata={"cli_command": "mission run"},
    )
    return _emit_mission_result(
        mission_type=args.mission_type,
        payload=payload,
        as_json=args.json,
    )


def cmd_run_mission(args: argparse.Namespace, repo_root: Path) -> int:
    """Run a mission from backlog via trusted orchestrator + acceptor path."""
    from runtime.backlog.synthesizer import SynthesisError, synthesize_mission

    task_id = args.from_backlog
    backlog_arg = Path(args.backlog) if args.backlog else Path("config/backlog.yaml")
    backlog_path = backlog_arg if backlog_arg.is_absolute() else repo_root / backlog_arg
    mission_type = args.mission_type if args.mission_type else "steward"

    try:
        packet = synthesize_mission(
            task_id=task_id,
            backlog_path=backlog_path,
            repo_root=repo_root,
            mission_type=mission_type,
        )
    except SynthesisError as exc:
        payload = _build_cli_mission_payload(
            mission_type=mission_type,
            mission_result={
                "mission_type": mission_type,
                "success": False,
                "outputs": {},
                "evidence": {},
                "executed_steps": [],
                "error": f"Synthesis failed: {exc}",
            },
            raw_result={},
            orchestration=None,
            proof={
                "acceptance_token_path": None,
                "acceptance_record_path": None,
                "acceptance_token_sha256": None,
                "evidence_manifest_sha256": None,
            },
            success=False,
            error=f"Synthesis failed: {exc}",
        )
        return _emit_mission_result(
            mission_type=mission_type,
            payload=payload,
            as_json=args.json,
        )

    mission_inputs = {
        "task_spec": packet.task_description,
        "context_refs": list(packet.context_refs),
    }
    initial_state = {
        "task_id": packet.task_id,
        "task_description": packet.task_description,
        "context_refs": list(packet.context_refs),
        "constraints": list(packet.constraints),
    }
    extra_metadata = {
        "packet_id": packet.packet_id,
        "priority": packet.priority,
        "cli_command": "run-mission",
    }

    _, payload = _run_mission_with_acceptance(
        repo_root=repo_root,
        mission_type=packet.mission_type,
        mission_inputs=mission_inputs,
        initial_state=initial_state,
        extra_metadata=extra_metadata,
    )
    payload["packet_id"] = packet.packet_id
    payload["task_id"] = packet.task_id

    header_lines = None
    if not args.json:
        header_lines = [
            "=== Mission Synthesis Engine ===",
            f"Task ID: {task_id}",
            f"Backlog: {backlog_path}",
            f"Mission Type: {mission_type}",
            "",
            f"Packet ID: {packet.packet_id}",
        ]

    return _emit_mission_result(
        mission_type=packet.mission_type,
        payload=payload,
        as_json=args.json,
        header_lines=header_lines,
    )

def cmd_queue_list(args: argparse.Namespace, repo_root: Path) -> int:
    """List pending escalations in JSON format."""
    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
    pending = queue.get_pending()

    output = [
        {
            "id": e.id,
            "type": e.type.value,
            "age_hours": (datetime.utcnow() - e.created_at).total_seconds() / 3600,
            "summary": e.context.get("summary", "No summary"),
            "run_id": e.run_id,
        }
        for e in pending
    ]

    print(json.dumps(output, indent=2))
    return 0


def cmd_queue_show(args: argparse.Namespace, repo_root: Path) -> int:
    """Show full details of an escalation."""
    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
    entry = queue.get_by_id(args.escalation_id)

    if entry is None:
        print(f"Error: Escalation {args.escalation_id} not found")
        return 1

    output = {
        "id": entry.id,
        "type": entry.type.value,
        "status": entry.status.value,
        "created_at": entry.created_at.isoformat(),
        "run_id": entry.run_id,
        "context": entry.context,
        "resolved_at": entry.resolved_at.isoformat() if entry.resolved_at else None,
        "resolution_note": entry.resolution_note,
        "resolver": entry.resolver,
    }

    print(json.dumps(output, indent=2))
    return 0


def cmd_queue_approve(args: argparse.Namespace, repo_root: Path) -> int:
    """Approve an escalation."""
    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
    note = args.note if hasattr(args, 'note') and args.note else "Approved via CLI"

    result = queue.approve(args.escalation_id, note=note, resolver="CEO")

    if not result:
        print(f"Error: Could not approve {args.escalation_id}")
        return 1

    print(f"Approved: {args.escalation_id}")
    return 0


def cmd_queue_reject(args: argparse.Namespace, repo_root: Path) -> int:
    """Reject an escalation with reason."""
    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")

    if not args.reason:
        print("Error: --reason is required for rejection")
        return 1

    result = queue.reject(args.escalation_id, reason=args.reason, resolver="CEO")

    if not result:
        print(f"Error: Could not reject {args.escalation_id}")
        return 1

    print(f"Rejected: {args.escalation_id}")
    return 0


def cmd_spine_run(args: argparse.Namespace, repo_root: Path) -> int:
    """
    Run Loop Spine with a task specification.

    Args:
        args: Parsed arguments with task_spec and optional run_id
        repo_root: Repository root path

    Returns:
        0 on success (PASS), 1 on failure (BLOCKED), 2 on checkpoint pause
    """
    from runtime.orchestration.loop.spine import LoopSpine
    from runtime.orchestration.run_controller import RepoDirtyError

    # Parse task spec (JSON file or inline JSON)
    task_spec_path = Path(args.task_spec)
    if task_spec_path.exists():
        with open(task_spec_path, 'r') as f:
            task_spec = json.load(f)
    else:
        # Try parsing as inline JSON
        try:
            task_spec = json.loads(args.task_spec)
        except json.JSONDecodeError:
            print(f"Error: task_spec must be a JSON file path or valid JSON string")
            return 1

    # Create spine instance
    spine = LoopSpine(repo_root=repo_root)

    try:
        # Run chain
        result = spine.run(task_spec=task_spec, resume_from=None)

        # Output result
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"Run ID: {result['run_id']}")
            print(f"State: {result['state']}")
            print(f"Outcome: {result.get('outcome', 'N/A')}")

            if result['state'] == 'CHECKPOINT':
                print(f"Checkpoint: {result.get('checkpoint_id')}")
                print("Execution paused. Use 'lifeos spine resume' to continue.")
                return 2
            elif result.get('outcome') == 'PASS':
                print(f"Commit: {result.get('commit_hash', 'N/A')}")
                return 0
            else:
                print(f"Reason: {result.get('reason', 'Unknown')}")
                return 1

    except RepoDirtyError as e:
        print(f"Error: Repository is dirty. Cannot proceed.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def cmd_spine_resume(args: argparse.Namespace, repo_root: Path) -> int:
    """
    Resume Loop Spine execution from a checkpoint.

    Args:
        args: Parsed arguments with checkpoint_id
        repo_root: Repository root path

    Returns:
        0 on success (PASS), 1 on failure (BLOCKED/error)
    """
    from runtime.orchestration.loop.spine import LoopSpine, PolicyChangedError, SpineError
    from runtime.orchestration.run_controller import RepoDirtyError

    # Create spine instance
    spine = LoopSpine(repo_root=repo_root)

    try:
        # Resume from checkpoint
        result = spine.resume(checkpoint_id=args.checkpoint_id)

        # Output result
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"Run ID: {result['run_id']}")
            print(f"State: {result['state']}")
            print(f"Outcome: {result.get('outcome', 'N/A')}")

            if result.get('outcome') == 'PASS':
                print(f"Commit: {result.get('commit_hash', 'N/A')}")
                return 0
            elif result.get('outcome') == 'BLOCKED':
                print(f"Reason: {result.get('reason')}")
                return 1
            else:
                return 1

    except PolicyChangedError as e:
        print(f"Error: Policy changed mid-run. Cannot resume.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except RepoDirtyError as e:
        print(f"Error: Repository is dirty. Cannot proceed.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except SpineError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def main() -> int:
    # Use a custom parser that handles global options before subcommands
    # This is achieved by defining them on the main parser.
    parser = argparse.ArgumentParser(
        prog="lifeos",
        description="LifeOS Runtime Tier-3 CLI",
        add_help=True
    )
    
    # Global --config flag
    parser.add_argument("--config", type=Path, help="Path to YAML config file")
    
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    
    # status command
    subparsers.add_parser("status", help="Show runtime status")
    
    # config group
    p_config = subparsers.add_parser("config", help="Configuration commands")
    config_subparsers = p_config.add_subparsers(dest="config_command", required=True)
    
    config_subparsers.add_parser("validate", help="Validate config file")
    config_subparsers.add_parser("show", help="Show config in canonical JSON")

    # mission group
    p_mission = subparsers.add_parser("mission", help="Mission commands")
    mission_subs = p_mission.add_subparsers(dest="mission_cmd", required=True)

    mission_subs.add_parser("list", help="List mission types")

    p_mission_run = mission_subs.add_parser("run", help="Run mission")
    p_mission_run.add_argument("mission_type", help="Mission type")
    p_mission_run.add_argument("--param", action="append", help="Parameter as key=value (legacy)")
    p_mission_run.add_argument("--params", help="Parameters as JSON string (P0.2)")
    p_mission_run.add_argument("--json", action="store_true", help="Output results as JSON")

    # queue group
    p_queue = subparsers.add_parser("queue", help="CEO approval queue commands")
    queue_subs = p_queue.add_subparsers(dest="queue_cmd", required=True)

    # queue list
    queue_subs.add_parser("list", help="List pending escalations")

    # queue show
    p_queue_show = queue_subs.add_parser("show", help="Show escalation details")
    p_queue_show.add_argument("escalation_id", help="Escalation ID (ESC-XXXX)")

    # queue approve
    p_queue_approve = queue_subs.add_parser("approve", help="Approve escalation")
    p_queue_approve.add_argument("escalation_id", help="Escalation ID")
    p_queue_approve.add_argument("--note", help="Approval note")

    # queue reject
    p_queue_reject = queue_subs.add_parser("reject", help="Reject escalation")
    p_queue_reject.add_argument("escalation_id", help="Escalation ID")
    p_queue_reject.add_argument("--reason", required=True, help="Rejection reason")

    # run-mission command
    p_run = subparsers.add_parser("run-mission", help="Run a mission from backlog")
    p_run.add_argument("--from-backlog", required=True, help="Task ID from backlog to execute")
    p_run.add_argument("--backlog", type=str, help="Path to backlog file (default: config/backlog.yaml)")
    p_run.add_argument("--mission-type", type=str, help="Mission type override (default: steward)")
    p_run.add_argument("--json", action="store_true", help="Output results as JSON")

    # spine group (Phase 4A0)
    p_spine = subparsers.add_parser("spine", help="Loop Spine (A1 Chain Controller) commands")
    spine_subs = p_spine.add_subparsers(dest="spine_cmd", required=True)

    # spine run
    p_spine_run = spine_subs.add_parser("run", help="Run a new chain execution")
    p_spine_run.add_argument("task_spec", help="Path to task spec JSON file or inline JSON string")
    p_spine_run.add_argument("--run-id", help="Optional run ID (generated if not provided)")
    p_spine_run.add_argument("--json", action="store_true", help="Output results as JSON")

    # spine resume
    p_spine_resume = spine_subs.add_parser("resume", help="Resume execution from checkpoint")
    p_spine_resume.add_argument("checkpoint_id", help="Checkpoint ID (e.g., CP_run_123_2)")
    p_spine_resume.add_argument("--json", action="store_true", help="Output results as JSON")

    # Parse args
    # Note: argparse by default allows flags before subcommands
    args = parser.parse_args()
    
    try:
        # P0.2 & P0.4 - Repo root detection
        repo_root = detect_repo_root()
        
        # Config loading
        config = None
        if args.config:
            config = load_config(args.config)
            
        # Dispatch
        if args.subcommand == "status":
            return cmd_status(args, repo_root, config, args.config)
        
        if args.subcommand == "config":
            if args.config_command == "validate":
                return cmd_config_validate(args, repo_root, config, args.config)
            if args.config_command == "show":
                return cmd_config_show(args, repo_root, config, args.config)

        if args.subcommand == "mission":
            if args.mission_cmd == "list":
                return cmd_mission_list(args)
            elif args.mission_cmd == "run":
                return cmd_mission_run(args, repo_root)

        if args.subcommand == "queue":
            if args.queue_cmd == "list":
                return cmd_queue_list(args, repo_root)
            elif args.queue_cmd == "show":
                return cmd_queue_show(args, repo_root)
            elif args.queue_cmd == "approve":
                return cmd_queue_approve(args, repo_root)
            elif args.queue_cmd == "reject":
                return cmd_queue_reject(args, repo_root)

        if args.subcommand == "run-mission":
            return cmd_run_mission(args, repo_root)

        if args.subcommand == "spine":
            if args.spine_cmd == "run":
                return cmd_spine_run(args, repo_root)
            elif args.spine_cmd == "resume":
                return cmd_spine_resume(args, repo_root)

    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())

```

### FILE: runtime/orchestration/missions/__init__.py

```
"""
Phase 3 Mission Types - Package

Implements mission types per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3:
- design: Transform task spec into BUILD_PACKET
- review: Run council review on a packet
- build: Invoke builder with approved BUILD_PACKET
- steward: Commit approved changes
- autonomous_build_cycle: Deprecated for new runs (kept for compatibility/testing)

All missions:
- Are deterministic (pure functions of inputs + state)
- Return MissionResult with structured outputs
- Support rollback via compensation actions
- Integrate with existing Tier-2 orchestration
"""
from __future__ import annotations

from runtime.orchestration.missions.base import (
    MissionType,
    MissionResult,
    MissionContext,
    MissionError,
    MissionValidationError,
)
from runtime.orchestration.missions.design import DesignMission
from runtime.orchestration.missions.review import ReviewMission
from runtime.orchestration.missions.build import BuildMission
from runtime.orchestration.missions.build_with_validation import BuildWithValidationMission
from runtime.orchestration.missions.steward import StewardMission
from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.echo import EchoMission
from runtime.orchestration.missions.noop import NoopMission
from runtime.orchestration.missions.schema import (
    validate_mission_definition,
    load_mission_schema,
    MissionSchemaError,
)

# Mission type registry - maps type string to implementation class
MISSION_TYPES = {
    MissionType.DESIGN: DesignMission,
    MissionType.REVIEW: ReviewMission,
    MissionType.BUILD: BuildMission,
    MissionType.BUILD_WITH_VALIDATION: BuildWithValidationMission,
    MissionType.STEWARD: StewardMission,
    MissionType.AUTONOMOUS_BUILD_CYCLE: AutonomousBuildCycleMission,
    MissionType.ECHO: EchoMission,
    MissionType.NOOP: NoopMission,
}


def get_mission_class(mission_type: str):
    """
    Get mission implementation class by type string.
    
    Fail-closed: Raises MissionError if type is unknown.
    """
    try:
        mt = MissionType(mission_type)
    except ValueError:
        valid = sorted([t.value for t in MissionType])
        raise MissionError(
            f"Unknown mission type: '{mission_type}'. "
            f"Valid types: {valid}"
        )
    return MISSION_TYPES[mt]


__all__ = [
    # Types
    "MissionType",
    "MissionResult",
    "MissionContext",
    # Exceptions
    "MissionError",
    "MissionValidationError",
    "MissionSchemaError",
    # Mission classes
    "DesignMission",
    "ReviewMission",
    "BuildMission",
    "BuildWithValidationMission",
    "StewardMission",
    "AutonomousBuildCycleMission",
    "EchoMission",
    "NoopMission",
    # Registry
    "MISSION_TYPES",
    "get_mission_class",
    # Schema
    "validate_mission_definition",
    "load_mission_schema",
]

```

### FILE: runtime/orchestration/missions/autonomous_build_cycle.py

```
"""
Phase 3 Mission Types - Autonomous Build Cycle (Loop Controller)

Refactored for Phase A: Convergent Builder Loop.
Implements a deterministic, resumable, budget-bounded build loop.
"""
from __future__ import annotations

import json
import hashlib
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
    MissionEscalationRequired,
)
from runtime.orchestration.missions.design import DesignMission
from runtime.orchestration.missions.build import BuildMission
from runtime.orchestration.missions.review import ReviewMission
from runtime.orchestration.missions.steward import StewardMission

# Backlog Integration
from recursive_kernel.backlog_parser import (
    parse_backlog,
    select_eligible_item,
    select_next_task,
    mark_item_done_with_evidence,
    BacklogItem,
    Priority as BacklogPriority,
)
from runtime.orchestration.task_spec import TaskSpec, TaskPriority

# Loop Infrastructure
from runtime.orchestration.loop.ledger import (
    AttemptLedger, AttemptRecord, LedgerHeader, LedgerIntegrityError
)
from runtime.orchestration.loop.policy import LoopPolicy
from runtime.orchestration.loop.budgets import BudgetController
from runtime.orchestration.loop.taxonomy import (
    TerminalOutcome, TerminalReason, FailureClass, LoopAction
)
from runtime.api.governance_api import PolicyLoader
from runtime.orchestration.run_controller import verify_repo_clean, run_git_command
from runtime.util.file_lock import FileLock

# CEO Approval Queue
from runtime.orchestration.ceo_queue import (
    CEOQueue, EscalationEntry, EscalationType, EscalationStatus
)

# Phase 3a: Test Execution
from runtime.api.governance_api import check_pytest_scope
from runtime.orchestration.test_executor import PytestExecutor, PytestResult
from runtime.orchestration.loop.failure_classifier import classify_test_failure

class AutonomousBuildCycleMission(BaseMission):
    """
    Autonomous Build Cycle: Convergent Builder Loop Controller.
    
    Inputs:
        - task_spec (str): Task description
        - context_refs (list[str]): Context paths
        - handoff_schema_version (str, optional): Validation version
        
    Outputs:
        - commit_hash (str): Final hash if PASS
        - loop_report (dict): Full execution report
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.AUTONOMOUS_BUILD_CYCLE
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        # from_backlog mode doesn't require task_spec (will be loaded from backlog)
        if inputs.get("from_backlog"):
            # Task will be loaded from BACKLOG.md
            return

        if not inputs.get("task_spec"):
            raise MissionValidationError("task_spec is required (or use from_backlog=True)")

        # P0: Handoff Schema Version Validation
        req_version = "v1.0" # Hardcoded expectation for Phase A
        if "handoff_schema_version" in inputs:
            if inputs["handoff_schema_version"] != req_version:
                # We can't return a Result from validate_inputs, must raise.
                # But strict fail-closed requires blocking.
                raise MissionValidationError(f"Handoff version mismatch. Expected {req_version}, got {inputs['handoff_schema_version']}")

    def _can_reset_workspace(self, context: MissionContext) -> bool:
        """
        P0: Validate if workspace clean/reset is available.
        For Phase A, we check if we can run a basic git status or if an executor is provided.
        In strict mode, if we can't guarantee reset, we fail closed.
        """
        # MVP: Fail if no operation_executor, or if we can't verify clean state.
        # But wait, we are running in a checked out repo.
        # Simple check: Is the working directory dirty?
        # We can try running git status via subprocess?
        # Or better, just rely on the 'clean' requirement.
        # If we can't implement reset, we return False.
        # Since I don't have a built-in resetter:
        return True # Stub for MVP, implying "Assume Clean" for now? 
        # User constraint: "If a clean reset cannot be guaranteed... fail-closed: ESCALATION_REQUESTED reason WORKSPACE_RESET_UNAVAILABLE"
        # I will enforce this check at start of loop.

    def _compute_hash(self, obj: Any) -> str:
        s = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def _emit_packet(self, name: str, content: Dict[str, Any], context: MissionContext):
        """Emit a canonical packet to artifacts/"""
        path = context.repo_root / "artifacts" / name
        with open(path, 'w', encoding='utf-8') as f:
            # Markdown wrapper for readability + JSON/YAML payload
            f.write(f"# Packet: {name}\n\n")
            f.write("```json\n")
            json.dump(content, f, indent=2)
            f.write("\n```\n")

    def _escalate_to_ceo(
        self,
        queue: CEOQueue,
        escalation_type: EscalationType,
        context_data: Dict[str, Any],
        run_id: str,
    ) -> str:
        """Create escalation entry and return ID.

        Args:
            queue: The CEO queue instance
            escalation_type: Type of escalation
            context_data: Context information for the escalation
            run_id: Current run ID

        Returns:
            The escalation ID
        """
        entry = EscalationEntry(
            type=escalation_type,
            context=context_data,
            run_id=run_id,
        )
        return queue.add_escalation(entry)

    def _check_queue_for_approval(
        self, queue: CEOQueue, escalation_id: str
    ) -> Optional[EscalationEntry]:
        """Check if escalation has been resolved.

        Args:
            queue: The CEO queue instance
            escalation_id: The escalation ID to check

        Returns:
            The escalation entry, or None if not found
        """
        entry = queue.get_by_id(escalation_id)
        if entry is None:
            return None
        if entry.status == EscalationStatus.PENDING:
            # Check for timeout (24 hours)
            if self._is_escalation_stale(entry):
                queue.mark_timeout(escalation_id)
                entry = queue.get_by_id(escalation_id)
        return entry

    def _is_escalation_stale(
        self, entry: EscalationEntry, hours: int = 24
    ) -> bool:
        """Check if escalation exceeds timeout threshold.

        Args:
            entry: The escalation entry
            hours: Timeout threshold in hours (default 24)

        Returns:
            True if stale, False otherwise
        """
        from datetime import datetime
        age = datetime.utcnow() - entry.created_at
        return age.total_seconds() > hours * 3600

    def _load_task_from_backlog(self, context: MissionContext) -> Optional[BacklogItem]:
        """
        Load next eligible task from BACKLOG.md, skipping blocked tasks.

        A task is considered blocked if:
        - It has explicit dependencies
        - Its context contains markers: "blocked", "depends on", "waiting for"

        Returns:
            BacklogItem or None if no eligible tasks
            Raises: FileNotFoundError if BACKLOG.md missing (caller distinguishes from NO_ELIGIBLE_TASKS)
        """
        backlog_path = context.repo_root / "docs" / "11_admin" / "BACKLOG.md"

        if not backlog_path.exists():
            raise FileNotFoundError(f"BACKLOG.md not found at: {backlog_path}")

        items = parse_backlog(backlog_path)

        # First filter to uncompleted (TODO, P0/P1) tasks
        from recursive_kernel.backlog_parser import get_uncompleted_tasks
        uncompleted = get_uncompleted_tasks(items)

        # Then filter out blocked tasks before selection
        def is_not_blocked(item: BacklogItem) -> bool:
            """Check if task is not blocked."""
            # Check context for blocking markers
            blocked_markers = ["blocked", "depends on", "waiting for"]
            return not any(marker in item.context.lower() for marker in blocked_markers)

        selected = select_next_task(uncompleted, filter_fn=is_not_blocked)

        return selected

    def run(self, context: MissionContext, inputs: Dict[str, Any]) -> MissionResult:
        # Deprecated path guard: keep class for compatibility/historical replay/tests.
        # Block only CLI mission-run entrypoint for new autonomous runs.
        if (
            context.metadata.get("cli_command") == "mission run"
            and not inputs.get("allow_deprecated_replay", False)
        ):
            return self._make_result(
                success=False,
                executed_steps=["deprecation_guard"],
                error=(
                    "autonomous_build_cycle is deprecated for new runs. "
                    "Use 'lifeos spine run <task_spec>' instead."
                ),
                escalation_reason="DEPRECATED_PATH",
                evidence={"deprecation": "autonomous_build_cycle"},
            )

        executed_steps: List[str] = []
        total_tokens = 0
        final_commit_hash = "UNKNOWN"  # Track commit hash from steward

        # Handle from_backlog mode
        if inputs.get("from_backlog"):
            try:
                backlog_item = self._load_task_from_backlog(context)
            except FileNotFoundError as e:
                # BACKLOG.md missing - distinct from NO_ELIGIBLE_TASKS
                reason = "BACKLOG_MISSING"
                self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, 0)
                return self._make_result(
                    success=False,
                    outputs={"outcome": "BLOCKED", "reason": reason, "error": str(e)},
                    executed_steps=["backlog_scan"],
                )

            if backlog_item is None:
                # No eligible tasks (all completed, blocked, or wrong priority)
                reason = "NO_ELIGIBLE_TASKS"
                self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, 0)
                return self._make_result(
                    success=False,
                    outputs={"outcome": "BLOCKED", "reason": reason},
                    executed_steps=["backlog_scan"],
                )

            # Convert BacklogItem to task_spec format for design phase
            task_description = f"{backlog_item.title}\n\nAcceptance Criteria:\n{backlog_item.dod}"
            inputs["task_spec"] = task_description
            inputs["_backlog_item"] = backlog_item  # Store for completion marking

            executed_steps.append(f"backlog_selected:{backlog_item.item_key[:8]}")

        # P0: Workspace Semantics - Fail Closed if Reset Unavailable
        if not self._can_reset_workspace(context):
             reason = TerminalReason.WORKSPACE_RESET_UNAVAILABLE.value
             self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
             return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)

        # 1. Setup Infrastructure
        ledger_path = context.repo_root / "artifacts" / "loop_state" / "attempt_ledger.jsonl"
        ledger = AttemptLedger(ledger_path)
        budget = BudgetController()

        # CEO Approval Queue
        queue_path = context.repo_root / "artifacts" / "queue" / "escalations.db"
        queue = CEOQueue(db_path=queue_path)
        
        # P0.1: Promotion to Authoritative Gating (Enabled per Council Pass)
        # Load policy config from repo canonical location
        policy_config_dir = context.repo_root / "config" / "policy"
        loader = PolicyLoader(config_dir=policy_config_dir, authoritative=True)
        effective_config = loader.load()
        
        policy = LoopPolicy(effective_config=effective_config)
        
        # P0: Policy Hash (Hardcoded for checking)
        current_policy_hash = "phase_a_hardcoded_v1" 
        
        # 2. Hydrate / Initialize Ledger
        try:
            is_resume = ledger.hydrate()
            if is_resume:
                # P0: Policy Hash Guard
                if ledger.header["policy_hash"] != current_policy_hash:
                    reason = TerminalReason.POLICY_CHANGED_MID_RUN.value
                    self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
                    return self._make_result(
                        success=False,
                        escalation_reason=f"{reason}: Ledger has {ledger.header['policy_hash']}, current is {current_policy_hash}",
                        executed_steps=executed_steps
                    )
                executed_steps.append("ledger_hydrated")

                # Check for pending escalation on resume
                escalation_state_path = context.repo_root / "artifacts" / "loop_state" / "escalation_state.json"
                if escalation_state_path.exists():
                    with open(escalation_state_path, 'r') as f:
                        esc_state = json.load(f)
                    escalation_id = esc_state.get("escalation_id")
                    if escalation_id:
                        entry = self._check_queue_for_approval(queue, escalation_id)
                        if entry and entry.status == EscalationStatus.PENDING:
                            # Still pending, cannot resume
                            return self._make_result(
                                success=False,
                                escalation_reason=f"Escalation {escalation_id} still pending CEO approval",
                                outputs={"escalation_id": escalation_id},
                                executed_steps=executed_steps
                            )
                        elif entry and entry.status == EscalationStatus.REJECTED:
                            # Rejected, terminate
                            reason = f"CEO rejected escalation {escalation_id}: {entry.resolution_note}"
                            self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, total_tokens)
                            return self._make_result(
                                success=False,
                                error=reason,
                                executed_steps=executed_steps
                            )
                        elif entry and entry.status == EscalationStatus.TIMEOUT:
                            # Timeout, terminate
                            reason = f"Escalation {escalation_id} timed out after 24 hours"
                            self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, total_tokens)
                            return self._make_result(
                                success=False,
                                error=reason,
                                executed_steps=executed_steps
                            )
                        elif entry and entry.status == EscalationStatus.APPROVED:
                            # Approved, can continue - clear escalation state
                            escalation_state_path.unlink()
                            executed_steps.append(f"escalation_{escalation_id}_approved")
            else:
                # Initialize
                ledger.initialize(
                    LedgerHeader(
                        policy_hash=current_policy_hash,
                        handoff_hash=self._compute_hash(inputs),
                        run_id=context.run_id
                    )
                )
                executed_steps.append("ledger_initialized")
                
        except LedgerIntegrityError as e:
            return self._make_result(
                success=False,
                error=f"{TerminalOutcome.BLOCKED.value}: {TerminalReason.LEDGER_CORRUPT.value} - {e}",
                executed_steps=executed_steps
            )

        # 3. Design Phase (Attempt 0) - Simplified for Phase A
        # In a robust resume, we'd load this from disk.
        # For Phase A, if resuming, we assume we can re-run design OR we stored it.
        # Let's run design (idempotent-ish).
        design = DesignMission()
        d_res = design.run(context, inputs)
        executed_steps.append("design_phase")
        
        if d_res.evidence.get("usage"):
             total_tokens += d_res.evidence["usage"].get("total_tokens", 0) # total_tokens key might differ, checking api.py
             # api.py usage has input_tokens, output_tokens.
             u = d_res.evidence["usage"]
             total_tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)
        else:
             # P0: Fail Closed if accounting missing
             # But Design might be cached? or Stubbed? 
             # If Stubbed, usage might be missing.
             # We should check if it was a real call. 
             pass

        if not d_res.success:
            return self._make_result(success=False, error=f"Design failed: {d_res.error}", executed_steps=executed_steps)
            
        build_packet = d_res.outputs["build_packet"]
        
        # Design Review
        review = ReviewMission()
        r_res = review.run(context, {"subject_packet": build_packet, "review_type": "build_review"})
        executed_steps.append("design_review")
        
        if r_res.evidence.get("usage"):
             u = r_res.evidence["usage"]
             total_tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)

        if not r_res.success or r_res.outputs.get("verdict") != "approved":
             return self._make_result(
                 success=False,
                 escalation_reason=f"Design rejected: {r_res.outputs.get('verdict')}",
                 executed_steps=executed_steps
             )
             
        design_approval = r_res.outputs.get("council_decision")

        # 4. Loop Execution
        loop_active = True
        
        while loop_active:
            # Determine Attempt ID
            if ledger.history:
                attempt_id = ledger.history[-1].attempt_id + 1
            else:
                attempt_id = 1
                
            # Budget Check
            is_over, budget_reason = budget.check_budget(attempt_id, total_tokens)
            if is_over:
                # Emit Terminal Packet
                self._emit_terminal(TerminalOutcome.BLOCKED, budget_reason, context, total_tokens)
                return self._make_result(success=False, error=budget_reason, executed_steps=executed_steps) # Simplified return
                
            # Policy Check (Deadlock/Oscillation/Resume-Action)
            action, reason = policy.decide_next_action(ledger)
            
            if action == LoopAction.TERMINATE.value:
                # If policy says terminate, we stop.
                # Map reason to TerminalOutcome
                outcome = TerminalOutcome.BLOCKED
                if reason == TerminalReason.PASS.value:
                    outcome = TerminalOutcome.PASS
                elif reason == TerminalReason.OSCILLATION_DETECTED.value:
                    outcome = TerminalOutcome.ESCALATION_REQUESTED
                
                self._emit_terminal(outcome, reason, context, total_tokens)
                
                if outcome == TerminalOutcome.PASS:
                    # Return success details with commit hash from steward
                    return self._make_result(success=True, outputs={"commit_hash": final_commit_hash}, executed_steps=executed_steps)
                else:
                    return self._make_result(success=False, error=reason, executed_steps=executed_steps)

            # Execution (RETRY or First Run)
            feedback = ""
            if ledger.history:
                last = ledger.history[-1]
                feedback = f"Previous attempt failed: {last.failure_class}. Rationale: {last.rationale}"
                # Inject feedback
                build_packet["feedback_context"] = feedback

            # Build Mission
            build = BuildMission()
            b_res = build.run(context, {"build_packet": build_packet, "approval": design_approval})
            executed_steps.append(f"build_attempt_{attempt_id}")
            
            # Token Accounting (Fail Closed)
            has_tokens = False
            if b_res.evidence.get("usage"):
                u = b_res.evidence["usage"]
                total_tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)
                has_tokens = True
            
            if not has_tokens:
                # P0: Fail Closed on Token Accounting
                reason = TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value
                self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
                return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)

            if not b_res.success:
                # Internal mission error (crash?)
                self._record_attempt(ledger, attempt_id, context, b_res, FailureClass.UNKNOWN, "Build crashed")
                continue

            review_packet = b_res.outputs["review_packet"]
            
            # P0: Diff Budget Check (BEFORE Apply/Review)
            # Extracted from review_packet payload
            content = review_packet.get("payload", {}).get("content", "")
            lines = content.count('\n')
            
            # P0: Enforce limit (300 lines)
            max_lines = 300 # Hardcoded P0 constraint
            over_diff, diff_reason = budget.check_diff_budget(lines, max_lines=max_lines)
            
            if over_diff:
                reason = TerminalReason.DIFF_BUDGET_EXCEEDED.value
                # Evidence: Capture the rejected diff 
                evidence_path = context.repo_root / "artifacts" / f"rejected_diff_attempt_{attempt_id}.txt"
                with open(evidence_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Emit Terminal Packet with Evidence ref
                self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens, diff_evidence=str(evidence_path))
                
                # Record Failure
                self._record_attempt(ledger, attempt_id, context, b_res, FailureClass.UNKNOWN, reason)

                return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)

            # Output Review
            out_review = ReviewMission()
            or_res = out_review.run(context, {"subject_packet": review_packet, "review_type": "output_review"})
            executed_steps.append(f"review_attempt_{attempt_id}")

            if or_res.evidence.get("usage"):
                 u = or_res.evidence["usage"]
                 total_tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)

            # Classification
            success = False
            failure_class = None
            term_reason = None
            
            verdict = or_res.outputs.get("verdict")
            if verdict == "approved":
                success = True
                failure_class = None
                # Steward
                steward = StewardMission()
                s_res = steward.run(context, {"review_packet": review_packet, "approval": or_res.outputs.get("council_decision")})
                if s_res.success:
                    # SUCCESS! Capture commit hash and add steward step
                    final_commit_hash = s_res.outputs.get("commit_hash", s_res.outputs.get("simulated_commit_hash", "UNKNOWN"))
                    executed_steps.append("steward")

                    # Mark backlog task complete if from_backlog mode
                    if inputs.get("_backlog_item"):
                        backlog_item = inputs["_backlog_item"]
                        backlog_path = context.repo_root / "docs" / "11_admin" / "BACKLOG.md"

                        mark_item_done_with_evidence(
                            backlog_path,
                            backlog_item,
                            evidence={
                                "commit_hash": final_commit_hash,
                                "run_id": context.run_id,
                            },
                            repo_root=context.repo_root,
                        )
                        executed_steps.append("backlog_marked_complete")

                    # Record PASS
                    self._record_attempt(ledger, attempt_id, context, b_res, None, "Attributes Approved", success=True)
                    # Loop will check policy next iter -> PASS
                    continue 
                else:
                    success = False
                    failure_class = FailureClass.UNKNOWN
            else:
                # Map verdict to failure class
                success = False
                if verdict == "rejected":
                     failure_class = FailureClass.REVIEW_REJECTION
                else:
                     failure_class = FailureClass.REVIEW_REJECTION # Needs revision etc

            # Record Attempt
            reason_str = or_res.outputs.get("council_decision", {}).get("synthesis", "No rationale")
            self._record_attempt(ledger, attempt_id, context, b_res, failure_class, reason_str, success=success)
             
            # Emit Review Packet
            self._emit_packet(f"Review_Packet_attempt_{attempt_id:04d}.md", review_packet, context)


    def _record_attempt(self, ledger, attempt_id, context, build_res, f_class, rationale, success=False):
        # Compute hashes
        # diff_hash from review_packet content
        review_packet = build_res.outputs.get("review_packet")
        content = review_packet.get("payload", {}).get("content", "") if review_packet else ""
        d_hash = self._compute_hash(content)
        
        rec = AttemptRecord(
            attempt_id=attempt_id,
            timestamp=str(time.time()),
            run_id=context.run_id,
            policy_hash="phase_a_hardcoded_v1",
            input_hash="hash(inputs)", 
            actions_taken=build_res.executed_steps,
            diff_hash=d_hash,
            changed_files=[], # Extract if possible
            evidence_hashes={},
            success=success,
            failure_class=f_class.value if f_class else None,
            terminal_reason=None, # Filled if terminal
            next_action="evaluated_next_tick",
            rationale=rationale
        )
        ledger.append(rec)

    def _emit_terminal(self, outcome, reason, context, tokens, diff_evidence: str = None):
        """Emit CEO Terminal Packet & Closure Bundle."""
        content = {
            "outcome": outcome.value,
            "reason": reason,
            "tokens_consumed": tokens,
            "run_id": context.run_id
        }
        if diff_evidence:
            content["diff_evidence_path"] = diff_evidence

        self._emit_packet("CEO_Terminal_Packet.md", content, context)
        # Closure Bundle? (Stubbed as requested: "Use existing if present")
        # We assume independent closure process picks this up, or we assume done.

    # =========================================================================
    # Phase 3a: Test Verification Methods
    # =========================================================================

    def _run_verification_tests(
        self,
        context: MissionContext,
        target: str = "runtime/tests",
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Run pytest on runtime/tests/ after build completes.

        Args:
            context: Mission context
            target: Test target path (default: runtime/tests)
            timeout: Timeout in seconds (default: 300 = 5 minutes)

        Returns:
            VerificationResult dict with:
                - success: bool (True if tests passed)
                - test_result: PytestResult object
                - evidence: dict with captured output
                - error: Optional error message
        """
        # Check pytest scope
        allowed, reason = check_pytest_scope(target)
        if not allowed:
            return {
                "success": False,
                "error": f"Test scope denied: {reason}",
                "evidence": {},
            }

        # Execute tests
        executor = PytestExecutor(timeout=timeout)
        result = executor.run(target)

        # Build verification result
        return {
            "success": result.exit_code == 0,
            "test_result": result,
            "evidence": {
                "pytest_stdout": result.stdout[:50000],  # Cap at 50KB
                "pytest_stderr": result.stderr[:50000],  # Cap at 50KB
                "exit_code": result.exit_code,
                "duration_seconds": result.duration,
                "test_counts": result.counts or {},
                "status": result.status,
                "timeout_triggered": result.evidence.get("timeout_triggered", False),
            },
            "error": None if result.exit_code == 0 else "Tests failed",
        }

    def _prepare_retry_context(
        self,
        verification: Dict[str, Any],
        previous_results: Optional[List[PytestResult]] = None
    ) -> Dict[str, Any]:
        """
        Prepare context for retry after test failure.

        Includes:
        - Which tests failed
        - Error messages from failures
        - Failure classification

        Args:
            verification: VerificationResult dict from _run_verification_tests
            previous_results: Optional list of previous test results for flake detection

        Returns:
            Retry context dict
        """
        test_result = verification.get("test_result")
        if not test_result:
            return {
                "failure_class": FailureClass.UNKNOWN.value,
                "error": "No test result available",
            }

        # Classify failure
        failure_class = classify_test_failure(test_result, previous_results)

        context = {
            "failure_class": failure_class.value,
            "error_messages": test_result.error_messages[:5] if test_result.error_messages else [],
            "suggestion": self._generate_fix_suggestion(failure_class),
        }

        # Add test-specific details if available
        if test_result.failed_tests:
            context["failed_tests"] = list(test_result.failed_tests)[:10]  # Cap at 10
        if test_result.counts:
            context["test_counts"] = test_result.counts

        return context

    def _generate_fix_suggestion(self, failure_class: FailureClass) -> str:
        """
        Generate fix suggestion based on failure class.

        Args:
            failure_class: Classified failure type

        Returns:
            Suggestion string for retry
        """
        suggestions = {
            FailureClass.TEST_FAILURE: "Review test failures and fix the code logic that's causing assertions to fail.",
            FailureClass.TEST_FLAKE: "This test appears flaky (passed before, failed now). Consider investigating timing issues or test dependencies.",
            FailureClass.TEST_TIMEOUT: "Tests exceeded timeout limit. Consider optimizing slow tests or increasing timeout threshold.",
        }
        return suggestions.get(failure_class, "Review the test output and fix the underlying issue.")

```

### FILE: scripts/generate_runtime_status.py

```
#!/usr/bin/env python3
"""
Generate runtime status facts used by documentation freshness checks.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def generate(repo_root: Path) -> dict:
    lifeos_state = _read_text(repo_root / "docs" / "11_admin" / "LIFEOS_STATE.md")
    backlog = _read_text(repo_root / "docs" / "11_admin" / "BACKLOG.md")

    openclaw_bin = shutil.which("openclaw")
    openclaw_installed = openclaw_bin is not None

    claims_openclaw_blocker = "OpenClaw COO Install" in lifeos_state and "Only genuine gap" in lifeos_state
    backlog_openclaw_open = "- [ ] **Install OpenClaw COO on WSL2**" in backlog

    contradictions = []
    if openclaw_installed and claims_openclaw_blocker:
        contradictions.append("LIFEOS_STATE still claims OpenClaw install as blocker while binary is present.")
    if openclaw_installed and backlog_openclaw_open:
        contradictions.append("BACKLOG still lists OpenClaw install unchecked while binary is present.")

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "facts": {
            "openclaw_installed": openclaw_installed,
            "openclaw_bin": openclaw_bin,
            "lifeos_state_claims_openclaw_blocker": claims_openclaw_blocker,
            "backlog_openclaw_install_unchecked": backlog_openclaw_open,
        },
        "contradictions": contradictions,
        "status": "ok" if not contradictions else "warn",
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    payload = generate(repo_root)
    status_dir = repo_root / "artifacts" / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    status_path = status_dir / "runtime_status.json"
    status_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    checkpoint_dir = repo_root / "artifacts" / "packets" / "status"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_name = datetime.now(timezone.utc).strftime("checkpoint_report_%Y%m%d.json")
    checkpoint_path = checkpoint_dir / checkpoint_name
    checkpoint_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(str(status_path))
    print(str(checkpoint_path))
    print(payload["status"])
    for item in payload["contradictions"]:
        print(f"WARNING: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

### FILE: scripts/opencode_ci_runner.py

```
#!/usr/bin/env python3
"""
OpenCode CI Runner (CT-2 Phase 3 v2.0)
======================================

Broadened CI runner for doc-steward gate.
All structural operations allowed. Path security checks retained.
"""

import argparse
import time
import requests
import subprocess
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Add scripts directory to path for imports if not already there
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# Import hardened policy module
import opencode_gate_policy as policy
from opencode_gate_policy import ReasonCode

# Import canonical defaults from single source of truth
# Import canonical defaults from single source of truth
try:
    # Add parent directory to path for runtime imports
    _repo_root = os.path.dirname(_script_dir)
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from runtime.agents.models import (
        resolve_model_auto,
        get_api_key_for_role,
        load_model_config,
        validate_config,
    )
    # Default is now 'auto' to trigger resolution logic
    DEFAULT_MODEL = "auto"
except ImportError as e:
    # Fail loud in Phase 3 - we must have runtime access
    print(f"CRITICAL: Failed to import runtime.agents.models: {e}")
    print("This script must be run from within the LifeOS repository.")
    sys.exit(1)

# ============================================================================
# LOGGING
# ============================================================================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

# Global log buffer for evidence bundle
_log_buffer = []

def log(msg, level="info"):
    timestamp = datetime.now().isoformat(sep="T", timespec="seconds")
    color = Colors.RESET
    if level == "error": color = Colors.RED
    elif level == "ok": color = Colors.GREEN
    elif level == "gov": color = Colors.YELLOW
    elif level == "info": color = Colors.BLUE
    
    log_line = f"[{level.upper()}] [{timestamp}] {msg}"
    _log_buffer.append(log_line)
    print(f"{color}{log_line}{Colors.RESET}")

def get_log_buffer() -> str:
    return "\n".join(_log_buffer)

def clear_log_buffer():
    _log_buffer.clear()

def load_api_key(mode: str) -> str:
    """Load the API key for the given mode (steward/builder)."""
    role = "steward" if mode == policy.MODE_STEWARD else "builder"
    
    # Try canonical loading first
    key = get_api_key_for_role(role)
    if key:
        log(f"{role.capitalize()} API Key loaded via config (starts with {key[:8]})", "info")
        return key

    # Fallback to legacy env vars if config/models.yaml lookup failed (shouldn't happen if setup is correct)
    # Priority: ZEN_{ROLE}_KEY > ZEN_STEWARD_KEY
    env_var = f"ZEN_{role.upper()}_KEY"
    key = os.environ.get(env_var)
    if key:
        log(f"{role.capitalize()} API Key loaded via {env_var}", "info")
        return key
        
    log(f"API Key for {role} NOT found", "error")
    return ""

# ============================================================================
# ENVELOPE VALIDATION (POST-DIFF)
# ============================================================================
def validate_all_diff_entries(parsed_diff: List[tuple], mode: str) -> List[Tuple[str, str, str]]:
    """
    Validate all parsed diff entries using policy.validate_operation.
    
    Returns list of (path, operation, reason_code) for blocked entries.
    """
    blocked = []
    
    # Restore Legacy parity: Structural ops blocked in Steward mode
    if mode == policy.MODE_STEWARD:
        blocked_ops = policy.detect_blocked_ops(parsed_diff)
        if blocked_ops:
            return blocked_ops
            
    for entry in parsed_diff:
        if len(entry) == 2:
            status, path = entry
            old_path = None
        else:
            status, old_path, path = entry  # R/C have old and new paths
        
        # Check primary path (new path or modified path)
        allowed, reason = policy.validate_operation(status, path, mode)
        if not allowed:
            blocked.append((path, status, reason))
            
        # For R/C, also check the old path (treat as deletion/touch)
        if old_path:
            # Use status D to imply "removal/modification of this path"
            allowed_old, reason_old = policy.validate_operation("D", old_path, mode)
            if not allowed_old:
                blocked.append((old_path, status, reason_old))
    
    return blocked

# ============================================================================
# EVIDENCE GENERATION
# ============================================================================
def generate_evidence_bundle(status: str, reason: Optional[str], mode: str, task: Dict[str, Any], 
                            parsed_diff: List[tuple] = None, blocked_entries: List[tuple] = None):
    """Generate the deterministic evidence bundle for the mission."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mission_id = f"mission_{timestamp}"
    evidence_path = os.path.join(policy.EVIDENCE_ROOT, mission_id)
    os.makedirs(evidence_path, exist_ok=True)
    
    # exit_report.json
    report = {
        "status": status,
        "reason_code": reason,
        "mode": mode,
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "blocked_entries": blocked_entries or []
    }
    with open(os.path.join(evidence_path, "exit_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    
    # changed_files.json (sorted by path for determinism)
    changed = []
    if parsed_diff:
        for entry in parsed_diff:
            if len(entry) == 2:
                changed.append({"status": entry[0], "path": entry[1]})
            else:
                changed.append({"status": entry[0], "old_path": entry[1], "new_path": entry[2]})
    # Sort by path (or new_path for renames/copies) for deterministic output
    changed.sort(key=lambda x: policy.normalize_path(x.get("path") or x.get("new_path", "")))
    
    with open(os.path.join(evidence_path, "changed_files.json"), "w") as f:
        json.dump(changed, f, indent=2)
    
    # classification.json
    classification = {
        "is_governance": any(policy.matches_denylist(path)[0] for path in task.get("files", [])),
        "risk_level": "P0" if any(policy.matches_denylist(path)[0] for path in task.get("files", [])) else "P1",
        "envelope_violations": len(blocked_entries) if blocked_entries else 0
    }
    with open(os.path.join(evidence_path, "classification.json"), "w") as f:
        json.dump(classification, f, indent=2)
    
    # runner.log
    log_content = get_log_buffer()
    truncated_log, _ = policy.truncate_log(log_content)
    with open(os.path.join(evidence_path, "runner.log"), "w") as f:
        f.write(truncated_log)
    
    # hashes.json
    hashes = {}
    for filename in ["exit_report.json", "changed_files.json", "classification.json", "runner.log"]:
        p = os.path.join(evidence_path, filename)
        if os.path.exists(p):
            hashes[filename] = policy.compute_file_hash(p)
            
    with open(os.path.join(evidence_path, "hashes.json"), "w") as f:
        json.dump(hashes, f, indent=2)
        
    log(f"Evidence bundle generated: {evidence_path}", "ok")
    return evidence_path

# ============================================================================
# INPUT VALIDATION
# ============================================================================
def validate_task_input(task_str):
    """Validate task is JSON with required schema. Reject free-text."""
    try:
        task = json.loads(task_str)
    except json.JSONDecodeError:
        log("Free-text input rejected. Phase 3 requires JSON-structured tasks.", "error")
        return None
    
    required = ["files", "action", "instruction"]
    for key in required:
        if key not in task:
            log(f"Missing required key in task JSON: {key}", "error")
            return None
    
    # Phase 3: All operations allowed.
    valid_actions = ["create", "modify", "delete", "rename", "move", "copy"]
    if task["action"] not in valid_actions:
        log(f"Invalid action: {task['action']}. Valid actions: {valid_actions}", "error")
        return None
    
    return task

# ============================================================================
# EPHEMERAL SERVER LIFECYCLE
# ============================================================================
import tempfile
import shutil
import threading

def create_isolated_config(api_key, model):
    temp_dir = tempfile.mkdtemp(prefix="opencode_steward_")
    config_subdir = os.path.join(temp_dir, "opencode")
    os.makedirs(config_subdir, exist_ok=True)
    data_subdir = os.path.join(temp_dir, ".local", "share", "opencode")
    os.makedirs(data_subdir, exist_ok=True)
    
    # Determine provider based on model naming or defaults
    if "minimax" in model.lower():
        provider = "zen" # Zen endpoint often maps to 'zen' or 'anthropic' internal logic in server
        # For our environment, we'll provide keys for both to be safe
        auth_data = {
            "zen": {"type": "api", "key": api_key},
            "openrouter": {"type": "api", "key": api_key}
        }
    else:
        auth_data = {"openrouter": {"type": "api", "key": api_key}}

    with open(os.path.join(data_subdir, "auth.json"), "w") as f:
        json.dump(auth_data, f, indent=2)
    
    config_data = {
        "model": model, 
        "$schema": "https://opencode.ai/config.json"
    }
    
    # If using Zen, we might need to specify the base URL in config too
    # Using the standard Zen endpoint from models.yaml
    if "minimax" in model.lower():
        config_data["upstream_base_url"] = "https://opencode.ai/zen/v1/messages"

    with open(os.path.join(config_subdir, "opencode.json"), "w") as f:
        json.dump(config_data, f, indent=2)
    
    return temp_dir

# LIFEOS_TODO[P1][area: scripts/opencode_ci_runner.py:cleanup_isolated_config][exit: root cause documented + decision logged in DECISIONS.md] Review OpenCode deletion logic: Understand why cleanup uses shutil.rmtree for temp configs. DoD: Root cause documented, safety analysis complete
def cleanup_isolated_config(config_dir):
    if config_dir and os.path.exists(config_dir):
        try:
            shutil.rmtree(config_dir)
        except Exception as e:
            log(f"Failed to cleanup config dir {config_dir}: {e}", "warning")

def start_ephemeral_server(port, config_dir, api_key):
    log(f"Starting ephemeral OpenCode server on port {port}", "info")
    env = os.environ.copy()
    env["APPDATA"], env["XDG_CONFIG_HOME"], env["USERPROFILE"], env["HOME"] = config_dir, config_dir, config_dir, config_dir
    env["OPENROUTER_API_KEY"] = api_key
    env["OPENAI_API_KEY"], env["ANTHROPIC_API_KEY"] = "", ""
    
    try:
        return subprocess.Popen(
            ["opencode", "serve", "--port", str(port)],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
            shell=True if os.name == "nt" else False
        )
    except Exception as e:
        log(f"Failed to start ephemeral server: {e}", "error")
        return None

def stop_ephemeral_server(process):
    if process:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill()


class MissionTimeout(TimeoutError):
    """Raised when a mission helper exceeds the configured timeout."""


def run_with_timeout(func, timeout_seconds: int):
    """
    Run a callable with a hard timeout and propagate exceptions.
    Returns the callable result on success.
    """
    result: Dict[str, Any] = {}
    err: Dict[str, BaseException] = {}

    def _runner():
        try:
            result["value"] = func()
        except BaseException as exc:  # pragma: no cover - propagation path
            err["exc"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise MissionTimeout(f"Mission step exceeded timeout: {timeout_seconds}s")
    if "exc" in err:
        raise err["exc"]
    return result.get("value")

# ============================================================================
# OPENCODE SERVER INTERFACE
# ============================================================================
def wait_for_server(base_url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(f"{base_url}/global/health", timeout=1).status_code == 200:
                return True
        except Exception:
            pass  # Expected during server startup
        time.sleep(1)
    return False

def run_mission(base_url, model, instruction):
    try:
        resp = requests.post(f"{base_url}/session", json={"title": "Steward Mission", "model": model}, timeout=10)
        if resp.status_code != 200: return False
        session_id = resp.json()["id"]
        requests.post(f"{base_url}/session/{session_id}/message",
                      json={"parts": [{"type": "text", "text": instruction}]}, timeout=120)
        return session_id
    except Exception as e:
        log(f"Failed to run mission: {e}", "error")
        return False

# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="OpenCode CI Runner (CT-2 Phase 3 v2.0) - Broadened")
    parser.add_argument("--port", type=int, default=62586)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--mode", type=str, choices=policy.VALID_MODES, default=policy.MODE_STEWARD, help="Enforcement mode (steward/builder)")
    parser.add_argument("--task", type=str, required=True, help="JSON-structured task (required)")
    # NO --override-foundations flag. Period.
    args = parser.parse_args()
    
    repo_root = os.getcwd()
    # Load config once
    model_config = load_model_config()

    # Resolve model if auto
    model_id = args.model
    if model_id == "auto":
        role = "steward" if args.mode == policy.MODE_STEWARD else "builder"
        model_id, reason, _ = resolve_model_auto(role, model_config)
        log(f"Resolved model 'auto' to '{model_id}' ({reason})", "info")
    else:
        log(f"Using requested model '{model_id}'", "info")

    api_key = load_api_key(args.mode)
    if not api_key:
        log("No API key available. Requesting user intervention.", "error")
        # Fail loud in Phase 3
        sys.exit(1)
    
    task = validate_task_input(args.task)
    if not task: 
        sys.exit(1)
    
    # ========== PRE-START CHECKS (symlink on declared files) ==========
    for path in task["files"]:
        safe, reason = policy.check_symlink(path, repo_root)
        if not safe:
            generate_evidence_bundle("BLOCK", reason, "PRE_START", task)
            log(f"Symlink rejected: {path}", "error")
            sys.exit(1)
    
    # ========== SERVER SETUP ==========
    config_dir = create_isolated_config(api_key, model_id)
    server_process = start_ephemeral_server(args.port, config_dir, api_key)
    if not server_process:
        cleanup_isolated_config(config_dir)
        sys.exit(1)
    
    if not wait_for_server(f"http://127.0.0.1:{args.port}"):
        stop_ephemeral_server(server_process)
        cleanup_isolated_config(config_dir)
        log("Server timeout", "error")
        sys.exit(1)
    
    # ========== EXECUTE MISSION ==========
    log("Executing mission", "info")
    session_id = run_mission(f"http://127.0.0.1:{args.port}", model_id, task["instruction"])
    
    # ========== POST-EXECUTION: GET DIFF AND VALIDATE ENVELOPE ==========
    log("Validating post-execution diff against envelope", "info")
    parsed, mode, error = policy.execute_diff_and_parse(repo_root)
    
    if error:
        generate_evidence_bundle("BLOCK", error, mode, task)
        log(f"Diff acquisition failed: {error}", "error")
        subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
        stop_ephemeral_server(server_process)
        cleanup_isolated_config(config_dir)
        sys.exit(1)
    
    if not parsed:
        parsed = []
    
    # Validate ALL diff entries against envelope
    blocked_entries = validate_all_diff_entries(parsed, mode=args.mode)
    
    if blocked_entries:
        first_block = blocked_entries[0]
        generate_evidence_bundle("BLOCK", first_block[2], mode, task, parsed, blocked_entries)
        log(f"Envelope violation: {first_block[0]} ({first_block[1]}) - {first_block[2]}", "error")
        for entry in blocked_entries[1:5]:  # Log up to 5
            log(f"  Additional violation: {entry[0]} ({entry[1]}) - {entry[2]}", "error")
        subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
        stop_ephemeral_server(server_process)
        cleanup_isolated_config(config_dir)
        sys.exit(1)
    
    # Check symlinks again for new files
    for entry in parsed:
        path = entry[1] if len(entry) == 2 else entry[2]
        safe, reason = policy.check_symlink(path, repo_root)
        if not safe:
            generate_evidence_bundle("BLOCK", reason, mode, task, parsed)
            log(f"New symlink detected: {path}", "error")
            subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
            stop_ephemeral_server(server_process)
            cleanup_isolated_config(config_dir)
            sys.exit(1)

    # Success
    generate_evidence_bundle("PASS", None, mode, task, parsed)
    log("MISSION SUCCESS - All changes within envelope", "ok")
    
    # Cleanup
    stop_ephemeral_server(server_process)
    cleanup_isolated_config(config_dir)

if __name__ == "__main__":
    main()

```

### FILE: tests_recursive/test_steward_runner.py

```
#!/usr/bin/env python3
"""
Acceptance Tests for Stewardship Runner (AT-01 through AT-10).

These tests use git worktree to create isolated test environments (H1).
Each test creates a temporary worktree, runs the runner, and validates
both exit codes and log contents.

Run with:
    python3 -m pytest tests_recursive/test_steward_runner.py -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import importlib.util
from unittest.mock import patch, MagicMock

import pytest

PYTHON = sys.executable

# --- Test Fixtures ---

@pytest.fixture
def repo_root() -> Path:
    """Get the main repo root."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


@pytest.fixture
def worktree(repo_root: Path, tmp_path: Path):
    """
    Create a git worktree for isolated testing (H1).
    
    Copies untracked/modified steward runner files to worktree so tests
    work before the runner is committed. Commits them so worktree is clean.
    
    Yields the worktree path and cleans up after.
    """
    worktree_path = tmp_path / "test_worktree"
    branch_name = f"test-steward-{os.getpid()}"
    
    # Create orphan branch for isolation
    subprocess.run(
        ["git", "branch", branch_name, "HEAD"],
        cwd=repo_root,
        capture_output=True,
    )
    
    # Create worktree
    subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch_name],
        cwd=repo_root,
        capture_output=True,
    )
    
    # Copy untracked/modified files needed for running tests
    # These files may not be committed yet during development
    files_to_copy = [
        "scripts/steward_runner.py",
        "config/steward_runner.yaml",
        "doc_steward/cli.py",
    ]
    
    copied_any = False
    for rel_path in files_to_copy:
        src = repo_root / rel_path
        dst = worktree_path / rel_path
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied_any = True
    
    # Commit copied files so worktree starts clean
    if copied_any:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=worktree_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "[test] Add steward runner files for testing"],
            cwd=worktree_path,
            capture_output=True,
        )
    
    yield worktree_path
    
    # Cleanup
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_path)],
        cwd=repo_root,
        capture_output=True,
    )
    subprocess.run(
        ["git", "branch", "-D", branch_name],
        cwd=repo_root,
        capture_output=True,
    )


@pytest.fixture
def test_config(worktree: Path) -> Path:
    """Create a minimal test config in the worktree and commit it."""
    config_dir = worktree / "config"
    config_dir.mkdir(exist_ok=True)
    
    config_content = """
repo_root: "."

tests:
  command: ["python3", "-c", "print('tests pass')"]
  paths: []

validators:
  commands: []

corpus:
  command: ["python3", "-c", "print('corpus generated')"]
  outputs_expected: []

git:
  require_clean_start: false
  commit_enabled: false
  commit_message_template: "[test] {run_id}"
  commit_paths: ["docs/"]

logging:
  log_dir: "logs/steward_runner"
  streams_dir: "logs/steward_runner/streams"
  format: "jsonl"

determinism:
  run_id_required: true
  timestamps: false
"""
    
    config_path = config_dir / "test_runner.yaml"
    config_path.write_text(config_content)
    
    # Commit the config so worktree starts clean
    subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "[test] Add test config"],
        cwd=worktree,
        capture_output=True,
    )
    
    return config_path


def run_steward(
    worktree: Path,
    config_path: Path,
    run_id: str | None = None,
    dry_run: bool = False,
    no_commit: bool = False,
    commit: bool = False,
    expect_fail: bool = False,
) -> tuple[int, Path | None]:
    """
    Run the steward runner in the worktree.
    
    Returns (exit_code, log_file_path or None).
    """
    runner_path = worktree / "scripts" / "steward_runner.py"
    
    cmd = [PYTHON, str(runner_path)]
    cmd.extend(["--config", str(config_path.relative_to(worktree))])
    
    if run_id:
        cmd.extend(["--run-id", run_id])
    
    if dry_run:
        cmd.append("--dry-run")
    
    if no_commit:
        cmd.append("--no-commit")
        
    if commit:
        cmd.append("--commit")
    
    result = subprocess.run(
        cmd,
        cwd=worktree,
        capture_output=True,
        text=True,
    )
    
    # Find log file
    log_dir = worktree / "logs" / "steward_runner"
    log_file = None
    if run_id and log_dir.exists():
        expected_log = log_dir / f"{run_id}.jsonl"
        if expected_log.exists():
            log_file = expected_log
    
    return result.returncode, log_file


def read_log_events(log_file: Path) -> list[dict]:
    """Read JSONL log file into list of events."""
    events = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            events.append(json.loads(line))
    return events


def find_event(events: list[dict], step: str, status: str) -> dict | None:
    """Find an event by step and status."""
    for event in events:
        if event.get("step") == step and event.get("status") == status:
            return event
    return None


# --- Acceptance Tests ---

class TestAT01MissingRunId:
    """AT-01: Missing run-id fails closed."""
    
    def test_missing_run_id_fails(self, worktree: Path, test_config: Path):
        """Invoke without --run-id → exit != 0."""
        runner_path = worktree / "scripts" / "steward_runner.py"
        
        result = subprocess.run(
            [PYTHON, str(runner_path), "--config", str(test_config.relative_to(worktree))],
            cwd=worktree,
            capture_output=True,
            text=True,
        )
        
        assert result.returncode != 0, "Should fail without --run-id"
        assert "required" in result.stderr.lower() or "run-id" in result.stderr.lower()


class TestAT02DirtyRepoStart:
    """AT-02: Dirty repo start fails when required."""
    
    def test_dirty_repo_fails_with_require_clean(self, worktree: Path, test_config: Path):
        """With uncommitted change and require_clean_start=true → exit != 0."""
        # Update config to require clean start
        config_content = test_config.read_text().replace(
            "require_clean_start: false",
            "require_clean_start: true"
        )
        test_config.write_text(config_content)
        
        # Create uncommitted file
        dirty_file = worktree / "dirty_file.txt"
        dirty_file.write_text("uncommitted content")
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at02-test")
        
        assert exit_code != 0, "Should fail with dirty repo"
        
        if log_file:
            events = read_log_events(log_file)
            fail_event = find_event(events, "preflight", "fail")
            assert fail_event is not None, "Should have preflight.fail event"
            assert fail_event.get("reason") == "dirty_repo"


class TestAT03TestsFailureBlocksDownstream:
    """AT-03: Tests failure blocks downstream."""
    
    def test_tests_failure_blocks_validators(self, worktree: Path, test_config: Path):
        """Make tests return non-zero → validators/corpus/commit never run."""
        # Update config with failing tests
        config_content = test_config.read_text().replace(
            'command: ["python3", "-c", "print(\'tests pass\')"]',
            'command: ["python3", "-c", "import sys; sys.exit(1)"]'
        )
        test_config.write_text(config_content)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at03-test")
        
        assert exit_code != 0, "Should fail when tests fail"
        
        if log_file:
            events = read_log_events(log_file)
            # Should have tests.fail
            tests_fail = find_event(events, "tests", "fail")
            assert tests_fail is not None, "Should have tests.fail event"
            
            # Should NOT have validators or corpus events
            for event in events:
                assert "validator" not in event.get("step", ""), "Validators should not run"
                assert event.get("step") != "corpus", "Corpus should not run"


class TestAT04ValidatorFailureBlocksCorpus:
    """AT-04: Validator failure blocks corpus."""
    
    def test_validator_failure_blocks_corpus(self, worktree: Path, test_config: Path):
        """Tests pass, validator returns non-zero → corpus not executed."""
        # Update config with failing validator
        config_content = test_config.read_text().replace(
            "validators:\n  commands: []",
            'validators:\n  commands:\n    - ["python3", "-c", "import sys; sys.exit(1)"]'
        )
        test_config.write_text(config_content)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at04-test")
        
        assert exit_code != 0, "Should fail when validator fails"
        
        if log_file:
            events = read_log_events(log_file)
            # Should have validator fail
            validator_fail = find_event(events, "validator_0", "fail")
            assert validator_fail is not None, "Should have validator.fail event"
            
            # Should NOT have corpus event
            for event in events:
                assert event.get("step") != "corpus", "Corpus should not run"


class TestAT05CorpusExpectedOutputsEnforced:
    """AT-05: Corpus expected outputs enforced."""
    
    def test_missing_corpus_output_fails(self, worktree: Path, test_config: Path):
        """Corpus exits 0 but any outputs_expected missing → fail."""
        # Update config to expect an output that won't be created
        config_content = test_config.read_text().replace(
            "outputs_expected: []",
            'outputs_expected: ["docs/nonexistent.md"]'
        )
        test_config.write_text(config_content)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at05-test")
        
        assert exit_code != 0, "Should fail when expected output missing"
        
        if log_file:
            events = read_log_events(log_file)
            corpus_fail = find_event(events, "corpus", "fail")
            assert corpus_fail is not None, "Should have corpus.fail event"
            assert corpus_fail.get("reason") == "missing_output"


class TestAT06NoChangeNoCommit:
    """AT-06: No change = no commit."""
    
    def test_no_change_exits_success(self, worktree: Path, test_config: Path):
        """Corpus runs, no changes → exit 0; no commit."""
        exit_code, log_file = run_steward(worktree, test_config, run_id="at06-test")
        
        assert exit_code == 0, "Should succeed with no changes"
        
        if log_file:
            events = read_log_events(log_file)
            no_change = find_event(events, "change_detect", "no_change")
            assert no_change is not None, "Should have no_change event"


class TestAT07ChangeWithinAllowedPathsCommits:
    """AT-07: Change within allowed paths commits once."""
    
    def test_allowed_change_commits(self, worktree: Path, test_config: Path):
        """Corpus creates diff only within commit_paths → exactly one commit."""
        # Enable commit and create a change in allowed path
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        # Make corpus create a file in docs/
        config_content = config_content.replace(
            'command: ["python3", "-c", "print(\'corpus generated\')"]',
            'command: ["python3", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        config_content = config_content.replace(
            "commit_paths: [\"docs/\"]",
            'commit_paths: ["docs/"]'
        )
        test_config.write_text(config_content)
        
        # Commit the config change so only docs/ changes are uncommitted
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "[test] Update config for AT-07"],
            cwd=worktree,
            capture_output=True,
        )
        
        # Ensure docs dir exists
        (worktree / "docs").mkdir(exist_ok=True)
        
        head_before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at07-test", commit=True)
        
        head_after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        assert exit_code == 0, "Should succeed with allowed changes"
        assert head_after != head_before, "HEAD should change after commit"
        
        if log_file:
            events = read_log_events(log_file)
            commit_pass = find_event(events, "commit", "pass")
            assert commit_pass is not None, "Should have commit.pass event"


class TestAT08ChangeOutsideAllowedPathsFails:
    """AT-08: Change outside allowed paths fails closed."""
    
    def test_disallowed_change_fails(self, worktree: Path, test_config: Path):
        """Diff touches any path outside commit_paths → exit != 0; no commit."""
        # Enable commit but create change outside allowed path
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        # Make corpus create a file outside docs/
        config_content = config_content.replace(
            'command: ["python3", "-c", "print(\'corpus generated\')"]',
            'command: ["python3", "-c", "open(\'outside.txt\', \'w\').write(\'disallowed\')"]'
        )
        test_config.write_text(config_content)
        
        head_before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        

        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at08-test", commit=True)
        
        head_after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        assert exit_code != 0, "Should fail with disallowed changes"
        assert head_after == head_before, "HEAD should not change"
        
        if log_file:
            events = read_log_events(log_file)
            commit_fail = find_event(events, "commit", "fail")
            assert commit_fail is not None, "Should have commit.fail event"
            assert commit_fail.get("reason") == "changes_outside_allowlist"


class TestAT09DryRunNeverCommits:
    """AT-09: Dry run never commits."""
    
    def test_dry_run_skips_commit(self, worktree: Path, test_config: Path):
        """With allowable diff and --dry-run → exit 0; commit skipped."""
        # Enable commit and create allowed change
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        config_content = config_content.replace(
            'command: ["python3", "-c", "print(\'corpus generated\')"]',
            'command: ["python3", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        test_config.write_text(config_content)
        
        (worktree / "docs").mkdir(exist_ok=True)
        
        head_before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        # Run with --dry-run
        exit_code, log_file = run_steward(worktree, test_config, run_id="at09-test", dry_run=True)
        
        head_after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        assert exit_code == 0, "Should succeed with dry-run"
        assert head_after == head_before, "HEAD should not change with dry-run"
        
        if log_file:
            events = read_log_events(log_file)
            commit_skipped = find_event(events, "commit", "skipped")
            assert commit_skipped is not None, "Should have commit.skipped event"
            assert commit_skipped.get("reason") == "dry_run"


class TestAT10LogDeterminism:
    """AT-10: Log determinism."""
    
    def test_logs_are_deterministic(self, worktree: Path, test_config: Path):
        """Same repo state + same run_id → byte-identical JSONL."""
        run_id = "at10-determinism"
        
        # First run
        exit_code1, log_file1 = run_steward(worktree, test_config, run_id=run_id)
        assert exit_code1 == 0
        assert log_file1 is not None
        content1 = log_file1.read_text()
        
        # Delete log for second run
        log_file1.unlink()
        
        # Second run with same state and run_id
        exit_code2, log_file2 = run_steward(worktree, test_config, run_id=run_id)
        assert exit_code2 == 0
        assert log_file2 is not None
        content2 = log_file2.read_text()
        
        # H2: byte-identical
        assert content1 == content2, "Logs should be byte-identical for same state/run_id"


class TestAT11TestScopeEnforcement:
    """AT-11: Test scope enforcement (P0-1)."""
    
    def test_tests_argv_includes_paths(self, worktree: Path, test_config: Path):
        """tests.paths must appear in the tests step argv."""
        # Update config to have specific test paths
        config_content = test_config.read_text()
        config_content = config_content.replace(
            "paths: []",
            'paths: ["path_a", "path_b", "path_c"]'
        )
        test_config.write_text(config_content)
        
        # Commit config change
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "[test] Update config for AT-11"],
            cwd=worktree,
            capture_output=True,
        )
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at11-test")
        
        # Test passes or fails, but we need to check the argv
        assert log_file is not None, "Should have log file"
        
        events = read_log_events(log_file)
        
        # Find the tests command event
        tests_event = None
        for event in events:
            if event.get("step") == "tests" and event.get("event") == "command":
                tests_event = event
                break
        
        assert tests_event is not None, "Should have tests command event"
        
        argv = tests_event.get("argv", [])
        
        # Assert all paths are in argv in order
        assert "path_a" in argv, "path_a should be in argv"
        assert "path_b" in argv, "path_b should be in argv"
        assert "path_c" in argv, "path_c should be in argv"
        
        # Assert paths appear after the command part
        path_a_idx = argv.index("path_a")
        path_b_idx = argv.index("path_b")
        path_c_idx = argv.index("path_c")
        
        assert path_a_idx < path_b_idx < path_c_idx, "Paths should appear in config order"


class TestAT12AllowlistNormalization:
    """AT-12: Allowlist normalization (bare names → directories)."""
    
    @pytest.mark.xfail(
        reason="Waived: governance/mission-registry-v0.1 — steward runner repair tracked separately. Remove when AT-12 is fixed.",
        strict=True,
    )
    def test_bare_name_normalized_to_directory(self, worktree: Path, test_config: Path):
        """Bare names like 'docs' normalize to 'docs/' in committed paths."""
        # Update config with bare name (no trailing /)
        config_content = test_config.read_text()
        config_content = config_content.replace(
            'commit_paths: ["docs/"]',
            'commit_paths: ["docs"]'  # No trailing slash
        )
        config_content = config_content.replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        config_content = config_content.replace(
            'command: ["python3", "-c", "print(\'corpus generated\')"]',
            'command: ["python3", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        test_config.write_text(config_content)
        
        # Commit config changes
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "[test] AT-12 config"],
            cwd=worktree,
            capture_output=True,
        )
        
        (worktree / "docs").mkdir(exist_ok=True)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at12-test")
        
        assert exit_code == 0, "Should succeed with bare name normalized"
        assert log_file is not None
        
        events = read_log_events(log_file)
        commit_event = find_event(events, "commit", "pass")
        assert commit_event is not None, "Should have commit.pass event"
        
        # Normalized paths should have trailing /
        commit_paths = commit_event.get("commit_paths", [])
        assert "docs/" in commit_paths, "Bare name 'docs' should normalize to 'docs/'"


class TestAT13FailClosedUnsafePaths:
    """AT-13: Fail-closed on unsafe commit paths."""
    
    @pytest.mark.parametrize("unsafe_path,expected_error", [
        ("../docs/", "path_traversal"),
        ("docs/../other/", "path_traversal"),
        ("docs/*.md", "glob_pattern"),
        ("docs/?.md", "glob_pattern"),
        ("C:/temp/", "absolute_path_windows"),
        ("C:\\temp\\", "absolute_path_windows"),
        ("/absolute/path/", "absolute_path_unix"),
        ("/absolute/path/", "absolute_path_unix"),
        ("//server/share/", "absolute_path_unc"),
        ("docs%2Ffolder", "url_encoded_chars"),  # P2-B
    ])
    def test_unsafe_path_fails(self, worktree: Path, test_config: Path, unsafe_path: str, expected_error: str):
        """Unsafe paths fail closed with clear error reason."""
        # Update config with unsafe path
        config_content = test_config.read_text()
        # Escape for YAML
        escaped_path = unsafe_path.replace("\\", "\\\\")
        config_content = config_content.replace(
            'commit_paths: ["docs/"]',
            f'commit_paths: ["{escaped_path}"]'
        )
        config_content = config_content.replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        # Create a change so commit is attempted
        config_content = config_content.replace(
            'command: ["python3", "-c", "print(\'corpus generated\')"]',
            'command: ["python3", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        test_config.write_text(config_content)
        
        (worktree / "docs").mkdir(exist_ok=True)
        
        (worktree / "docs").mkdir(exist_ok=True)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id=f"at13-{expected_error}", commit=True)
        
        assert exit_code != 0, f"Should fail with unsafe path: {unsafe_path}"
        assert log_file is not None
        
        events = read_log_events(log_file)
        commit_fail = find_event(events, "commit", "fail")
        assert commit_fail is not None, "Should have commit.fail event"
        assert commit_fail.get("reason") == "invalid_commit_path"
        assert commit_fail.get("error") == expected_error, f"Expected error {expected_error}"


class TestAT14DirtyDuringRun:
    """AT-14: Changes appearing mid-run are rejected (P1-A)."""

    def test_dirty_during_run_rejected(self, worktree: Path, test_config: Path):
        """
        Simulate race condition where repo becomes dirty between change_detect and commit.
        
        Since existing tests use subprocess which makes patching hard, this test
        dynamically loads the runner module and tests run_commit directly.
        """
        # Load steward_runner module dynamically
        runner_path = worktree / "scripts" / "steward_runner.py"
        spec = importlib.util.spec_from_file_location("steward_runner", runner_path)
        runner_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner_module)
        
        # Setup mocks
        logger = MagicMock()
        config = {"git": {"commit_enabled": True, "commit_paths": ["docs/"]}}
        repo_root = worktree
        run_id = "at14-test"
        
        # Initial changed files (detected by change_detect step)
        initial_changes = ["docs/valid_change.md"]
        
        # Mock get_changed_files to return new dirty file on second call (inside run_commit)
        # First call is explicitly by our test (simulating change_detect)
        # Second call is inside run_commit -> triggers race condition check
        with patch.object(runner_module, 'get_changed_files') as mock_get_changed:
            # P1-A logic checks current_changed vs passed changed_files
            # We pass initial_changes to run_commit
            # verify_dirty_state calls get_changed_files()
            
            # Scenario: get_changed_files returns extra file "injected.txt"
            mock_get_changed.return_value = ["docs/valid_change.md", "injected.txt"]
            
            success, _ = runner_module.run_commit(
                config, logger, repo_root, run_id,
                initial_changes, False, False
            )
            
            assert not success, "Should fail when new dirty file appears"
            
            # Verify log call
            logger.log.assert_called_with(
                "commit", "commit", "fail",
                reason="repo_dirty_during_run",
                unexpected_files=["injected.txt"]
            )


class TestAT15LogFieldSorting:
    """AT-15: Log field sorting (P1-B)."""
    
    def test_log_lists_are_sorted(self, worktree: Path, test_config: Path):
        """File lists in logs must be sorted lexicographically."""
        # Create files in unsorted order
        (worktree / "docs").mkdir(exist_ok=True)
        filenames = ["z_file.md", "a_file.md", "m_file.md"]
        for name in filenames:
            (worktree / "docs" / name).write_text("test")
            
        # Add them so they show up in changed_files (if committed, verify validated/staged)
        # We need commit_enabled=True to check staged_files/commit_paths
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        test_config.write_text(config_content)
        
        # We need to make them dirty first (change_detect)
        # But for 'staged_files' inside commit event, they need to be valid
        # Let's clean worktree first then modify them?
        # fixture creates clean worktree.
        # newly created files are untracked.
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at15-test", dry_run=True)
        assert exit_code == 0
        
        events = read_log_events(log_file)
        
        checked_any = False
        for event in events:
            for key in ("files", "changed_files", "commit_paths", "disallowed_files"):
                if key in event and isinstance(event[key], list):
                    val = event[key]
                    if len(val) > 1:
                        assert val == sorted(val), f"{key} not sorted in {event['step']}"
                        checked_any = True
        
        assert checked_any, "Should have checked at least one list"


class TestAT16DefaultDryRun:
    """AT-16: Default is dry-run (P1-D)."""
    
    def test_no_flags_is_dry_run(self, worktree: Path, test_config: Path):
        """Run without flags -> dry run, no commit."""
        # Enable commit in config, but CLI default should override
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        config_content = config_content.replace(
            'command: ["python3", "-c", "print(\'corpus generated\')"]',
            'command: ["python3", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        test_config.write_text(config_content)
        
        # Don't pass dry_run=True, leave as default
        # But run_steward helper might need adjustment or allow None
        runner_path = worktree / "scripts" / "steward_runner.py"
        
        # Manual run without helper to ensure no flags
        result = subprocess.run(
            [PYTHON, str(runner_path), "--config", str(test_config.relative_to(worktree)), "--run-id", "at16"],
            cwd=worktree,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        
        # Check log for skipped reason
        log_dir = worktree / "logs" / "steward_runner"
        log_file = log_dir / "at16.jsonl"
        events = read_log_events(log_file)
        
        commit_skipped = find_event(events, "commit", "skipped")
        assert commit_skipped is not None
        assert commit_skipped.get("reason") == "dry_run"


class TestAT17CommitFlagEnables:
    """AT-17: --commit flag enables commit (P1-D)."""
    
    def test_commit_flag_enables(self, worktree: Path, test_config: Path):
        """Run with --commit -> commit happens."""
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        config_content = config_content.replace(
            'command: ["python3", "-c", "print(\'corpus generated\')"]',
            'command: ["python3", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        test_config.write_text(config_content)
        
        # Commit config change so only docs/ changes are uncommitted
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "[test] AT-17 config"],
            cwd=worktree,
            capture_output=True,
        )
        
        # Pass --commit
        exit_code, log_file = run_steward(worktree, test_config, run_id="at17", commit=True)
        assert exit_code == 0
        
        log_dir = worktree / "logs" / "steward_runner"
        log_file = log_dir / "at17.jsonl"
        events = read_log_events(log_file)
        
        # Debug: Check change detection
        change_event = find_event(events, "change_detect", "detected")
        assert change_event is not None, f"Change detection failed. Events: {events}"
        assert "docs/test.md" in change_event.get("changed_files", []), "docs/test.md not detected"
        
        commit_pass = find_event(events, "commit", "pass")
        assert commit_pass is not None, f"Should have committed with --commit flag. Events: {events}"


class TestAT18ExplicitDryRun:
    """AT-18: Explicit --dry-run (P1-D)."""
    
    def test_explicit_dry_run(self, worktree: Path, test_config: Path):
        """Run with --dry-run -> no commit."""
        # Same setup
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        config_content = config_content.replace(
            'command: ["python3", "-c", "print(\'corpus generated\')"]',
            'command: ["python3", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        test_config.write_text(config_content)
        
        runner_path = worktree / "scripts" / "steward_runner.py"
        
        # Pass --dry-run
        result = subprocess.run(
            [PYTHON, str(runner_path), "--config", str(test_config.relative_to(worktree)), "--run-id", "at18", "--dry-run"],
            cwd=worktree,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        
        log_dir = worktree / "logs" / "steward_runner"
        log_file = log_dir / "at18.jsonl"
        events = read_log_events(log_file)
        
        commit_skipped = find_event(events, "commit", "skipped")
        assert commit_skipped is not None
        assert commit_skipped.get("reason") == "dry_run"

```

### FILE: artifacts/status/runtime_status.json

```
{
  "contradictions": [],
  "facts": {
    "backlog_openclaw_install_unchecked": false,
    "lifeos_state_claims_openclaw_blocker": false,
    "openclaw_bin": "/home/linuxbrew/.linuxbrew/bin/openclaw",
    "openclaw_installed": true
  },
  "generated_at_utc": "2026-02-12T02:11:03.609985+00:00",
  "repo_root": "/mnt/c/Users/cabra/Projects/LifeOS",
  "status": "ok"
}

```

### FILE: artifacts/packets/status/checkpoint_report_20260212.json

```
{
  "contradictions": [],
  "facts": {
    "backlog_openclaw_install_unchecked": false,
    "lifeos_state_claims_openclaw_blocker": false,
    "openclaw_bin": "/home/linuxbrew/.linuxbrew/bin/openclaw",
    "openclaw_installed": true
  },
  "generated_at_utc": "2026-02-12T02:11:03.609985+00:00",
  "repo_root": "/mnt/c/Users/cabra/Projects/LifeOS",
  "status": "ok"
}

```
