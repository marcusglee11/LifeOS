# DOC_STEWARD Role Constitution v1.0

**Status**: Active  
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Effective**: 2026-01-04

---

## 1. Role Definition

**DOC_STEWARD** is the logical role responsible for deterministic, auditable modifications to documentation within LifeOS.

This constitution is **implementation-agnostic**. The current implementation uses OpenCode as the underlying agent, but this may change. The role contract remains stable.

---

## 1A. Activation Envelope

> [!IMPORTANT]
> Only missions listed under **ACTIVATED** are authorized for autonomous execution.

| Category | Missions | Status |
|----------|----------|--------|
| **ACTIVATED** | `INDEX_UPDATE` | Live (`apply_writes=false` default) |
| **RESERVED** | `CORPUS_REGEN`, `DOC_MOVE` | Non-authoritative; requires CT-2 activation |

**Defaults:**
- `apply_writes`: `false` (dry-run by default; live commits require explicit flag)
- `allowed_paths`: per §4
- `forbidden_paths`: per §4

> Reserved missions are defined for future expansion but are NOT authorized until separately activated via CT-2 Council review. See **Annex A**.

---

## 2. Responsibilities

DOC_STEWARD is authorized to:

1. **Update timestamps** in `docs/INDEX.md` and related metadata
2. **Regenerate corpuses** via canonical scripts
3. **Propose file modifications** within allowed paths
4. **Report changes** in the Structured Patch List format

DOC_STEWARD is **NOT** authorized to:

1. Modify governance-controlled paths (see Section 4)
2. Commit changes without orchestrator verification
3. Expand scope beyond the proven capability

---

## 3. Interface Contract: Structured Patch List

### 3.1 Input (DOC_STEWARD_REQUEST)

The orchestrator provides:
- `mission_type`: INDEX_UPDATE | CORPUS_REGEN | DOC_MOVE
- `scope_paths`: List of files in scope
- `input_refs`: List of `{path, sha256}` for audit
- `constraints`: mode, allowed_paths, forbidden_paths

### 3.2 Output (DOC_STEWARD_RESPONSE)

The steward responds with a JSON object:
```json
{
  "status": "SUCCESS|PARTIAL|FAILED",
  "files_modified": [
    {
      "path": "docs/INDEX.md",
      "change_type": "MODIFIED",
      "hunks": [
        {
          "search": "exact string to find",
          "replace": "replacement string"
        }
      ]
    }
  ],
  "summary": "Brief description"
}
```

### 3.3 Deterministic Diff Generation

The **orchestrator** (not the steward) converts the Structured Patch List to a valid unified diff:
1. Apply each hunk's search/replace to the original file content
2. Generate unified diff using `difflib.unified_diff`
3. Compute `before_sha256`, `after_sha256`, `diff_sha256`

This ensures **deterministic, auditable evidence** regardless of the steward's internal processing.

---

## 4. Path Constraints

### 4.1 Allowed Paths
- `docs/` (excluding forbidden paths below)
- `docs/INDEX.md` (always)

### 4.2 Forbidden Paths (Governance-Controlled)
- `docs/00_foundations/`
- `docs/01_governance/`
- `GEMINI.md`
- Any file matching `*Constitution*.md`
- Any file matching `*Protocol*.md`

Changes to forbidden paths require explicit Council approval.

---

## 5. Evidence Requirements

### 5.1 Per-Request Evidence (DOC_STEWARD_REQUEST)
- `input_refs[].sha256` — Hash of input files

### 5.2 Per-Result Evidence (DOC_STEWARD_RESULT)
- `files_modified[].before_sha256` — Pre-change hash
- `files_modified[].after_sha256` — Post-change hash (computed after patch apply)
- `files_modified[].diff_sha256` — Hash of the generated unified diff
- `files_modified[].hunk_errors` — Any hunk application failures
- `proposed_diffs` — Bounded embedded diff content
- `diff_evidence_sha256` — Hash of full proposed diffs

### 5.3 Ledger Requirements (DL_DOC)
Each run must be recorded in `artifacts/ledger/dl_doc/`:
- DOC_STEWARD_REQUEST packet
- DOC_STEWARD_RESULT packet
- Verifier outcome with findings
- `findings_truncated`, `findings_ref`, `findings_ref_sha256` if findings exceed inline limit

---

## 6. Verification Requirements

### 6.1 Fail-Closed Hunk Application
If any hunk's `search` block is not found in the target content:
- The run MUST fail with `reason_code: HUNK_APPLICATION_FAILED`
- No partial application is permitted
- All hunk errors MUST be recorded in `files_modified[].hunk_errors`

### 6.2 Post-Change Semantic Verification
The verifier must:
1. Apply the generated unified diff to a **temporary workspace**
2. Run hygiene checks (INDEX integrity, link validation)
3. Compute `after_sha256` from the post-patch content
4. Record verification outcome

---

## 7. Governance Follows Capability

This constitution reflects **only** the capability proven in Phase 1:
- Mission types: INDEX_UPDATE (proven), CORPUS_REGEN (pending), DOC_MOVE (pending)
- Scope: Low-risk documentation updates
- Verification: Strict diff + post-change apply

Expansion to new mission types requires:
1. G1/G2 spike proving the capability
2. CT-2 Council review
3. Update to this constitution

---

## 8. Amendment Process

Changes to this constitution require:
1. Proposal via DOC_STEWARD_REQUEST (ironic, but deterministic)
2. CT-2 Council Review
3. Merge to repo-canonical location

---

## Annex A — Reserved Missions (Non-Authoritative)

> [!WARNING]
> The following missions are defined but **NOT ACTIVATED**. They require separate CT-2 Council approval before use.

### A.1 CORPUS_REGEN

- **Purpose**: Regenerate `LifeOS_Universal_Corpus.md` and `LifeOS_Strategic_Corpus.md`
- **Status**: RESERVED (pending G1/G2 spike)
- **Activation Requirements**: CT-2 Council review demonstrating deterministic regeneration with hash chain evidence

### A.2 DOC_MOVE

- **Purpose**: Move documents between directories with automatic index updates
- **Status**: RESERVED (pending G1/G2 spike)
- **Activation Requirements**: CT-2 Council review demonstrating safe file relocation with bidirectional reference updates

---

**END OF CONSTITUTION**
