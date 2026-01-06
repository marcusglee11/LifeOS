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

---

## v0.2 Delta — Synthesis + Validation

v0.2 adds deterministic mission synthesis and explicit validation:

### New Public API

- **`MissionSynthesisRequest`** — Structured input for synthesis
- **`synthesize_mission(request, config=None)`** — Single entrypoint (validate → build → validate)
- **`validate_mission_definition_v0_2(defn, config=None)`** — Explicit validation entrypoint

### Contract Lock (v0.2.3)
- **ID Contract**: Whitespace-only IDs REJECTED/
- **Hygiene**: Empty/whitespace-only tags and metadata keys REJECTED.
- **Defaults**: Restored to v0.1 values (`max_description_chars=4000`, `max_tags=25`).

### Synthesis Pattern

```python
from runtime.mission import MissionSynthesisRequest, synthesize_mission

req = MissionSynthesisRequest(
    id="my-mission",
    name="My Mission",
    description="A deterministic mission",
    tags=("core", "automated"),
    metadata={"author": "antigravity"},
)
defn = synthesize_mission(req)  # Returns validated MissionDefinition
```

### Evidence

- **Tests**: `runtime/tests/test_mission_registry/test_mission_registry_v0_2.py` (24 tests)
- **Golden Hash**: `4907f6d1d305089e05d16cb3e89fde4b7b200db8173b3734e2ebebe2222751b7`

---

## Version

`TIER3_MISSION_REGISTRY_VERSION` is defined in `runtime/api/__init__.py` and re-exported here as `__version__`.

