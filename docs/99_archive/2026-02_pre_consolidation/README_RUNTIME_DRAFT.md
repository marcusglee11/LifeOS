# LifeOS Runtime (v1.1)

This package contains the core generic runtime engine for LifeOS, ported from `coo-agent`.

## Components
- **engine.py**: The core Finite State Machine (FSM).
- **freeze.py**: Deterministic state freezing.
- **gates.py**: Approval gates.
- **rollback.py**: Infinite-context rollback.
- **migration.py**: State migration.

## Dependencies
- **project_builder**: Now available in `LifeOS/project_builder`.

## Status: PORTED
The `runtime` and `project_builder` packages have been successfully migrated to LifeOS.

## Usage
```bash
python -m runtime.cli
```

## Testing
```bash
# Requires environment variables (e.g. OPENAI_API_KEY)
pytest runtime/tests
```

