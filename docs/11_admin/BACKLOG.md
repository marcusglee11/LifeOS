# BACKLOG (prune aggressively; target ≤ 40 items)

<!-- markdownlint-disable MD012 MD013 -->

## Workflow Hook

**"Done means" checklist:**

- [ ] Update BACKLOG item status + evidence pointer (commit/packet)
- [ ] Update `LIFEOS_STATE.md` (Current Focus/Blockers/Recent Wins)
- [ ] Refresh baseline pack pointer + sha (`artifacts/packets/status/Repo_Autonomy_Status_Pack__Main.zip`)

**Last Updated:** 2026-04-27 (rev17)

## Architecture Normalization — RESOLVED (per ADR-001 through ADR-004 and changelog A1-A5)

- [x] **Ratify human approval capture contract** — ADR-003 ratified 2026-04-26 via PR #38. §9 in `COO_Operating_Contract_v1.0.md`.
- [x] **Ratify active vs standby COO semantics and sole-writer boundary** — ADR-001 ratified 2026-04-24 via PR #36. §7 in `COO_Operating_Contract_v1.0.md`.
- [x] **Resolve Drive / Workspace role in canon** — ADR-004 ratified 2026-04-26 via PR #39. Drive/Workspace = non-canonical collaboration surface.
- [x] **Resolve Hermes ↔ OpenClaw directionality and pushback rules** — ADR-002 ratified 2026-04-24 via PR #36. §8 in `COO_Operating_Contract_v1.0.md`.
- [x] **Reconcile communications draft with canon or mark proposal-only** — Changelog A4 implemented 2026-04-27 via PR #40. Communications draft classified proposal-only/non-canonical.
- [x] **Install architecture-maintenance checks after canon is stable** — Changelog A5 implemented 2026-04-27 via PR #40. Event-triggered pre-merge architecture impact rule active.

---

## Now (ready soon; not in WIP yet)

### P0 (Critical)

- [x] **Run-lock implementation** — DoD: Single-flight enforcement, stale lock detection, concurrent test + stale test pass — Owner: antigravity — Context: Build Loop Plan v2.1 Week 1 prerequisite — **Done: 2026-02-26** — `runtime/orchestration/loop/run_lock.py` (142L), wired to spine, 8 tests (`test_run_lock.py`)
- [x] **Terminal packet + receipt emission** — DoD: Schema matches Evidence Contract; dry-run cycle produces valid packet + receipt index — Owner: antigravity — Context: Build Loop Plan v2.1 Week 1 prerequisite — **Done: 2026-02-26** — `runtime/receipts/invocation_receipt.py` (189L), wired to spine, 12 tests (`test_invocation_receipt.py`, `test_invocation_schema.py`)
- [x] **Council V2 shadow-mode wiring** — DoD: V2 receives payloads in parallel, verdicts logged, does not gate; legacy remains sole gate — Owner: antigravity — Context: Build Loop Plan v2.1 Week 1 prerequisite — **Done: 2026-02-27** — `ShadowCouncilRunner` imported + called in `spine._run_chain_steps` after review phase (`7e36284e`); 2 wiring tests added
- [x] **Shadow agent capture mechanism** — DoD: Dispatches payload, stores evidence, does not affect pipeline — Owner: antigravity — Context: Build Loop Plan v2.1 Week 1 prerequisite — **Done: 2026-02-26** — `runtime/agents/shadow_capture.py` (185L), wired to spine, 5 tests (`test_shadow_capture.py`)
- [x] **GitHub Actions feasibility report** — DoD: Investigation report at artifacts/reports/github_actions_feasibility.md — Owner: antigravity — Context: Build Loop Plan v2.1 Week 1 (investigation only) — **Done: 2026-02-27** — 10 sections, 8 workflows, 5 blockers (B3 RESOLVED), 10 recommendations (`87f548c5`)
- [x] **Burn-in task curation (CEO approval required)** — DoD: 5-7 tasks proposed at artifacts/reports/burn_in_task_proposal.md, CEO approved, ready for Batch 1 — Owner: antigravity — Context: Build Loop Plan v2.1 §1 — **Done: 2026-02-27** — Batch 1 completed; report at `docs/11_admin/Batch1_BurnIn_Report.md` (`78473e3`)
- [x] **Batch 2 burn-in** — DoD: 5 cycles post top-3 fixes; Batch 2 summary report with delta from Batch 1; Council V2 promotion criteria evaluated — Owner: antigravity — Context: Build Loop Plan v2.1 §2 — Preceded by: apply F5 (steward budget), F2 (default allowed_paths), F3 (attempt ledger auto-commit)

### P1 (High)

- [ ] **Phase 7 `prod_ci` canonical closure** — DoD: default-branch `Prod CI Proof` workflow dispatches and passes, `T-022` repeat-run proof is re-recorded from a clean worktree, and canon is reconciled — Owner: codex — Context: local `main` is 117 commits ahead of `origin/main`; `gh workflow run .github/workflows/prod_ci_proof.yml --ref main` currently returns 404 — Priority: P1
- [ ] **Authority audit WP2: CEO decision packet** — G-CBS canonicality, Council protocol references, DAP consistency, Build Loop canonicality — Owner: active COO — Context: audit OD-AUDIT-003, C-003, C-008, C-009, C-010 — priority: P1 — See `artifacts/plans/WP2_CEO_DECISION_PACKET_2026-04-27.md`
- [ ] **Authority audit WP3: approval/authority enforcement design** — `approval_receipt.v1` schema, `execution_order.v1` authority fields, parser guard plan — Owner: active COO — Context: audit C-006, C-007, APPROVAL-002 — priority: P1 — See `artifacts/plans/WP3_APPROVAL_ENFORCEMENT_DESIGN_2026-04-27.md`
- [ ] **Authority audit WP4: lifecycle/closure semantics design** — `succeeded` disposition, `closed` requirements, closure receipt path — Owner: active COO — Context: audit C-016, STATE-002, OD-AUDIT-002 — priority: P1 — See `artifacts/plans/WP4_LIFECYCLE_CLOSURE_DESIGN_2026-04-27.md`
- [ ] **T-027 COO closure packet schemas and loader** — DoD: `artifacts/coo/schemas.md` documents the new packet family; `closures.py` validates and loads close/context/council-request artifacts; targeted tests pass — Owner: codex — Context: first slice of the COO coordination loop; file-based artifacts only — Priority: P1
- [ ] **T-028 decision-support backlog field and dispatch gate** — DoD: `decision_support_required` round-trips through backlog state transitions and blocks L0 auto-dispatch until the latest matching council request is resolved — Owner: codex — Context: second slice of the COO coordination loop — Priority: P1
- [ ] **T-029 `coo process-closures` and orientation updates** — DoD: `python3 -m runtime.cli coo process-closures` validates and summarizes closure artifacts; COO brief now reads closures and `artifacts/for_ceo/` — Owner: codex — Context: third slice of the COO coordination loop — Priority: P1
- [ ] **T-030 sprint-close emission and CT-6 governance hook** — DoD: wrappers emit `sprint_close_packet.v1`; governance and handoff updates land only after Council approval — Owner: codex — Context: final protected slice of the COO coordination loop; blocked on Council ruling — Priority: P1
- [x] **Ledger Hash Chain (Trusted Builder P1)** — DoD: Tamper-proof linking of bypass records — Owner: antigravity — Context: Deferred from Trusted Builder v1.1 Ratification
- [ ] **OpenClaw distill lane operational rollout** — DoD: Session-scoped shadow rollout completed with 12-run / 2-session clean window, CEO-approved shadow success receipt recorded, `models status` active promotion gated by fresh preflight + forced-failure drill + CEO approval, runbook/state updated — Owner: Substrate — Context: Collaborators COO + CEO; distill lane is merged on `main` but not yet an active operating practice; milestone 1 keeps raw path authoritative and `status --all --usage` shadow-only — Priority: P1
- [ ] **Bypass Monitoring (Trusted Builder P1)** — DoD: Alerting on high bypass utilization — Owner: antigravity — Context: Deferred from Trusted Builder v1.1 Ratification
- [ ] **Semantic Guardrails (Trusted Builder P1)** — DoD: Heuristics for meaningful changes — Owner: antigravity — Context: Deferred from Trusted Builder v1.1 Ratification
- [ ] **Fix test_steward_runner.py (25/27 failing)** — DoD: Tests pass or are properly restructured — Owner: antigravity — Context: Import/fixture issues, not code bugs; currently skipped on WSL (build/doc-refresh-and-test-debt)
- [x] **Finalize Intent_Routing_Rule v1.1** — DoD: Markers removed — Owner: antigravity
- [x] **Finalize Test_Protocol v2.0** — DoD: Markers removed — Owner: antigravity
- [x] **Finalize Tier_Definition_Spec v1.1** — DoD: Markers removed — Owner: antigravity
- [x] **Finalize ARTEFACT_INDEX_SCHEMA v1.0** — DoD: Markers removed — Owner: antigravity
- [x] **Finalize QUICKSTART v1.0** — DoD: Context scan pass complete — Owner: antigravity
- [x] **Fix claude_doc_stewardship_gate.py INDEX.md timestamp bug** — DoD: --auto-fix handles `[Last Updated: YYYY-MM-DD (revN)]` format correctly — Owner: antigravity — Context: Auto-fix regex corrupts INDEX.md timestamp in bracket format (P2)


## Next (valuable, but not imminent)

### Agent Efficiency Initiative

See living doc: `artifacts/plans/2026-04-06-agent-efficiency-improvements.md`

- [x] **T-AE-01 Run-level token ledger + CLI estimation** — DoD: Cumulative token spend visible across all agent calls in a run; 80% budget warning emitted before exhaustion; CLI invocations contribute `estimated_tokens` (not just API calls) — Owner: Substrate — Context: Port aggregation pattern from `autonomous_build_cycle.py:337` into LoopSpine/dispatch/COO path; extend `budgets.py:23` and `api.py:671` — Priority: P1 — **Done: 2026-04-07** — Evidence: `runtime/agents/api.py`, `runtime/orchestration/loop/budgets.py`, `runtime/orchestration/loop/spine.py`; `pytest runtime/tests -q` PASS (`3058 passed, 6 skipped`); focused AE token suite PASS (`24 passed`)
- [x] **T-AE-02 COO context telemetry + stable block reuse** — DoD: `build_propose_context()` logs serialized byte sizes per block; stable blocks (REPO_MAP, delegation_envelope) get content-addressed IDs excluding ephemeral fields; repeated same-session invocations skip re-serializing unchanged blocks — Owner: Substrate — Context: `context.py:148` (cache keys), `context.py:152` (slim actionable_tasks fields), `invoke.py:105` — Priority: P1 — **Done: 2026-04-07** — Evidence: `runtime/orchestration/coo/context.py`; `runtime/tests/orchestration/coo/test_context.py`; `pytest runtime/tests -q` PASS (`3058 passed, 6 skipped`); focused AE token suite PASS (`24 passed`)
- [x] **T-AE-03 REPO_MAP freshness gate in start_build.py** — DoD: `start_build.py` warns (or blocks, configurable) when REPO_MAP.md is >7 days old; reuses existing detector at `scripts/entropy/scan_v1.py:55`; no auto-commit automation — Owner: Substrate — Context: REPO_MAP was 25 days stale at 2026-04-06 analysis — Priority: P1 — **Done: 2026-04-07** — Evidence: `scripts/workflow/start_build.py`, `scripts/entropy/scan_v1.py`, `runtime/tests/test_build_start_close.py`; `pytest runtime/tests -q` PASS (`3058 passed, 6 skipped`); focused AE token suite PASS (`24 passed`)

- [ ] **Tech Debt Audit Follow-up** — DoD: Address items in `docs/11_admin/TECH_DEBT_INVENTORY.md` as their trigger conditions are met — Context: Inventory created 2026-02-27 during 3-pass audit; 5 resolved items, 8 tracked items with explicit triggers — Priority: P2

- [ ] **Strategic refresh of lifeos-master-operating-manual to v2.2** — Scope: Strategic rewrite and alignment with current runtime state — Deliverable: Diff-based update reflecting consolidation, alignment, and automation changes — Owner: antigravity — Context: Out-of-band for admin consolidation initiative; deferred
- [ ] **Configure GCP Employee instance** — Context: Hardened OpenClaw config, dedicated accounts, Tailscale
- [ ] **Revenue Track: LinkedIn daily posts** — Context: COO drafts, CEO reviews. Seed: "What autonomous AI agents actually cost to run"
- [ ] **Revenue Track: B5 Governance Guide** — Context: 19,500 lines of real code + 1,440 tests backing the content
- [ ] **Mission Type Extensions** — Why Next: Add new mission types based on backlog needs
- [ ] **Gate 6: Agent-Agnostic Gate Runner** — DoD: Refactor claude-specific gates into `coo gate run-all`; wire into `coo land` — Owner: antigravity — Context: Doc stewardship status report identifies Claude-specific gates as non-portable
- [x] **Tech Debt: Rehabilitate Legacy Git Workflow Tests** — Context: Quarantined to archive_legacy_r6x due to missing run_cmd mock. Rehabilitate or remove.

### COO Step 6 Known Gaps (carried forward 2026-03-08)

- [x] **COO Sandboxing Decision** — DoD: Council ruling on OS-level containment strategy — Owner: Council — Context: COO currently runs with full filesystem + exec access (`sandboxed: false`); autonomy boundary is delegation envelope + fail-closed reasoning only. Requires architectural decision before L1/L2 autonomy promotion — Priority: P2 — **Done: 2026-03-24** — Council ruling APPROVED (2026-03-20); COO promoted to unsandboxed prod L3; manifest active; Gate-6 UAT 5/5 PASS
- [ ] **COO schema drift guard** — DoD: `output_schema` in `context.py` and `artifacts/coo/schemas.md` stay in sync; add CI check or single source-of-truth — Owner: Substrate — Context: Step 6 gap #3; `build_propose_context()` embeds schema inline, divergence from `schemas.md` is silent — Priority: P2
- [x] **`cmd_coo_direct()` live Stage A parity** — DoD: Escalation and ambiguous parity cases pass live COO replay (not just mock tests) — Owner: Substrate — Context: Step 6 gap #4; only mocked tests exist; Stage A escalation/ambiguous cases were SKIPPED — Priority: P2 — **Done: 2026-04-02** — `T-016` closed from Gate 6 evidence plus direct-path coverage on main
- [x] **COO retry/backoff in `invoke_coo_reasoning()`** — DoD: Gateway timeouts trigger exponential backoff (max 2 retries) before raising `InvocationError` — Owner: Substrate — Context: Step 6 gap #5; current adapter is single-shot; gateway restarts cause cascading failures — Priority: P3 — **Done: 2026-03-27** — merged `1cd86177` + `69eb7a10`
- [x] **COO cron/event trigger** — DoD: `lifeos coo propose` runs on a schedule or backlog-change event without manual invocation — Owner: Wiring — Context: Step 6 gap #6; currently manual-pull only — Priority: P2 — **Done: 2026-03-09** — OpenClaw cron heartbeat registered (`T-018`)
- [x] **`coo.md` output schema section** — DoD: `config/agent_roles/coo.md` includes inline output schema matching `context.py`; `schemas.md` cross-referenced — Owner: Docs — Context: Step 6 gap #7; schema lives only in `schemas.md` + `context.py`, not in the role definition the COO reads — Priority: P2 — **Done: 2026-04-02** — `T-019` closed with prompt authority split in `config/agent_roles/coo.md` and `config/coo/prompt_canonical.md`
- [x] **`_normalize_proposal_indentation()` field coverage** — DoD: Either generalize the normalizer or add a regression test that fails when new COO sub-keys appear at column 0 — Owner: Substrate — Context: Step 6 gap #2; currently hard-codes 4 field names; new sub-keys silently ignored — Priority: P3 — **Done: 2026-04-02** — `T-020` closed with fail-closed normalization coverage in main
- [ ] **Thread `OPENCLAW_BIN` into promotion state version check** — DoD: `_current_openclaw_version()` in `openclaw_promotion_state.py` uses `OPENCLAW_BIN` env var (already set by `openclaw_coo_update_protocol.sh`) instead of bare PATH lookup; test with fake binary at explicit path — Owner: Substrate — Context: Codex review finding on `build/openclaw-runtime-upgrade`; version check gates promotion but resolves binary from untrusted PATH; defense-in-depth, not urgent since orchestrated-mode + attestation TTL bound the attack window — Priority: P2

## Later (not actionable / unclear / exploratory)

- [ ] **Fuel track exploration** — Why Later: Not blocking Core; future consideration per roadmap
- [ ] **Productisation of Tier-1/Tier-2 engine** — Why Later: Depends on Core stabilisation

## Done (last ~25 only)

- [x] **W5-T02 Checkpoint/Resume E2E Proof** — Date: 2026-02-19 — 6 integration tests proving full checkpoint/resume cycle with policy hash continuity and ledger anchoring. Evidence: `artifacts/evidence/W5_T02_checkpoint_resume_proof.txt`
- [x] **W4-T03 Worktree Dispatch Governance** — Date: 2026-02-18 — Spine now enforces isolated worktree lifecycle + clean-worktree fail-closed check (`runtime/orchestration/loop/spine.py`)
- [x] **W4-T04 Validator Lifecycle Hooks (OpenClaw Path)** — Date: 2026-02-18 — OpenClaw execution bridge + CLI command + lifecycle-integrated test coverage (`runtime/orchestration/openclaw_bridge.py`, `runtime/cli.py`)
- [x] **Guard deprecated `autonomous_build_cycle` path** (W0-T04) — Date: 2026-02-13 — cli.py deprecation guard + autonomous_build_cycle.py migration notice
- [x] **Doc freshness skeleton gate** (W0-T06) — Date: 2026-02-14 — Runtime status generator, checkpoint artifacts, close-build integration
- [x] **Fix test_e2e_smoke_timeout.py** (W0-T05) — Date: 2026-02-14 — Tests already passing, no work needed
- [x] **E2E Loop Test: Real task through full pipeline** — Date: 2026-02-14 — run_20260214_053357 completed full 6-phase chain, finalized Emergency_Declaration_Protocol v1.0, discovered/fixed model config issues
- [x] **Finalize Emergency_Declaration_Protocol v1.0** — Date: 2026-02-14 — Completed via autonomous spine run, markers removed, status changed to ACTIVE
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
