# Cabra Readiness Baseline

**Issue:** #108  
**Timestamp:** 2026-05-04T13:24:36Z  
**Branch:** fix/codex-only-ea-dispatch  
**HEAD:** 7729cde490307aa8fd72b949e5d96fec199de712  
**EA:** claude-sonnet-4-6 (Claude Code)

---

## 1. OpenClaw Version / Status

| Field | Value |
|-------|-------|
| Binary path | `/home/cabra/bin/openclaw` |
| Version | `OpenClaw 2026.4.27 (cbc2ba0)` |
| Binary exists | YES (executable, -rwxr-xr-x) |
| runtime_status.json | `ok` (generated 2026-04-28T00:44:40Z) |
| active_coo.yaml status | `active` |
| active_coo_id | `openclaw` |
| Profile | `coo_unsandboxed_prod_l3` |
| Sandbox posture | `unsandboxed` |

**Notes:** Runtime status confirmed `openclaw_installed: true` and `openclaw_bin: /home/cabra/bin/openclaw`. Last refresh was 2026-04-28 (6 days ago). No live OpenClaw session was started (not approved).

---

## 2. Gateway Health / Status

| Field | Value |
|-------|-------|
| artifacts/health/provider_state.json | **MISSING** (FILE_NOT_FOUND) |
| Gateway module | `runtime/gateway/deterministic_call.py` — present |
| Configured endpoint | `https://opencode.ai/zen/v1/messages` |
| Gateway health state file | Not initialized |

**Notes:** The provider_state.json health file defined in `config/dispatch.yaml` (`artifacts/health/provider_state.json`) does not exist. Gateway module code is present and importable. No live connectivity check performed (would require API keys/external call).

---

## 3. Effective Model / Fallback Chain

### config/models.yaml (authoritative config)
```
default_chain:
  1. claude-sonnet-4-5
  2. opencode/glm-5-free
  3. opencode/minimax-m2.5-free

role_overrides: (all roles same chain)
  designer, reviewer_architect, builder, steward, build_cycle, council_reviewer → same chain

agents:
  All COO-dispatched EA roles:
    dispatch_mode: cli
    cli_provider: codex
    cli_fallback: ""
    allow_api_fallback: false
    provider: zen / model: claude-sonnet-4-5
    endpoint: https://opencode.ai/zen/v1/messages
```

### config/coo/telegram_model.json (EA COO execution model)
```
primary: openai-codex/gpt-5.4
fallbacks:
  1. openai-codex/gpt-5.3-codex
  2. openai-codex/gpt-5.1
  3. openai-codex/gpt-5.1-codex-max
  4. github-copilot/gpt-5-mini
  5. google-gemini-cli/gemini-3-flash-preview
```

### Live Session Model
- Current EA session: `claude-sonnet-4-6`
- Config primary: `claude-sonnet-4-5`

**Model drift:** Live Claude Code session uses `claude-sonnet-4-6`; `config/models.yaml` specifies `claude-sonnet-4-5`. This drift is **benign** — `config/models.yaml` governs API/Zen orchestration calls (via the runtime gateway), not Claude Code UI sessions. The EA was invoked directly as Sonnet 4-6 by the user, bypassing the config chain. No mutation needed; a **resolution recommendation** is in blockers.md.

### EA Dispatch Policy (post-fix commit 7729cde4)
- Codex is the only CLI execution lane for COO-dispatched EA roles
- `allow_api_fallback: false` on all agent roles
- Falls closed (does not fall back to Claude/Gemini/API)

---

## 4. Memory Backend / Search Availability

| Component | Status |
|-----------|--------|
| COO memory dir | `COO/memory/` — PRESENT |
| MEMORY.md | Present |
| MEMORY_ARCH_SPEC_v0.1.md | Present |
| coo-memory.py | Present |
| coo-memory.js | Present |
| structured/ | Present |
| checkpoints/ | Present |
| memory.schema.json | `COO/memory/structured/memory.schema.json` |
| Escalation DB | `artifacts/queue/escalations.db` (SQLite) |
| Vector/search backend | NOT FOUND (no vector DB config detected) |

**Notes:** Structured memory schema exists. No vector search backend (e.g., chromadb, pinecone, weaviate) was found in config or dependency files. Search availability is limited to file-based structured YAML/JSON memory.

---

## 5. LifeOS Orientation Access

| Source | Path | Status |
|--------|------|--------|
| Backlog | `config/tasks/backlog.yaml` | ✓ ACCESSIBLE |
| State | `docs/11_admin/LIFEOS_STATE.md` | ✓ ACCESSIBLE |
| Delegation envelope | `config/governance/delegation_envelope.yaml` | ✓ ACCESSIBLE |
| Dispatch inbox | `artifacts/dispatch/inbox/` | ✓ ACCESSIBLE (empty — only .gitkeep) |

All four mandatory orientation sources are accessible via the approved path. No repair needed. No hidden shell improvisation used.

---

## 6. Dispatch Inbox Visibility

| Field | Value |
|-------|-------|
| Inbox path | `artifacts/dispatch/inbox/` |
| Contents | Empty (only `.gitkeep`) |
| Last modified | 2026-03-10 |
| Active orders | 0 |
| Nightly queue | 3 tasks queued (QUEUE-001, -002, -003) |

---

## 7. GitHub Auth / Bus Visibility

| Field | Value |
|-------|-------|
| Auth status | ✓ Logged in to github.com |
| Account | `marcusglee11` |
| Token type | `gho_****` (OAuth) |
| Token scopes | `gist`, `read:org`, `repo` |
| Git protocol | SSH |
| Bus access | ✓ Can read issues/PRs via `gh` CLI |

---

## 8. Messaging Policy / Channel Gates (dry-run / readback only)

| Component | Status |
|-----------|--------|
| Telegram model config | `config/coo/telegram_model.json` — PRESENT |
| Primary model | `openai-codex/gpt-5.4` |
| Messaging channel expansion | NOT approved — not performed |
| External message send test | NOT approved — not performed |
| Dry-run gate inspection | Readback only |

**Policy posture:** `config/policy/posture.yaml` = `mode: PRIMARY`, `allow_posture_loosen: false`.

No messaging send tests were performed. Channel gate state confirmed by config readback only.

---

## 9. Cron Inventory State

| Field | Value |
|-------|-------|
| .claude/settings.json crons | `[]` (empty) |
| Scheduled tasks in Claude settings | 0 |
| Nightly queue file | `artifacts/dispatch/nightly_queue.yaml` — 3 tasks |
| Cron re-enable | NOT approved — not performed |
| Active cron triggers | NONE DETECTED |

**Notes:** The nightly queue YAML contains tasks but no active cron mechanism is wired in Claude settings. Whether this is intentional (cron disabled) or a gap is recorded in blockers.md.

---

## 10. Node / Python Status

| Component | Status |
|-----------|--------|
| Python | 3.12.3 (GCC 13.3.0) — ✓ OK |
| pytest collection | 3216 tests collected — ✓ OK |
| OpenClaw binary | Present and executable |
| Codex binary | Config references `codex` binary; availability not verified live |

---

## 11. Native Subagent / EA Routing State

| Field | Value |
|-------|-------|
| EA dispatch policy | Codex-only (commit 7729cde4, 2026-04-28) |
| api_fallback_allowed | false (all agent roles) |
| CLI provider | codex |
| Fallback | empty string (fail closed) |
| Council provider_overrides | All roles → codex |
| Native subagent expansion | NOT approved — not performed |

**Current branch** (`fix/codex-only-ea-dispatch`) enforces Codex-only routing. This is the fix branch; the change is not yet merged to main. On main (pre-merge), EA could potentially fall back to other providers.
