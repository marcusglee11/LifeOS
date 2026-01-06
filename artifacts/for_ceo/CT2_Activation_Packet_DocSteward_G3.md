# CT-2 Activation Packet: DOC_STEWARD G3

**Status**: PENDING COUNCIL REVIEW  
**Created**: 2026-01-06  
**Author**: Antigravity (Doc Steward Orchestrator)

---

## 1. DECISION REQUEST

Activate DOC_STEWARD for `INDEX_UPDATE` mission at G3 (live dry-run with verification).

**Council Triggers**: CT-2 (Capability Promotion), CT-3 (Interface Definition)

---

## 2. CHANGE SUMMARY

### Governance Documents
- **DOC_STEWARD_Constitution_v1.0.md**: Added Activation Envelope (§1A) + Annex A (Reserved Missions)
- **Document_Steward_Protocol_v1.0.md**: Added Activation Envelope (§10.0) with boundary enforcement rules

### Code Hardening
- **Match-Count Enforcement**: Fails on match_count = 0 OR match_count > 1, reason_code: `HUNK_MATCH_COUNT_MISMATCH`
- **Boundary Enforcement**: Orchestrator pre-check + Verifier ERROR for files outside `allowed_paths` or `scope_paths`
- **Verifier Constraints**: Verifier now accepts and enforces request constraints
- **Fail-Closed Import**: Verifier import failure now returns `passed=False`
- **SKIPPED Logic**: Verifier outcome `SKIPPED` when no diffs generated
- **Structured Error Reporting**: `HUNK_MATCH_COUNT_MISMATCH` now details `match_count_found` and `match_count_expected`

---

## 3. EVIDENCE MAP (Audit Trace)

### 3.1 Hashing Policy

SHA256 is computed on **exact file bytes at repo path**. No transformation.

### 3.2 Proof Runs Summary

| Run Type | Case ID | Status | Reason Code | Verifier |
|----------|---------|--------|-------------|----------|
| **Positive Smoke** | `7a7c1afa` | SUCCESS | SUCCESS | PASS |
| **Neg: Match=0** | `58338342` | FAILED | HUNK_MATCH_COUNT_MISMATCH | SKIPPED |
| **Neg: Boundary** | `71a50370` | FAILED | OUTSIDE_SCOPE_PATHS | SKIPPED |
| **Neg: Match>1** | `dfb3279f` | FAILED | HUNK_MATCH_COUNT_MISMATCH | SKIPPED |

### 3.3 Ledger Evidence (Sorted by Path)

| Artifact Path | SHA256 |
|---------------|--------|
| `artifacts/ledger/dl_doc/2026-01-06_neg_test_58338342.yaml` | `F7322365E48B2D13881A41628EAC77652E9A8653697A142E269E23472AF94CCF` |
| `artifacts/ledger/dl_doc/2026-01-06_neg_test_boundary_71a50370.yaml` | `D6AF32FEBB1E6BAE1D4C18EE308D97B10D7CE5CDBC341900BE12AA3C67B00B8F` |
| `artifacts/ledger/dl_doc/2026-01-06_neg_test_multi_dfb3279f.yaml` | `2CBEBA995941BE7B52BF3D39431845B58C686B92B30C606FFC06AC26B312C610` |
| `artifacts/ledger/dl_doc/2026-01-06_smoke_test_7a7c1afa.yaml` | `A4C2B4704786A20F5B253B79D13DA13EF8172C8555676F7267BD978DCB2CC67B` |
| `artifacts/ledger/dl_doc/2026-01-06_smoke_test_7a7c1afa_findings.yaml` | `60CAA0B8B8411F95AAC42ABD5929D18744770D1E82292E789A25F8DE50E981E7` |

### 3.4 Fail-Closed Proof

**Match-Count = 0 (neg_test_58338342):**
- Result: `FAILED` with `HUNK_MATCH_COUNT_MISMATCH`
- Hunk error: Search block not found in file

**Match-Count > 1 (neg_test_multi_dfb3279f):**
- Result: `FAILED` with `HUNK_MATCH_COUNT_MISMATCH`
- Hunk error: "Match count mismatch - found 17, expected 1"
- Ledger fields: `match_count_found: 17`, `match_count_expected: 1`

**Boundary Violation (neg_test_boundary_71a50370):**
- Result: `FAILED` with `OUTSIDE_SCOPE_PATHS`

---

## 4. CONSTITUTIONAL ARTIFACTS

| Artifact | Location |
|----------|----------|
| Constitution | `docs/01_governance/DOC_STEWARD_Constitution_v1.0.md` |
| Protocol | `docs/02_protocols/Document_Steward_Protocol_v1.0.md` |
| Orchestrator | `scripts/delegate_to_doc_steward.py` |
| Verifier | `runtime/verifiers/doc_verifier.py` |

---

## 5. ACTIVATION ENVELOPE

| Category | Missions | Status |
|----------|----------|--------|
| **ACTIVATED** | `INDEX_UPDATE` | Live (`apply_writes=false` default) |
| **RESERVED** | `CORPUS_REGEN`, `DOC_MOVE` | Non-authoritative; requires separate CT-2 |

---

## 6. RECOMMENDATION

**GO for G3 Activation** — INDEX_UPDATE mission only.

---

**END OF PACKET**
