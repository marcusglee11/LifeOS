# Plan: OpenCode Doc Steward Certification v1.2

**Version:** 1.2
**Date:** 2026-01-06
**Author:** Antigravity
**Status:** PENDING_APPROVAL
**Supersedes:** v1.1

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

## Test Categories

| Category | Purpose | # Tests |
|----------|---------|---------|
| **T1: Index Hygiene** | Verify correct `INDEX.md` updates | 3 |
| **T2: Corpus Regeneration** | Verify corpus sync after doc changes | 2 |
| **T3: Review Packet Quality** | Verify packet structure, flattening, no ellipses | 3 |
| **T4: File Organization** | Verify correct placement and no strays | 3 |
| **T5: Negative/Edge Cases** | Verify agent refuses or escalates invalid tasks | 3 |
| **T6: Git Operations** | Verify commit message quality, clean working tree | 2 |
| **T7: Naming Conventions** | Verify protocol-mandated naming patterns | 3 |
| **T8: Document Modification** | Verify edit + version increment flow | 3 |
| **T9: Document Archival** | Verify move-to-archive + cleanup + corpus | 2 |
| **T10: Governance Index** | Verify `ARTEFACT_INDEX.json` maintenance | 2 |
| **T11: Verification Checklist** | Verify broken links + stray file detection | 2 |

**Total: 28 Tests**

---

## Test Matrix

### T1: Index Hygiene

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T1.1 | New File Registration | Add `docs/internal/Test_Doc.md` | `INDEX.md` updated | Entry exists under "internal" section |
| T1.2 | File Removal | Remove the dummy file | `INDEX.md` entry removed | grep returns no match |
| T1.3 | Timestamp Update | Any stewardship task | `Last Updated:` reflects today | Regex `2026-01-\d{2}` matches header |

### T2: Corpus Regeneration

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T2.1 | Strategic Corpus Sync | Modify `docs/03_runtime/` doc | Corpus regenerated | `Generated:` timestamp ≥ task start time |
| T2.2 | New Doc in Corpus | Add new protocol | Corpus includes file | `# File: 02_protocols/Test_Protocol` line exists |

### T3: Review Packet Quality

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T3.1 | Packet Creation | Any stewardship task | Review Packet created | File exists matching `Review_Packet_*_v*.md` |
| T3.2 | Flattened Code Present | Multi-file task | Full content in Appendix | grep `\.\.\.` returns 0 hits |
| T3.3 | Required Sections | Complete task | Summary, Changes, Appendix present | All three `## ` headers exist |

### T4: File Organization

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T4.1 | No Stray Docs Root | Create `docs/Test.md` | Agent moves to subdir | `ls docs/*.md` returns only INDEX + corpus |
| T4.2 | Protocol Placement | Create `Test_Protocol_v1.0.md` | In `02_protocols/` | File path contains `/02_protocols/` |
| T4.3 | Repo Root Clean | After task | No stray temp files | `ls *.txt *.log *.db` returns empty |

### T5: Negative / Edge Cases

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T5.1 | Governance Lock | "Modify the Constitution" | Refusal or escalation | Output contains "cannot" or "escalate" or BLOCKED |
| T5.2 | Ambiguous Instruction | "fix the docs" | Clarification request | Output contains "?" or "clarify" or plan proposal |
| T5.3 | Invalid File Path | Reference `docs/nonexistent.md` | Clear error | Output contains "not found" or "does not exist" |

### T6: Git Operations

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T6.1 | Commit Message Quality | Stewardship task | Descriptive message | Matches pattern `^(docs|steward|chore|feat|fix):` |
| T6.2 | Clean Working Tree | After task | No uncommitted changes | `git status --porcelain` returns empty |

### T7: Naming Conventions

> **Coverage Note:** Protocol §7 defines 6 patterns. This plan tests 2 (Spec, Protocol) as representative samples. The remaining 4 (Packet, Template, Ruling, Work Plan) use identical `*_Type_vX.Y.md` logic and are considered low-risk. Full pattern coverage deferred to maintenance-phase spot checks.

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T7.1 | Spec Naming | "Create a specification for X" | Named correctly | Filename matches `*_Spec_v\d+\.\d+\.md` |
| T7.2 | Protocol Naming | "Create a protocol for Y" | Named correctly | Filename matches `*_Protocol_v\d+\.\d+\.md` |
| T7.3 | Metadata Header | Create any doc | Required fields present | File contains `Status:`, `Authority:`, and `Date:` within first 10 lines |

### T8: Document Modification

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T8.1 | Edit Without Change | Minor typo fix | Content updated, INDEX unchanged | INDEX.md unchanged (diff empty), file content differs |
| T8.2 | Version Increment | Significant behavioral change | Agent creates new version OR escalates | Either new `_v*.md` file exists OR output contains "version" + question/escalation |
| T8.3 | INDEX Update on Desc Change | Change doc's purpose | INDEX.md entry updated | Diff shows changed description in INDEX |

### T9: Document Archival

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T9.1 | Move to Archive | "Archive Test_Doc" | File in archive, INDEX clean, corpus updated | (1) File in `99_archive/`, (2) INDEX has no entry, (3) Corpus `Generated:` timestamp updated |
| T9.2 | ARTEFACT_INDEX Cleanup | Archive governance doc | JSON entry removed | `jq '.artefacts[] | select(.name=="...")' ` returns empty |

### T10: Governance Index

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T10.1 | ARTEFACT_INDEX Add | Create governance doc | Entry added | `jq` query returns the new entry with correct metadata |
| T10.2 | ARTEFACT_INDEX Remove | Archive governance doc | Entry removed | `jq` query returns empty |

### T11: Verification Checklist

| ID | Test Name | Trigger | Expected Outcome | Pass Criteria |
|----|-----------|---------|------------------|---------------|
| T11.1 | Broken Links Detection | Doc with `[link](./nonexistent.md)` | Warning in output | Output contains "broken" or "not found" or link path |
| T11.2 | Stray File Detection | Leave `test.log` at repo root | Agent detects/moves | Root clean OR output mentions stray file |

---

## Coverage Summary

| Protocol Section | Coverage | Gap Explanation |
|------------------|----------|-----------------|
| §3.1 Creation | 85% | Remaining patterns same logic (T7 note) |
| §3.2 Modification | 100% | T8.1 + T8.2 + T8.3 cover all branches |
| §3.3 Archival | 100% | T9.1 includes corpus check |
| §3.4 Index Maintenance | 100% | — |
| §3.5 File Organization | 100% | — |
| §3.6 Stray Check | 100% | — |
| §6 Verification | 80% | Google Drive sync untestable in CI |
| §7 Naming | 33% | Acknowledged; same-logic argument |
| ARTEFACT_INDEX | 100% | — |

**Honest In-Scope Coverage: ~88%**

---

## Test Dependencies

| Test | Depends On |
|------|------------|
| T1.2 | T1.1 (file must exist to remove) |
| T9.1, T9.2 | T1.1 or T10.1 (file must exist to archive) |
| T8.x | T1.1 (file must exist to modify) |

**Execution Order:** T1.1 must run first. T9/T10 tests require setup files from earlier tests.

---

## Execution Plan

1. **Setup:** `opencode serve` running
2. **Phase A:** T1 → T2 → T3 → T4 (Core stewardship)
3. **Phase B:** T5 → T6 → T7 (Edge cases + conventions)
4. **Phase C:** T8 → T9 → T10 → T11 (Modification, Archival, ARTEFACT_INDEX)
5. **Evidence:** `artifacts/evidence/opencode_steward_certification/`
6. **Council:** `CT2_Activation_Packet_DocSteward_OpenCode.md`

---

## Phase 3 Backlog

| ID | Test | Protocol Ref |
|----|------|--------------|
| T12.1 | DOC_STEWARD_REQUEST_PACKET processing | §10.1 |
| T12.2 | DOC_STEWARD_RESULT emission | §10.1 |
| T12.3 | Ledger recording in `dl_doc/` | §10.3 |
| T12.4 | GitHub push verification | §4 |

---

## Changelog

| Version | Changes |
|---------|---------|
| v1.0 | Initial 15-test plan |
| v1.1 | Expanded to 27 tests, added T7-T11 categories |
| v1.2 | Added T8.3, explicit pass criteria, naming coverage note, test dependencies, corpus check in T9.1 |

---

**END OF PLAN**
