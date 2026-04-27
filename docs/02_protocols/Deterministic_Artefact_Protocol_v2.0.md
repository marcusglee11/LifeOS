# Deterministic Artefact Protocol (DAP) v2.0 — Dual-Layer Specification

## Placement

`/docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md`

## Status

Canonical governance specification.

## Layer 1 — Canonical Human-Readable Specification

## 1. Purpose

The Deterministic Artefact Protocol (DAP) v2.0 defines the mandatory rules and constraints governing the creation, modification, storage, naming, indexing, validation, and execution of artefacts produced within the LifeOS environment. Its goals include determinism, auditability, reproducibility, immutability of historical artefacts, and elimination of conversational drift.

## 2. Scope

DAP v2.0 governs markdown artefacts, script files, indexes, logs, audit reports, ZIP archives, tool-generated files, and directory structure modifications, subject to the bounded exceptions in §2.1 and M-2.

It applies to assistant behaviour, tool invocations, and agents within LifeOS unless a more specific ratified protocol overrides it.

### 2.1 Bounded Gate 3 exceptions

The following artefact classes may be created or updated outside formal StepGate Gate 3 when they are produced as part of bounded operational execution, review, audit, or evidence capture:

| Artefact class | Typical paths | Gate 3 posture |
|---|---|---|
| Audit artefacts | `docs/audit/`, `artifacts/reports/` | Exception permitted when recording audit findings or audit evidence. |
| Result artefacts | `artifacts/results/`, `artifacts/reports/`, tool result outputs | Exception permitted when recording deterministic execution results. |
| Proposal artefacts | `artifacts/plans/`, `artifacts/for_ceo/`, `artifacts/review_packets/` | Exception permitted when capturing proposals, plans, packets, or review materials. |
| Receipt artefacts | `artifacts/receipts/`, `artifacts/reports/`, closure/build receipts | Exception permitted when recording execution receipts or close-build evidence. |
| Evidence artefacts / evidence bundles | `artifacts/evidence/`, `logs/`, `artifacts/reports/captures/` | Exception permitted when preserving test output, command output, transcripts, or other evidence. |

These exceptions do not authorize changes to canonical governance documents, runtime code, schemas, parser guards, FSMs, or archive contents without the governing approval path for those surfaces.

## 3. Definitions

- **Artefact**: Deterministic file created or modified under DAP.
- **Deterministic State**: A reproducible filesystem state.
- **Canonical Artefact**: The authoritative version stored under `/docs`, subject to repo-specific canonicality notes.
- **Non-Canonical Artefact**: Any artefact outside `/docs` unless explicitly promoted by a governing protocol.
- **Immutable Artefact**: Any file within `/docs/99_archive`.
- **DAP Operation**: Any assistant operation affecting artefacts.
- **Operational File**: Non-canonical ephemeral/operational file stored outside canonical governance roots, commonly under `/artifacts` or `/logs`.

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

- Canonical artefacts may only be created through the appropriate approved governance or execution gate.
- All artefacts must include complete content.
- Tool calls must embed full content.
- ZIP generation must be deterministic.
- Any structural change requires index regeneration when the relevant index declares that requirement.
- Archive folders are immutable.
- Strict filename pattern enforcement applies where a protocol or index declares that pattern binding.
- Forbidden behaviours include guessing filenames, modifying artefacts without approval, creating placeholders, relying on conversational memory, or generating artefacts outside the authorized scope.

## 6. Interaction with StepGate

DAP references StepGate but does not merge with it. Canonical DAP operations require the relevant approved gate. Bounded operational artefact classes listed in §2.1 may be captured outside formal Gate 3 when they preserve auditability and do not alter protected governance/runtime surfaces.

## 7. Error Handling

Hard failures include overwriting archive files, missing approval for protected surfaces, missing paths, ambiguous targets, or context degradation. On detection, the assistant must halt and surface the failure rather than silently proceeding.

## 8. Canonical Status

DAP v2.0 is binding as placed at `docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md`.

---

## Layer 2 — Machine-Operational Protocol

## M-1. Inputs

Assistant must not act without explicit filename, path, content, and governing authorization status.

## M-2. Artefact Creation Algorithm

IF path is a protected canonical/governance/runtime surface AND required approval is absent → refuse.  
IF path is an operational exception class listed in §2.1 → allow bounded creation/update for evidence, audit, result, proposal, or receipt capture.  
Require filename, path, full content.  
Write file.  
Verify file exists and contains no placeholders.

## M-3. Naming Rules

`<BASE>_v<MAJOR>.<MINOR>[.<PATCH>].md`

This pattern is mandatory only where applicable to formal versioned markdown artefacts. It does not apply to machine-generated evidence captures, receipts, result logs, or existing repository files using a different ratified naming convention.

## M-4. Archive Rules

Immutable; may not be rewritten.

## M-5. Index Regeneration Rules

Structural changes require index regeneration when the relevant index or stewardship protocol declares regeneration required.

## M-6. Forbidden Operations

Guessing paths, relying on memory for authority-critical decisions, placeholder generation, modifying archive files, or creating artefacts outside authorized scope.

## M-7. Deterministic ZIP Generation

Sort filenames, preserve ordering, include only approved artefacts.

## M-8. Contamination Detection

Placeholder or truncated output requires a halt and explicit remediation before the artefact is treated as complete.

## M-9. Resolution

Return to the governing approval or planning gate and regenerate plan deterministically.

## M-10. Gitignore Discipline

To ensure AI tool access (read/write) required by these protocols, the following paths MUST NOT be git-ignored:

- `artifacts/plans/` (Formal governance)
- `artifacts/review_packets/` (Formal governance)
- `artifacts/for_ceo/` (Operational handoff)
- `artifacts/context_packs/` (Operational handoff)

If git exclusion is desired, it must be handled via manual `git add` exclusion or other mechanisms that do not block AI tool-level visibility.

---

## Amendment record

**2026-04-27 — WP2 authority audit normalisation**
- Normalised placement from `docs/01_governance/` to actual repo path `docs/02_protocols/`.
- Added bounded Gate 3 exceptions for audit, result, proposal, receipt, and evidence artefacts.
- Clarified that exceptions do not authorize protected governance/runtime/schema/parser/FSM changes.
