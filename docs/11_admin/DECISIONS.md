# DECISION LOG (append-only; low volume)

- **2026-01-02 — Decision:** Activate Tier-2.5 Semi-Autonomous Development Layer
  - **Why:** All activation conditions (F3, F4, F7) satisfied; Tier-2 tests 100% pass
  - **Scope:** Enables semi-autonomous doc stewardship, recursive builder, agentic missions
  - **Evidence:** [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](../01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md)

- **2026-01-02 — Decision:** Approve Stewardship Runner for agent-triggered runs
  - **Why:** Provides authoritative gating mechanism for stewardship ops with mandatory dry-run
  - **Scope:** Runtime stewardship, doc hygiene automation
  - **Evidence:** [Council_Review_Stewardship_Runner_v1.0.md](../01_governance/Council_Review_Stewardship_Runner_v1.0.md)

- **2026-01-03 — Decision:** Adopt thin control plane v1.1
  - **Why:** Reduces friction by externalising in-head state; prevents scaffolding spiral
  - **Scope:** Project admin via LIFEOS_STATE, BACKLOG, DECISIONS, INBOX
  - **Evidence:** `293f227`, `docs/11_admin/`

- **2026-01-03 — Decision:** Upgrade thin control plane to v1.2
  - **Why:** Refine evidence rules (anchoring), clarify hygiene triggers, adopt default sequencing rule
  - **Scope:** Admin hygiene protocols and evidence standards
  - **Evidence:** `3e545f7`, `docs/11_admin/`

- **2026-01-06 — Decision:** Activate Core TDD Design Principles v1.0
  - **Why:** Governance-first determinism for Core Track (runtime/mission, runtime/reactive); fail-closed enforcement scanner
  - **Scope:** TDD principles, allowlist governance, deterministic harness discipline
  - **Evidence:** [Council_Ruling_Core_TDD_Principles_v1.0.md](../01_governance/Council_Ruling_Core_TDD_Principles_v1.0.md)

- **2026-01-07 — Decision:** PASS (GO) for CT-2 Phase 2 — OpenCode Doc Steward Activation
  - **Why:** Full hardening of gate logic, diff envelope, and evidence hygiene verified (v2.4)
  - **Scope:** Enforced doc-steward gate (Phase 2), structural-op blocking, fail-closed CI diff
  - **Evidence:** [Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md](../01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md)
- **2026-01-07 — Decision:** PASS (GO) for Phase Gate Lift — Repair Bundle v1.3
  - **Why:** Full audit-mechanical remediation verified (v1.3); portability and determinism hygiene confirmed.
  - **Scope:** Authorizes transition from Hardening phase to Tier-2.5 Phase 2 Maintenance & Tier-3 Kickoff.
  - **Evidence:** `Bundle_COO_Runtime_Repair_v1.3.zip` (SHA256: `81AC0AB67B122359C0F8D6048F78818FE991F96349B6B24863A952495008D505`)

- **2026-01-23 — Decision:** CSO Role Constitution v1.0 Finalized
  - **Why:** Resolved Phase 3 approval condition C1; establishes Chief Strategy Officer role boundaries and responsibilities
  - **Scope:** Strategic planning, architectural decisions, long-range roadmap authority
  - **Decider:** Council
  - **Evidence:** [CSO_Role_Constitution_v1.0.md](../01_governance/CSO_Role_Constitution_v1.0.md)

- **2026-01-26 — Decision:** Trusted Builder Mode v1.1 Ratified
  - **Why:** Establishes autonomous build authority boundaries and guardrails for Phase 4 autonomous construction
  - **Scope:** Autonomous build loop policy, protected path enforcement, governance boundaries
  - **Decider:** Council
  - **Evidence:** [Council_Ruling_Trusted_Builder_Mode_v1.1.md](../01_governance/Council_Ruling_Trusted_Builder_Mode_v1.1.md)

- **2026-02-03 — Decision:** Phase 4 (4A0-4D) Merged to Main
  - **Why:** Full autonomous build loop stack validated (1327 passing tests); CEO Queue, Loop Spine, Test Executor, Code Autonomy all canonical
  - **Scope:** Autonomous build infrastructure operational; spine execution, policy hash, ledger integration, test execution complete
  - **Decider:** CEO (via Council authority)
  - **Evidence:** Merge commit `9f4ee41`, Phase 4A0-4D implementation, `docs/11_admin/LIFEOS_STATE.md`

- **2026-02-08 — Decision:** EOL Policy v1.0 Canonical
  - **Why:** Root cause fixed (system core.autocrlf conflict with .gitattributes); LF line endings enforced, clean gate hardened
  - **Scope:** Line ending normalization (289 files), config-aware clean gate, acceptance closure validator, 37 new tests
  - **Decider:** COO (policy execution)
  - **Evidence:** [EOL_Policy_v1.0.md](../02_protocols/EOL_Policy_v1.0.md), commits fixing CRLF issues, clean gate implementation

- **2026-02-14 — Decision:** E2E Spine Proof Complete (W5-T01)
  - **Why:** First successful autonomous build loop execution validated; core spine infrastructure proven through full 6-phase chain
  - **Scope:** Finalized Emergency_Declaration_Protocol v1.0 via autonomous run `run_20260214_053357`; fixed 2 blockers (obsolete model names, timeout)
  - **Decider:** COO Runtime (autonomous execution)
  - **Evidence:** [E2E_Spine_Proof_Build_Summary_2026-02-14.md](./build_summaries/E2E_Spine_Proof_Build_Summary_2026-02-14.md), terminal artifact `TP_run_20260214_053357.yaml`, commit `195bd4d`
