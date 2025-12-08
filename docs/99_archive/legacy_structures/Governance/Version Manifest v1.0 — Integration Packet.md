Version Manifest v1.0 — Integration Packet

(Hybrid Manifest Architecture)

0. Purpose

This packet formally introduces the Hybrid Version Manifest Architecture into the LifeOS constitutional framework and COO Runtime Spec. It defines structure, governance rules, Judiciary checks, Builder Mode requirements, and update semantics. This is now the canonical mechanism for ensuring deterministic system identity across recursive evolution.

1. Authority Chain

This packet is subordinate to:

LifeOS Constitutional Spec v1.1

Alignment Layer v1.4

Judiciary v1.0 (newly integrated)

COO Runtime Spec v1.0

Existing Fix Packs (R1–R6.5.x)

Supersedes all earlier implicit or ad-hoc versioning practices.

2. Architectural Overview — Hybrid Model

LifeOS now uses two manifest layers:

2.1 Canonical Root Manifest (manifest.root.json)

The single, authoritative representation of entire system version state.

Contains:

Full component list

Exact version of each component

Exact version of each spec/constitution

Exact version of all external dependencies

Exact model identifiers + parameters

Hash of every component manifest

Global fingerprint (hash of entire root manifest)

Runtime determinism + Judiciary review always refer to the canonical root manifest.

2.2 Component Manifests (/manifests/<component>.json)

Readable, human-sized manifests for:

runtime

judiciary

hub

builder

council/board

config

external models

environment fingerprints

tools / agents

Component manifests are:

advisory for readability

machine-validated during development

not authoritative (authority always resides in root manifest)

3. Root Manifest Schema (canonical)
{
  "manifest_version": "1.0",
  "lifeos": {
    "constitution": "1.1",
    "alignment_layer": "1.4",
    "judiciary": "<version>",
    "governing_docs_hash": "<sha256>"
  },
  "components": {
    "<component_name>": {
      "version": "<semver-or-epoch>",
      "hash": "<sha256>",
      "manifest_hash": "<sha256-of-component-manifest>"
    },
    ...
  },
  "external_models": {
    "<model_name>": {
      "provider": "<api-provider>",
      "model_id": "<exact-model>",
      "temperature": <float>,
      "other_params": { ... },
      "hash": "<sha256-of-config>"
    }
  },
  "environment": {
    "os": "...",
    "python_version": "...",
    "hardware": "...",
    "pip_dependencies_hash": "<sha256-lock>",
    "env_fingerprint_hash": "<sha256>"
  },
  "global_hash": "<sha256-of-entire-root>"
}


Note: global_hash defines system identity for:

Replay

Rollback

Judiciary

Hub scheduling

Proof-of-lineage

4. Component Manifest Schema (auxiliary)

Component manifests are minimal:

{
  "component": "<name>",
  "version": "<version>",
  "owning_spec": "<spec-file>",
  "invariants": [ ... ],
  "dependencies": [ ... ],
  "interface_summary": { ... }
}


Non-authoritative, but must match the root manifest’s values.

5. Governing Rules
5.1 Root manifest supremacy

The root manifest is the single, authoritative source of truth for all versioned state.

5.2 No transition without manifest update

Every governed modification must:

Update the affected component manifest

Update the root manifest

Produce new global_hash

5.3 Judiciary enforcement

A transition is unconstitutional if:

Root manifest missing or malformed

Manifest hashes inconsistent

Component manifest does not match root manifest

Version increment not monotonic

Change commits without manifest update

Builder Mode does not attach manifest delta

5.4 Version Monotonicity

x.y.z may only increase.

Rollback restores a prior manifest exactly — no partial rollbacks.

5.5 Manifest as part of Audit Log

Audit entries include:

Pre-change manifest hash

Post-change manifest hash

Delta summary

Replay reconstructs by sequentially applying deltas.

6. Builder Mode Requirements

Builder Mode must:

Produce both a component manifest and root manifest update for every change

Attach a manifest-delta artefact

Validate dependency versions

Ensure manifests remain schema-conformant

Not perform silent version bumps

Fail the build if manifest and implementation diverge

7. Judiciary Protocol for Manifest Validation

Every governed transition triggers:

7.1 Static validation

Schema correctness

Version monotonicity

Root/component hash consistency

Global hash reproducibility

7.2 Behavioural validation

Judiciary checks that:

Manifest changes align with the change being proposed

No component changes hidden inside “unrelated” manifests

No external model configuration changes occur without proper governance

7.3 Rejection conditions

Judiciary rejects if:

Manifest changes do not match implementation

Deltas exceed permitted scope

Component manifest omitted

Manifest changes appear auto-generated but unreviewed

8. Rollback & Replay
8.1 Rollback

Rollback to version v requires:

All manifests restored to exact prior state

Global hash match

Verification that no subsequent transitions remain in log scope

8.2 Replay

Replay re-executes transitions using:

Locked manifest for that version

Environment pinned to environment fingerprint

Component versions exactly restored

9. Constitutional Amendments Required

The following amendments are introduced:

Amendment MAN-1: Manifest Supremacy

Root manifest is authoritative for all system version state.

Amendment MAN-2: Mandatory Manifest Update

Every governed modification requires manifest update and Judiciary validation.

Amendment MAN-3: No-Silent-Change Rule

Any code, spec, or configuration update without corresponding manifest delta is unconstitutional.

Amendment MAN-4: Global Deterministic Hash

global_hash defines system identity and must be reproducible bit-for-bit.

10. Runtime Spec Amendments
RS-M1: Root Manifest Location

Canonical manifest must reside at:

/system/manifest.root.json

RS-M2: Component Manifest Directory

Component manifests must reside at:

/system/manifests/<component>.json

RS-M3: Runtime Must Load Only Root Manifest

Component manifests are optional for execution.

RS-M4: Transition Contract

A transition without a manifest-delta is invalid.

11. Implementation Notes
11.1 Monotonic versioning

Use epoch or semver — but never decrease.

11.2 Manifest change minimalism

Manifest diffs capture exact and minimal intended change.

11.3 Suite-level reproducibility

CI and system-check flows must validate global_hash deterministically.

12. Deliverables (artefacts)

This packet includes:

Manifest Root Schema v1.0

Component Manifest Schema v1.0

Manifest Governance Rules

Judiciary Manifest Validation Procedure

Amendments MAN-1 → MAN-4

Runtime Spec Amendments RS-M1 → RS-M4

End of Version Manifest v1.0 Integration Packet