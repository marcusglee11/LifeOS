# Step 6 Parity Pack Manifest

**Created:** 2026-03-08
**Purpose:** Frozen replay inputs for Step 6 Stage A shadow validation (deterministic parity replay)
**Step 5 commit SHA:** 4483fdf0

This parity pack is read-only after creation. Do not modify these files.

---

## Source Provenance

| Pack file | Source path | Burn-in cycle |
|-----------|-------------|---------------|
| `propose_context.json` | `artifacts/coo/burnin/cycles/02/context.json` | Cycle 02 — Scenario 2: Propose from Backlog — Prioritisation |
| `propose_expected.yaml` | `artifacts/coo/burnin/cycles/02/parsed.yaml` | Cycle 02 parser output |
| `escalation_context.json` | `artifacts/coo/burnin/cycles/04/context.json` | Cycle 04 — Scenario 4: Escalation — Protected Path Touch |
| `escalation_expected.yaml` | `artifacts/coo/burnin/cycles/04/parsed.yaml` | Cycle 04 parser output |
| `ambiguous_context.json` | `artifacts/coo/burnin/cycles/05/context.json` | Cycle 05 — Scenario 5: Escalation — Ambiguous Scope |
| `ambiguous_expected.yaml` | `artifacts/coo/burnin/cycles/05/parsed.yaml` | Cycle 05 parser output |
| `ntp_context.json` | `artifacts/coo/burnin/cycles/06/context.json` | Cycle 06 — Scenario 6: NothingToPropose |
| `ntp_expected.yaml` | `artifacts/coo/burnin/cycles/06/parsed.yaml` | Cycle 06 parser output |

---

## Step 5 Acceptance Evidence

- CEO approval: 2026-03-08 (see `artifacts/coo/burnin/recommendation.md`, decision field checked)
- All 7 cycles passed (5 gating + 2 non-gating)
- No R/C/S defects in gating scenarios
- Step 5 squash merge: commit `4483fdf0`
