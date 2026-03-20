# Review Packet — Gate A-P1.5 v1.0

## Summary
- Gate objective closed: manual Telegram DM smoke captured as metadata-only evidence and P1 acceptance verifier returns PASS.
- Privacy posture preserved: no Telegram message content, IDs, usernames, or phone numbers stored in repo evidence.
- Deterministic operator tooling added for repeatable metadata capture and acceptance verification.

## Changes
- Added `runtime/tools/openclaw_record_manual_smoke.sh`.
- Added `runtime/tools/openclaw_verify_p1_acceptance.sh`.
- Updated `runtime/tools/OPENCLAW_COO_RUNBOOK.md` with manual smoke and acceptance steps.

## Acceptance Evidence
- Evidence directory: `artifacts/evidence/openclaw/p1_5/20260211T064452Z`
- Manual smoke note: `artifacts/evidence/openclaw/p1_5/20260211T064452Z/manual_smoke_note.md`
- Verifier output: `artifacts/evidence/openclaw/p1_5/20260211T064452Z/verify_p1_acceptance_output.txt`
- PASS line:
  PASS p1_acceptance=true manual_smoke=pass source_pointer=memory/daily/2026-02-10.md:1-5 summary=/tmp/ocv_p1_5/p1/summary.txt

## Privacy Posture
- `openclaw_record_manual_smoke.sh` stores only `ts_utc`, `surface`, `result`, `sources`, and verifier context (branch + head SHA).
- Source input is fail-closed and restricted to strict `file:line-range` tokens or `(none)`.

## Appendix A — Flattened Code

### File: runtime/tools/openclaw_record_manual_smoke.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage:
  runtime/tools/openclaw_record_manual_smoke.sh --surface telegram_dm --result pass|fail --sources <file:line-range[,file:line-range...]|(none)>
USAGE
}

SURFACE=""
RESULT=""
SOURCES=""

while [ $# -gt 0 ]; do
  case "$1" in
    --surface)
      SURFACE="${2:-}"
      shift 2
      ;;
    --result)
      RESULT="${2:-}"
      shift 2
      ;;
    --sources)
      SOURCES="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$SURFACE" != "telegram_dm" ]; then
  echo "surface must be telegram_dm" >&2
  exit 2
fi
if [ "$RESULT" != "pass" ] && [ "$RESULT" != "fail" ]; then
  echo "result must be pass or fail" >&2
  exit 2
fi
if [ -z "$SOURCES" ]; then
  echo "sources is required" >&2
  exit 2
fi

# Fail-closed: only allow strict source pointer tokens or literal (none).
# No spaces or free-form text are allowed.
if [ "$SOURCES" != "(none)" ]; then
  if printf '%s' "$SOURCES" | rg -q '[[:space:]]'; then
    echo "sources must not contain whitespace" >&2
    exit 2
  fi
  if ! printf '%s' "$SOURCES" | rg -q '^[A-Za-z0-9_./-]+:[0-9]+-[0-9]+(,[A-Za-z0-9_./-]+:[0-9]+-[0-9]+)*$'; then
    echo "sources must be file:line-range tokens, comma-separated" >&2
    exit 2
  fi
fi

TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
HEAD_SHORT="$(git rev-parse --short HEAD)"
EV_BASE="${P1_5_EVDIR:-artifacts/evidence/openclaw/p1_5/$TS_UTC}"
mkdir -p "$EV_BASE"
NOTE_PATH="$EV_BASE/manual_smoke_note.md"

{
  echo "ts_utc: $TS_UTC"
  echo "surface: $SURFACE"
  echo "result: $RESULT"
  echo "sources: $SOURCES"
  echo "verifier_context: branch=$BRANCH head=$HEAD_SHORT"
} > "$NOTE_PATH"

echo "$NOTE_PATH"
```

### File: runtime/tools/openclaw_verify_p1_acceptance.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_P1_ACCEPTANCE_OUT_DIR:-$STATE_DIR/verify-p1-acceptance/$TS_UTC}"
CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_P1_ACCEPTANCE_TIMEOUT_SEC:-45}"

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify-p1-acceptance/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

MEM_OUT="$OUT_DIR/verify_memory.txt"
IFACE_OUT="$OUT_DIR/verify_interfaces.txt"
RECALL_OUT="$OUT_DIR/verify_recall.txt"
SUMMARY_OUT="$OUT_DIR/summary.txt"

set +e
timeout "$CMD_TIMEOUT_SEC" runtime/tools/openclaw_verify_memory.sh > "$MEM_OUT" 2>&1
RC_MEM=$?
timeout "$CMD_TIMEOUT_SEC" runtime/tools/openclaw_verify_interfaces.sh > "$IFACE_OUT" 2>&1
RC_IFACE=$?
timeout "$CMD_TIMEOUT_SEC" runtime/tools/openclaw_verify_recall_e2e.sh > "$RECALL_OUT" 2>&1
RC_RECALL=$?
set -e

PASS=1
if [ "$RC_MEM" -ne 0 ] || [ "$RC_IFACE" -ne 0 ] || [ "$RC_RECALL" -ne 0 ]; then
  PASS=0
fi

if ! rg -q '^PASS ' "$MEM_OUT"; then PASS=0; fi
if ! rg -q '^PASS ' "$IFACE_OUT"; then PASS=0; fi
if ! rg -q '^PASS .*sources_present=true' "$RECALL_OUT"; then PASS=0; fi

EVDIR="${P1_5_EVDIR:-}"
if [ -z "$EVDIR" ]; then
  latest="$(ls -1dt artifacts/evidence/openclaw/p1_5/* 2>/dev/null | head -n1 || true)"
  EVDIR="$latest"
fi
NOTE="$EVDIR/manual_smoke_note.md"

if [ -z "$EVDIR" ] || [ ! -f "$NOTE" ]; then
  PASS=0
else
  rg -q '^surface: telegram_dm$' "$NOTE" || PASS=0
  rg -q '^result: pass$' "$NOTE" || PASS=0
  rg -q '^sources: memory/daily/2026-02-10.md:1-5$' "$NOTE" || PASS=0
fi

{
  echo "ts_utc=$TS_UTC"
  echo "verify_memory_exit=$RC_MEM"
  echo "verify_interfaces_exit=$RC_IFACE"
  echo "verify_recall_exit=$RC_RECALL"
  echo "manual_note=$NOTE"
  echo "memory_out=$MEM_OUT"
  echo "interfaces_out=$IFACE_OUT"
  echo "recall_out=$RECALL_OUT"
} > "$SUMMARY_OUT"

if [ "$PASS" -eq 1 ]; then
  echo "PASS p1_acceptance=true manual_smoke=pass source_pointer=memory/daily/2026-02-10.md:1-5 summary=$SUMMARY_OUT"
  exit 0
fi

echo "FAIL p1_acceptance=false manual_smoke_note=$NOTE summary=$SUMMARY_OUT" >&2
exit 1
```

### File: runtime/tools/OPENCLAW_COO_RUNBOOK.md
```markdown
# OpenClaw COO Runbook

## Canonical Commands

- OpenClaw operations: `coo openclaw -- <args>`
- Shell/process operations: `coo run -- <command>`

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

HTTP mode setup (when provisioning is approved):

1. Create Slack app and copy Signing Secret + Bot Token.
2. Configure `channels.slack.mode="http"` and `channels.slack.webhookPath="/slack/events"`.
3. Set Slack Event Subscriptions, Interactivity, and Slash Command Request URL to `/slack/events`.
4. Keep channel disabled until tokens are injected and validated.

## Safety Invariants

- Default receipt generation must not write to repo paths.
- Ledger and receipts must remain redacted-safe.
- Leak scan must pass for runtime receipt + runtime ledger entry.
- Verify is fail-closed on security audit, sandbox invariants, and policy assertion.
- Receipts include a non-deep memory status capture; they do not run memory index by default.
- Receipts include memory policy guard summary status (`memory_policy_ok`, violation count).
- Receipts include recall trace metadata (`recall_trace_enabled`, `last_recall`).
- Receipts include a non-deep channels status capture and never include Slack secrets.
```
