# AUR_20260112 A1/A2 Re-closure v2.1c — Sign-Off

**Decision**: CLOSED / GO
**Scope**: A1/A2 Re-closure (Hardening v2.1c)
**Bundle Version**: v2.1c
**Date**: 2026-01-12

---

## Evidence

1. **G-CBS v1.1 Audit**: PASS (Detached Digest Verified)
2. **Verbatim Capture**: Checked via `generate_a1a2_evidence.py` scanning logic (fail-closed truncation signatures).
3. **Internal Path Consistency**: ZIP listing verifies `evidence/` structure matches `gates.json` and `outputs.txt`.
4. **No-Truncation Invariant**: Confirmed PASS via `validate_closure_bundle.py --deterministic`.

---

## Canonical Artefacts (SHA256)

| Path | SHA256 (Full) |
|------|---------------|
| `artifacts/bundles/Bundle_A1_A2_Closure_v2.1c.zip` | `8F26A3E1C93D8AA57F98533324A5068688496C10C0B48048B868B190B9873C3A` |
| `artifacts/reclosure_work/final_audit_report_v2.1.md` | `B49943F0269916C9FB03E644BE35A91BB3AB8D51CF07807B4DB003EB9D456CD3` |
| `artifacts/review_packets/Review_Packet_A1_A2_Reclosure_v2.1c.md` | `338857F84D338CFF6864418FD940EEA2012BED42AEBE13F5998BEADD0C517D1D` |

---

## ZIP Listing Evidence

Command: `zipinfo -1 artifacts/bundles/Bundle_A1_A2_Closure_v2.1c.zip | sort`

```
audit_report.md
closure_addendum.md
closure_manifest.json
evidence/env_info.txt
evidence/pytest_a1.txt
evidence/pytest_a2.txt
```

> [!IMPORTANT]
> No hashes are truncated anywhere in this sign-off record.
