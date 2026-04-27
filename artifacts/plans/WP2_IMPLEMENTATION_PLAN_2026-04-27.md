# WP2 — Implementation Plan: Authority Audit Decisions

**Status:** Planning artifact — awaiting execution instruction
**Ruling:** `artifacts/plans/WP2_CEO_DECISION_PACKET_2026-04-27.md` (ratified 2026-04-27)
**Branch:** `wp2/ratify-ceo-decisions`
**Owner:** Active COO
**Audit baseline:** `043c3f1d6b98f3cf713d3a29783e23383851dfa0`

---

## Goal

Capture planning artifacts for WP2 authority-audit decisions D1–D4b. Planning only — no runtime code, no parser changes, no lifecycle migration.

---

## Task Map

### D1 — G-CBS Demotion

| # | Task | Files touched |
|---|---|---|
| D1.1 | Audit `Council_Protocol_v1.3.md` for binding G-CBS references | `docs/01_governance/Council_Protocol_v1.3.md` |
| D1.2 | Patch or annotate binding G-CBS references as advisory | `docs/01_governance/Council_Protocol_v1.3.md` (and others as found) |
| D1.3 | Verify WP4 `closure_receipt.v1` schema exists and is referenced as the minimal closure-evidence standard (deferred until WP4 approval) | `artifacts/plans/WP4_LIFECYCLE_CLOSURE_DESIGN_2026-04-27.md` (reference only) |
| D1.4 | Mark G-CBS status as `Draft / Advisory` in any authoritative index if not already | `docs/02_protocols/G-CBS_Standard_v1.1.md` (annotation only) |

**Constraint:** Do not ratify G-CBS. Do not retire it. Keep as draft/advisory.

---

### D2 — Council Protocol Version Register

| # | Task | Files touched |
|---|---|---|
| D2.1 | Author `PROTOCOL_VERSION_REGISTER.md` | `docs/01_governance/PROTOCOL_VERSION_REGISTER.md` (new) |
| D2.2 | Catalogue stale protocol references (C-003 docs: binding spec, procedural spec, context pack schema, intent routing rule) | register entries only; no doc edits unless semantic compatibility verified |
| D2.3 | Add register reference to affected C-003 docs (annotation/stub, not version-bump) | `docs/02_protocols/Council_Invocation_Runtime_Binding_Spec_v1.1.md`, `docs/02_protocols/AI_Council_Procedural_Spec_v1.1.md`, `docs/02_protocols/Council_Context_Pack_Schema_v0.3.md`, `docs/02_protocols/Intent_Routing_Rule_v1.1.md` |

**Constraint:** Do not mass-bump docs to v1.3 unless semantic compatibility is verified per-document. Stale references are marked through the register, not silenced by bulk edits.

---

### D3 — DAP Normalisation

| # | Task | Files touched |
|---|---|---|
| D3.1 | Read current DAP (expect `docs/02_protocols/Deterministic_Artefact_Protocol_v1.0.md` or similar) | `docs/02_protocols/DAP_*.md` |
| D3.2 | Add bounded Gate 3 exceptions for: authority-audit packets, reconciliation receipts, closure receipts, generated evidence bundles | same DAP doc |
| D3.3 | Normalise path/status references to reflect actual repo usage | same DAP doc |

**Constraint:** No exhaustive artefact-path audit. Scope is bounded to adding the listed exceptions and correcting any immediately observable inconsistencies.

---

### D4a — Build Loop Canonicality Header

| # | Task | Files touched |
|---|---|---|
| D4a.1 | Read `LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md` | `docs/architecture/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md` |
| D4a.2 | Add canonicality header: canonical for build-loop design semantics and work-order flow; not canonical evidence of deployed runtime behaviour | same doc |
| D4a.3 | Runtime truth remains: receipts, tests, CI, current main, operational state — make this explicit in header or a footnote | same doc |

---

### D4b — Active COO Registry Source

| # | Task | Files touched |
|---|---|---|
| D4b.1 | Author `config/governance/active_coo.yaml` stub (empty or with current COO placeholder) | `config/governance/active_coo.yaml` (new) |
| D4b.2 | Document in the register (or a governance note) that GitHub issue state and GitHub Actions variables are mirrors only, not authoritative | `docs/01_governance/PROTOCOL_VERSION_REGISTER.md` or separate governance note |
| D4b.3 | Note that WP3 parser guards must fail closed if `active_coo_id` is missing or inconsistent with registry | Implementation note in plan; guard code is WP3 scope |

**Constraint:** `active_coo.yaml` is authorized for creation. WP3 parser guard implementation is out of scope.

---

## Files Expected to Be Created

| File | Purpose |
|---|---|
| `docs/01_governance/PROTOCOL_VERSION_REGISTER.md` | Source of truth for protocol version bindings |
| `config/governance/active_coo.yaml` | Authoritative active COO registry |

---

## Files Expected to Be Modified

| File | Decision | Change |
|---|---|---|
| `artifacts/plans/WP2_CEO_DECISION_PACKET_2026-04-27.md` | (this plan) | Updated to ratified status (done in this branch) |
| `docs/01_governance/Council_Protocol_v1.3.md` | D1 | Patch binding G-CBS references as advisory |
| `docs/02_protocols/G-CBS_Standard_v1.1.md` | D1 | Annotate status as Draft/Advisory |
| `docs/02_protocols/DAP_*.md` | D3 | Add Gate 3 bounded exceptions; normalise path/status |
| `docs/architecture/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md` | D4a | Add scoped canonicality header |
| `docs/02_protocols/Council_Invocation_Runtime_Binding_Spec_v1.1.md` | D2 | Add register reference (annotation, not version-bump) |
| `docs/02_protocols/AI_Council_Procedural_Spec_v1.1.md` | D2 | Add register reference |
| `docs/02_protocols/Council_Context_Pack_Schema_v0.3.md` | D2 | Add register reference |
| `docs/02_protocols/Intent_Routing_Rule_v1.1.md` | D2 | Add register reference |

---

## Explicit Non-Goals

The following are **not** in scope for WP2:

- WP3 approval enforcement implementation (schema, parser guards, execution_order authority fields)
- WP4 lifecycle/closure semantics implementation (closure_receipt.v1 schema, lifecycle_state.v1 FSM, disposition definitions)
- Runtime parser or FSM changes
- G-CBS ratification
- Lifecycle migration
- Exhaustive artefact-path audit
- Changes to `runtime/orchestration/coo/*` or `runtime/tests/orchestration/coo/*`
- Changes to `artifacts/coo/schemas.md` except as reference in this plan

---

## Acceptance Checklist

- [ ] `PROTOCOL_VERSION_REGISTER.md` created in `docs/01_governance/`
- [ ] `config/governance/active_coo.yaml` created (stub or initial value)
- [ ] `Council_Protocol_v1.3.md` binding G-CBS references patched or annotated
- [ ] G-CBS Standard annotated as Draft/Advisory
- [ ] DAP doc has bounded Gate 3 exceptions for audit/result/proposal/receipt/evidence artefacts
- [ ] Build Loop doc has scoped canonicality header
- [ ] No WP3/WP4 runtime code, parser changes, or FSM changes made
- [ ] No exhaustive artefact-path audit run
- [ ] Branch pushed; PR ready for review

---

## Tests and Checks Expected

**For this plan-only work package (artifacts/plans/*.md edits):**
- No repo-wide pytest required — plan-only close-build gate applies
- `git status` clean before commit

**For future WP2 execution pass (implementation):**
- `pytest runtime/tests -q` must pass before commit (no regressions)
- Quality gate (`python3 scripts/workflow/quality_gate.py check --scope changed --json`) on any modified code files
- Markdown lint on any new or modified `.md` files

---

## Dependency Notes

- D1.3 (WP4 `closure_receipt.v1` verification) is deferred until WP4 is independently approved.
- D4b parser guard failure-mode is documented for WP3 implementation; guard code itself is out of scope.
- WP3 implementation remains blocked on D1 (G-CBS demotion) and D4b (active COO registry) being resolved in a prior pass.