# BACKLOG (prune aggressively; target ≤ 40 items)

## Workflow Hook

**"Done means" checklist:**

- [ ] Update BACKLOG item status + evidence pointer (commit/packet)
- [ ] Update `LIFEOS_STATE.md` (Current Focus/Blockers/Recent Wins)
- [ ] Refresh baseline pack pointer + sha (`artifacts/packets/status/Repo_Autonomy_Status_Pack__Main.zip`)

**Last Updated:** 2026-02-17 (rev4)

## Now (ready soon; not in WIP yet)

### P0 (Critical)

(None — W5-T01 E2E proof complete, W7 stabilization next)

### P1 (High)

- [x] **Ledger Hash Chain (Trusted Builder P1)** — DoD: Tamper-proof linking of bypass records — Owner: antigravity — Context: Deferred from Trusted Builder v1.1 Ratification
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

- [ ] **Strategic refresh of lifeos-master-operating-manual to v2.2** — Scope: Strategic rewrite and alignment with current runtime state — Deliverable: Diff-based update reflecting consolidation, alignment, and automation changes — Owner: antigravity — Context: Out-of-band for admin consolidation initiative; deferred
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
