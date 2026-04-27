# WP2 — CEO Decision Packet: Authority Audit Follow-Up

**Status:** RATIFIED — CEO decisions incorporated
**Ruling date:** 2026-04-27
**Ruling source:** CEO ruling (this session)
**Recording branch:** `wp2/ratify-ceo-decisions`
**Owner:** Active COO
**Source:** `docs/audit/LIFEOS_AUTHORITY_AUDIT_RESULT_2026-04-27.md` §H (C-003, C-008, C-009, C-010), §Open Decisions (OD-AUDIT-003, OD-AUDIT-004, OD-AUDIT-006)

---

## CEO Ruling

The following five decisions are final and binding for WP2 planning and future implementation. They do not authorize runtime parser/FSM changes, G-CBS ratification, lifecycle migration, or exhaustive artefact-path audit.

---

## D1 — G-CBS (OD-AUDIT-003, C-008)

**Decision:** Do not ratify G-CBS now.

**Ruling:**
- Demote G-CBS as binding for current closure enforcement.
- Remove or patch binding G-CBS dependencies where they block closure.
- `WP4/closure_receipt.v1` is to become the minimal canonical closure-evidence standard for current lifecycle closure, once WP4 is approved.
- G-CBS may remain draft/advisory pending later ratification or retirement.

**Rationale preserved from proposal:** G-CBS standard is draft/CT-2 while the Council Protocol v1.3 treats it as gating — a circular dependency. Demotion unblocks closure without requiring full ratification process. WP4's lightweight closure standard is the cleaner path for current needs.

**Effect on docs:** Any binding G-CBS reference in `Council_Protocol_v1.3.md` or related governance docs must be patched or annotated as advisory in the implementation pass.

---

## D2 — Council Protocol reference alignment (C-003, OD-AUDIT-006)

**Decision:** Approve Option B — create `PROTOCOL_VERSION_REGISTER.md`.

**Ruling:**
- Create `docs/01_governance/PROTOCOL_VERSION_REGISTER.md` as the source of truth for current Council/protocol version bindings.
- Do not mass-bump dependent docs merely to say v1.3 unless semantic compatibility is verified.
- Mark stale dependent references through the register (i.e. the register notes which docs are verified-compatible vs. stale).

**Rationale preserved from proposal:** Single source of truth for version binding; lowest long-term maintenance cost; referenced by docs, CI lints, and version-check tests.

**Effect on docs:** Version register to be authored in implementation pass. Binding doc edits to reference register are out of scope unless semantic compatibility is verified.

---

## D3 — DAP path/status consistency (C-009)

**Decision:** Keep DAP canonical; normalise to current repo practice.

**Ruling:**
- DAP remains the canonical Deterministic Artefact Protocol.
- Normalise DAP path/status to reflect actual repo usage.
- Add bounded exceptions for the following artefact types so DAP Gate 3 does not incorrectly block them:
  - audit artefacts
  - result artefacts
  - proposal artefacts
  - receipt artefacts
  - evidence artefacts / evidence bundles

**Excluded from this work:** Exhaustive artefact-path audit. Do not run one in this WP.

**Rationale preserved from proposal:** C-009 is MINOR severity — lightweight normalisation appropriate. Exemptions are bounded and specific; DAP authority is preserved for canonical artefact types.

---

## D4a — Build Loop canonicality (C-010, OD-AUDIT-004)

**Decision:** Add a scoped canonicality header to `LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md`.

**Ruling:**
- The document is canonical for build-loop design semantics and work-order flow only.
- It is **not** canonical evidence of deployed runtime behaviour.
- Runtime truth remains: receipts, tests, CI, current main, and operational state.

**Rationale preserved from proposal:** The doc is actively referenced and functionally canonical for build semantics. A header clarifies scope without breaking references.

---

## D4b — Active COO registry source (OD-AUDIT-004)

**Decision:** Use `config/governance/active_coo.yaml` as the authoritative active COO registry.

**Ruling:**
- `config/governance/active_coo.yaml` is the authoritative source for the active COO identity.
- GitHub issue state and GitHub Actions variables may mirror or cache the registry but are **not authoritative**.
- WP3 parser guards must fail closed if `active_coo_id` is missing or inconsistent with the registry.

**Note:** The file itself is not to be created in this work package — it is authorized for future creation in WP2 implementation pass.

**Rationale preserved from proposal:** Machine-checkable; explicit; cheapest path for sole-writer guard to read at dispatch time.

---

## Original Decision Options (preserved for audit trail)

| # | Decision | Options | Recommended | Final ruling |
|---|---|---|---|---|
| D1 | G-CBS ratify/demote/replace | A / B / C | B (demote) | **B — demote to advisory; WP4 closure_receipt.v1 becomes minimal standard** |
| D2 | Council Protocol reference alignment | A / B / C | B (version register) | **B — create PROTOCOL_VERSION_REGISTER.md; do not mass-bump unless semantic compatibility verified** |
| D3 | DAP path/status consistency | A / B / C | A (normalise) | **A — keep canonical; normalise with bounded Gate 3 exceptions for audit/result/proposal/receipt/evidence artefacts** |
| D4a | Build Loop canonicality | A / B | A (canonicality header) | **A — scoped canonicality header; canonical for design semantics/work-order flow only, not runtime truth** |
| D4b | Active COO registry source | A / B / C | B (config file) | **B — config/governance/active_coo.yaml authoritative; GitHub issue/Actions variables mirror only** |

---

## Implementation Boundary

These rulings authorize **planning and future implementation of WP2 only**, triggered by an explicit execution instruction.

They do **NOT** authorize:
- WP3 or WP4 implementation
- Runtime parser/FSM changes
- G-CBS ratification
- Lifecycle migration
- Exhaustive artefact-path audit
- Creation of `config/governance/active_coo.yaml` or `PROTOCOL_VERSION_REGISTER.md` in this pass (planning artifacts only)