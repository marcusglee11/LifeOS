# Review Packet: EOL Clean Invariant Hardening v2.0 (Closure-Grade)

**Mode**: Standard
**Date**: 2026-02-10
**Branch**: `build/eol-clean-invariant`
**HEAD**: `29a516e30fae578be4b970260530a340772de715`

---

## Scope Envelope

### Allowed Paths

- `runtime/tools/coo_land_policy.py` — Config-aware clean gate + receipt emission
- `runtime/tools/coo_acceptance_policy.py` — Acceptance/closure validator (NEW)
- `runtime/tools/coo_worktree.sh` — Gate integration at choke-points
- `runtime/tests/test_coo_land_policy.py` — Tests (+15 including receipt test)
- `runtime/tests/test_coo_acceptance_policy.py` — Tests (NEW, 23 tests)
- `.gitattributes` — CRLF safety exceptions for *.bat/*.cmd
- `artifacts/acceptance/SCHEMA__Acceptance_Closure_v1.0.md` — Schema (NEW)
- `artifacts/evidence/` — Receipts and proofs (gitignored)
- `artifacts/notes/REPORT__Doc_Stewardship_Status__v1.0.md` — Report (NEW)
- `docs/02_protocols/EOL_Policy_v1.0.md` — Canonical EOL policy doc (NEW)
- `docs/11_admin/LIFEOS_STATE.md` — State update
- `docs/11_admin/BACKLOG.md` — Gate 6 backlog entry
- `docs/INDEX.md` — Index update
- `docs/LifeOS_Strategic_Corpus.md` — Regenerated

### Forbidden Paths (NOT modified)

- `docs/00_foundations/` | `docs/01_governance/` | `GEMINI.md`

---

## Summary

Eliminated persistent CRLF/EOL "dirty repo" condition. Root cause: system-level `core.autocrlf=true` (Windows Git installer default at `C:/Program Files/Git/etc/gitconfig`) conflicted with `.gitattributes eol=lf`. The system config directed Git to convert LF→CRLF on checkout while `.gitattributes` demanded LF in the index, causing 289 files to appear modified with zero semantic changes.

### Root Cause Chain

```
System gitconfig: core.autocrlf=true
    → Git checkout converts LF (index) → CRLF (working tree)
    → .gitattributes: eol=lf demands LF in index
    → git diff detects CRLF (worktree) ≠ LF (index)
    → 289 phantom-dirty files
```

### Fix

1. Set `core.autocrlf=false` at repo-local level (overrides system)
2. Mechanical renormalization: `git add --renormalize .` (289 files, zero semantic diff)
3. Code-enforced gates prevent recurrence

---

## Issue Catalogue

| Priority | Issue | Status |
|----------|-------|--------|
| P0 | CRLF oscillation (289 phantom-dirty files) | **RESOLVED** — repo-local `core.autocrlf=false` + mechanical renormalization |
| P0 | No config compliance gate | **RESOLVED** — `check_repo_clean()` checks effective `core.autocrlf` |
| P0 | Clean gate not wired into choke-points | **RESOLVED** — integrated into `coo land` preflight + postflight |
| P0 | No acceptance clean-proof enforcement | **RESOLVED** — `coo_acceptance_policy.py` with fail-closed validation |
| P0 | CRLF-required files (.cmd) without exceptions | **RESOLVED** — `*.bat`/`*.cmd text eol=crlf` in `.gitattributes` |
| P0 | No machine-verifiable gate receipts | **RESOLVED** — `--receipt` flag emits JSON with HEAD, status, autocrlf provenance |
| P1 | No operational EOL documentation | **RESOLVED** — `docs/02_protocols/EOL_Policy_v1.0.md` |
| P1 | 270 vs 289 count inconsistency | **RESOLVED** — Canonical count is 289 (from `git diff --name-only` on commit `e11eae0`). The "270" was an imprecise estimate from `git status --porcelain=v1` before renormalization which may have counted unstaged entries differently. |
| P2 | Gate 6 (agent-agnostic gate runner) | **LOGGED** — added to BACKLOG.md Next section |

---

## Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Config provenance captured verbatim | ✅ PASS | `RECEIPT__EOL_Config_Provenance__2026-02-10.md` §1 |
| .gitattributes application proven on 4 file types | ✅ PASS | `RECEIPT__EOL_Config_Provenance__2026-02-10.md` §2 |
| CRLF-required files handled (.cmd) | ✅ PASS | `RECEIPT__EOL_Config_Provenance__2026-02-10.md` §3 |
| Mechanical renormalization has semantic-diff zero proof | ✅ PASS | `RECEIPT__EOL_Config_Provenance__2026-02-10.md` §4.1 |
| Checkout doesn't re-dirty | ✅ PASS | `RECEIPT__EOL_Config_Provenance__2026-02-10.md` §4.3 |
| Clean-check gate at enforcement choke-points | ✅ PASS | `coo_worktree.sh` L1083-1098 (preflight), L1466-1469 (postflight) |
| Gate emits machine-verifiable receipt | ✅ PASS | `clean-check --receipt` emits JSON with HEAD, status, autocrlf provenance |
| Acceptance validator enforces clean proofs (fail-closed) | ✅ PASS | 23 test cases including dirty/missing proof rejection |
| EOL churn detection classifies correctly | ✅ PASS | CLEAN, EOL_CHURN, CONTENT_DIRTY, CONFIG_NONCOMPLIANT all tested |
| All tests pass | ✅ PASS | 38/38 pass (`pytest -v`) |
| Count reconciled (270 vs 289) | ✅ PASS | See Issue Catalogue P1 entry |
| core.autocrlf=false proven via --show-origin | ✅ PASS | `file:.git/config  false` |
| Doc stewardship executed | ✅ PASS | INDEX, Strategic Corpus, STATE, BACKLOG updated |

---

## Closure Evidence Checklist

| Category | Requirement | Verified |
|----------|-------------|----------|
| **Provenance** | Renormalization commit hash + msg | `e11eae0` chore(eol): enforce canonical line endings |
| | Gate code commit hash + msg | `3eb111d` feat(eol): config-aware clean gate + acceptance validator |
| | Doc stewardship commit hash + msg | `e83b53c` docs: stewardship update |
| | Review packet commit hash + msg | `b4d8713` docs: add renormalization receipt + review packet |
| | Integration commit hash + msg | `c1dc3db` feat(eol): receipt-emitting clean gate + coo land integration |
| | Changed file list | See Appendix: File Manifest |
| **Artifacts** | Config provenance receipt | `artifacts/evidence/RECEIPT__EOL_Config_Provenance__2026-02-10.md` |
| | Renormalization receipt | `artifacts/evidence/RECEIPT__Renormalization_Mechanical_EOL__2026-02-10.md` |
| | Review Packet | `artifacts/review_packets/Review_Packet_EOL_Clean_Invariant_v2.0.md` |
| | Acceptance Schema | `artifacts/acceptance/SCHEMA__Acceptance_Closure_v1.0.md` |
| | Doc Stewardship Report | `artifacts/notes/REPORT__Doc_Stewardship_Status__v1.0.md` |
| **Repro** | Test command | `pytest runtime/tests/test_coo_acceptance_policy.py runtime/tests/test_coo_land_policy.py -v` (38 pass) |
| | Clean check command | `python -m runtime.tools.coo_land_policy clean-check --repo .` |
| | Checkout-doesn't-re-dirty | `git checkout -- . && git status --porcelain=v1` → empty |
| **Governance** | Doc-Steward routing | INDEX.md updated, Strategic Corpus regenerated |
| | EOL Policy doc | `docs/02_protocols/EOL_Policy_v1.0.md` |
| **Outcome** | Terminal outcome | PASS — 38/38 tests, clean repo, config compliant, gates integrated |

---

## Non-Goals

- System-level gitconfig was NOT changed (only repo-local override)
- Existing acceptance notes were NOT retroactively validated
- Gate 6 (agent-agnostic gate runner) was NOT implemented (logged to BACKLOG)
- Git hooks were NOT modified (clean-check is a standalone gate, not a hook)

---

## Appendix: File Manifest

### Commit 1: `e11eae0` — Mechanical renormalize

- 289 files: CRLF→LF in index (zero semantic changes)

### Commit 2: `3eb111d` — Config-aware clean gate + acceptance validator

| File | Change | Size |
|------|--------|------|
| `runtime/tools/coo_land_policy.py` | MODIFIED | +131 lines |
| `runtime/tools/coo_acceptance_policy.py` | NEW | 206 lines |
| `runtime/tests/test_coo_land_policy.py` | MODIFIED | +119 lines |
| `runtime/tests/test_coo_acceptance_policy.py` | NEW | 207 lines |
| `artifacts/acceptance/SCHEMA__Acceptance_Closure_v1.0.md` | NEW | 97 lines |
| `docs/02_protocols/EOL_Policy_v1.0.md` | NEW | 77 lines |
| `artifacts/notes/REPORT__Doc_Stewardship_Status__v1.0.md` | NEW | 92 lines |

### Commit 3: `e83b53c` — Doc stewardship

| File | Change |
|------|--------|
| `docs/INDEX.md` | MODIFIED |
| `docs/LifeOS_Strategic_Corpus.md` | MODIFIED |
| `docs/11_admin/LIFEOS_STATE.md` | MODIFIED |
| `docs/11_admin/BACKLOG.md` | MODIFIED |

### Commit 4: `b4d8713` — Receipts + review packet v1

| File | Change |
|------|--------|
| `artifacts/evidence/RECEIPT__Renormalization_Mechanical_EOL__2026-02-10.md` | NEW |
| `artifacts/review_packets/Review_Packet_EOL_Clean_Invariant_v1.0.md` | NEW (superseded by v2.0) |

### Commit 5: `c1dc3db` — Gate integration + bat/cmd safety

| File | Change | Size |
|------|--------|------|
| `.gitattributes` | MODIFIED | +4 lines (*.bat/*.cmd eol=crlf) |
| `runtime/tools/coo_land_policy.py` | MODIFIED | +35 lines (receipt emission) |
| `runtime/tools/coo_worktree.sh` | MODIFIED | +21 lines (preflight/postflight gates) |
| `runtime/tests/test_coo_land_policy.py` | MODIFIED | +15 lines (receipt test) |

### Commit 6: (this commit) — Closure-grade evidence

| File | Change |
|------|--------|
| `artifacts/evidence/RECEIPT__EOL_Config_Provenance__2026-02-10.md` | NEW |
| `artifacts/review_packets/Review_Packet_EOL_Clean_Invariant_v2.0.md` | NEW |
