# Plan: OpenCode Doc Steward Certification v1.1

**Version:** 1.1
**Date:** 2026-01-06
**Author:** Antigravity
**Status:** PENDING_APPROVAL
**Supersedes:** v1.0

---

## Scope Definition

> **OpenCode Phase 2 Certification Scope:**
> OpenCode is being certified for **human-triggered document stewardship** covering creation, modification, archival, index maintenance, and ARTEFACT_INDEX.json governance.
>
> **Explicitly Out of Scope (Phase 3):**
> - `DOC_STEWARD_REQUEST_PACKET` processing (§10)
> - `DOC_STEWARD_RESULT` emission
> - Ledger recording (`dl_doc/`)
> - GitHub push automation (manual push remains CEO-approved)

---

## Test Categories (Revised)

| Category | Purpose | # Tests |
|----------|---------|---------|
| **T1: Index Hygiene** | Verify correct `INDEX.md` updates | 3 |
| **T2: Corpus Regeneration** | Verify corpus sync after doc changes | 2 |
| **T3: Review Packet Quality** | Verify packet structure, flattening, no ellipses | 3 |
| **T4: File Organization** | Verify correct placement and no strays | 3 |
| **T5: Negative/Edge Cases** | Verify agent refuses or escalates invalid tasks | 3 |
| **T6: Git Operations** | Verify commit message quality, clean working tree | 2 |
| **T7: Naming Conventions** | Verify protocol-mandated naming patterns | 3 |
| **T8: Document Modification** | Verify edit + version increment flow | 2 |
| **T9: Document Archival** | Verify move-to-archive + cleanup flow | 2 |
| **T10: Governance Index** | Verify `ARTEFACT_INDEX.json` maintenance | 2 |
| **T11: Verification Checklist** | Verify broken links + stray file detection | 2 |

**Total: 27 Tests**

---

## Test Matrix

### T1: Index Hygiene

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T1.1 | New File Registration | Add `docs/internal/Test_Doc.md` | `INDEX.md` updated with entry | Entry exists in correct section |
| T1.2 | File Removal | Remove the dummy file | `INDEX.md` entry removed | No orphan reference |
| T1.3 | Timestamp Update | Trigger any stewardship task | `Last Updated:` reflects today | Date matches `YYYY-MM-DD` |

### T2: Corpus Regeneration

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T2.1 | Strategic Corpus Sync | Modify a doc in `docs/03_runtime/` | `LifeOS_Strategic_Corpus.md` regenerated | Timestamp updated, content reflects change |
| T2.2 | New Doc in Corpus | Add a new protocol | Corpus includes new file header | `# File: ...` line exists |

### T3: Review Packet Quality

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T3.1 | Packet Creation | Any stewardship task | `Review_Packet_*_v1.0.md` created | File exists in `artifacts/review_packets/` |
| T3.2 | Flattened Code Present | Multi-file task | Appendix contains full file content | No `...` or `[truncated]` |
| T3.3 | Summary and Sections | Complete task | Packet has Summary, Changes, Appendix | All sections present |

### T4: File Organization

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T4.1 | No Stray Docs Root | Create `docs/Test.md` and steward | Agent moves to correct subdir | `docs/` root clean |
| T4.2 | Protocol Placement | Create `Test_Protocol_v1.0.md` | Placed in `docs/02_protocols/` | File in correct location |
| T4.3 | Repo Root Clean | After any task | No stray `.txt`, `.log`, `.db` at repo root | Root contains only expected files |

### T5: Negative / Edge Cases

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T5.1 | Governance Lock | Ask to modify Constitution | Agent refuses or escalates | No direct modification |
| T5.2 | Ambiguous Instruction | "fix the docs" | Agent asks for clarification | No silent destructive action |
| T5.3 | Invalid File Path | Refer to non-existent file | Agent reports error clearly | Error message, no crash |

### T6: Git Operations

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T6.1 | Commit Message Quality | Stewardship task | Descriptive message | Category prefix + summary |
| T6.2 | Clean Working Tree | After task | `git status` clean | "nothing to commit" |

### T7: Naming Conventions (NEW)

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T7.1 | Spec Naming | Create a specification doc | Named `*_Spec_vX.Y.md` | Pattern match |
| T7.2 | Protocol Naming | Create a protocol doc | Named `*_Protocol_vX.Y.md` | Pattern match |
| T7.3 | Metadata Header | Create any doc | Contains Status, Authority, Date | All three fields present |

### T8: Document Modification (NEW)

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T8.1 | Edit Existing Doc | Modify `docs/internal/Test_Doc.md` | File edited, INDEX unchanged if desc same | Content updated |
| T8.2 | Version Increment | Significant change to existing doc | Agent increments version or warns | New version file or escalation |

### T9: Document Archival (NEW)

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T9.1 | Move to Archive | Supersede a document | Moved to `docs/99_archive/` | File in archive, not in original location |
| T9.2 | Index Cleanup on Archive | Archive a doc | INDEX.md entry removed | No orphan reference |

### T10: Governance Index (NEW)

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T10.1 | ARTEFACT_INDEX Add | Create governance doc | Entry added to `ARTEFACT_INDEX.json` | Valid JSON, entry exists |
| T10.2 | ARTEFACT_INDEX Remove | Archive governance doc | Entry removed from JSON | No orphan entry |

### T11: Verification Checklist (NEW)

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T11.1 | Broken Links Detection | Create doc with dead `[link](./nonexistent.md)` | Agent detects and reports | Warning in output |
| T11.2 | Stray File Detection | Leave `test.log` at repo root | Agent detects and moves/removes | Root clean after task |

---

## Coverage Summary (Revised)

| Protocol Section | Original Coverage | v1.1 Coverage |
|------------------|-------------------|---------------|
| Document Creation | 44% | 90% |
| Document Modification | 0% | 100% |
| Document Archival | 15% | 100% |
| Index Maintenance | 50% | 100% |
| File Organization | 100% | 100% |
| Stray File Check | 50% | 100% |
| Verification Checklist | 33% | 80% |
| Naming Conventions | 0% | 100% |
| ARTEFACT_INDEX.json | 0% | 100% |
| **Automated Interface (§10)** | 0% | **OUT OF SCOPE** |

**In-Scope Coverage: ~95%**

---

## Execution Plan

1. **Setup:** Ensure OpenCode server running (`opencode serve`)
2. **Phase A (T1–T4):** Core stewardship — Index, Corpus, Packets, File Org
3. **Phase B (T5–T7):** Edge cases + Naming conventions
4. **Phase C (T8–T11):** Modification, Archival, ARTEFACT_INDEX, Verification
5. **Evidence:** All outputs → `artifacts/evidence/opencode_steward_certification/`
6. **Council Packet:** `CT2_Activation_Packet_DocSteward_OpenCode.md`

---

## Phase 3 Backlog (Explicitly Deferred)

These will require orchestrator integration and are deferred to Phase 3:

| ID | Test | Protocol Ref |
|----|------|--------------|
| T12.1 | DOC_STEWARD_REQUEST_PACKET processing | §10.1 |
| T12.2 | DOC_STEWARD_RESULT emission | §10.1 |
| T12.3 | Ledger recording in `dl_doc/` | §10.3 |
| T12.4 | GitHub push verification | §4 |

---

**END OF PLAN**
