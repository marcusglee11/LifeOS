# Mission Registry v0.1

Tier-3 definition-only mission registry for LifeOS.

## Scope

**Definition-only** — This module provides:
- Immutable data types for mission definitions
- Pure, deterministic registry operations
- Canonical serialization for hashing/comparison

**Explicitly excluded:**
- Mission execution
- I/O operations
- Scheduling/planning logic
- Time/randomness dependencies
- Arbitrary logic validation

## Interface Contracts (AT1)
The registry provides a complete definition lifecycle interface:
- **`register(definition)`**: Add a new mission.
- **`get(id)`**: Retrieve by ID.
- **`list()`**: List all (insertion order).
- **`update(definition)`**: update existing mission (validating check).
- **`remove(id)`**: Remove by ID (raises if missing).

## Distinction from Tier-2 Registry

| Aspect | `runtime/mission/` (Tier-3) | `runtime/orchestration/registry.py` (Tier-2) |
|--------|---------------------------|---------------------------------------------|
| Purpose | Definition storage | Execution dispatch |
| Side effects | None | Runs workflows |
| Returns | New immutable instances | OrchestrationResult |
| Dependencies | `runtime.errors` only | Orchestration engine |

## Ordering Policy

- `MissionRegistry.list()` → **insertion order** (for UX)
- `MissionRegistry.to_state()` → **sorted by MissionId.value** (for AT3 determinism)

## Tag Policy

Tags are **order-significant, case-sensitive, no deduplication**.

Different tag orders produce different hashes. This is intentional.

## Metadata Canonicalization

Metadata is stored as `tuple[tuple[str, str], ...]` but serialized with keys sorted alphabetically in `to_dict()`.

## Exception Taxonomy

All exceptions subclass `AntiFailureViolation` from `runtime.errors`:

```
AntiFailureViolation (runtime.errors)
├── MissionBoundaryViolation  # Input validation failures
├── MissionNotFoundError      # ID not in registry
└── MissionConflictError      # Duplicate ID on register
```

## Boundaries & Constraints (P2)
Determinstic boundaries are enforced on all inputs:
- **Max Missions**: 1000 (configurable via `MissionBoundaryConfig`)
- **Max Metadata Pairs**: 50
- **Max Metadata Key Length**: 64 chars
- **Max Metadata Value Length**: 1000 chars

### Migration Path
This module is currently standalone. Future integration:
- `runtime/orchestration/registry.py` may delegate definition storage here.
- Exceptions map cleanly to shared `AntiFailureViolation`.

When first external consumer outside `runtime/mission/` appears:
- Map `MissionBoundaryViolation` → `AntiFailureViolation` (already is)
- No changes needed; exceptions are already in the shared hierarchy

## Version

`TIER3_MISSION_REGISTRY_VERSION` is defined in `runtime/api/__init__.py` and re-exported here as `__version__`.
