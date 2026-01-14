# Plan Schema Rollout Note (v1.2) - 2026-01-14

## Context

To prevent review iteration loops caused by unproven mandates and non-deterministic paths, we have introduced a strict `PLAN_PACKET` schema and a preflight validator.

## Changes

1. **Schema**: Added `PLAN_PACKET` to `lifeos_packet_schemas_CURRENT.yaml`.
2. **Template**: Created `docs/02_protocols/templates/plan_packet_template.md`.
3. **Tooling**: Added `scripts/validate_plan_preflight.py`.
4. **Fixtures**: Added 6 fixtures in `tests/fixtures/plan_packet/` for regression testing.

## Usage

Run preflight before submitting any plan:

```bash
python scripts/validate_plan_preflight.py path/to/plan.md
```

## Failure Codes

- `PPV001`: Missing Section
- `PPV002`: Invalid Order
- `PPV003`: Missing Mandate Evidence
- `PPV004`: Missing Path Evidence
- `PPV005`: Invalid Pointer Grammar
