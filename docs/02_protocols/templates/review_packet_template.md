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

## 7. SELF-GATING CHECKLIST (Computed)

> [!IMPORTANT]
> This section must be populated by computing values from the final Evidence Bundle.
> FAIL-CLOSED: If any item is FAIL, Packet Status must be "IMPLEMENTED / NOT VERIFIED (BLOCKED BY CHECKLIST)".

| ID | Item | Status | Evidence |
|----|------|--------|----------|
| **E1** | ZIP Hash Integrity | PASS | `Bundle...zip.sha256` matches computed hash |
| **E2** | Packet Hash Citation Matches ZIP | PASS | Packet citation matches .sha256 file |
| **E3** | Bundle Layout Matches Contract | PASS | Strict layout (e.g., `artifacts/<scope>/`), no root files |
| **E4** | Canonical Protocol Doc Reference | PASS | Unique canonical path cited |
| **E5** | Provenance Hygiene | PASS | No "VERIFIED" claim without PR/Commit SHAs |
| **E6** | Audit-Grade Manifest | PASS | `manifest.txt` excludes itself; `.sha256` provided |
