# Process Hardening Notes: G-CBS v1.0

**Date**: 2026-01-05
**Topic**: Generic Closure Bundle Standard (G-CBS)

## 1. How to Run (One-Line Commands)

### Build a Closure Bundle
To build a compliant bundle, you must use the builder script. Do not manually zip files.

```bash
python scripts/closure/build_closure_bundle.py --profile step_gate_closure --include path/to/evidence_list.txt --output artifacts/bundles/MyClosure.zip
```

### Validate a Bundle
To audit a received bundle (audit gate):

```bash
python scripts/closure/validate_closure_bundle.py artifacts/bundles/MyClosure.zip
```

**Pass**: Exit Code 0. Report at `audit_report.md`.
**Fail**: Exit Code 1. Report contains reason codes.

## 2. Reason Codes

| Code | Meaning | Severity | Debt Score |
|------|---------|----------|------------|
| `SHA256_MISMATCH` | Evidence file integrity check failed. | Critical | 90 |
| `ZIP_PATH_NON_CANONICAL` | Paths contain `\`, `..`, or are absolute. | High | 50 |
| `TRUNCATION_TOKEN_FOUND` | Log contains `...`, `[PENDING]`. | Major | 80 |
| `REQUIRED_FILE_MISSING` | Manifest or Addendum missing from root. | Critical | 95 |
| `EVIDENCE_MISSING` | File listed in manifest not in zip. | Critical | 90 |
| `MANIFEST_INVALID_JSON` | Parsing error. | Critical | 95 |

## 3. Debt Management Policy

### The "Debt Expiry Rule"
Any item recorded in `BACKLOG.md` as `[DEBT]` represents a borrowed risk acceptance.

- **DUE Date Compliance**: If the current date > DUE date, the item is **EXPIRED**.
- **Blocker Status**: An EXPIRED debt item is considered a **P0 Blocking Hygiene Issue**. No new feature work (except emergency fix) may proceed until it is resolved or re-negotiated (re-waived).

### Automated Scoring
The `waiver_record.py` script automatically assigns a `Debt_Score` (0-100) based on reason codes.
- **Score > 80**: High Risk. Review monthly.
- **Score > 50**: Moderate Risk. Review quarterly.

### Ingestion
Waivers are automatically ingested into `docs/11_admin/BACKLOG.md` for visibility.

## 4. Troubleshooting
- **"Builder failed"**: Ensure all paths in your `--include` file exist.
- **"Validator failed"**: Check `audit_report.md` for the specific failing path.
