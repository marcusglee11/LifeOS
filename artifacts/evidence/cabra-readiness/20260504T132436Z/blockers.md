# Residual Blockers — Cabra Readiness

**Issue:** #108  
**Timestamp:** 2026-05-04T13:24:36Z  
**Branch:** fix/codex-only-ea-dispatch

---

## FAIL Blockers (Must resolve before full operational readiness)

### BLOCKER-1: ZEN API keys not in shell environment

| Field | Value |
|-------|-------|
| Severity | FAIL — blocks Zen API dispatch |
| Affected keys | ZEN_BUILDER_KEY, ZEN_STEWARD_KEY, ZEN_DESIGNER_KEY, ZEN_BUILD_CYCLE_KEY, ZEN_REVIEWER_KEY |
| Detection | `env \| grep ZEN` returned empty |
| Impact | All configured agent roles (builder, steward, designer, etc.) use `provider: zen`. Without these keys, gateway calls to `https://opencode.ai/zen/v1/messages` will fail with auth errors at runtime. |
| Resolution | **Approval gate: provider/model config or secret injection** — Outside scope of Phase 0-3. Requires Cabra to confirm keys are set in the environment where OpenClaw sessions are launched (not in this Claude Code shell). No action taken. |

### BLOCKER-2: artifacts/health/provider_state.json missing

| Field | Value |
|-------|-------|
| Severity | FAIL — gateway health tracking not initialized |
| Path | `artifacts/health/provider_state.json` |
| Defined in | `config/dispatch.yaml` health.path |
| Impact | Dispatch engine cannot read or update provider health state. The file is referenced by the dispatch engine but was never created/initialized. |
| Resolution | **Approval needed:** Creating/initializing this file is a non-destructive write to `artifacts/`. No external call required. Approval needed to determine whether initialization is within EA scope or requires Cabra/COO action. Exact approval: "EA may create `artifacts/health/provider_state.json` with empty/default health state." |

---

## WARN Items (Advisory — do not block operation)

### WARN-1: OpenClaw update available

| Field | Value |
|-------|-------|
| Severity | WARN |
| Current | 2026.4.27 (cbc2ba0) |
| Available | 2026.5.3-1 |
| Channel | stable |
| Impact | Running slightly stale version. May have bug fixes or new features relevant to Cabra readiness. |
| Resolution | **Approval gate: OpenClaw update** — Not approved in this sprint. Requires explicit Cabra approval. |

### WARN-2: Cron inventory empty

| Field | Value |
|-------|-------|
| Severity | WARN |
| Detection | `.claude/settings.json` crons=[] |
| Nightly queue | `artifacts/dispatch/nightly_queue.yaml` has 3 tasks queued (QUEUE-001, -002, -003) |
| Impact | No active cron trigger is wired. Nightly queue tasks will not execute automatically. |
| Resolution | **Approval gate: cron re-enable** — Not approved in this sprint. If nightly automation is desired, Cabra must explicitly enable via `.claude/settings.json` cron configuration. |

### WARN-3: Node service (systemd) not installed

| Field | Value |
|-------|-------|
| Severity | WARN |
| Detection | `openclaw status` → "Node service: systemd not installed" |
| Impact | Node service does not auto-restart on system restart. Gateway service IS installed and running via systemd. |
| Resolution | May require systemd unit installation for Node. Low urgency; gateway is running. |

---

## Model/Config Drift — Resolution Recommendation

| Field | Value |
|-------|-------|
| Config primary | `claude-sonnet-4-5` (config/models.yaml) |
| Live EA session | `claude-sonnet-4-6` (this Claude Code session) |
| Root cause | `config/models.yaml` governs API/Zen orchestration calls via the runtime gateway. Claude Code UI sessions are not launched by the runtime gateway — they are invoked directly by the user via the Claude Code CLI/app with whatever model the user selects. |
| Is this a bug? | **No.** The two model chains serve different purposes: (1) config/models.yaml → Zen API calls for automated agent tasks; (2) Claude Code UI model → interactive EA sessions invoked by Cabra. |
| Recommendation | No mutation needed. If Cabra wants to document that Claude Code EA sessions should use a specific model version, add a note to `config/governance/active_coo.yaml` or `docs/02_protocols/`. Do **not** modify `config/models.yaml` — it governs the Zen API chain, not interactive Claude Code sessions. |

---

## Not-Blocked Items (Confirmed Clear)

- LifeOS orientation sources: all 4 accessible
- Active COO registry: openclaw/active
- Gateway: running and reachable (127ms local loopback)
- Memory: enabled (plugin memory-core)
- GitHub auth: authenticated, repo scope present
- Python runtime: 3.12.3
- Test suite: 3216 tests collect; targeted suites PASS
- Auto-dispatch predicates: working correctly
- Codex-only EA dispatch policy: enforced and tested
- Dispatch inbox: accessible (empty — expected)
- Policy posture: PRIMARY, loosen=false
- Protected artefacts: config present
