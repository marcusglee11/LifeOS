# Roadmap: Fully Autonomous Build Loops
## v1.1 (Re-ordered to match verified reality)

**Version:** 1.1  
**Date:** 2026-02-02  
**Status:** PLANNING (updated critical path)  
**End-state:** OpenCode as builder + doc-steward; Antigravity orchestrates in the interim.

---

## 1. Vision (Invariant)
Transform LifeOS into an exception-based autonomous build system:
- CEO states intent
- System selects tasks, designs, reviews, plans, builds, reviews, closes
- CEO involvement only via escalations / approvals

(Keep review intensity tiered per Council Protocol v1.3.) :contentReference[oaicite:18]{index=18}

---

## 2. Current State (Verified)
- Planning artifacts for Phase 4 are complete (Index + Roadmap + Phase plans). :contentReference[oaicite:19]{index=19}
- However, the chain-grade “A1 Loop Controller / loop spine” does not exist. :contentReference[oaicite:20]{index=20}

Therefore the roadmap must begin with a new Phase 4A0.

---

## 3. Phase 4A0 (P0): Loop Spine (A1 Controller) — NEW CRITICAL PHASE

### Goal
Implement the deterministic loop controller that:
- Hydrates from AttemptLedger
- Consults ConfigurableLoopPolicy for next-action decisions
- Sequences the canonical pipeline:
  intent/backlog → design → review → plan → review → build → review → packet → close
- Stops at checkpoints (e.g., CEO_REVIEW) and resumes deterministically

### Deliverables
- `runtime/orchestration/loop_controller.py` (or equivalent canonical location)
- Deterministic “run state” model persisted in ledger
- Checkpoint mechanism (pause/resume)
- End-to-end integration test: one dummy task runs full pipeline with a simulated checkpoint

### Success Criteria
- One command runs the pipeline until a checkpoint, exits cleanly, then resumes cleanly after “approval”
- Policy decisions are honored (not just logged)
- Evidence packet emitted on completion

---

## 4. Phase 4A (P0): CEO Approval Queue
(Keep the existing plan; it’s strong.) :contentReference[oaicite:21]{index=21}:contentReference[oaicite:22]{index=22}

### Key integration requirement (new)
CEO Queue must plug into Phase 4A0 checkpointing: “CEO_REVIEW” becomes a persisted queue item and the loop resumes only after resolution.

---

## 5. Phase 4B (P0): Backlog-Driven Execution
Goal: loop selects next task from BACKLOG.md and marks it complete on success. :contentReference[oaicite:23]{index=23}

### Dependency
Requires Phase 4A0 (spine) + Phase 4A (queue) to behave well in real usage.

---

## 6. Phase 4C (P1): OpenCode Envelope Expansion
Goal: expand execution surface so OpenCode can reliably run tests/build steps under the governed envelope. :contentReference[oaicite:24]{index=24}

---

## 7. Phase 4D (P1): Full Code Autonomy
Goal: broaden what can be modified while protecting governance/self-mod paths, so the loop can do real work safely.

---

## 8. Phase 4E (P2): Self-Improvement Loop
Goal: system proposes improvements to itself, routed through CEO review, with strong auditability. :contentReference[oaicite:25]{index=25}

---

## 9. Roadmap “North Star” Metrics (Operator-facing)
Track these to know autonomy is improving:
- % runs completed without CEO intervention
- Escalation rate
- Mean time from backlog selection to merge/close
- Review rejection rate by stage (design/plan/build)
- Flake/waiver frequency

(Keep this simple at first; don’t over-instrument.)

---
