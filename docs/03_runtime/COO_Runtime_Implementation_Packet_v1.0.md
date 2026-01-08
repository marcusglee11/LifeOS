IMPLEMENTATION PACKET v1.0

Mechanical Execution Guide for COO Runtime v1.0
Subordinate to:

LifeOS Constitution v2.0

Governance Protocol v1.0

COO Runtime Spec v1.0
Prepared for: Antigravity

## Patches Applied
- Patch R6.5-C1A (Unified Import Update)
  Applied: 2025-12-01
  Reference: R6.5 Fix Pack
- Patch P0-FIX (Consistency & Mechanical-Enforceability)
  Applied: 2026-01-07
  Reference: P0 Consistency Fix Pack
- Patch P1-HYGIENE (Manual Rollback & Scope Tightening)
  Applied: 2026-01-07
  Reference: P1 Hygiene Patch

0. PURPOSE

A detailed, deterministic instruction set for Antigravity to implement the COO Runtime v1.0 and the PB→COO consolidation in a safe, reproducible, constitutional manner.

This packet covers:

Required directory structure

Required files, manifests, and metadata

Required deterministic algorithms

Required test and replay harnesses

Required environmental constraints

Required migration scripts

Required rollback scripts

Required logging formats

Required integration points with Antigravity's build system

No governance or decision-making authority exists in this document.

1. SUBORDINATION CLAUSE
LifeOS Constitution v2.0 is supreme.  
Governance Protocol v1.0 and COO Runtime Spec v1.0 define all governance, sequencing, authority, and determinism.  
This Implementation Packet defines only mechanical behaviour.  
If any instruction conflicts with a superior document, this packet yields without exception.

2. DIRECTORY & FILE STRUCTURE

Antigravity MUST create the following directory structure.

**Canonical Runtime Package Namespace**: `coo/`

All Python imports MUST use `coo.*` (e.g., `from coo.runtime import state_machine`).

```
coo/
    runtime/
        __init__.py
        state_machine.py
        amendment_engine.py
        lint_engine.py
        governance_leak_scanner.py
        freeze.py
        amu_capture.py
        migration.py
        gates.py
        replay.py
        rollback.py
        logging.py

    manifests/
        tools_manifest.json
        environment_manifest.json
        hardware_manifest.json
        sandbox_digest.txt
        freeze_manifest.json

    tests/
        test_determinism.py
        test_migration.py
        test_replay.py
        test_governance_integrity.py
        test_sandbox_security.py

    scripts/
        apply_amendments.py
        run_lint.py
        run_scanner.py
        run_tests.py
        run_replay.py
        run_migration.py
        run_rollback.py

    reference/
        phase3_reference_mission.json
        governance_leak_ruleset.json
```

No other directories are permitted unless explicitly added by future specs.

2.1 UNIFIED IMPORT UPDATE (Patched by R6.5-C1A)

Antigravity MUST implement a single deterministic AST transformation pass that:

- Scans both the test modules and the runtime modules.
- Updates all imports that reference pre-fix packet structures (e.g., `project_builder.*`) to the canonical namespace `coo.*`.
- Applies identical transformation rules to tests and runtime in one atomic pass.
- Ensures there is no intermediate state where tests and runtime disagree on canonical import paths.

This unified pass is executed as **Migration Step 3** (see Section 9). It replaces the previously separate conceptual steps ("Update test imports" and "Update production imports") with a single atomic operation.

3. REQUIRED MANIFESTS

All manifests MUST be present before migration:

3.1 tools_manifest.json

Contains:

- Full SHA256 of each executable
- Version numbers
- Build toolchain versions

3.2 environment_manifest.json

Contains:

- OS version
- Kernel version
- Python version
- Locale
- PATH
- Env vars relevant to runtime

3.3 hardware_manifest.json

Contains:

- CPU ID
- Microcode version
- NUMA topology
- Filesystem type
- Virtualization flags

3.4 sandbox_digest.txt

SHA256 of OCI sandbox image.

3.5 freeze_manifest.json

Generated after CEO approval and Freeze activation.

4. AMENDMENT ENGINE (MECHANICAL)

Antigravity MUST implement a deterministic amendment engine:

4.1 Deterministic Anchoring

Anchor resolution MUST use:

- Clause IDs (e.g., `[SPEC-1.2.3]`)
- Header names (e.g., `## Section Title`)
- Strict whitespace normalization
- UTF-8 canonical encoding

Anchoring resolution MUST be byte-exact without fuzzy matching.

4.2 Amendment Application Algorithm

Pseudo-code:

```python
for amendment in sorted(amendments, key=lambda a: a.id):
    anchors = locate_anchor_deterministically(amendment.anchor)
    if len(anchors) == 0:
        emit_escalation_artefact("MissingAnchor", amendment)
        raise AmendmentHaltException("MissingAnchor")
    if len(anchors) > 1:
        emit_escalation_artefact("AmbiguousAnchor", amendment)
        raise AmendmentHaltException("AmbiguousAnchor")
    apply_replacement_or_insertion(anchors[0], amendment)
    update_amendment_log(amendment)
```

4.3 Ambiguity Handling Contract

When `MissingAnchor` or `AmbiguousAnchor` is detected:

1. **Emit Escalation Artefact**: Write `escalation_<amendment_id>.json` to `coo/manifests/` containing:
   - `type`: "MissingAnchor" | "AmbiguousAnchor"
   - `amendment_id`: The amendment that failed
   - `searched_anchor`: The anchor pattern that was searched
   - `candidates_found`: List of candidate matches (for AmbiguousAnchor)
2. **Halt Execution**: Raise `AmendmentHaltException` (a Python exception).
3. **Do NOT Proceed**: The amendment engine MUST NOT continue to the next amendment.

This contract is mechanically testable: unit tests MUST assert that the engine raises `AmendmentHaltException` and produces the escalation artefact when fed ambiguous inputs.

4.4 Outputs

- Amended PB
- Amended IP
- `amendment_log.json`
- `amendment_diff.patch`

5. GOVERNANCE-LEAK SCANNER

Antigravity MUST implement scanner rules inlined from archived Alignment Layer v1.4 (Section 4.1):

5.1 Scope Restriction

The scanner MUST scan only the following paths:

- `coo/runtime/**/*.py`
- `coo/scripts/**/*.py`
- `docs/01_governance/**/*.md`
- `docs/02_protocols/**/*.md`

Files outside this scope are explicitly excluded.

5.2 Forbidden Patterns (Governance Leakage)

A governance-leak is any statement that implies non-CEO discretion or autonomous approval.
Forbidden strings (case-insensitive):
- "must approve" / "approves"
- "authorizes" / "validates" / "confirms"
- "requires approval" / "requires confirmation"
- Implicit role verbs: "review", "decide", "designate", "govern" (when applied to non-CEO agents)

5.3 Permitted Patterns

- "CEO approves"
- "CEO authorizes"
- Exact phrases required by LifeOS Constitution v2.0

5.4 Ruleset Pinning

- The scanner MUST load patterns from `coo/reference/governance_leak_ruleset.json`.
- This file contains the canonical list of forbidden and permitted patterns.
- "Inlined from archive" means the patterns from Alignment Layer v1.4 are copied into this JSON file.
- The SHA256 of `governance_leak_ruleset.json` MUST be recorded in the mission configuration.
- Deterministic reporting format is REQUIRED.

5.5 Output Format

```json
{
  "status": "PASS" | "FAIL",
  "violations": [
    {
      "file": "...",
      "line": number,
      "pattern": "ForbiddenPatternName",
      "excerpt": "..."
    }
  ],
  "scanned_paths": ["coo/runtime/**/*.py", "coo/scripts/**/*.py", "docs/01_governance/**/*.md", "docs/02_protocols/**/*.md"],
  "ruleset_sha256": "..."
}
```

6. CONSTITUTIONAL LINT ENGINE

Lint engine MUST validate:

- Invariant compliance
- Forbidden constructs
- Required clauses
- Missing escalation paths

Error = halt.

7. FREEZE PREPARATION

Antigravity MUST provide runtime calls to:

- Halt async processes
- Close file descriptors
- Enforce read-only filesystem lock
- Enforce DB quiescence
- Compute SHA256 for tooling and sandbox
- Produce freeze_manifest.json
- Set FREEZE=TRUE

No mutations allowed after FREEZE=TRUE.

8. AMU₀ CAPTURE

Antigravity MUST implement deterministic snapshot tools for:

- Filesystem
- Database
- Sandbox digest
- All manifests
- Hardware identity
- Reference missions

All snapshots MUST be:

- Byte-identical across captures
- Stored in canonical sorted order
- SHA256 hashed
- Verified before and after capture

9. MIGRATION ENGINE (Atomic 5-Step Sequence)

The PB→COO consolidation MUST occur inside a single atomic operation following this strict sequence:

1. **Create canonical coo/ directory**: `mkdir -p coo/`
2. **Port PB code → coo/**: Port all modules using `sorted(os.walk)` to ensure byte-identical order.
3. **Unified Import Update (R6.5-C1A)**: Execute single AST transformation pass to rewrite ALL imports from `project_builder.*` to `coo.*` across both tests and runtime simultaneously.
4. **Pre-Deletion Verification**: Run full test suite; record as Snapshot 1.
5. **Delete Legacy Path**: `rm -rf project_builder/`
6. **Post-Deletion Verification**: Run full test suite; record as Snapshot 2.

**Snapshot Equality Algorithm** (Section 9.1):

If any failure occurs or Snapshot 1 != Snapshot 2 → rollback to AMU₀.

9.1 Snapshot Equality Algorithm

A **Snapshot** is defined as:

```json
{
  "manifest_version": "1.0",
  "files": [
    {"path": "relative/path/to/file.py", "sha256": "abc123..."},
    ...
  ],
  "test_results": {
    "passed": 42,
    "failed": 0,
    "skipped": 0,
    "exit_code": 0
  }
}
```

**Equality Definition**:

```python
def snapshots_equal(s1: Snapshot, s2: Snapshot) -> bool:
    # Files must be identical (sorted by path, compared by sha256)
    if sorted(s1.files, key=lambda f: f.path) != sorted(s2.files, key=lambda f: f.path):
        return False
    # Test results must be identical
    if s1.test_results != s2.test_results:
        return False
    return True
```

The `files` list MUST include all files in the `coo/` directory tree. Files are sorted lexicographically by path before comparison.

10. GATES ENGINE

Antigravity MUST implement each gate exactly in this order:

**Gate A: Repo Unification Integrity**
Validate directory structure, imports, and verify no legacy PB paths remain.

**Gate B: Deterministic Modules**
Hash of module outputs MUST match across repeated invocations.

**Gate C: Sandbox Security**
Validate sandbox digest and entrypoint integrity.

**Gate D: Test Suite Integrity**
Full test pass required (Snapshot 2 equivalence).

**Gate E: Governance Integrity**
Run governance-leak scanner (Section 5) and constitutional lint.

**Gate F: Deterministic Replay**
Call replay engine (Section 11) using reference mission contract.

Failure at ANY gate triggers rollback engine.

11. REPLAY ENGINE

The replay engine MUST NOT rely on abstract "freezing" of the host OS. Instead, it MUST use **Deterministic Abstraction Layers** and **Metadata Assertions**:

11.1 Controlled Inputs

- **RNG Seed**: Fixed to `0xDEADBEEF`.
- **System Time**: Mocked to `2025-01-01T00:00:00Z`.
- **Environment**: Allowlist only (scrubbed of PATH drift).
- **Filesystem**: Mocked or Read-Only Overlay with deterministic inode sorting.

11.2 Comparison Surface

The replay engine compares the following artefacts:

| Artefact | Path | Format |
|----------|------|--------|
| Mission Output | `coo/manifests/mission_output.json` | JSON |
| Gate Results | `coo/manifests/gate_results.json` | JSON |
| Amendment Log | `coo/manifests/amendment_log.json` | JSON |
| Scanner Report | `coo/manifests/scanner_report.json` | JSON |

11.3 Normalization Algorithm

Before byte-comparison, each artefact MUST be normalized using this algorithm:

```python
import json
from datetime import datetime

MASKED_FIELDS = ["timestamp", "created_at", "updated_at", "pid", "ppid", "hostname"]
STABLE_REPLACEMENT = "<MASKED>"

def normalize_artefact(data: dict) -> str:
    """Produce canonical, comparable string from artefact."""
    def mask_fields(obj):
        if isinstance(obj, dict):
            return {k: (STABLE_REPLACEMENT if k in MASKED_FIELDS else mask_fields(v)) 
                    for k, v in obj.items()}
        elif isinstance(obj, list):
            return [mask_fields(item) for item in obj]
        else:
            return obj
    
    masked = mask_fields(data)
    # Canonical JSON: sorted keys, no whitespace variation
    return json.dumps(masked, sort_keys=True, separators=(',', ':'))

def artefacts_equal(a1: dict, a2: dict) -> bool:
    return normalize_artefact(a1) == normalize_artefact(a2)
```

Normalized artefacts are written to `coo/manifests/normalized/` for audit purposes.
**Retention Policy**: This directory is **ephemeral**. It MUST be git-ignored and cleaned up after verification.

11.4 Verification

After normalization, outputs MUST be byte-identical. Any difference is a replay failure.

12. ROLLBACK ENGINE & MANUAL CONFIRMATION CONTRACT

12.1 Manual Confirmation Specification

- **Algorithm**: Human-in-the-loop confirmation.
- **Mechanism**: The Runtime MUST pause execution and await explicit user confirmation before applying any rollback.
- **Input Channel**: CLI prompt ("Type 'CONFIRM_ROLLBACK' to proceed") or presence of `CONFIRM_ROLLBACK` file in the runtime root.

12.2 Verification

Before applying rollback:
1. Runtime detects rollback condition (Gate Failure or Snapshot Mismatch).
2. Runtime halts and requests confirmation.
3. Runtime validates input matches `CONFIRM_ROLLBACK` exactly.
4. If invalid: **HALT** with `RollbackAbortedException`.

12.3 Rollback Operations

Rollback MUST:

1. Restore filesystem snapshot from AMU₀
2. Restore DB dump from AMU₀
3. Restore sandbox digest from AMU₀
4. Restore all manifests from AMU₀
5. Restore environment lock from AMU₀

12.5 Rollback Count Rules

- 1 automatic request allowed per migration attempt.
- Rollback MUST be deterministic.

13. LOGGING

Antigravity MUST implement deterministic log formats with:

- sequence_id
- config SHA256
- environment SHA256
- FSM transitions
- DB transaction logs
- Gate results
- Replay results
- Rollback logs

Logs MUST be immutable and sorted.

14. OUTPUT ARTEFACTS

Antigravity MUST produce:

14.1 Final COO Runtime Spec (regenerated)

Regeneration MUST follow the COO Runtime Spec v1.0 generation template.

14.2 Implementation Pack (this document)

MUST be included in final migration bundle.

14.3 Migration Log Bundle

Contains:

- All logs
- Diff files
- Manifests
- Checksums
- Replay results
- Gate summaries

15. PROHIBITED ACTIONS

Antigravity MUST NOT:

- Interpret governance logic
- Infer missing intent
- Skip steps
- Execute nondeterministic sequences
- Use heuristics
- Allow environment drift
- Allow sandbox rebuilds during Freeze
- Allow deletion outside declared directories

16. PHASE 4 P0 IMPLEMENTATION CHECKLIST (DOCUMENT-ONLY)

The following modules MUST be implemented in dependency order:

1. **`logging.py`**: Deterministic JSON logger with secret scrubbing.
2. **`manifests/`**: Environment, Tools, and Hardware discovery scripts.
3. **`amendment_engine.py`**: Deterministic anchoring via Clause IDs.
4. **`governance_leak_scanner.py`**: Pattern-matching scanner with pinned ruleset.
5. **`freeze.py`**: Quiescence and AMU₀ capture logic.
6. **`migration.py`**: Atomic 5-step repo unification sequence.
7. **`gates.py`**: Gate A-F verification sequence.
8. **`replay.py`**: Execution under frozen RNG/Time with byte-comparison.
9. **`rollback.py`**: Verified restoration from AMU₀.

END OF IMPLEMENTATION PACK v1.0
