# LifeOS Runtime (v1.1)

This package contains the core generic runtime engine for LifeOS.

## Provenance & Deprecation
**Migrated from:** `coo-agent` (December 2025)
**Status:** Canonical / Authoritative

The old `coo-agent` repository is **DEPRECATED**. All development must occur here in `LifeOS/runtime`. See [Deprecation Notice](docs/10_meta/COO_Runtime_Deprecation_Notice_v1.0.md) for details.

## Components
- **engine.py**: The core Finite State Machine (FSM).
- **freeze.py**: Deterministic state freezing.
- **gates.py**: Approval gates.

## Usage
```bash
python -m runtime.cli
```

## Testing
```bash
pytest runtime/tests
```
