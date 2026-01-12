# Tier-2 API Evolution & Versioning Strategy v1.0
**Status**: Draft (adopted on 2026-01-03)
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Scope**: Tier-2 Deterministic Runtime Interfaces  
**Effective (on adoption)**: 2026-01-03

---

## 1. Purpose

The LifeOS Tier-2 Runtime is a **certified deterministic core**. Its interfaces are contracts of behaviour and contracts of **evidence**: changing an interface can change system hashes and invalidate `AMU₀` snapshots and replay chains.

This document defines strict versioning, deprecation, and compatibility rules for Tier-2 public interfaces to ensure long-term stability for Tier-3+ layers.

---

## 2. Definitions

### 2.1 Tier-2 Public Interface
Any callable surface, schema, or emitted evidence format that Tier-3+ (or external tooling) can depend on, including:
- Entrypoints invoked by authorized agents
- Cross-module result schemas (e.g., orchestration and test-run results)
- Configuration schemas consumed by Tier-2
- Evidence formats parsed downstream (e.g., timeline / flight recording)

### 2.2 Protected Interface (“Constitutional Interface”)
A Tier-2 interface classified as replay-critical and governance-sensitive. Breaking changes require Fix Pack + Council Review.

---

## 3. Protected Interface Registry (authoritative)

This registry is the definitive list of Protected Interfaces. Any Tier-2 surface not listed here is **not Protected** by default, but still subject to normal interface versioning rules.

| Protected Surface | Kind | Canonical Location | Notes / Contract |
|---|---|---|---|
| `run_daily_loop()` | Entrypoint | `runtime.orchestration.daily_loop` | Authorized Tier-2.5 entrypoint |
| `run_scenario()` | Entrypoint | `runtime.orchestration.harness` | Authorized Tier-2.5 entrypoint |
| `run_suite()` | Entrypoint | `runtime.orchestration.suite` | Authorized Tier-2.5 entrypoint |
| `run_test_run_from_config()` | Entrypoint | `runtime.orchestration.config_adapter` | Authorized Tier-2.5 entrypoint |
| `aggregate_test_run()` | Entrypoint | `runtime.orchestration.test_run` | Authorized Tier-2.5 entrypoint |
| Mission registry | Registry surface | `runtime/orchestration/registry.py` | Adding mission types requires code + registration here |
| `timeline_events` schema | Evidence format | DB table `timeline_events` | Replay-critical event stream schema |
| `config/models.yaml` schema | Config schema | `config/models.yaml` | Canonical model pool config |

**Registry rule**: Any proposal to (a) add a new Protected Interface, or (b) remove one, must be made explicitly via Fix Pack and recorded as a registry change. Entrypoint additions require Fix Pack + Council + CEO approval per the runtime↔agent protocol.

---

## 4. Interface Versioning Strategy (Semantic Governance)

Tier-2 uses Semantic Versioning (`MAJOR.MINOR.PATCH`) mapped to **governance impact**, not just capability.

### 4.1 MAJOR (X.0.0) — Constitutional / Breaking Change
MAJOR bump required for:
- Any breaking change to a Protected Interface (Section 3)
- Any change that alters **evidence hashes for historical replay**, unless handled via Legacy Mode (Section 6.3)

Governance requirement (default):
- Fix Pack + Council Review + CEO sign-off (per active governance enforcement)

### 4.2 MINOR (1.X.0) — Backward-Compatible Extension
MINOR bump allowed for:
- Additive extensions that preserve backwards compatibility (new optional fields, new optional config keys, new entrypoints added via governance)
- Additions that do not invalidate historical replay chains (unless clearly version-gated)

### 4.3 PATCH (1.1.X) — Hardening / Bugfix / Docs
PATCH bump for:
- Internal refactors
- Bugfixes restoring intended behaviour
- Docs updates

**Constraint**:
- Must not change Protected schemas or emitted evidence formats for existing missions.

---

## 5. Compatibility Rules (Breaking vs Non-Breaking)

### 5.1 Entrypoints
Non-breaking (MINOR/PATCH):
- Add optional parameters with defaults
- Add new entrypoints (governed) without changing existing ones

Breaking (MAJOR):
- Remove/rename entrypoints
- Change required parameters
- Change semantics

### 5.2 Result / Payload schemas
Non-breaking (MINOR/PATCH):
- Add fields as `Optional` with deterministic defaults
- Add keys that consumers can safely ignore

Breaking (MAJOR):
- Remove/rename fields/keys
- Change types non-widening
- Change semantics

### 5.3 Config schemas
Non-breaking (MINOR/PATCH):
- Add optional keys with defaults
Breaking (MAJOR):
- Remove/rename keys
- Change required structure
- Change semantics

---

## 6. Deprecation Policy

### 6.1 Two-Tick Rule
Any feature planned for removal must pass through two interface ticks:

**Tick 1 — Deprecation**
- Feature remains functional
- Docs marked `[DEPRECATED]`
- Entry added to Deprecation Ledger (Section 11)
- If warnings are enabled (Section 6.2), emit a deterministic deprecation event

**Tick 2 — Removal**
- Feature removed or disabled by default
- Any use raises deterministic failure (`GovernanceViolation` or `NotImplementedError`)
- Removal occurs only at the next MINOR or MAJOR bump consistent with classification

### 6.2 Deterministic Deprecation Warnings (single flag, deterministic format)
Deprecation warnings are OFF by default.

If enabled via a single explicit flag:
- **Flag name (standard)**: `debug.deprecation_warnings = true`
- Warning emission must be deterministic and replay-safe:
  - Emit as a structured timeline event (not stdout)
  - Event type: `deprecation_warning`
  - Event JSON MUST include:
    - `interface_version` (current)
    - `deprecated_surface`
    - `replacement_surface`
    - `removal_target_version`
    - `first_seen_at` (deterministic: derived from run start / mission metadata, not ad hoc wall-clock time)

**Hash impact note**: enabling warnings changes evidence (timeline) and therefore changes hashes; that is acceptable only because the flag is an explicit input and must be preserved across replay.

### 6.3 Immutable History Exception (Legacy Mode)
If a deprecated feature is required to replay a historical `AMU₀` snapshot:
- Move implementation to `runtime/legacy/`
- Expose it only through an explicit replay path (“Legacy Mode”)
- Legacy Mode must be auditable and explicit (no silent fallback)

---

## 7. Hash-Impact Guardrail (enforceable rule)

**Rule (load-bearing)**:  
Any Tier-2 change that alters emitted evidence for an already-recorded run (e.g., `timeline_events` shape/content, result serialization, receipts) is **MAJOR by default**, unless:
1) the change is confined to a newly versioned schema branch (Section 9), or  
2) the historical behaviour is preserved via Legacy Mode (Section 6.3).

This prevents accidental replay invalidation and makes “contracts of evidence” operational rather than rhetorical.

---

## 8. Change Requirements (artefacts and tests)

Every Tier-2 interface change must include:
- Classified bump type: PATCH/MINOR/MAJOR (default to MAJOR if uncertain)
- Updated Interface Version (single authoritative location; Section 10)
- Updated interface documentation and (if relevant) a migration note
- Test coverage demonstrating:
  - backward compatibility (MINOR/PATCH), or
  - explicit break + migration/legacy path (MAJOR)
- Deprecation Ledger entry if any surface is deprecated

---

## 9. Schema Versioning Inside Artefacts

All Protected structured artefacts MUST carry explicit schema versioning in their serialized forms.

### 9.1 Standard field
Every `to_dict()` / serialized payload for Protected result/evidence types must include:

- `schema_version`: string (e.g., `"orchestration_result@1"`, `"scenario_result@1"`, `"test_run_result@1"`)

### 9.2 Relationship to Interface Version
- `schema_version` is per-object-type and increments only when that object’s serialized contract changes.
- Interface Version increments according to Section 4 based on governance impact.

### 9.3 Config schema versioning
Protected config schemas must include either:
- a `schema_version` key, or
- an explicit top-level `version` key

Additive introduction is MINOR; removal/rename is MAJOR.

---

## 10. Interface Version Location (single source of truth)

Tier-2 MUST expose the **current Interface Version** from exactly one authoritative location. This location must be:
- deterministic (no environment-dependent mutation),
- importable/parseable by Tier-3+ consumers, and
- testable in CI.

**Steward decision required**: the Doc Steward will select the lowest-friction authoritative location (doc field vs code constant) that preserves auditability and minimizes recurring operator effort. Once chosen, the exact path and access method must be recorded here:

- **Authoritative interface version location**: `runtime.api.TIER2_INTERFACE_VERSION` (code constant)
- **How consumers read it**: `from runtime.api import TIER2_INTERFACE_VERSION`
- **How CI asserts it**: `runtime/tests/test_compatibility_matrix.py` asserts validity and semantic versioning.

After this decision, Tier-3+ surfaces must fail-fast when encountering an unsupported interface version range.

---

## 11. Compatibility Test Matrix

Tier-2 must maintain a small, explicit compatibility suite to prevent accidental breaks.

### 11.1 Required fixtures
Maintain fixtures for:
- prior `schema_version` payloads for each Protected result type
- prior config schema examples for each Protected config

### 11.2 Required tests
- **Decode compatibility**: current code can load/parse prior fixtures
- **Serialize stability**: `to_dict()` produces canonical ordering / stable shape
- **Replay invariants**: where applicable, evidence/event emission matches expectations under the same inputs and flags

### 11.3 Storage convention (recommended)
- `runtime/tests/fixtures/interface_v{X}/...`
- Each fixture file name includes:
  - object type
  - schema_version
  - short provenance note

---

## 12. Deprecation Ledger (append-only)

| Date | Interface Version | Deprecated Surface | Replacement | Removal Target | Hash Impact? | Notes |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Ledger rules:
- Append-only (supersede by adding rows)
- Every deprecation must specify replacement + removal target
- “Hash Impact?” must be explicitly marked `yes/no/unknown` (unknown defaults to MAJOR until resolved)

---

## 13. Adoption Checklist (F2 completion)

F2 is complete when:
1) This document is filed under the canonical runtime docs location.
2) The Protected Interface Registry (Section 3) is adopted as authoritative.
3) Interface Version location is selected and recorded (Section 10).
4) Deprecation warnings flag and event format (Section 6.2) are standardized.
5) Schema versioning rules (Section 9) are applied to all Protected result/evidence serializers moving forward.
6) Compatibility test matrix fixtures + tests (Section 11) exist and run in CI.
