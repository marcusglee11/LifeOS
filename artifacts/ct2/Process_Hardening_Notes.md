# CT-2 Process Hardening Notes

## New Rule: No Ad-Hoc Bundles

All CT-2 bundles MUST be produced by the automated pipeline:

```powershell
python scripts/run_ct2_proof_runs.py   # Generate evidence
python scripts/build_ct2_bundle.py     # Build & audit bundle
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/ct2_audit_check.py` | Validates bundle structure, hashes, elisions, proof coverage |
| `scripts/build_ct2_bundle.py` | Deterministic bundler with auto-audit |
| `scripts/run_ct2_proof_runs.py` | Generates smoke + negative proof runs |

## Audit Failure Codes

| Code | Meaning |
|------|---------|
| `ZIP_PATH_CANONICAL` | Backslash or absolute path in zip |
| `EVIDENCE_MAP_PATHS_EXIST` | Referenced path missing from zip |
| `SHA256_MATCH` | Hash mismatch |
| `NO_ELISIONS_IN_RAW_LOG` | Literal `...` found in evidence log |
| `PROOF_COVERAGE` | Missing required ledger pattern |
| `REASON_CODES` | Missing reason_code or match counts |

## Controlled Fixture

Multi-match test uses `docs/ct2_fixture.md` with exactly 2 occurrences of `TARGET_BLOCK`.
