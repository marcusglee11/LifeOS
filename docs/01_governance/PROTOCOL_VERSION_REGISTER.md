# Protocol Version Register

**Status:** Canonical governance register  
**Effective date:** 2026-04-27  
**Authority:** WP2 CEO decisions D1-D4b, ratified in `artifacts/plans/WP2_CEO_DECISION_PACKET_2026-04-27.md`  
**Audit baseline:** `043c3f1d6b98f3cf713d3a29783e23383851dfa0`

---

## 1. Purpose

This register is the source of truth for current protocol version bindings where subordinate or procedural documents contain older local references.

It does not silently ratify stale subordinate text. Where a document references an older protocol version, the register records the current binding and the compatibility posture until that document is semantically reviewed and amended.

---

## 2. Current protocol bindings

| Protocol surface | Current binding | Status | Notes |
|---|---:|---|---|
| Council Protocol | `docs/02_protocols/Council_Protocol_v1.3.md` | Canonical | Binding constitutional Council Review procedure. |
| AI Council Procedural Specification | `docs/02_protocols/AI_Council_Procedural_Spec_v1.1.md` | Active procedural layer | Operationalises Council procedure; local references to older Council Protocol versions are superseded by this register. |
| Council Invocation Runtime Binding Spec | `docs/01_governance/Council_Invocation_Runtime_Binding_Spec_v1.1.md` | Active runtime binding | Runtime invocation binding remains active; Council Protocol references are interpreted through this register. |
| Council Context Pack Schema | `docs/02_protocols/Council_Context_Pack_Schema_v0.3.md` | Template / pre-v1.0 | Template references are non-ratifying and interpreted through this register. |
| Intent Routing Rule | `docs/02_protocols/Intent_Routing_Rule_v1.1.md` | WIP / Non-Canonical | Routing rule remains subordinate to CEO authority and higher governance documents; Council Protocol references are interpreted through this register. |
| Deterministic Artefact Protocol | `docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md` | Canonical governance specification | Current repo placement is `docs/02_protocols/`; older path text is normalised in the DAP document. |
| Generic Closure Bundle Standard | `docs/02_protocols/G-CBS_Standard_v1.1.md` | Draft / Advisory | Not ratified. Binding references must be interpreted as advisory unless and until CT-2 activation occurs. |

---

## 3. Stale-reference handling rule

When a binding or procedural document references a non-current Council Protocol version:

1. The document is not automatically amended by implication.
2. The current binding is resolved through this register.
3. Any semantic incompatibility must be handled by a targeted amendment, not by bulk version-bump.
4. If the stale reference would change runtime behaviour, fail closed and escalate for governance review.

---

## 4. Mirrors and non-authoritative surfaces

GitHub issue state, labels, PR status, and GitHub Actions variables may mirror governance state, but they are not authoritative unless a specific protocol designates them as such.

For active COO identity, the authoritative registry is:

- `config/governance/active_coo.yaml`

WP3 parser guards may consume that registry in a later work package, but parser-guard implementation is outside WP2 scope.

---

## 5. Amendment record

**2026-04-27 — WP2 authority audit implementation**
- Created protocol version register.
- Established Council Protocol v1.3 as current binding for Council behaviour.
- Recorded G-CBS as Draft / Advisory rather than ratified.
- Recorded `config/governance/active_coo.yaml` as authoritative active COO registry.
