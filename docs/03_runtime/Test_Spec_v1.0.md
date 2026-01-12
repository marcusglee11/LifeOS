# Test Specification v1.0

## Purpose
Define the canonical testing requirements for LifeOS runtime components to ensure determinism, governance compliance, and regression safety across Tier-2+ systems.

## Scope
Applies to all runtime modules under `runtime/`, including orchestration, governance, safety, validators, and gateways.

## Test Classes

### 1. Unit Tests
- Pure function validation
- Deterministic inputs/outputs
- No filesystem or network access

### 2. Integration Tests
- Module-to-module contracts
- Schema and protocol adherence
- Controlled filesystem fixtures only

### 3. Governance Tests
- Invariant enforcement
- Council ruling compliance
- Version-lock and contract checks

### 4. Safety Tests
- Failure mode validation
- Guardrail and gate activation
- Explicit denial-path coverage

### 5. Regression Tests
- Previously closed issues
- Bundle replay verification
- Evidence-backed assertions

## Determinism Requirements
- Tests must be order-independent
- No reliance on wall-clock time
- Seeded randomness only

## Evidence Output
- All test runs must emit machine-verifiable evidence
- Evidence artifacts stored under `artifacts/`
- Hashes recorded where applicable

## Pass/Fail Criteria
- Zero unexpected failures
- Explicitly waived tests require Council reference

## Enforcement
This specification is enforced by CI and OpenCode runtime gates. Non-compliance blocks promotion.
