# OpenClaw COO Runbook

## Canonical Operator Flow

Standard lifecycle for any session:

```bash
coo ensure
coo doctor
coo doctor --apply-safe-fixes
coo app
# or:
coo tui
coo stop
```

If `coo start`, `coo app`, or `coo tui` fail, run `coo doctor` first.

`coo` is the wrapper-only surface (`runtime/tools/coo_worktree.sh`).
Python orchestration for backlog/proposals/approvals lives under `lifeos coo ...`.

## Canonical Commands

- OpenClaw operations: `coo openclaw -- <args>`
- Shell/process operations: `coo run -- <command>`

## Distill Lane Operations (Milestone 1)

Distill lane is optional and default-off. Raw COO behavior remains authoritative.

Session-scoped enablement only:

```bash
export LIFEOS_DISTILL_ENABLE=1
export LIFEOS_DISTILL_MODE=shadow
```

Do not enable through persistent shell profiles, tmux startup, service env, or system-wide env in milestone 1.

Preflight:

```bash
python3 runtime/tools/openclaw_distill_lane.py preflight --state-dir "$OPENCLAW_STATE_DIR" --mode shadow
```

Audit and health-state paths:

- `$OPENCLAW_STATE_DIR/runtime/gates/distill/audit.jsonl`
- `$OPENCLAW_STATE_DIR/runtime/gates/distill/health_state.json`
- `$OPENCLAW_STATE_DIR/runtime/gates/distill/payloads/`

Milestone-1 scope:

- Shadow only:
  - `coo openclaw -- models status`
  - `coo openclaw -- status --all --usage`
- Active allowed only for:
  - `coo openclaw -- models status`

Requested `LIFEOS_DISTILL_MODE=active` does not override stale or invalid health/preflight state and does not override post-drift shadow suppression.

Shadow observation window:

- 12 successful shadow invocations total
- at least 6 `coo openclaw -- models status`
- at least 6 `coo openclaw -- status --all --usage`
- across at least 2 separate operator sessions

A successful shadow invocation is one in-scope seam command where:

- effective behavior remains shadow or raw-bypass only
- operator output remains usable
- a per-attempt audit record is written
- no blocker reason is recorded

Shadow-completion blockers:

- `health_state_invalid`
- `distill_lane_unavailable`
- `schema_failure`
- `distill_call_failed`
- any timeout event
- any auth/provider failure event
- any health-state corruption event
- any unintended active replacement on `status --all --usage`
- any unexpected raw bypass on `models status`

Blocker-bearing runs do not count toward the observation window. Timeout/auth/provider failures are blockers and prevent shadow completion until a clean observation window is re-established.

Shadow receipt and promotion:

- substrate/maintainer prepares the shadow success receipt from audit and health-state evidence
- CEO approves the shadow success receipt
- only then may `models status` be considered for active promotion

Forced-failure drill before active:

1. Disable the lane or invalidate health state
2. Confirm `coo openclaw -- models status` continues on the raw path
3. Restore valid shadow/active candidate state

Active candidate session:

```bash
export LIFEOS_DISTILL_ENABLE=1
export LIFEOS_DISTILL_MODE=active
```

Active promotion requires:

- fresh preflight under the current fingerprint
- CEO-approved shadow success receipt under the current fingerprint
- successful forced-failure drill
- explicit CEO re-promotion after any fingerprint drift

Rollback:

```bash
unset LIFEOS_DISTILL_ENABLE LIFEOS_DISTILL_MODE
```

or:

```bash
export LIFEOS_DISTILL_ENABLE=0
```

Upgrade or fingerprint drift handling:

1. Run `openclaw --version`
2. Verify current fingerprint inputs:
   - observed OpenClaw version
   - observed channel if available
   - configured cheap lane id
   - configured cheap model target
   - wrapper schema version
3. Rerun distill preflight
4. Rerun at least 2 shadow checks on `coo openclaw -- models status`
5. Confirm audit and health-state updated cleanly
6. Require full CEO re-approval path before restoring active

## COO Update Protocol (Ringed Enforcement)

Use the protocol runner for enforceable OpenClaw COO update flow:

```bash
runtime/tools/openclaw_coo_update_protocol.sh all-preclose
```

Promotion packet flow for an actual version upgrade:

```bash
runtime/tools/openclaw_upgrade_module.sh propose --channel stable
runtime/tools/openclaw_coo_update_protocol.sh promotion-seq-allocate --instance coo
# Construct promotion_packet.json from propose's promotion_packet_base + the allocated ticket:
# jq -s '.[0].promotion_packet_base * {ticket: .[1]}' proposal.json ticket.json > <dir>/promotion_packet.json
runtime/tools/openclaw_coo_update_protocol.sh promotion-verify --packet-dir <dir>
npm install -g openclaw@<target_version>   # mutating — only after verify passes
openclaw --version                          # confirm installed version matches packet
runtime/tools/openclaw_coo_update_protocol.sh promotion-run --packet-dir <dir>
```

Step-by-step mode:

```bash
runtime/tools/openclaw_coo_update_protocol.sh preflight
runtime/tools/openclaw_coo_update_protocol.sh concurrency-check
runtime/tools/openclaw_coo_update_protocol.sh operational-check
runtime/tools/openclaw_coo_update_protocol.sh escalation-check
runtime/tools/openclaw_coo_update_protocol.sh preclose
```

After merge to `main`:

```bash
runtime/tools/openclaw_coo_update_protocol.sh postmerge
```

Notes:

- Manual operator checks use:
  - `openclaw models list --all`
  - `openclaw models status`
  - `openclaw models aliases list`
- `promotion-run` does not install OpenClaw. It attests and records the promotion after the target version is already installed.
- `promotion_packet.json` should include `target_commit`, `target_version`, and `previous_version` in addition to the promotion ticket.
- Automated escalation checks run `runtime/tools/openclaw_models_preflight.sh`, which internally uses `openclaw models list` and `openclaw models status --probe`.
- Merge/push remains fail-closed via `.claude/hooks/close-build-gate.sh`.

## Receipts (Runtime Default)

Canonical operator path is runtime-only receipts (no repo writes by default):

- `$OPENCLAW_STATE_DIR/receipts/<UTC_TS>/Receipt_Bundle_OpenClaw.md`
- `$OPENCLAW_STATE_DIR/receipts/<UTC_TS>/receipt_manifest.json`
- `$OPENCLAW_STATE_DIR/receipts/<UTC_TS>/openclaw_run_ledger_entry.jsonl`
- `$OPENCLAW_STATE_DIR/ledger/openclaw_run_ledger.jsonl`

If `$OPENCLAW_STATE_DIR` is not writable, scripts fall back to `/tmp/openclaw-runtime/...`.

Run default mode:

```bash
runtime/tools/openclaw_receipts_bundle.sh
```

Optional explicit repo export (copy-only):

```bash
runtime/tools/openclaw_receipts_bundle.sh --export-repo
```

Export path:

- `artifacts/evidence/openclaw/receipts/Receipt_Bundle_OpenClaw_<UTC_TS>.md`

Export is optional and should only be used when a repo-local evidence copy is required.

## Verify Surface

Run full verify flow (security/model/sandbox/gateway checks + receipt generation + ledger append + leak scan):

```bash
runtime/tools/openclaw_verify_surface.sh
```

Expected output:

- `PASS security_audit_mode=<mode> confinement_detected=<true|false> ... runtime_receipt=<path> ledger_path=<path>`
- or `FAIL security_audit_mode=<mode> confinement_detected=<true|false> ... runtime_receipt=<path> ledger_path=<path>`

Security audit strategy:

- `security audit --deep` is attempted first.
- If deep fails with known host confinement signature
  `uv_interface_addresses returned Unknown system error 1`,
  verify runs bounded fallback `security audit` (non-deep).
- Any other deep failure remains fail-closed and verify returns non-zero.
- When fallback triggers, verify and ledger include:
  `confinement_detected=true` and
  `confinement_flag=uv_interface_addresses_unknown_system_error_1`.

Sandbox posture strategy:

- COO shared-ingress posture is repo-owned via `config/openclaw/instance_profiles/coo.json`.
- Runtime verify accepts the configured posture semantically, not via a hard-coded mode string.
- Current COO expectation is:
  `target_posture=shared_ingress`,
  `allowed_modes=["all"]`,
  `sessionIsSandboxed=true`,
  `elevated.enabled=false`.
- `gate_status.json` records expected and observed sandbox posture fields for startup diagnostics.

Model policy assertion:

```bash
python3 runtime/tools/openclaw_policy_assert.py --json
```

Optional memory verifier (not part of P0 security PASS path):

```bash
runtime/tools/openclaw_verify_memory.sh
```

Expected output:

- `PASS memory_policy_ok=true provider=local fallback=none ...`
- or `FAIL memory_policy_ok=false provider=<x> fallback=<y> ...`

Safe memory indexing wrapper (guarded):

```bash
runtime/tools/openclaw_memory_index_safe.sh
```

Behavior:

- Runs `runtime/tools/openclaw_memory_policy_guard.py` first (fail-closed).
- Runs `coo openclaw -- memory index --agent main --verbose` only when guard passes.

## Embedding Provider Trial (Opt-In, No Default Drift)

Default policy stays enforced as local-only memory embeddings:

- `memorySearch.provider=local`
- `memorySearch.fallback=none`

Use this trial command only for A/B checks. It runs with a temporary overlay config under `$OPENCLAW_STATE_DIR/embedding-trials/` and does not mutate your base config:

```bash
python3 runtime/tools/openclaw_embedding_trial.py --provider openai --model text-embedding-3-small --index --json
```

Other provider trials:

```bash
python3 runtime/tools/openclaw_embedding_trial.py --provider gemini --model gemini-embedding-001 --index --json
python3 runtime/tools/openclaw_embedding_trial.py --provider voyage --model voyage-3.5-lite --index --json
```

Interpretation:

- `trial_pass=true` with `hit_count>=1` means the provider worked for current corpus/search.
- `trial_pass=false` means auth/model/provider failed in trial mode; baseline local policy remains unchanged.

Optional interfaces verifier (Telegram hardening posture):

```bash
runtime/tools/openclaw_verify_interfaces.sh
```

Expected output:

- `PASS telegram_posture=allowlist+requireMention replyToMode=first ...`
- or `FAIL telegram_posture=allowlist+requireMention replyToMode=<x> ...`

Grounded recall verifier (memory ↔ interface contract):

```bash
runtime/tools/openclaw_verify_recall_e2e.sh
```

Expected output:

- `PASS recall_mode=telegram_sim|cli_only sources_present=true MANUAL_SMOKE_REQUIRED=<true|false> ...`
- or `FAIL recall_mode=... sources_present=false ...`

Recall contract:

- Recall/decision intents must use memory search first.
- Answers must include a `Sources:` section with `file:line-range` pointers.
- If no hits, response must be: `No grounded memory found. Which timeframe or document should I check?`
- Receipts/ledger store recall metadata only (`query_hash`, hit count, sources), never raw query content.

## Manual Telegram Smoke (Metadata-Only)

Operator step (allowed Telegram DM only):

1. Send exactly:
   `what did we decide last week about lobster-memory-seed-001?`
2. Expected behavior:
   - grounded answer returned
   - `Sources:` section includes `memory/daily/2026-02-10.md:1-5`
3. Record metadata only (no message text, no IDs/usernames/phone numbers):

```bash
coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && P1_5_EVDIR=artifacts/evidence/openclaw/p1_5/<UTC_TS> runtime/tools/openclaw_record_manual_smoke.sh --surface telegram_dm --result pass --sources memory/daily/2026-02-10.md:1-5'
```

Fail branch:

```bash
coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && P1_5_EVDIR=artifacts/evidence/openclaw/p1_5/<UTC_TS> runtime/tools/openclaw_record_manual_smoke.sh --surface telegram_dm --result fail --sources "(none)"'
```

## P1 Acceptance Verifier

Run:

```bash
coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && P1_5_EVDIR=artifacts/evidence/openclaw/p1_5/<UTC_TS> runtime/tools/openclaw_verify_p1_acceptance.sh'
```

Expected:

- `PASS p1_acceptance=true manual_smoke=pass source_pointer=memory/daily/2026-02-10.md:1-5 ...`

## Multi-User Posture Verifier

Run:

```bash
runtime/tools/openclaw_verify_multiuser_posture.sh
```

Expected:

- `PASS multiuser_posture_ok=true enabled_channels_count=<n> allowlist_counts=<k=v,...> ...`
- or `FAIL ...` when any allowlist/owner boundary/Telegram posture invariant drifts.

## Operator Onboarding (Controlled + Auditable)

Generate an onboarding checklist with a non-sensitive internal reference label:

```bash
runtime/tools/openclaw_onboard_operator.sh --candidate-ref operator-two-change-request
```

Notes:

- The helper stores only `candidate_ref_sha256` and never raw identifiers.
- Apply config changes manually via reviewed PR/commit; then run:
  - `python3 runtime/tools/openclaw_multiuser_posture_assert.py --json`
  - `runtime/tools/openclaw_verify_multiuser_posture.sh`

## Telegram Hardening

- `channels.telegram.allowFrom` must be non-empty and must not include `"*"`.
- `channels.telegram.groups` must use explicit group IDs (no `"*"`), with `requireMention: true`.
- `agents.list[].groupChat.mentionPatterns` should include stable mention triggers (for example `@openclaw`, `openclaw`).
- `messages.groupChat.historyLimit` should stay conservative (30-50).
- `channels.telegram.replyToMode` uses `first` for predictable threading.

## Slack Scaffold (Blocked Until Tokens)

Slack is scaffolded in secure-by-default mode only:

- `channels.slack.enabled=false`
- optional HTTP wiring keys only (`mode="http"`, `webhookPath="/slack/events"`)
- no `botToken`, `appToken`, or `signingSecret` in config

Slack enablement uses env-only overlay generation. Tokens are never written into
`~/.openclaw/openclaw.json`, repo files, or evidence artifacts.

Socket mode enablement (when provisioning is approved):

1. Export env vars in shell/session only:
   - `OPENCLAW_SLACK_MODE=socket`
   - `OPENCLAW_SLACK_APP_TOKEN`
   - `OPENCLAW_SLACK_BOT_TOKEN`
2. Launch with overlay:
   - `runtime/tools/openclaw_slack_launch.sh --apply`
3. Run post-enable checks:
   - `runtime/tools/openclaw_verify_interfaces.sh`
   - `runtime/tools/openclaw_verify_multiuser_posture.sh`
   - `runtime/tools/openclaw_verify_slack_guards.sh`

HTTP mode enablement (when provisioning is approved):

1. Export env vars in shell/session only:
   - `OPENCLAW_SLACK_MODE=http`
   - `OPENCLAW_SLACK_BOT_TOKEN`
   - `OPENCLAW_SLACK_SIGNING_SECRET`
2. Ensure request URL uses `/slack/events` and signature verification remains enabled.
3. Launch with overlay:
   - `runtime/tools/openclaw_slack_launch.sh --apply`
4. Run same post-enable checks as socket mode.

## Safety Invariants

- Default receipt generation must not write to repo paths.
- Ledger and receipts must remain redacted-safe.
- Leak scan must pass for runtime receipt + runtime ledger entry.
- Verify is fail-closed on security audit, sandbox invariants, and policy assertion.
- Receipts include a non-deep memory status capture; they do not run memory index by default.
- Receipts include memory policy guard summary status (`memory_policy_ok`, violation count).
- Receipts include recall trace metadata (`recall_trace_enabled`, `last_recall`).
- Receipts include a non-deep channels status capture and never include Slack secrets.
- Receipts include multi-user posture status (`multiuser_posture_ok`, channel names, allowlist counts, violations count) and never include allowlist values.
- Receipts include Slack guard posture (`slack_ready_to_enable`, `slack_base_enabled`, `slack_env_present`, `slack_overlay_last_mode`) with booleans/counts only.
