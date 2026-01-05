# BLOCKED: Phase 1 Real API Round-Trip

| Field | Value |
|-------|-------|
| **Date** | 2026-01-04 |
| **Status** | BLOCKED |
| **Reason** | API_UNREACHABLE |

---

## Blocker Description

Real API calling cannot be performed. OpenCode server is not running at `http://127.0.0.1:4096`.

**Error**: `[WinError 10061] No connection could be made because the target machine actively refused it`

---

## What Was Completed

### Code Changes (Correctly Separate dry-run vs simulate)

| File | Change |
|------|--------|
| `scripts/delegate_to_doc_steward.py` | v2 with correct mode semantics |
| `runtime/verifiers/doc_verifier.py` | v2 with proposed changes verification |

### CLI Semantics (Fixed)

```
--dry-run (default): Real API call → produce diffs → verify → ledger → NO disk writes
--simulate:          Offline synthetic response, no API call (testing harness)
--execute:           Real API call → produce diffs → verify → ledger → APPLY disk writes
```

### Evidence-by-Reference (Implemented)

DOC_STEWARD_REQUEST now includes:
- `input_refs`: list of `{path, sha256}` for all scope files
- `scope_paths`: explicit list of paths in scope
- `constraints.mode`: explicit mode flag

DOC_STEWARD_RESULT now includes:
- `files_modified`: list with `{path, change_type, before_sha256, after_sha256, diff_sha256}`
- `proposed_diffs`: embedded bounded unified diff
- `diff_evidence_sha256`: hash of proposed changes
- `reason_code`: explicit error codes (API_UNREACHABLE, SESSION_FAILED, etc.)
- `latency_ms`: timing for audit

---

## What Is Needed to Unblock

1. **Start OpenCode server**: `npx opencode --api-only`
2. **Ensure OPENROUTER_API_KEY is set**: OpenCode requires this for LLM calls
3. **Verify server health**: `http://127.0.0.1:4096/global/health` should return 200

---

## Synthetic Test (SIMULATED)

The orchestrator was tested in `--simulate` mode to validate packet and verifier plumbing:

```
python scripts/delegate_to_doc_steward.py --mission INDEX_UPDATE --simulate --trial-type smoke_test
```

This produces a ledger entry with synthetic diff, demonstrating the full flow works offline.

---

## Files Changed

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/delegate_to_doc_steward.py` | ~480 | Orchestrator v2 with mode semantics |
| `runtime/verifiers/doc_verifier.py` | ~300 | Verifier v2 with proposed changes |

---

## Ledger Evidence (Failed API Attempt)

```
artifacts/ledger/dl_doc/2026-01-04_smoke_test_f1673366.yaml
```

Contains:
- Status: FAILED
- Reason: API_UNREACHABLE
- Latency: 2019ms (time to health check failure)

---

## Next Steps

When OpenCode server is available:

1. Re-run G1: `python scripts/delegate_to_doc_steward.py --mission INDEX_UPDATE --dry-run --trial-type smoke_test`
2. Re-run G2 (3x): `python scripts/delegate_to_doc_steward.py --mission INDEX_UPDATE --dry-run --trial-type shadow_trial`
3. Package evidence and produce updated Spike Findings

---

*BLOCKED artifact produced per Section G fail-closed behavior.*
