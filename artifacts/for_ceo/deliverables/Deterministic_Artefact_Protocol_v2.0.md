# Deterministic Artefact Protocol (DAP) v2.0 — Dual-Layer Specification

## Placement
`/docs/01_governance/Deterministic_Artefact_Protocol_v2.0.md`

## Status
Canonical governance specification.

## Layer 1 — Canonical Human-Readable Specification

## 1. Purpose
The Deterministic Artefact Protocol (DAP) v2.0 defines the mandatory rules and constraints governing the creation, modification, storage, naming, indexing, validation, and execution of all artefacts produced within the LifeOS environment. Its goals include determinism, auditability, reproducibility, immutability of historical artefacts, and elimination of conversational drift.

## 2. Scope
DAP v2.0 governs all markdown artefacts, script files, indexes, logs, audit reports, ZIP archives, tool-generated files, and directory structure modifications. It applies to all assistant behaviour, tool invocations, and agents within LifeOS.

## 3. Definitions
- **Artefact**: Deterministic file created or modified under DAP.
- **Deterministic State**: A reproducible filesystem state.
- **Canonical Artefact**: The authoritative version stored under `/docs`.
- **Non-Canonical Artefact**: Any artefact outside `/docs`.
- **Immutable Artefact**: Any file within `/docs/99_archive`.
- **DAP Operation**: Any assistant operation affecting artefacts.

## 4. Core Principles
- Determinism
- Explicitness
- Idempotence
- Immutability
- Auditability
- Isolation
- Version Discipline
- Canonical Tree Enforcement

## 5. Mandatory Workflow Rules
- Artefacts may only be created at StepGate Gate 3.
- All artefacts must include complete content.
- Tool calls must embed full content.
- ZIP generation must be deterministic.
- Any structural change requires index regeneration.
- Archive folders are immutable.
- Strict filename pattern enforcement.
- Forbidden behaviours include guessing filenames, modifying artefacts without approval, creating placeholders, relying on conversational memory, or generating artefacts outside StepGate.

## 6. Interaction with StepGate
DAP references StepGate but does not merge with it. All DAP operations require Gate 3; violations require halting and returning to Gate 0.

## 7. Error Handling
Hard failures include overwriting archive files, missing approval, missing paths, ambiguous targets, or context degradation. On detection, the assistant must declare a contamination event and require a fresh project.

## 8. Canonical Status
DAP v2.0 becomes binding upon placement at the specified path.

---

## Layer 2 — Machine-Operational Protocol

## M-1. Inputs
Assistant must not act without explicit filename, path, content, StepGate Gate 3 status.

## M-2. Artefact Creation Algorithm
IF Gate != 3 → refuse.  
Require filename, path, full content.  
Write file.  
Verify file exists and contains no placeholders.

## M-3. Naming Rules
`<BASE>_v<MAJOR>.<MINOR>[.<PATCH>].md`

## M-4. Archive Rules
Immutable; may not be rewritten.

## M-5. Index Regeneration Rules
Structural changes require new index version with diff summary.

## M-6. Forbidden Operations
Guessing paths, relying on memory, placeholder generation, modifying archive files, or creating artefacts outside Gate 3.

## M-7. Deterministic ZIP Generation
Sort filenames, preserve ordering, include only approved artefacts.

## M-8. Contamination Detection
Placeholder or truncated output requires contamination event and new project.

## M-9. Resolution
Return to Gate 0, regenerate plan deterministically.


