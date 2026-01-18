# Review Packet: Council Prompt Alignment

**Mode:** Lightweight Stewardship (Diff-Based Context)
**Date:** 2026-01-06
**Files Changed:** 3 (1 prompt, 2 indexes)
**Mission Type:** Operational Hygiene

## Summary
Aligned `chair_prompt_v1.2.md` with critical Protocol v1.2 updates (F3 Independence Rule and F6 Seat Completion validation) to ensure the operationalised council process is fully reflected in runtime prompts.

## Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `docs/09_prompts/v1.2/chair_prompt_v1.2.md` | MODIFIED | Added F3 (Independence check) and F6 (Seat completion check) |
| `docs/INDEX.md` | MODIFIED | Updated timestamp |
| `docs/LifeOS_Strategic_Corpus.md` | MODIFIED | Regenerated per stewardship protocol |

## Diff Appendix

### chair_prompt_v1.2.md

```diff
--- docs/09_prompts/v1.2/chair_prompt_v1.2.md
+++ docs/09_prompts/v1.2/chair_prompt_v1.2.md
@@ -43,6 +43,7 @@
 - [ ] Apply deterministic mode rules unless `override.mode` exists (then record rationale).
 - [ ] Confirm topology is set (MONO/HYBRID/DISTRIBUTED).
 - [ ] If MONO and mode is M1/M2: schedule a distinct Co‑Chair challenge pass.
+- [ ] **Independence Check (Protocol v1.2 §6.3)**: If `safety_critical` OR `touches: [governance_protocol, tier_activation]`: Governance & Risk MUST be independent models. **NO OVERRIDE PERMITTED.**
 
 ### 2.3 Evidence gating policy
 State explicitly at the top of the run:

@@ -54,6 +54,8 @@
 ## 3) Orchestration rules (deterministic)
 
 ### 3.1 MONO topology (single model)
+**Step 1.5 — Seat Completion Validation**: Before synthesis, verify ALL assigned seats have submitted valid outputs. Do not proceed with partial results.
+
 Run seats sequentially and compartmentalise. Use this header before each seat:
```
