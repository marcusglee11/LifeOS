# Council Context Pack — Build Handoff v0.5.1 / Scripts v1.0

**Pack ID**: Council_Context_Pack_Build_Handoff_20260104  
**Created**: 2026-01-04T14:35:00Z  
**Purpose**: Complete context for CT-2 council review of GEMINI.md Article XVII and Build Handoff Protocol

---

## A. CANONICAL COUNCIL PROCEDURE ASSETS (LOCATED)

### A1. Council Role Prompts (FOUND)

| Role | Path | Status |
|------|------|--------|
| Chair | `docs/09_prompts/v1.0/roles/chair_prompt_v1.0.md` | ✅ Canonical |
| Co-Chair | `docs/09_prompts/v1.0/roles/cochair_prompt_v1.0.md` | ✅ Canonical |
| L1 Unified Reviewer | `docs/09_prompts/v1.0/roles/reviewer_l1_unified_v1.0.md` | ✅ Canonical |
| Architect+Alignment | `docs/09_prompts/v1.0/roles/reviewer_architect_alignment_v1.0.md` | ✅ Canonical |

### A2. Council Output Template (FOUND)

From `Council_Protocol_v1.0.md` Section 3 — Reviewer Output Template (INVARIANT):

```
# Reviewer: [Role]

## 1. VERDICT
Accept / Go With Fixes / Reject

## 2. ISSUES
3–10 issues, prioritised

## 3. INVARIANT CHECK
Relation to LifeOS v1.1 invariants

## 4. NEW RISKS
Emergent architectural or governance risks

## 5. CEO-ONLY ALIGNMENT
Does the artefact move the system closer or further from CEO-Only mode?
```

### A3. Protected Paths Policy (FOUND)

**Canonical Source**: `config/governance/protected_artefacts.json`

```json
{
  "protected_paths": [
    "docs/00_foundations",
    "docs/01_governance",
    "docs/02_alignment",
    "docs/INDEX_v1.1.md",
    "config/governance/protected_artefacts.json"
  ],
  "locked_at": "2025-12-09T19:09:00+11:00",
  "locked_by": "Tier1_Hardening_v0.1"
}
```

**Note**: GEMINI.md is NOT in protected_artefacts.json but IS listed as governance-controlled in:
- `GEMINI.md` Article XIII Section 4: "These paths ALWAYS require Plan Artefact approval: ... GEMINI.md"
- This is agent-level protection, not runtime-level

---

## B. ARTEFACTS UNDER REVIEW

### B1. Modified Governance Docs

| File | Change Summary |
|------|----------------|
| `GEMINI.md` | Added Article XVII (Build Handoff Protocol) — 7 sections |
| `docs/02_protocols/Build_Handoff_Protocol_v1.0.md` | New protocol document |
| `docs/11_admin/LIFEOS_STATE.md` | Converted to Context Capsule format |
| `artifacts/workstreams.yaml` | New internal mapping file |

### B2. Scripts Under Review

| Script | Purpose |
|--------|---------|
| `docs/scripts/package_context.py` | Context pack generation |
| `docs/scripts/steward_blocked.py` | BLOCKED visibility |
| `docs/scripts/check_readiness.py` | Preflight with hash attestation |

### B3. Tests

| Test File | Coverage |
|-----------|----------|
| `runtime/tests/test_build_handoff_scripts.py` | 7 tests for scripts |

---

## C. ARTICLE XVII DIFF SUMMARY

**Added to GEMINI.md** (Constitution v2.7 → v2.8):

```markdown
# ARTICLE XVII — BUILD HANDOFF PROTOCOL (MANDATORY)

## Section 1. Internal Lineage Rules
- Mode 0: MAY generate new lineage for new workstream; MUST inherit for continuation
- Mode 1+: MUST NOT invent lineage; must accept from context packet

## Section 2. Preflight Priority
1. check_readiness.py if exists → 2. pytest fallback → 3. Blockers → 4. BLOCKED packets

## Section 3. Evidence Requirement
- Mode 0: log path required
- Mode 1: hash attestation required

## Section 4. ACK Handshake
Reply: "ACK loaded <path>. Goal: <1 line>. Constraints: <N>."

## Section 5. TTL Behavior
- Default: 72 hours
- Stale context blocks by default

## Section 6. CT-5 Restriction
- Requires objective CT-1..CT-4 linkage

## Section 7. No Internal IDs to CEO
- Agent MUST NOT surface lineage IDs/slugs to CEO

## Section 8. Clickable Pickup Links
- Auto-open Explorer for bundle delivery
- Provide raw copyable path
```

---

## D. TRIGGER CLASSIFICATION

| Trigger | Description | Applies |
|---------|-------------|---------|
| CT-2 | Touches governance-protected paths | ✅ GEMINI.md, Protocol doc |
| CT-3 | New CI script or gating change | ⚠️ check_readiness.py is preflight script |

---

## E. DECISION QUESTIONS FOR COUNCIL

1. **Approve Article XVII as written?**
2. **Approve `Build_Handoff_Protocol_v1.0.md` as controlling protocol for agent handoffs?**
3. **Confirm trigger classification CT-2 is correct and sufficient?**
4. **Approve deferral posture** (scripts implemented, pytest fallback acceptable for one cycle)?
5. **Any mandatory amendments before activation?**

---

## F. REFERENCES

| Document | Path | Purpose |
|----------|------|---------|
| Council Protocol v1.0 | `docs/99_archive/legacy_structures/Specs/council/Council_Protocol_v1.0.md` | Canonical procedure |
| Council Invocation Spec | `docs/01_governance/Council_Invocation_Runtime_Binding_Spec_v1.0.md` | Invocation rules |
| Governance Runtime Manual | `docs/08_manuals/Governance_Runtime_Manual_v1.0.md` | Role definitions |
| Protected Artefacts | `config/governance/protected_artefacts.json` | Protected paths list |
| Review Packet v0.5.1 | `artifacts/review_packets/Review_Packet_Build_Handoff_v0.5.1.md` | Architecture review |
| Review Packet Scripts | `artifacts/review_packets/Review_Packet_Build_Handoff_Scripts_v1.0.md` | Scripts review |
| Readiness Packet | `artifacts/packets/readiness/READINESS_build_handoff_scripts_20260104_031322.yaml` | Attestation |

---

## G. COUNCIL INVOCATION

Per `Council_Invocation_Runtime_Binding_Spec_v1.0.md`:

**Required Inputs** (Section 4.2):
1. ✅ Artefact Under Review (AUR) — GEMINI.md Article XVII, Build_Handoff_Protocol_v1.0.md
2. ✅ Role Set — L1 Unified Reviewer OR Architect+Alignment
3. ✅ Council Objective — Approve governance-protected changes
4. ✅ Output Requirements — Verdict, Issues, Invariant Check, Risks, Required Changes

**Recommended Role Set for CT-2**:
- Architect + Alignment Reviewer (governance focus)
- L1 Unified Reviewer (comprehensive single-pass)

---

**END OF COUNCIL CONTEXT PACK**
