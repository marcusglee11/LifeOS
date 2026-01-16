---
artifact_id: ""              # [REQUIRED] UUID v4
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "1.0"
status: "PENDING_REVIEW"
# Optional
chain_id: ""
mission_ref: ""
council_trigger: ""
parent_artifact: ""
tags: []
terminal_outcome: ""         # [REQUIRED] PASS | BLOCKED | REJECTED
closure_evidence: {}         # [REQUIRED] key-value pairs
---

> **Reviewer Behavior**: Apply RTR-1.0 from `docs/02_protocols/Project_Planning_Protocol_v1.0.md`.

# Review_Packet_<Mission>_v1.0

# Scope Envelope

- **Allowed Paths**: `...`
- **Forbidden Paths**: `...`
- **Authority**: ...

# Summary
<!-- 1-3 sentences on what was done -->

# Issue Catalogue

| Issue ID | Description | Resolution | Status |
|----------|-------------|------------|--------|
| P0.1     |             |            | FIXED  |

# Acceptance Criteria

| ID | Criterion | Status | Evidence Pointer | SHA-256 |
|----|-----------|--------|------------------|---------|
| AC1| AC1       | PASS   | logs/run.txt:L10 | a1b2... |

# Closure Evidence Checklist

| Category | Requirement | Verified |
|----------|-------------|----------|
| **Provenance** | Code commit hash + message | [Hash/Msg] |
| | Docs commit hash + message | [Hash/Msg] OR N/A |
| | Changed file list (paths) | [List/Count] |
| **Artifacts** | `attempt_ledger.jsonl` | [Path/SHA] OR N/A |
| | `CEO_Terminal_Packet.md` | [Path/SHA] OR N/A |
| | `Review_Packet_attempt_XXXX.md` | [Path/SHA] OR N/A |
| | Closure Bundle + Validator Output | [Path/SHA] OR N/A |
| | Docs touched (each path) | [Path/SHA] |
| **Repro** | Test command(s) exact cmdline | [Command] |
| | Run command(s) to reproduce artifact | [Command] |
| **Governance** | Doc-Steward routing proof | [Path/Ref] OR Waiver |
| | Policy/Ruling refs invoked | [Path/Ref] |
| **Outcome** | Terminal outcome proof | [PASS/BLOCKED/etc] |

# Non-Goals

- ...

# Appendix

## File Manifest

- `path/to/file`

## Flattened Code

### File: `path/to/file`

```python
...
```

**EOF_SENTINEL**
