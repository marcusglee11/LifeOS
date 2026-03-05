# Handoff: COO-Jarda Parity v5 Review

**Date:** 2026-03-05
**From:** Codex session (implementation + ops cutover)
**To:** Claude Code (review)
**Type:** Code + runtime operations review

---

## Scope

Review the COO-Jarda parity v5 implementation work in this worktree, plus runtime cutover actions completed on Jarda and COO host environments.

Worktree:
`/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/sprint-deferments-d1-d3/.worktrees/coo-jarda-parity-v5`

---

## Branch / Status

Current branch in worktree:
`build/coo-jarda-parity-v5`

Git status includes modified/new files (not committed yet):
- `runtime/tools/coo_worktree.sh`
- `runtime/tools/openclaw_verify_surface.sh`
- `runtime/tools/openclaw_policy_assert.py`
- `runtime/tools/openclaw_verify_memory.sh`
- `runtime/tools/openclaw_memory_policy_guard.py`
- `runtime/tools/openclaw_coo_update_protocol.sh`
- `runtime/tools/workflow_pack.py`
- `runtime/tools/openclaw_memory_index_safe.sh`
- `runtime/tools/openclaw_verify_recall_e2e.sh`
- `runtime/tools/openclaw_receipts_bundle.sh`
- `runtime/tools/openclaw_gate_reason_catalog.py` (new)
- `runtime/tools/openclaw_host_cron_parity_guard.py` (new)
- `runtime/tools/openclaw_promotion_state.py` (new)
- `runtime/tools/openclaw_shared_memory_sync_wrapper.sh` (new)
- `config/openclaw/gate_reason_catalog.json` (new)
- `config/openclaw/shared_memory_sources.schema.json` (new)
- `config/openclaw/instance_profiles/coo.json` (new)
- updated/new tests under `runtime/tests/` for the above surfaces

---

## What Was Implemented

### 1) Parity / Gate / Promotion surfaces

- Added canonical gate reason catalog surface and loader usage.
- Added host-cron parity guard and verify-surface integration.
- Added promotion state runtime tool with:
  - sequence allocation
  - packet verify
  - apply with lock/state tracking
- Added new command surfaces in `openclaw_coo_update_protocol.sh`:
  - `promotion-seq-allocate`
  - `promotion-verify`
  - `promotion-run`
  - `promotion-record`
  - direct `promotion-apply` constrained as internal-only path.

### 2) Memory policy / phase migration

- `openclaw_policy_assert.py` now supports `--policy-phase burnin|qmd`.
- Canonical top-level backend checks added (`memory.backend`).
- `openclaw_verify_memory.sh` updated to phase-aware backend assertions.
- Guard and callsites updated for explicit raw/curated mode behavior.

### 3) Shared-memory safety

- `openclaw_memory_policy_guard.py` extended with:
  - `--mode raw|curated`
  - `--roots-file`
  - `--fail-on-pii`
- Added curated roots schema at `config/openclaw/shared_memory_sources.schema.json`.
- Added wrapper `openclaw_shared_memory_sync_wrapper.sh` as stable cron target.

### 4) Test routing

- `workflow_pack.py` matcher routing extended for new parity/promotion/guard files.

---

## Runtime/Ops Cutover Completed

### COO local (this machine)

- Installed `qmd` CLI: `@tobilu/qmd@1.0.7`.
- Installed `supermemory` SDK package: `supermemory@4.15.0`.
- Updated OpenClaw config at `~/.openclaw/openclaw.json`:
  - `memory.backend = qmd`
  - `memory.qmd.command = /home/linuxbrew/.linuxbrew/bin/qmd`
- Verification:
  - `coo openclaw -- memory status --deep --agent main --json` returns backend/provider `qmd` and probe `ok=true`.
  - `python3 runtime/tools/openclaw_policy_assert.py --json --policy-phase qmd` passes.

### Secret Manager split

Created and verified in project `openclawhost`:
- `supermemory-api-key-jarda` (enabled version 1)
- `supermemory-api-key-coo` (enabled version 1)

### Jarda host (`openclaw-ww5r`, user `garfieldlee11`)

Updated script defaults from shared secret to instance secret:
- `/mnt/openclaw/home/workspace/tools/shared-memory-sync.sh`
- `/mnt/openclaw/home/workspace/tools/shared-memory-search.sh`
- `/mnt/openclaw/home/workspace/tools/supermemory-poll.sh`

Backups created with suffix timestamp:
- `*.20260305T105906Z.bak`

Updated crontab explicit secret usage:
- `shared-memory-sync.sh --secret supermemory-api-key-jarda ...`

Jarda verification:
- Secret fetch succeeds (`jarda_secret_len=90`, length only).
- Sync dry run succeeds:
  - `shared-memory sync complete: total=6 uploaded=0 skipped=6 failed=0`
- Live shared-memory search succeeds (`search_exit=0`) with results returned.

COO Supermemory verification:
- Secret fetch succeeds (`coo_secret_len=31`, length only).
- Live API query with COO key succeeds (`api_ok=true`).

---

## Test Evidence (Repo)

Previously executed in this worktree:
- Static checks on modified scripts/tools passed (`py_compile`, `bash -n`).
- Targeted pytest bundle for new/updated parity/promotion surfaces passed.
- Full `pytest runtime/tests -q` repeatedly stalled/hung in this environment (historical note for reviewer).

---

## Reviewer Focus (Claude Code)

Please review with priority on:
1. Fail-closed behavior correctness in gate reason catalog integration.
2. Promotion state transaction semantics and replay/downgrade protections.
3. Policy phase migration correctness (`burnin` vs `qmd`) and callsite consistency.
4. Host-cron guard behavior for multi-instance keys and reason emission.
5. Memory guard changes (curated roots, PII/secret blocking, backward compatibility in raw mode).
6. Workflow test routing coverage for all new parity/promotion files.
7. Any mismatch between repo tooling and live host scripts currently in Jarda workspace.

---

## Suggested Review Commands

From this worktree:

```bash
pytest runtime/tests/test_openclaw_gate_reason_catalog.py -q
pytest runtime/tests/test_openclaw_host_cron_parity_guard.py -q
pytest runtime/tests/test_openclaw_promotion_state.py -q
pytest runtime/tests/test_openclaw_coo_update_protocol_promotion.py -q
pytest runtime/tests/test_openclaw_policy_assert.py -q
pytest runtime/tests/test_openclaw_memory_policy_assert.py -q
pytest runtime/tests/test_openclaw_memory_policy_guard_curated.py -q
pytest runtime/tests/test_workflow_pack.py -q
```

Optional full suite (known to stall in this environment):

```bash
pytest runtime/tests -q
```

---

## Open Notes

- Old shared secret `supermemory-api-key` can be deleted after final confirmation no consumers remain.
- Added canonical in-repo sync target: `runtime/tools/openclaw_shared_memory_sync.sh` to satisfy wrapper runtime contract.
