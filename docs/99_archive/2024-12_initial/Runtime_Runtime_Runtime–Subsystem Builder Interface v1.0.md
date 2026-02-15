# Runtime–Subsystem Builder Interface v1.0

## Purpose
Define how Runtime constructs governed subsystems (Council, Judiciary, Governance Hub, Advisors, etc.) in a deterministic and constitutional manner.

## 1. Builder Invocation

Function: `runtime.builder.build_subsystem(spec_path, output_path)`

Inputs:
- spec_path: path to a Subsystem Specification
- output_path: deterministic output location

Outputs:
- generated_artifacts: list of generated files
- builder_log: complete deterministic log
- builder_checksum: digest of all artifacts

Rules:
- Must run with temperature = 0
- Must use pinned model versions from Version Manifest
- Must log all model calls with exact prompts + outputs

## 2. Builder Stages

### Stage 1 — Parse
Load spec, validate using schema from this interface.

### Stage 2 — Plan
Generate build-plan.json:
- list of artifacts to generate
- ordering dependencies
- validation rules

### Stage 3 — Generate
Produce each artifact deterministically:
- code
- templates
- prompts
- config
- documentation

### Stage 4 — Validate
Check artifacts against:
- invariants (section 4)
- audit requirements (section 6.3)
- constitutional boundaries (section 6 of spec)

### Stage 5 — Emit
Write artifacts to output_path.
Write builder_log.
Write builder_checksum.

## 3. Governance Gates

Subsystem building is **gated** unless explicitly marked “ungated” in the spec.

If gated:
- Runtime MUST request Judiciary review
- Judiciary MUST return a Verdict Template
- Verdict MUST be applied before commit

## 4. Determinism Requirements

- Given spec + version manifest, builder must produce identical outputs.
- All external calls forbidden.
- Randomness forbidden.
- Pinned model versions only.

## 5. Logging Requirements

Builder MUST log:
- full spec contents
- build-plan
- every model invocation
- every artifact before/after validation
- checksum of emitted artifacts
- version manifest binding

## 6. Failure Modes

Builder returns one of:
- SUCCESS
- VALIDATION_FAILED
- GOVERNANCE_REJECTED
- SPEC_INVALID
- VERSION_MISMATCH

## 7. Integration Points

Builder integrates with:
- Judiciary (review)
- Version Manifest
- Governance Hub (future)
- Audit Ledger

All integrations MUST be version-bound.

