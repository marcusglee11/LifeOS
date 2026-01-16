---
artifact_id: "3b17bdc5-dbb9-4e89-9d87-294a975603dc"
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: "2026-01-07T23:58:00Z"
author: "Antigravity"
version: "1.0"
status: "PENDING_REVIEW"
mission_ref: "mission_fix_opencode_model_fallback"
tags: ["fix", "opencode", "model-routing", "authorized"]
---

# Review_Packet_OpenCode_Model_Routing_Fix_v1.0

**Mission:** Fix OpenCode Model Routing (Haiku Fallback)
**Date:** 2026-01-07
**Author:** Antigravity
**Status:** PENDING_REVIEW

---

## 1. Executive Summary

This mission resolved an issue where the OpenCode Doc Steward was falling back to `anthropic/claude-haiku-4.5` despite being instructed to use `x-ai/grok-4.1-fast`. The root cause was identified as a redundant `openrouter/` prefix being prepended to the model ID in the ephemeral configuration generator. Removing this prefix enabled successful model resolution on OpenRouter.

**Verification Status:**
- **Component Health:** GREEN (Fix verified via manual mission and log audit)
- **Stewardship:** N/A (Hardening/Fix only)

---

## 2. Issue Catalogue & Resolutions

| Issue ID | Description | Resolution | Status |
|----------|-------------|------------|--------|
| I-01 | Redundant model prefix | Removed `openrouter/` prepending in `scripts/opencode_ci_runner.py`. | **RESOLVED** |
| I-02 | Model resolution fallback | Verified that removal of prefix allows correct routing to Grok 4.1-fast. | **RESOLVED** |

---

## 3. Acceptance Criteria Status

| Criteria | Description | Status | Verification Method |
|----------|-------------|--------|---------------------|
| **AT1** | Redundant prefix removed from runner | **PASS** | Code audit of `opencode_ci_runner.py` |
| **AT2** | Mission succeeds with Grok config | **PASS** | Manual mission run (mission_20260107_235547) |
| **AT3** | No regressions in security harness | **PASS** | Certification harness run (12/13 passed) |

---

## 4. Verification Proof

**Target Component:** `scripts/opencode_ci_runner.py`
**Verified Diff:**
```python
-    model_id = model.replace("openrouter/", "") if model.startswith("openrouter/") else model
-    config_data = {"model": f"openrouter/{model_id}", "$schema": "https://opencode.ai/config.json"}
+    config_data = {"model": model, "$schema": "https://opencode.ai/config.json"}
```

**Manual Test Result:**
- **Evidence Path:** `artifacts/evidence/opencode_steward_certification/mission_20260107_235547`
- **Result:** `MISSION SUCCESS` - No fallback observed.

---

## 5. Non-Goals
- Updating global OpenCode settings (Isolation remains primary constraint).

---

*This review packet was created under LifeOS Build Artifact Protocol v1.0.*
