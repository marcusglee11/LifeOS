# Bootstrap Cycle Addendum v1.0

## Purpose
Define the minimal bootstrapping sequence required to safely activate governed recursion.

## Phase 0 — Pre-Bootstrap Checks
System must verify:
- Judiciary_v1.0 installed
- Runtime–Subsystem Builder Interface installed
- Subsystem Specification Template present
- Version Manifest v1.0 coherent

If any check fails → recursion forbidden.

## Phase 1 — Judiciary Self-Check
Runtime triggers:
`judge.validate_runtime(RUNTIME_V1)`
Judiciary must return COMPLIANT.

If not → recursion forbidden.

## Phase 2 — Council V1 Construction
Runtime calls Builder with:
- subsystem spec for Council
- builder logs everything
- Judiciary reviews generated Council

If approved → Runtime installs Council V1.

## Phase 3 — Council Review of Runtime
Council V1 reviews Runtime V1 → produces Runtime V1.1 Fix Pack.

Fix Pack must pass Judiciary review.

If approved → Runtime applies changes.

## Phase 4 — Governance Hub V1
Runtime builds Governance Hub V1 using the same mechanism.

Judiciary + Council must both approve.

## Phase 5 — Takeoff Activation
Once:
- Council active
- Judiciary active
- Hub active
- Version Manifest consistent

→ Recursive Improvement Loop is active.

## Phase 6 — Continuous Evolution
Runtime may continue generating improvements under:
- Judiciary gating
- Council review
- CEO oversight

