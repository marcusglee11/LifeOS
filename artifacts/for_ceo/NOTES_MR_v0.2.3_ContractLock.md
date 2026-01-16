# Mission Registry v0.2.3 Contract Lock (v0.2.3)

## 1. Boundary Default Drift (P0)
- **Resolution**: Option A (Restored v0.1 defaults).
- **Values**:
    - `max_description_chars`: 4000 (restored from 1000)
    - `max_tags`: 25 (restored from 10)
- **Rationale**: Prioritizing contract stability for existing consumers. Strict hygiene checks (emptiness) retained as they do not violate v0.1 contract (proven by tests).

## 2. Export Surface (P1)
- **Proof**: `test_ambiguous_validate_names_are_not_exported` confirms clean surface. No generic `validate` export.

## 3. Hygiene Alignment (P1)
- **Decision**: Strict mirroring. `boundaries.py` enforces whitespace-only rejection for tags/keys.
- **Safety**: 40/40 v0.1 tests passed.

## 4. Verification
- **Full Suite**: 70 tests passed.
- **Evidence**: `TEST_REPORTS_MR_v0.2.3_ContractLock.txt`
