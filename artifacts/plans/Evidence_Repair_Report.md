# CT-2 Evidence Repair Report v2

**Date:** 2026-01-05
**Author:** Antigravity (Doc Steward Orchestrator)

## 1. Hashing Policy (P0)

**Source of Truth**: SHA256 is computed on the exact file bytes as stored at the repo-relative path.
- **No transformations** are applied before hashing (line endings preserved as-is).
- **Path format**: Repo-relative using forward slashes (e.g., `artifacts/ledger/dl_doc/...`).

## 2. Regeneration Summary (P1)

All proof runs were **regenerated** (not patched) using the mock server. New case IDs were assigned:

| Run Type | Case ID | Status | Reason Code | Verifier |
|----------|---------|--------|-------------|----------|
| Positive Smoke | `dc8ab438` | SUCCESS | SUCCESS | PASS |
| Negative: Match Count | `cb3bab97` | FAILED | HUNK_MATCH_COUNT_MISMATCH | SKIPPED |
| Negative: Boundary | `7c7c0907` | FAILED | OUTSIDE_SCOPE_PATHS | SKIPPED |

## 3. Authoritative SHA256 Values

These hashes are computed from repo file bytes with no transformation:

| Artifact Path | SHA256 |
|---------------|--------|
| `artifacts/ledger/dl_doc/2026-01-05_neg_test_boundary_7c7c0907.yaml` | `797DEAE558BCD934DA35442A2070672F367430C2210A5B24B65632C9273FEF8A` |
| `artifacts/ledger/dl_doc/2026-01-05_neg_test_cb3bab97.yaml` | `9844E940424DB06565FE225CB2202A1534782689B11B8EE507422C5EC4DA67F0` |
| `artifacts/ledger/dl_doc/2026-01-05_smoke_test_dc8ab438.yaml` | `E8BA4D804211D32F960A47A8D5D32CEEB2D244973E74E6A6E7655BE23F3DA81B` |
| `artifacts/ledger/dl_doc/2026-01-05_smoke_test_dc8ab438_findings.yaml` | `60CAA0B8B8411F95AAC42ABD5929D18744770D1E82292E789A25F8DE50E981E7` |

## 4. Bundle Integrity (P3)

The bundle includes artifacts at their **repo-relative paths** (not flattened) to ensure the hashed bytes match exactly:
- `artifacts/ledger/dl_doc/2026-01-05_smoke_test_dc8ab438.yaml`
- `artifacts/ledger/dl_doc/2026-01-05_smoke_test_dc8ab438_findings.yaml`
- `artifacts/ledger/dl_doc/2026-01-05_neg_test_cb3bab97.yaml`
- `artifacts/ledger/dl_doc/2026-01-05_neg_test_boundary_7c7c0907.yaml`

## 5. Commands Used

```powershell
# Start mock server
Start-Process python -ArgumentList "scripts\temp_mock_server.py" -NoNewWindow

# Run 3 proof tests
python scripts/delegate_to_doc_steward.py --mission INDEX_UPDATE --trial-type smoke_test --dry-run 2>&1
python scripts/delegate_to_doc_steward.py --mission INDEX_UPDATE --trial-type neg_test --dry-run 2>&1
python scripts/delegate_to_doc_steward.py --mission INDEX_UPDATE --trial-type neg_test_boundary --dry-run 2>&1

# Compute hashes
Get-FileHash -Algorithm SHA256 (Get-ChildItem "artifacts\ledger\dl_doc\2026-01-05_*.yaml")
```

---
**END OF REPORT**
