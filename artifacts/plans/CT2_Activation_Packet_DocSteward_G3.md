# CT-2 Activation Packet: DOC_STEWARD G3

**Status**: APPROVED  
**Created**: 2026-01-06  
**Author**: Antigravity (Doc Steward Orchestrator)

## Council Sign-Off

| Field | Value |
|-------|-------|
| **Decision** | GO (Council-DONE) |
| **Bundle** | `Bundle_CT2_CouncilDONE_2026-01-06.zip` |
| **Audit** | PASS (all 5 checks) |
| **Approved** | 2026-01-06 |

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
| `artifacts/ledger/dl_doc/2026-01-06_neg_test_8c509d2a.yaml` | `FF1512059C5E8169910FDB59AE95604FD7B14E570575F428D20C124053C3B9E1` |
| `artifacts/ledger/dl_doc/2026-01-06_neg_test_boundary_126292d8.yaml` | `49AF1212F9A738CCC172811A3856A7B0D834A74D091CC474010DCC8981562339` |
| `artifacts/ledger/dl_doc/2026-01-06_neg_test_multi_5d73b8fa.yaml` | `055775FF332E5AA9BDB9AED2069E317EA4E6AFF6DF80009A19AADE50081CCD11` |
| `artifacts/ledger/dl_doc/2026-01-06_smoke_test_0e9431f2.yaml` | `B65BF0FB776B208EC09CAAAEA51BC308966A5EE19C068D9BC9D7E33099DBF4B2` |
| `artifacts/ledger/dl_doc/2026-01-06_smoke_test_0e9431f2_findings.yaml` | `60CAA0B8B8411F95AAC42ABD5929D18744770D1E82292E789A25F8DE50E981E7` |

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
