---
artifact_id: "c8433bf9-0587-4533-a591-713520f572fb"
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-07T14:19:30+11:00"
author: "Antigravity"
version: "1.0"
status: "PENDING_REVIEW"
mission_ref: "OpenCode-First Doc Stewardship Implementation"
tags: ["governance", "stewardship", "opencode", "gate"]
---

# Plan: OpenCode-First Doc Stewardship (Phase 2)

## Executive Summary
Implement the "OpenCode-First Doc Stewardship" policy to mandate routing of in-envelope documentation changes through the OpenCode steward and its CT-2 gate. This ensures strict evidence hygiene and eliminates ambiguity in the documentation lifecycle by making OpenCode the mandatory default steward for all eligible changes.

## Problem Statement
Currently, documentation updates may be performed by Antigravity directly or through various stewardship paths. This Lack of a single mandatory route for in-envelope changes can lead to inconsistent evidence capture and audit gaps. By enforcing OpenCode stewardship for eligible changes, we achieve mechanical auditability and proof of hygiene (no-ellipsis rule) for all doc updates.

## Authoritative Inputs (Audit Chain)

Execution must be mechanically faithful to the following specs:

| Artefact | Path | Version | SHA-256 |
| :--- | :--- | :--- | :--- |
| **Gate Runner** | [scripts/opencode_ci_runner.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_ci_runner.py) | v1.3 | *latest* |
| **Gate Policy** | [scripts/opencode_gate_policy.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_gate_policy.py) | v1.3 | *latest* |
| **CT-2 Ruling** | [docs/01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md](file:///c:/Users/cabra/Projects/LifeOS/docs/01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md) | v1.1 | *latest* |
| **DAP** | [docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md](file:///c:/Users/cabra/Projects/LifeOS/docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md) | v2.0 | *latest* |

## Interfaces + Artefact Schemas

### CLI Entrypoint (Mandatory)
```bash
python scripts/opencode_ci_runner.py --task "<JSON_PAYLOAD>"
```

### Output Artefact Schema (Evidence Bundle)
Each stewardship run MUST emit a bundle in `artifacts/evidence/opencode_steward_certification/mission_<timestamp>/` containing:
1. `exit_report.json`: Status, duration, reason codes.
2. `changed_files.json`: Sorted list of (status, path).
3. `classification.json`: Metadata classification of detected changes.
4. `runner.log`: Full execution trace (NO ELLIPSES).
5. `hashes.json`: SHA-256 manifest of all processed files.

## Determinism Contract
- **Input Freeze**: All inputs are normalized via `normalize_path` per [opencode_gate_policy.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_gate_policy.py).
- **No-Ellipsis Proof**: Compliance checked via `pytest tests_recursive/test_opencode_gate_policy.py::TestRunnerLogHygiene`.
- **Zero-Ambiguity Footer**: `truncate_log` in `opencode_gate_policy.py` MUST contain `cap_lines`, `cap_bytes`, `observed_lines`, `observed_bytes`.

## Gate Definitions (Gate PH2)
| Check | Deterministic Output | Failure Reason Code |
| :--- | :--- | :--- |
| **Denylist Root** | `is_denylisted(path) == True` | `DENYLIST_ROOT_BLOCKED` |
| **Structural Ops** | `git diff --name-status` contains R/C/D | `PH2_DELETE/RENAME/COPY_BLOCKED` |
| **Path Traversal** | `normalize_path(path)` contains `..` | `PATH_TRAVERSAL_BLOCKED` |
| **Extensions** | `ext != ".md"` in `docs/` | `NON_MD_EXTENSION_BLOCKED` |

## State Machine Truth Table
| Current State | Input / Condition | Next State | Consequence |
| :--- | :--- | :--- | :--- |
| `IDLE` | Trigger mission | `PENDING` | Load refs & environment |
| `PENDING` | Diff success & Envelope match | `EXECUTING` | Apply hunks / run script |
| `EXECUTING` | Verification pass | `SUCCESS` | Emit bundle & Exit |
| `ANY` | Envelope violation | `BLOCK` | Emit reason code & Exit |
| `ANY` | Critical Error (No refs/IO) | `ERROR` | Diagnostic dump -> **QUESTION** |

> [!NOTE]
> **QUESTION** = A formal human gate requiring direct interaction (notify_user) to resolve environmental ambiguity or CI failure before retry.

## Proposed Changes

### Governance and Policy

#### [NEW] [OpenCode_First_Stewardship_Policy_v1.0.md](file:///c:/Users/cabra/Projects/LifeOS/docs/01_governance/OpenCode_First_Stewardship_Policy_v1.0.md)
- Define the policy, including Purpose, Definitions, Default Routing Rule, Exceptions, Mixed Changes Rule, Evidence Requirements, and Adoption/Enforcement.
- Reference `scripts/opencode_ci_runner.py` and `scripts/opencode_gate_policy.py`.

#### [MODIFY] [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](file:///c:/Users/cabra/Projects/LifeOS/docs/03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md)
- Incorporate the "OpenCode-First Doc Stewardship" rule in Section 7.3.
- Explicitly state the exceptions and fail-closed behavior.

#### [NEW] [Council_Ruling_OpenCode_First_Stewardship_v1.0.md](file:///c:/Users/cabra/Projects/LifeOS/docs/01_governance/Council_Ruling_OpenCode_First_Stewardship_v1.0.md)
- Record the PASS (GO) for this policy adoption.

### Index Updates

#### [MODIFY] [INDEX.md](file:///c:/Users/cabra/Projects/LifeOS/docs/01_governance/INDEX.md)
- Link the new Policy and Ruling.

## Verification Plan

### Automated
1. Verify all new files exist.
2. Verify links resolve.
3. Verify `LifeOS_Strategic_Corpus.md` picks up the new policy.

### Manual
1. (Simulation) Demonstrate routing an in-envelope change through the OpenCode-first logic.

## DONE Checklist (Auditable Outputs)

- [x] New policy and ritual updates implemented in `docs/01_governance/` and `docs/03_runtime/`.
- [x] Antigravity's own operating protocol enforced via Section 7.3.
- [ ] Review Packet `v1.0` produced with flattened code snapshots.
- [ ] Council Ruling `v1.0` (Sign-off record) created for policy adoption.
- [ ] Proof of compliance: Simulation of in-envelope routing results in a complete CT-2 Evidence Bundle with zero ellipses and a valid machine-readable footer.
