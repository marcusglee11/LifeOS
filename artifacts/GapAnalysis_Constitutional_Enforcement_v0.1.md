# Constitutional Enforcement Audit

## Scope
Systematic audit of GEMINI.md v2.3 to identify requirements that:
1. Are stated but lack enforcement mechanisms
2. Have no explicit trigger points
3. Could be violated due to ambiguity
4. Need self-check sequences like Article XII

---

## Findings

### CRITICAL — Requires Immediate Reinforcement

| Article | Requirement | Gap | Severity |
|---------|-------------|-----|----------|
| **II.1** | "Produce Plan Artefact before any substantive proposed change" | No enforcement. I frequently skip planning for "simple" tasks | **CRITICAL** |
| **II.1.2** | "Await human review before generating diffs/code" | No gate. I proceed after plan without waiting for approval | **CRITICAL** |
| **IV.1** | "Enforce Document Steward Protocol v1.0" | Already violated. No trigger tied to file modifications in `docs/` | **CRITICAL** |
| **VII.2** | "Skip the Plan Artefact step" is prohibited | No enforcement mechanism | **CRITICAL** |

### HIGH — Should Be Reinforced

| Article | Requirement | Gap | Severity |
|---------|-------------|-----|----------|
| **III** | Artefacts must include metadata (Title, Version, Date, etc.) | No validation checklist | HIGH |
| **V.1** | "May not directly apply changes" to governance code | No explicit list of governance-controlled paths | HIGH |
| **VI.1** | "Must produce Gap Analysis Artefact for issues" | No trigger - when is a GAA required? | HIGH |
| **Appendix A.5** | "Index files must not be directly edited" | Which files are indexes? No explicit list | HIGH |

### MEDIUM — Ambiguous Requirements

| Article | Requirement | Gap | Severity |
|---------|-------------|-----|----------|
| **I.3** | "Immutable Boundaries" list | Items like "foundational documents" undefined | MEDIUM |
| **II.3** | "No direct writes for Governance specs" | What files are governance specs? No list | MEDIUM |
| **III.1** | Plan Artefact "must precede any implementation" | What counts as implementation? | MEDIUM |
| **VII.8** | "Write or delete files without artefact flow" | Artefact flow undefined for code files | MEDIUM |

### STRUCTURAL ISSUES

| Issue | Description |
|-------|-------------|
| **Missing Article VIII/IX** | Article XII refers to "Article VIII/IX requirements" but they don't exist |
| **Section 5 orphaned** | "Section 5 — Stewardship Validation Rule" appears after Appendix A, not in an article |
| **Duplicate content** | Lines 189-194 duplicate lines 192-195 |

---

## Proposed Fixes

### Fix 1: Plan Artefact Gate (Article II enforcement)
Add self-check before any file creation/modification:
```
□ Is this a substantive change (creating code, modifying logic)?
□ Did I create an implementation_plan.md first?
□ Did the user approve the plan?
□ Only then: proceed to execution
```

### Fix 2: Document Steward Protocol Gate
Add self-check after any file modification in `docs/`:
```
□ Did I modify any file in docs/?
□ If yes: Update docs/INDEX.md timestamp
□ If yes: Regenerate LifeOS_Universal_Corpus.md
□ Include these in Review Packet
```

### Fix 3: Governance File List
Create explicit list of paths that cannot be modified without artefact flow:
- `docs/00_foundations/`
- `docs/01_governance/`
- `GEMINI.md`
- `runtime/governance/`

### Fix 4: Article Number Cleanup
- Renumber Section 5 as Article VIII
- Add Article IX for file/path governance
- Article X → XII already exist correctly

### Fix 5: Add Prohibited Action for Plan Skipping
Add enforcement: "If substantive file changes are about to occur without an approved plan, STOP and produce Plan Artefact first"

---

## Priority Order for Fixes
1. **Plan Artefact Gate** — Most frequently violated
2. **Document Steward Protocol Gate** — Already violated twice 
3. **Governance File List** — Prevents ambiguity
4. **Article Number Cleanup** — Structural integrity
