# Council Ruling — Phase 9 Ops Ratification v1.0

**Ruling ID:** CR_20260403_Phase9_Ops_Ratification
**Ruling Date:** 2026-04-03
**Decision**: RATIFIED
**Basis:** AUR_20260403_phase9_ops_ratification (CCP + 11 seat outputs)

---

## 1. Decision

The `workspace_mutation_v1` constrained ops lane is hereby **RATIFIED** as the sole
approved operational lane for Phase 9. Certification profiles `ci` and `live` may
now pass when `approval_ref` points to this ruling.

---

## 2. Scope Statement

This ruling ratifies:

- **Lane:** `workspace_mutation_v1`
- **Allowed actions:** `workspace.file.write`, `workspace.file.edit`, `lifeos.note.record`
- **Approval class:** `explicit_human_approval` (all actions require human approval)
- **Profiles:** `local`, `ci`, `live` — all now eligible to certify

This ruling does **NOT**:

1. Expand executor scope beyond the three named actions
2. Pre-authorize any Phase 10 lane or operational class
3. Approve unattended (auto-approved) operations
4. Modify the COO Operating Contract or delegation envelope

---

## 3. Verdict Breakdown

| Seat                     | Model              | Verdict | Confidence | Independence |
| ------------------------ | ------------------ | ------- | ---------- | ------------ |
| Co-Chair                 | claude-opus-4-6    | Accept  | High       | primary      |
| Architect                | claude-opus-4-6    | Accept  | High       | primary      |
| Alignment                | claude-opus-4-6    | Accept  | High       | primary      |
| Structural & Operational | claude-opus-4-6    | Accept  | High       | primary      |
| Simplicity               | claude-opus-4-6    | Accept  | High       | primary      |
| Technical                | codex (OpenAI)     | Revise  | Medium     | primary      |
| Testing                  | codex (OpenAI)     | Revise  | Medium     | primary      |
| Risk/Adversarial         | gemini-3-pro       | Accept  | High       | independent  |
| Determinism              | gemini-3-pro       | Accept  | High       | independent  |
| Governance               | gemini-3-pro       | Accept  | High       | independent  |

**Mode:** M2_FULL | **Topology:** HYBRID | **Independence:** §6.3 MUST satisfied (gemini)

---

## 4. P0 Blockers

None. The two Revise verdicts (codex Technical/Testing) raised defensive
hardening concerns about empty-manifest edge cases. These were assessed
against §7.2 P0 Blocker Criteria and classified as P2 (non-blocking
guidance) — they concern hypothetical configuration corruption, not
governance boundary bypass or authority chain violation.

---

## 5. Deferred Items (Backlog)

| Priority | Item                                                   | Source Seat          |
| -------- | ------------------------------------------------------ | -------------------- |
| P1       | Add git commit SHA to `ops_readiness.json`             | Determinism (gemini) |
| P2       | Fail closed on empty/missing lanes list                | Technical (codex)    |
| P2       | Require non-empty `required_suites` for ci/live        | Technical (codex)    |
| P2       | Add tests for empty lanes, missing profiles, worktrees | Testing (codex)      |
| P2       | Consider cryptographic signing of readiness artifact   | Risk (gemini)        |

---

## 6. Evidence References

| Artifact             | Location                                                          |
| -------------------- | ----------------------------------------------------------------- |
| CCP                  | `artifacts/council_reviews/phase9_ops_ratification.ccp.yaml`      |
| Phase 9 Spec         | `artifacts/plans/2026-04-02-phase9-ops-autonomy-spec.md`          |
| Review Packet        | `artifacts/review_packets/Phase9_Ops_Autonomy_Review_Packet.md`   |
| Lane Manifest        | `config/ops/lanes.yaml`                                           |
| Certification Runner | `scripts/run_ops_certification.py`                                |
| Certification Tests  | `runtime/tests/test_ops_certification.py`                         |
| Chair Synthesis      | `artifacts/council_reviews/phase9_seat_outputs/`                  |
| Pre-review state     | local: prod\_local, ci: red, live: red                            |

---

## 7. Ratification Authority

This ruling is issued under the authority of the LifeOS Council governance
framework as defined in Council Protocol v1.3. CEO approval was granted
explicitly on 2026-04-03.

---

## Amendment Record

**v1.0 (2026-04-03)** — Initial ratification of `workspace_mutation_v1`
constrained ops lane. No conditions. 5 items deferred to backlog
(1 P1, 4 P2).
