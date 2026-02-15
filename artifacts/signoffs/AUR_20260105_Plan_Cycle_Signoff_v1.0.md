# Sign-Off: AUR_20260105 Plan Cycle Amendment (v1.4)

## 1. Decision
**CLOSED / GO**

## 2. Scope
**AUR_20260105 Plan Cycle Amendment**
This amendment introduces schema-enforced planning through subtypes (`BUILD_PACKET.build_type=PLAN`), removing the need for dedicated packet types.

## 3. Canonical Outcomes
- **Subtypes Implemented**:
  - `BUILD_PACKET`: Added `build_type`, `spec`, `tasks`.
  - `REVIEW_PACKET`: Added `review_type`, `plan_hash`.
- **Taxonomy Preserved**:
  - Core: 9 types (MVP).
  - Deprecated: 3 types.
  - No `PLAN_PACKET` or `PLAN_REVIEW_PACKET`.
- **Validation**:
  - Schema Alias: `docs/02_protocols/schemas/lifeos_packet_schemas_CURRENT.yaml`
  - Validator: Hardened against overlap; zero ellipses.

## 4. Evidence (Portable)
- **Regression Tests**: `pytest runtime/tests/test_packet_validation.py` -> **20 passed**
- **Invariants**: No literal "..." in `scripts/validate_packet.py` (Verified via grep/read).
- **Review Packet**: Validates against CURRENT schema (exit 0).

## 5. Canonical Artefacts (SHA256)

| Artefact (Relative Path) | SHA256 |
|--------------------------|--------|
| docs/02_protocols/schemas/lifeos_packet_schemas_v1.2.yaml | 84BF431E83C92DB14E19B0E923E14A059CB67CC65A3A936D7CBB27DAA0EE1865 |
| docs/02_protocols/schemas/lifeos_packet_schemas_CURRENT.yaml | 84BF431E83C92DB14E19B0E923E14A059CB67CC65A3A936D7CBB27DAA0EE1865 |
| scripts/validate_packet.py | EB8F74F9A7C6E9B9C6F99DFF1D6666BE07E3370559014F67B2F82CABBF86BB12 |
| runtime/tests/test_packet_validation.py | DCFF9E8832D94FE916EF2770F132CB8D99A11455F847D53E6E0B218D9B7E04ED |
| artifacts/review_packets/Review_Packet_AUR_20260105_Plan_Cycle_v1.4.md | A0DED48166A8DADD2B9B6B11157C10864DA544A0E21F0E85BA1F50B6B25409EF |
