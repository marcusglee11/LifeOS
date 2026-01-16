# Reactive Task Layer v0.1

**Status**: Active  
**Authority**: [LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md](../../docs/03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md)  
**Date**: 2026-01-03

**Definition-only**, **deterministic**, **no-I/O** surface for reactive task planning.

> **Scope**: This spec covers Reactive Task Layer v0.1 only. Mission Registry / Executor are not included.

---

## Boundaries

| Constraint | Enforcement |
|------------|-------------|
| No execution | No calling Builder/Orchestrator |
| No I/O | No filesystem, network, clocks, randomness |
| Determinism | Identical input → identical surface + JSON + hash |
| Exception taxonomy | Local-only `ReactiveBoundaryViolation` for v0.1 |

---

## Plan Surface v0.1 Schema

```json
{
  "version": "reactive_task_layer.v0.1",
  "task": {
    "id": "<str>",
    "title": "<str>",
    "description": "<str>",
    "tags": ["<str>", ...]
  },
  "constraints": {
    "max_payload_chars": <int>
  }
}
```

---

## Semantic Rules

| Field | Semantics |
|-------|-----------|
| `id`, `title` | Raw strings; no transformation applied to stored values. Validation rejects empty/whitespace-only. |
| `description` | Raw string; no transformation. |
| `tags` | Must be `tuple[str, ...]`; order-preserving; `None` → `[]`; no sorting/normalization |
| `max_payload_chars` | Enforced via `validate_surface()` |

---

## Canonical JSON (Pinned Settings)

```python
json.dumps(
    surface,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
    allow_nan=False
)
```

---

## Hash

```python
sha256(canonical_json(surface).encode("utf-8")).hexdigest()
```

---

## Validation Call Flow

```
validate_request(req, cfg)  # before surface creation
surface = to_plan_surface(req, cfg)
validate_surface(surface, cfg)  # after surface creation
```

`to_plan_surface()` does not validate internally.

---

## Boundary Defaults

| Config | Default |
|--------|---------|
| `max_title_chars` | 200 |
| `max_description_chars` | 4000 |
| `max_tags` | 25 |
| `max_tag_chars` | 64 |
| `max_payload_chars` | 8000 |
