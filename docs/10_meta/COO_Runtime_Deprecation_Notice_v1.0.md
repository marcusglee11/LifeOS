# COO Runtime Deprecation Notice v1.0

**Date**: December 2025
**Status**: ACTIVE
**Topic**: Migration of COO Runtime to LifeOS

## 1. Notice
The standalone COO Runtime repository (commonly known as `coo-agent` or `COOProject`) is **officially deprecated**.

## 2. New Canonical Location
The authoritative implementation of the COO Runtime now resides in this repository at:
- `LifeOS/runtime/` (Core Engine)
- `LifeOS/project_builder/` (Support Logic)

## 3. Implications
- **Do not** commit code to the old `coo-agent` repo.
- **Do not** run runtime tests from the old repo.
- All future features (R6.x series) must be implemented in `LifeOS`.

## 4. History
This migration was performed in December 2025 to consolidate the "LifeOS Kernel" into a single, deterministic monorepo.

