# Template: Blocked Report v1.0

---
artifact_id: ""  # Generate UUID v4
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: ""   # ISO 8601
author: "Antigravity"
version: "1.0"
status: "DRAFT"
tags: ["blocked", "gate-violation", "fail-closed"]
---

## Executive Summary
This execution was halted by the security gate due to an envelope violation or environmental failure. No changes were applied to the repository.

## Gate Context
- **Gate Runner**: `scripts/opencode_ci_runner.py`
- **Gate Policy**: `scripts/opencode_gate_policy.py`
- **Current Branch**: `[GIT_BRANCH]`
- **Merge Base**: `[GIT_MERGE_BASE]`

## Block Details
| Field | Value |
| :--- | :--- |
| **Reason Code** | `[REASON_CODE]` |
| **Violating Path** | `[PATH]` |
| **Classification** | `[A/M/D]` |
| **Envelope Requirement** | `[REQUIREMENT_EXPLANATION]` |

## Diagnostics
```text
[UNELIDED_GATE_LOG_OR_ERROR_TRACE]
```

## Next Actions
- [ ] If out-of-envelope: Submit a Governance Packet Request.
- [ ] If structural op: Re-structure changes to avoid delete/rename in Phase 2.
- [ ] If environmental failure: Escalate to CEO for CI/ref repair.

---
**END OF REPORT**
