# Review Packet: OpenClaw Viability Recovery Implementation v1.0

## Mission
Implement the subscription-first OpenClaw viability recovery plan and produce the full evidence package under ~/.openclaw/evidence/viability_recovery_v1/.

## Outcome
- Implemented config/auth/lane hardening in-place.
- Installed OpenClaw burn-in probes and host cron monitoring/check scripts.
- Generated baseline/probe/report/runbook evidence artifacts.

## Changed Repo Files
- artifacts/plans/Plan_OpenClaw_Viability_Recovery_SubscriptionFirst_v1.0.md
- artifacts/review_packets/Review_Packet_OpenClaw_Viability_Recovery_Implementation_v1.0.md

## External Runtime Changes (Non-Repo)
- ~/.openclaw/openclaw.json (runtime hardening)
- ~/.openclaw/agents/main/agent/auth-profiles.json (auth order pin confirmed)
- ~/.openclaw/evidence/viability_recovery_v1/* (evidence outputs)

## Validation
- All three burn-in probes have successful run history entries.
- Daily viability report generated from stored probe snapshot.
- Auth gate and daily checks scripts dry-run successful after PATH hotfix.

## Appendix A: Flattened Code for Changed Files

### File: artifacts/plans/Plan_OpenClaw_Viability_Recovery_SubscriptionFirst_v1.0.md

```md
# OpenClaw Viability Recovery (Subscription-First) v1.0

## 1. Objective
Restore OpenClaw to stable, usable service first, then run a 7-day burn-in with evidence gates.

Priority order for runtime routing:
1. ChatGPT subscription lane (`openai-codex/*`)
2. GitHub subscription lane (`github-copilot/*`)
3. Google AI subscription lane (`google-gemini-cli/*`)
4. API providers as cold-standby only during burn-in

Claude-Max is quarantined during burn-in and evaluated later in a separate lane.

## 2. Scope and Constraints
- In scope:
  - DM/session isolation hardening
  - deterministic model ladder and allowlist hardening
  - auth order pinning and auth-expiry monitoring gate
  - OpenClaw cron probes + daily viability reporting
  - daily security and gateway checks
  - prepared (not executed) partial rebuild runbook
- Out of scope:
  - new channel installs
  - plugin installs
  - full rebuild unless Day-7 criteria force it

## 3. Deterministic Runtime Ladder
- Primary: `openai-codex/gpt-5.3-codex`
- Fallback 1: `github-copilot/claude-opus-4.6`
- Fallback 2: `google-gemini-cli/gemini-3-flash-preview`
- Active allowlist: only the three models above (plus strictly required infra entries if proven necessary)
- `claude-max/*`: removed from active routing/allowlist for burn-in

## 4. Execution Phases

### Phase P0: Baseline + Freeze
1. Create evidence tree:
   - `~/.openclaw/evidence/viability_recovery_v1/{baseline,config,probes,reports,runbooks}`
2. Log every command (verbatim command + stdout/stderr + exit code) in `baseline/`.
3. Capture baseline snapshots:
   - `openclaw --version`
   - `openclaw status --json`
   - `openclaw gateway status --json` (fallback plain)
   - `openclaw models status --json`
   - `openclaw models status --probe --json` (token-consuming)
   - `openclaw channels status --probe --json`
   - `openclaw security audit --deep` and `--json`
   - `openclaw doctor`
4. Freeze notes include current ladder, auth.order, dmScope, and current tool posture.

### Phase P0.1: DM/session hardening
1. Backup `~/.openclaw/openclaw.json` pre-change.
2. Set `session.dmScope = "per-account-channel-peer"` (fallback to `per-channel-peer` only if required by account topology).
3. Preserve pairing/allowlist posture for Telegram and existing DM policies.
4. Save post-change config copy, sha256 hash, and short diff summary.

### Phase P0.2: Ladder + allowlist hardening
1. Discover exact available model refs from live CLI.
2. Enforce deterministic ladder above in `agents.defaults` and all `agents.list[*]`.
3. Reduce active allowlist to the ladder set.
4. Remove `claude-max/*` from active allowlist and routing; document as quarantined.
5. Align CLI fallback list (`openclaw models fallbacks`) to fallback #1 and #2.

### Phase P0.3: Auth hardening + monitoring gate
1. Resolve `<agentId>` from `openclaw status --json`.
2. Pin `auth.order[openai-codex]` to one known-good profile id.
3. Keep stale profiles out of `order` without deleting secrets unless clearly dead.
4. Install host auth gate automation:
   - run `openclaw models status --check`
   - exit code policy: `0=ok`, `1=expired/missing`, `2=expiring soon`
   - on `1`/`2`: send Telegram alert + write dated alert file under `reports/`

### Phase P0.4: Burn-in probes + reports
1. Create three isolated OpenClaw cron jobs:
   - Probe-T every 30 min (fast non-empty output)
   - Probe-U every 60 min (status/introspection + one-line summary)
   - Probe-F daily with model override `github-copilot/claude-opus-4.6`
2. Delivery settings: announce to Telegram control peer, best effort disabled.
3. Export cron definitions and run history snapshots into `probes/`.
4. Generate deterministic daily viability report from stored snapshots:
   - total runs, success/failure per probe
   - failure classes: auth invalid, 429, empty reply, timeout, delivery fail, other
   - model/provider attribution when available
   - SLO-A and SLO-B percentages

### Phase P1: Daily security + gateway checks
1. Install daily host check automation:
   - `openclaw security audit --deep`
   - `openclaw gateway status`
2. Save dated outputs in `reports/`.

### Phase P2: Partial rebuild fallback runbook (prepare only)
Create `runbooks/partial_rebuild_v1.md` with:
1. new clean `agentDir` creation (never reuse old `agentDir`)
2. preserved assets only: memory artifacts, channel identities/allowlists, logs
3. rebuilt components: auth routing metadata, ladder, session routing, gateway bootstrap
4. rollback steps back to stabilized in-place config

## 5. Fail-Closed Rules
If any required value cannot be discovered from machine/config (agentId, Telegram control peer, required model ref, profile ID):
1. write `reports/BLOCKED_<timestamp>.md`
2. include failed command and stderr
3. stop changes immediately

## 6. Day-7 Decision Gates
- Continue in-place if:
  - SLO-A >= 98%
  - SLO-B >= 98%
  - no recurring auth-expiry incidents
  - no recurring empty-reply pattern
- Trigger partial rebuild if thresholds miss for 2 consecutive days.
- Abandon only if partial-rebuild pilot cannot recover thresholds within 48 hours.

## 7. Deliverables
1. Evidence tree populated
2. Final config copy (redacted for sharing) + sha256
3. Cron job definitions + latest run history snapshot
4. Sample daily viability report
5. Partial rebuild runbook
6. Operator notes (risks, skips, rationale)
```
