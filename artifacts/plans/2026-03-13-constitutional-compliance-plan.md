# Plan: Constitutional Compliance Remediation — Determinism, Auditability, Reversibility

**Status:** COMPLETE (all 8 sprints, commit 913bd9e8)
**Branch:** build/constitutional-compliance

---

## Context

LifeOS was built on three Hard Invariants from the Constitution (v2.0):

1. **Determinism** — Reproducible, side-effect-free execution within the deterministic envelope
2. **Auditability** — "All actions must be logged. No silent or unlogged operations."
3. **Reversibility** — "System state must be versioned and reversible. Irreversible actions require explicit CEO authorization."

Strong foundational infrastructure exists: deterministic call gateway, hash-chained lineage (AMU0), execution envelope, receipt system (v2.4), canonical JSON, deep-copy immutability. But recent additions (COO/OpenClaw, OpenCode client, missions, CLI dispatch) were integrated **without wiring into this infrastructure**. The system is deterministic-capable but non-deterministic in practice.

---

## Compliance Verdict (pre-remediation)

| Principle | Status | Summary |
|---|---|---|
| **Determinism** | BROKEN | `uuid.uuid4()` and `datetime.now()` in 5+ call paths; COO bypasses gateway entirely |
| **Auditability** | ~70% | Core receipt/lineage works; COO, Codex dispatch, CLI dispatch produce ZERO receipts |
| **Reversibility** | PARTIAL | Inputs immutable; but no transactional rollback, no mission compensation, LLM calls terminal |

---

## Critical Audit Gaps (pre-remediation)

| Action Path | Location | Current Audit | Severity |
|---|---|---|---|
| COO/OpenClaw invocation | `runtime/orchestration/coo/invoke.py:86` | NONE | CRITICAL |
| Codex CLI dispatch | `scripts/workflow/dispatch_codex.sh:108` | NONE | CRITICAL |
| CLI agent dispatch | `runtime/agents/cli_dispatch.py:140` | Partial (result struct, no receipt) | HIGH |
| Mission execution | `runtime/orchestration/engine.py:370-500` | State mutation, no pre/post hash | MEDIUM |
| Repo-map injection | `engine.py:21`, `coo/context.py:25` | NONE (silent load) | MEDIUM |
| Remote op queue | `runtime/orchestration/ceo_queue.py` | SQLite only, no receipt | MEDIUM |

## Determinism Violations (pre-remediation)

| Location | Violation | Fix |
|---|---|---|
| `runtime/agents/opencode_client.py:589` | `uuid.uuid4()` for LLM call_id | `sha256(model+prompt)` |
| `runtime/agents/opencode_client.py:706` | `datetime.now()` for timestamps | Annotated `# AUDIT-ONLY` |
| `runtime/agents/api.py:360` | Random `call_id_audit` | Annotated `# AUDIT-ONLY` |
| `runtime/orchestration/engine.py:444` | `uuid.uuid4()` for mission run_id | `compute_sha256({mission_type, step_id, inputs})` |
| `runtime/orchestration/coo/commands.py:287` | `uuid.uuid4().hex[:8]` for COO direct run_id | `compute_sha256({context, mode})` |

---

## Remediation Phases

### Phase 1: Close Critical Audit Gaps ✅ DONE

Every consequential external call must produce an invocation receipt. Zero dark paths.

#### 1A: COO Invocation Receipts ✅

**File:** `runtime/orchestration/coo/invoke.py`
- Added `run_id: str = ""` parameter to `invoke_coo_reasoning()`
- Captures start/end timestamps around subprocess call
- Emits receipt with `provider_id="openclaw"`, `seat_id="coo_{mode}"` on ALL paths
- Error paths (timeout, bad exit, parse failure) ALL emit receipt

**Caller:** `runtime/orchestration/coo/commands.py`
- `run_id` = `compute_sha256({"context": context, "mode": mode})` — content-addressable, not uuid
- `uuid` import removed

**Tests:** `runtime/tests/orchestration/coo/test_invoke_receipts.py` (7 tests)

#### 1B: CLI Agent Dispatch Receipts ✅

**File:** `runtime/agents/cli_dispatch.py`
- Added `run_id: str = ""` parameter to `dispatch_cli_agent()`
- Emits receipt after subprocess on success, failure, and timeout

**Tests:** `runtime/tests/test_cli_dispatch_receipts.py` (5 tests)

#### 1C: Codex Shell Dispatch Receipts ✅

**File:** `scripts/workflow/dispatch_codex.sh`
- Removed `exec` prefix from codex invocation (enables post-execution logging)
- Calls `emit_dispatch_receipt.py` after codex exits

**New file:** `scripts/workflow/emit_dispatch_receipt.py`
- CLI wrapper that calls `record_invocation_receipt()` with provider/exit/worktree/topic
- `--python-root` param for import path separation from output dir

**Tests:** `runtime/tests/test_emit_dispatch_receipt.py` (4 tests)

---

### Phase 2: Determinism Restoration ✅ DONE

Content-addressable IDs everywhere. Wall-clock time explicitly labelled audit-only.

#### 2A: Eliminate Random UUIDs ✅

| Site | Fix |
|---|---|
| `opencode_client.py:589` | `sha256(json({model, prompt}))` |
| `engine.py:444` | `compute_sha256({mission_type, step_id, inputs})` |
| `coo/commands.py:287` | `compute_sha256({context, mode})` |
| `api.py:360` | Documented as `# AUDIT-ONLY: non-deterministic trace ID` |
| `opencode_client.py:706` | Documented as `# AUDIT-ONLY: wall-clock metadata` |

**Tests:** `runtime/tests/test_determinism_ids.py` (7 tests)

#### 2B+2C: Timestamp Discipline + Execution Envelope Notes ✅

**New file:** `runtime/util/time.py`
- `audit_timestamp()` — wall-clock UTC ISO, docstring says AUDIT-ONLY
- `deterministic_timestamp(pinned)` — validates and returns pinned value

**File:** `runtime/envelope/execution_envelope.py`
- Added `LIFEOS_TODO[P1]` note on network-check post-import gap
- Added `verify_network_restrictions_post_hoc()` for end-of-run detection
- Logs warning in sandbox mode instead of silently passing

**Tests:** `runtime/tests/test_time_util.py` (7 tests)

---

### Phase 3: Reversibility Hardening ✅ DONE

#### 3A: Transactional State Snapshots ✅

**File:** `runtime/orchestration/engine.py` — `run_workflow()`
- Snapshots state with `copy.deepcopy(state)` BEFORE each step
- `OrchestrationResult.state_snapshots` holds the list
- `rollback_to_step(index)` returns deep copy of pre-step state
- Lineage includes `snapshot_hashes` (SHA-256 of each snapshot)

**Tests:** `runtime/tests/test_state_snapshots.py` (8 tests)

#### 3B: Mission Compensation Interface ✅

**File:** `runtime/orchestration/missions/base.py`
- New `CompensableMission` mixin with `compensate(context, run_result) -> bool`

**File:** `runtime/orchestration/engine.py`
- `_run_compensation()` iterates executed mission steps in reverse on failure
- Best-effort: failed compensation logged, does not mask original failure

#### 3C: LLM Replay Cache ✅

**File:** `runtime/agents/api.py`
- `_write_replay_cache()` writes response to `artifacts/replay_cache/<call_id>.json`
- Keyed by deterministic `call_id`: same inputs → same key → cache hit on retry
- Best-effort: write failure logged, never propagated
- `artifacts/replay_cache/` added to `.gitignore`

**Tests:** `runtime/tests/test_compensation_and_cache.py` (7 tests)

---

### Phase 4: Audit Completeness ✅ DONE

#### 4A: LLM Input Prompt Capture ✅

**Files:** `runtime/receipts/invocation_receipt.py`, `invocation_schema.py`, `runtime/agents/api.py`
- `InvocationReceipt` gains optional `input_hash` field
- Schema updated with `"input_hash": {"type": ["string", "null"]}`
- `call_agent()` passes `packet_hash` as `input_hash` on successful calls

#### 4B: Repo-Map Injection Audit ✅

**File:** `runtime/orchestration/engine.py`
- `_execute_llm_call()`: if step payload includes `repo_map_path`, computes `sha256_file()` and stores in `{output_key}_metadata["repo_map_hash"]`

#### 4C: Queue State Change Receipts ✅

**File:** `runtime/orchestration/ceo_queue.py`
- `add_escalation()`, `approve()`, `reject()` each emit `record_invocation_receipt()`
- Best-effort (logged, never raises)

**Tests:** `runtime/tests/test_audit_completeness.py` (7 tests)

---

## What Does NOT Change

- Receipt system infrastructure (already well-designed, just needs wider coverage)
- Deterministic call gateway stub status (Tier-2 activation is separate)
- Governance documents (`docs/00_foundations/`, `docs/01_governance/`)
- Protected paths
- No new dependencies or libraries
- No import hooks for runtime envelope enforcement (future work)

## Existing Infrastructure Reused

| Infrastructure | Location | Used In |
|---|---|---|
| `record_invocation_receipt()` | `runtime/receipts/invocation_receipt.py` | 1A, 1B, 1C, 4A, 4C |
| `compute_sha256()` | `runtime/util/canonical.py` | 2A, 4B |
| `atomic_write_json()` | `runtime/util/atomic_write.py` | 3C |
| `copy.deepcopy` pattern | `runtime/orchestration/engine.py:550` | 3A |

## Verification Results

- **Full test suite:** 2476 passed, 7 skipped, 0 failed
- **New tests added:** 46 across 8 test files
- **Zero regressions**

## Remaining / Future Work

The following items are OUTSIDE scope of this remediation but noted for future sprints:

1. **`datetime.now()` replacement** — Multiple `datetime.now()` calls in `api.py`, `logging.py`, `coo/context.py`, `receipt_emitter.py` are audit-only but not yet replaced with `runtime.util.time.audit_timestamp()`. Annotated correctly; refactor is mechanical.

2. **Envelope post-import enforcement** — `LIFEOS_TODO[P1]` noted in `execution_envelope.py`. Call `verify_network_restrictions_post_hoc()` at end of workflow runs.

3. **Replay cache READ path** — `_write_replay_cache()` is implemented but `call_agent()` does not yet CHECK the cache before making a live call (only the existing fixture-based `is_replay_mode()` does this). Wiring the new file-based cache as a fallback is a follow-on sprint.

4. **Deterministic call gateway activation** — The gateway stub exists (`runtime/gateway/deterministic_call.py`) but COO still bypasses it. Tier-2 activation is a separate architectural decision.
