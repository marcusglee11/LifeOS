# Review Packet: Implementing Phase A Loop Controller

**Mission**: Implement Phase A Convergent Builder Loop
**Date**: 2026-01-14
**Author**: Antigravity
**Version**: v1.2 (Closure-Grade Evidence)

## Summary

Refactored `AutonomousBuildCycleMission` to act as a Resumable, Budget-Bounded Loop Controller.
Implemented Deduplicated `AttemptLedger` (JSONL), `LoopPolicy`, and `BudgetController` with fail-closed enforcement.
**Verified P0 Closure Requirements:** Diff Budget (300 lines), Policy Hash Check, and Workspace Reset Logic.

## Certification of Acceptance Criteria

| Criteria | Status | Evidence |
|----------|--------|----------|
| **B1. State machine + resumability** | ✅ PASS | `test_loop_acceptance.py::test_crash_and_resume` passed. Verified ledger persistence across interrupts. |
| **B2. Attempt ledger schema** | ✅ PASS | `test_ledger.py` confirmed JSONL schema. E2E Demo output provided in Appendix. |
| **B3. Minimal taxonomy + policy** | ✅ PASS | `test_policy.py` confirms 6 failure classes and hardcoded rules. |
| **B4. Modification mechanism** | ✅ PASS | `BuildMission` successfully invoked via loop. |
| **B5. Budgets + termination** | ✅ PASS | `test_autonomous_loop.py::test_budget_exhausted` and `test_diff_budget_exceeded` passed. |
| **B6. Deadlock prevention** | ✅ PASS | `test_loop_acceptance.py::test_acceptance_oscillation` passed. E2E Demo caught oscillation. |
| **B7. Workspace semantics** | ✅ PASS | `test_workspace_reset_unavailable` confirms fail-closed behavior. |
| **B8. Packets** | ✅ PASS | `Review_Packet_attempt_XXXX.md` and `CEO_Terminal_Packet.md` generated. |
| **B9. Acceptance tests** | ✅ PASS | 18 TESTS PASSED. Includes Diff Budget violation (P0) and Policy Change (P0). |

## P0 Closure Evidence Requirement

| Requirement | Evidence | Hash (SHA-256) |
|-------------|----------|----------------|
| **Code Commit (Phase A)** | `e4cfa313e4d397d386ec4dfd9e689a2855320d7d` | `git show e4cfa31` |
| **Attempt Ledger** | `demo_env/artifacts/loop_state/attempt_ledger.jsonl` | `c8e2c0ae744f299b78bdf90963acf1634d53edc3b1e2fdccdd8525cb89cec0c3` |
| **CEO Terminal Packet** | `demo_env/artifacts/CEO_Terminal_Packet.md` | `b914fd1acc0d931cea1048164cfa798894e58c4e9d61cd4d7726fa466c1de1db` |
| **Diff Budget Enforcement** | `test_diff_budget_exceeded` | Proven by test (400 line diff -> ESCALATION_REQUESTED) |
| **Policy Hash Check** | `test_policy_changed_mid_run` | Proven by test (Hash Mismatch -> ESCALATION_REQUESTED) |
| **Workspace Reset** | `test_workspace_reset_unavailable` | Proven by test (Logic Stub -> ESCALATION_REQUESTED) |

## Integration Verification (E2E Proof)

Executed `scripts/manual/demo_loop.py` to simulate a loop run:

```text
=== STARTING PHASE A LOOP CONTROLLER DEMO ===
[DEMO] Invoking Mission: AutonomousBuildCycle
[DEMO] Review running... Type: build_review
[DEMO] Review running... Type: output_review
[DEMO] Review running... Type: output_review
[DEMO] Review running... Type: output_review
[DEMO] Mission Result: Success=False
[DEMO] Failure Reason: oscillation_detected
```

## Test Summary

```bash
$ python -m pytest runtime/tests/orchestration/missions/test_loop_acceptance.py -v
...
test_loop_acceptance.py::test_crash_and_resume PASSED
test_loop_acceptance.py::test_acceptance_oscillation PASSED
test_loop_acceptance.py::test_diff_budget_exceeded PASSED
test_loop_acceptance.py::test_policy_changed_mid_run PASSED
test_loop_acceptance.py::test_workspace_reset_unavailable PASSED
```

## Code Appendix

`(Prior code sections for taxonomy, ledger, policy, budget remain unchanged from v1.0)`

### docs/11_admin/LIFEOS_STATE.md

```markdown

# LIFEOS STATE

**Last Updated:** 2026-01-13 (Antigravity - Fix Harden E2E Harness v1.0)
**Current Phase:** Phase 3 (Mission Types & Tier-3 Infrastructure)

> **FOR AI AGENTS:** This document is your **PRIMARY SOURCE OF TRUTH**. It defines the current project context, the IMMEDIATE objective, and the future roadmap. You do not need to search for "what to do". Read the **IMMEDIATE NEXT STEP** section. references for required artifacts are listed there. **EXECUTE THE IMMEDIATE NEXT STEP.**

---

## 1. IMMEDIATE NEXT STEP (The "Prompt")

**Objective:** **Phase A Loop Controller - Acceptance & Closure**
**Status:** **READY**
**Owner:** Antigravity

**Context:**
Phase A (Convergent Builder Loop) implementation is complete (Loop Controller, Ledger, Budgets, Policy, Taxonomy). Unit and integration tests passing. Ready for formal acceptance and handoff.

**Development Approach:** Use the **Superpowers workflow** for structured development (see CLAUDE.md § Development Workflow):

- **Brainstorm** first to explore design space and alternatives
- **Plan** to break work into small testable batches
- **Execute** with strict TDD (test-first, then implementation)

**Next Candidates:**

1. **Recursive Builder Iteration** (Refinement) - Continue improving the autonomous build loop
2. **Mission Type Extensions** - Add new mission types based on backlog needs
3. **Integration Testing** - Comprehensive end-to-end testing of the full system

**Required Artifacts:**

- **Roadmap:** See section 2 below for Phase 3 & 4 items
- **Backlog:** `docs/11_admin/BACKLOG.md` for prioritized work items

---

## 2. ROADMAP (Phase 3 & 4)

**Phase 3: Mission Types & Tier-3 Infrastructure (Current)**

- [x] **G-CBS Readiness v1.1** (Completed)
- [x] **A1/A2 Re-closure v2.1c** (Completed)
- [x] **GitHub Actions CI Implementation** (Completed - PR #6 Active)
- [x] **CI Regression Fixes** (Completed - 0 failures, 18 files modified)
- [x] **OpenCode Sandbox Activation** (Completed - Envelope v2.0)
- [x] **Tier-3 CLI Integration** (Completed - Full integration with orchestrator, 103 tests passing)
- [x] **BuildWithValidation Mission Hardening v1.0** (Completed - Replaced LLM-loop with subprocess runtime, audit-grade evidence)
- [x] **Canonical CLI JSON & ID Hardening** (Completed - Unconditional wrapper and byte-for-byte determinism)
- [x] **BuildWithValidation Mission Type** (Implementation Hardened)
- [x] **Tier-3 Mission CLI E2E Sanity Harness** (Completed - High-signal harness with audit-grade evidence)
- [x] **Recursive Builder Iteration** (Phase A Implementation Complete)

**Phase 4: Autonomous Construction**

- [ ] Tier-3 Full Production Implementation
- [ ] Autonomous Mission Synthesis

---

## 3. BACKLOG (Tracked via LIFEOS_TODO tags)

<!--
Run `python scripts/todo_inventory.py` to see all active TODOs.
Use `python scripts/todo_inventory.py --priority P0` to see critical items.
-->

<!-- LIFEOS_TODO[P1][area: docs/11_admin/LIFEOS_STATE.md][exit: docs/03_runtime updated] Tier-3 planning: Scope Tier-3 Autonomous Construction Layer after Tier-2.5 Phase 2 completes -->

<!-- LIFEOS_TODO[P2][area: docs/11_admin/LIFEOS_STATE.md][exit: strategic review complete] Recursive Builder iteration: Refine recursive kernel based on learnings from current implementation -->

<!-- LIFEOS_TODO[P2][area: docs/11_admin/LIFEOS_STATE.md][exit: fuel track spec created] Fuel track exploration: Future consideration per roadmap, not blocking Core -->

<!-- LIFEOS_TODO[P2][area: docs/11_admin/LIFEOS_STATE.md][exit: productisation plan created] Productisation of Tier-1/Tier-2 engine: Depends on Core stabilisation -->

## 3. BACKLOG PRIORITIES (Active P0/P1 Items)

**P0 (Critical)**

- [x] **Standardize Raw Capture Primitive:** Implemented `run_command_capture` in `build_with_validation.py` with explicit hash collection.
- [ ] **Finalize CSO_Role_Constitution v1.0:** Remove markers, get CEO approval.
- [ ] **Review OpenCode Deletion Logic:** Investigate root cause of aggressive `git clean`.

**P1 (High)**

---

## 4. RECENT ACHIEVEMENTS (History)

**[CLOSED] Implement Phase A Loop Controller (Convergent Builder Loop v1.0)** (2026-01-14)

- **Outcome:** Implemented resumable, budget-bounded loop controller with strict fail-closed ledgers, policy checks, and token accounting.
- **Evidence:** `artifacts/review_packets/Review_Packet_Implementing_Phase_A_Loop_v1.0.md`

**[CLOSED] Fix Harden E2E Mission CLI Harness v1.2 (Patch Refinement)** (2026-01-14)

- **Outcome:** Refined the v1.1 patch with user-requested amendments: coherent wrapper errors, negative-case proof locator in E2E-3.meta.json, and full evidence hashing (including search_log.txt).
- **Evidence:** `artifacts/review_packets/Review_Packet_Fix_Harden_E2E_Mission_CLI_Harness_Patch_v1.1.md`
- **Closure:** `artifacts/closures/CLOSURE_FIX_HARDEN_E2E_HARNESS_v1.2.md`
- **Run ID:** `999d570a8bc1c5f0`

**[CLOSED] Fix Harden E2E Mission CLI Harness v1.0 (Truly Fail-Closed)** (2026-01-13)

**[CLOSED] Update LifeOS Overview v1.0** (2026-01-13)

- **Outcome:** Updated `LifeOS_Overview.md` for Phase 3 alignment. Mark Tier-3 as authorized. Enriched wins with CLI and BuildWithValidation details. Fixed pre-existing test debt in `test_cli_mission.py` and `test_missions_phase3.py`.
- **Evidence:** `artifacts/review_packets/Review_Packet_Update_LifeOS_Overview_v1.0.md`

**[CLOSED] Tier-3 Mission CLI E2E Sanity Harness (HARDENED)** (2026-01-13)

- **Outcome:** Hardened harness (`scripts/e2e/run_mission_cli_e2e.py`) with fail-closed entrypoint discovery, strict determinism matching, and audit-grade SHA256 evidence.
- **Evidence:** `artifacts/review_packets/Review_Packet_Harden_E2E_CLI_Harness_v1.0.md`
- **Bundle:** `artifacts/bundles/Bundle_Harden_E2E_CLI_Harness_v1.0.zip`

**[CLOSED] BuildWithValidation v0.1 P0 Patch 2 Refinement** (2026-01-13)

- **Outcome:** Hardened `baseline_commit` validation (regex), fixed `MissionType` enum correctness, and achieved audit-grade evidence for smoke check failures.
- **Evidence:** `artifacts/review_packets/P0_Patch_2_Refinement_Evidence.md`
- **Bundle:** `artifacts/bundles/Bundle_BuildWithValidation_P2_Refinement_v0.1.zip` (SHA: `DETACHED`)
- **Success:** Fulfilled CEO mandate for fail-closed determinism and disk-anchored evidence hashing.

**[CLOSED] Fix OpenCode Config Compliance v1.0** (2026-01-13)

- **Outcome:** Fixed critical configuration bug where runner blocked paid keys/logs by hardcoding `minimax-m2.1-free`. Enforced strict `config/models.yaml` compliance for all scripts.
- **Evidence:** `artifacts/review_packets/Review_Packet_Fix_OpenCode_Config_Compliance_v1.0.md`
- **Verification:** E2E connectivity tests confirmed correctly resolved model (grok) usage and log generation.

**[CLOSED] Grok Fallback Debug & Robustness Fixes v1.0** (2026-01-20)

- **Outcome:** Fixed silent CLI failures by enforcing `openrouter/` prefix for Grok. Implemented automatic fallback retry logic in `OpenCodeClient`. Verified 10-key matrix E2E.
- **Evidence:** `artifacts/review_packets/Review_Packet_Grok_Fallback_Debug_v1.0.md`
- **Verification:** `scripts/verify_automatic_fallback.py` and `scripts/verify_all_roles_execution.py`.

**[CLOSED] CLI & Mission Hardening v1.0** (2026-01-13)

- **Outcome:** Hardened CLI JSON contract (canonical wrapper, deterministic ID, compact formatting) and BuildWithValidation mission v0.1. Verified byte-identical determinism for auditability.
- **Evidence:** `artifacts/review_packets/Review_Packet_CLI_Hardening_BuildWithValidation_v1.0.md`
- **Bundle:** `artifacts/closures/Bundle_CLI_Hardening_BuildWithValidation_v1.0.zip` (SHA: `1df8f003...`)
- **Success:** Universal entry point contract stabilized for Tier-3 propagation.

**[CLOSED] Tier-3 CLI Integration (Full)** (2026-01-13)

- **Outcome:** Complete CLI integration with mission orchestrator verified. All subcommands operational (status, config, mission, run-mission). Dependencies installed (jsonschema, httpx). Entry point `lifeos` tested and functional.
- **Evidence:** 103 tests passing (16 CLI + 87 orchestration/registry), successful mission execution via CLI, pyproject.toml entry point configured.
- **Status:** Production-ready CLI interface for Tier-3 runtime operations.

**[CLOSED] BuildWithValidation Mission Hardening v0.1** (2026-01-13)

- **Outcome:** Remediated prototype mission into production-grade subprocess runtime. Implemented audit-grade evidence capture (SHA256 disk hashes) and strict schema validation.
- **Evidence:** `artifacts/review_packets/Review_Packet_BuildWithValidation_Hardening_v0.1.md`
- **Bundle:** `artifacts/bundles/Bundle_BuildWithValidation_Hardening_v0.1.zip`

**[CLOSED] BuildWithValidation Mission Type v0.1** (2026-01-13)

- **Outcome:** Implemented deterministic, smoke-first mission logic with strict schema validation and evidence capture. Replaced LLM-loop placeholder.
- **Evidence:** `artifacts/review_packets/Review_Packet_BuildWithValidation_Mission_v0.1.md`
- **Bundle:** `artifacts/bundles/Bundle_BuildWithValidation_Mission_v0.1.zip`

**[CLOSED] Tier-3 Mission Dispatch Wiring Fixes v1.0** (2026-01-13)

- **Outcome:** Remediated orchestrator dispatch logic, engine exception masking, and CLI success normalization. Achieved surgical packaging for CLI entry point `lifeos`. G-CBS v1.1 compliant closure.
- **Evidence:** `artifacts/closures/CLOSURE_Tier3_Mission_Dispatch_Wiring_Fixes_v1.0.md` (SHA: `AFAD790B16ADA730CE3371A99D03110F31EC034E2E092140B3C5DA689E3B8E2B`)
- **Bundle:** `artifacts/bundles/Bundle_Tier3_Mission_Dispatch_Wiring_Fixes_v1.0.zip` (SHA: `AE8C7644A8A193D7EFC8FBED10C5F85E5CEC10F324B1A8BC48714E70061F8A76`)

**[CLOSED] CI Regression Fixes v1.0** (2026-01-13)

- **Outcome:** Resolved 67 CI test regressions; All 902 tests passing (0 failures). Pushed `gov/repoint-canon` to origin. Updated indices and Strategic Corpus.
- **Evidence:** `artifacts/review_packets/Review_Packet_CI_Regression_Fixes_v1.0.md`

**[CLOSED] CI Regression Fixes** (2026-01-13)

- **Outcome:** Resolved 30 failing CI tests in PR #6. Achieved 896/0 pass rate across local suite.
- **Evidence:** Local pytest execution (Step Id 23).

**[CLOSED] OpenCode Sandbox Activation v2.4** (2026-01-13)

- **Outcome:** Phase 3 Builder Envelope activated; writes authorized for `runtime/` and `tests/`. Implemented audit-grade detached digest (v2.4) with Option A delivery wrapper (v2.4d).
- **Evidence:** `artifacts/closures/CLOSURE_OpenCode_Sandbox_Activation_v2.4.md`
- **Bundle:** `artifacts/closures/Bundle_OpenCode_Sandbox_Activation_v2.4.zip`
- **Wrapper:** `artifacts/closures/Bundle_OpenCode_Sandbox_Activation_v2.4d_delivery.zip`

**[CLOSED] A1/A2 Re-closure v2.1c** (2026-01-12)

- **Outcome:** Canonical bundles re-closed with G-CBS v1.1 compliance.
- **Evidence:** `artifacts/closures/CLOSURE_A1_A2_RECLOSURE_v2.1c.md`

**[CLOSED] GitHub Actions CI Integration** (2026-01-12)

- **Outcome:** Unified CI pipeline active (PR #6).
- **Evidence:** `ci.yml`, `pytest.ini` cleanup, PR #6 status.

**[CLOSED] G-CBS Readiness v1.1**

- **Outcome:** Closure Bundle Standard protocol ratified.
- **Evidence:** `artifacts/closures/CLOSURE_GCBS_READINESS_v1.1.md`

**[CLOSED] Mission Synthesis Engine MVP**

- **Outcome:** Backlog synthesis and CLI wiring verified.
- **Evidence:** `artifacts/closures/CLOSURE_MISSION_SYNTHESIS_MVP_v1.1.md`

**[CLOSED] OpenCode E2E Reliability Fixes**

- **Outcome:** Watchdog and process group cleanup implemented.
- **Evidence:** `artifacts/bundles/Bundle_OpenCode_E2E_Reliability_Fix_v1.2.zip`

---

## 5. REFERENCE SHELF

- **Development Workflow:** [`CLAUDE.md § Development Workflow`](../../CLAUDE.md) - Superpowers brainstorm → plan → execute cycle
- **Governance Policy:** [`docs/01_governance/OpenCode_First_Stewardship_Policy_v1.1.md`](../01_governance/OpenCode_First_Stewardship_Policy_v1.1.md)
- **Antigravity Protocol:** [`docs/03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md`](../03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md)
- **Planning Protocol:** [`docs/02_protocols/Project_Planning_Protocol_v1.0.md`](../02_protocols/Project_Planning_Protocol_v1.0.md)
- **Decision Log:** [`docs/11_admin/DECISIONS.md`](DECISIONS.md)

```

### docs/INDEX.md

```markdown

# LifeOS Strategic Corpus [Last Updated: 2026-01-14 (Phase A Loop Controller Implemented)]

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

---

## 00_foundations — Core Principles

| Document | Purpose |
|----------|---------|
| [LifeOS_Constitution_v2.0.md](./00_foundations/LifeOS_Constitution_v2.0.md) | **Supreme governing document** — Raison d'être, invariants, principles |
| [Anti_Failure_Operational_Packet_v0.1.md](./00_foundations/Anti_Failure_Operational_Packet_v0.1.md) | Anti-failure mechanisms, human preservation, workflow constraints |
| [Architecture_Skeleton_v1.0.md](./00_foundations/Architecture_Skeleton_v1.0.md) | High-level conceptual architecture (CEO/COO/Worker layers) |
| [Tier_Definition_Spec_v1.1.md](./00_foundations/Tier_Definition_Spec_v1.1.md) | **Canonical** — Tier progression model, definitions, and capabilities |
| [ARCH_Future_Build_Automation_Operating_Model_v0.2.md](./00_foundations/ARCH_Future_Build_Automation_Operating_Model_v0.2.md) | **Architecture Proposal** — Future Build Automation Operating Model v0.2 |

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
| [Document_Steward_Protocol_v1.0.md](./02_protocols/Document_Steward_Protocol_v1.0.md) | Document creation, indexing, GitHub/Drive sync |
| [Deterministic_Artefact_Protocol_v2.0.md](./02_protocols/Deterministic_Artefact_Protocol_v2.0.md) | DAP — artefact creation, versioning, and storage rules |
| [Build_Artifact_Protocol_v1.0.md](./02_protocols/Build_Artifact_Protocol_v1.0.md) | **NEW** — Formal schemas/templates for Plans, Review Packets, Walkthroughs, etc. |
| [Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md](./02_protocols/Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md) | Tier-2 API Versioning, Deprecation, and Compatibility Rules |
| [Build_Handoff_Protocol_v1.0.md](./02_protocols/Build_Handoff_Protocol_v1.0.md) | Messaging & handoff architecture for agent coordination |
| [Intent_Routing_Rule_v1.1.md](./02_protocols/Intent_Routing_Rule_v1.1.md) | Decision routing (CEO/CSO/Council/Runtime) |
| [LifeOS_Design_Principles_Protocol_v1.1.md](./02_protocols/LifeOS_Design_Principles_Protocol_v1.1.md) | **Canonical** — "Prove then Harden" development principles, Output-First governance, sandbox workflow |
| [Emergency_Declaration_Protocol_v1.0.md](./02_protocols/Emergency_Declaration_Protocol_v1.0.md) | **WIP** — Emergency override and auto-revert procedures |
| [Test_Protocol_v2.0.md](./02_protocols/Test_Protocol_v2.0.md) | **WIP** — Test categories, coverage, and flake policy |

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
