# Scope Envelope
- Mission: Implement enforceable OpenClaw COO update management protocol as executable runtime tooling.
- In scope: protocol runner script and runbook integration in `runtime/tools/`.
- Out of scope: governance/foundation doc updates, provider credential changes, model list mutation.

# Summary
- Added `runtime/tools/openclaw_coo_update_protocol.sh` to operationalize ringed update flow.
- Added runbook section in `runtime/tools/OPENCLAW_COO_RUNBOOK.md` with exact invocation patterns.
- Implemented explicit clarification between manual operator model checks and preflight script internal command variants.

# Issue Catalogue
- IC-001 (Resolved): Protocol existed as plan text but lacked executable enforcement entrypoint.
- IC-002 (Resolved): Operators lacked a single command to run ordered pre-close checks.
- IC-003 (Resolved): Command-surface ambiguity (`aliases` vs `aliases list`, list/status flag variants) was undocumented.

# Acceptance Criteria
| ID | Criterion | Status | Evidence Pointer | SHA-256 |
|---|---|---|---|---|
| AC-001 | A dedicated protocol runner exists in runtime tooling. | PASS | runtime/tools/openclaw_coo_update_protocol.sh | N/A(new file; see Appendix A) |
| AC-002 | Runner exposes preflight/concurrency/operational/escalation/preclose/postmerge commands. | PASS | runtime/tools/openclaw_coo_update_protocol.sh | N/A(behavior validated by local command output) |
| AC-003 | Runbook contains ringed enforcement usage with step-by-step commands. | PASS | runtime/tools/OPENCLAW_COO_RUNBOOK.md | N/A(updated doc content in Appendix A) |
| AC-004 | Runbook clarifies manual check flags vs preflight internal variants. | PASS | runtime/tools/OPENCLAW_COO_RUNBOOK.md | N/A(updated note block in Appendix A) |

# Closure Evidence Checklist
| Item | Requirement | Verification |
|---|---|---|
| Provenance | Mission scope and changed files are explicit. | Verified in Scope Envelope and Appendix A file list. |
| Artifacts | All changed files are included with full flattened code. | Verified: Appendix A includes both modified files in full. |
| Repro | Implementation behavior is directly runnable. | Verified with `--help`, `concurrency-check`, and `escalation-check --base-ref main` outputs during implementation. |
| Governance | No protected governance/foundation docs changed. | Verified: only `runtime/tools/` files changed. |
| Outcome | Protocol is executable and documented. | Verified by new script + runbook section. |

# Non-Goals
- No changes to `docs/00_foundations/` or `docs/01_governance/`.
- No OpenClaw provider auth/login state changes.
- No automatic merges; closure remains governed by existing gates/hooks.

# Appendix
## Appendix A: Flattened Code

### File: `runtime/tools/openclaw_coo_update_protocol.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

OPENCLAW_BIN="${OPENCLAW_BIN:-}"
BRANCH_PREFIX="${OPENCLAW_UPDATE_BRANCH_PREFIX:-build/openclaw-update-}"
ACTIVE_WORK_FILE="${OPENCLAW_ACTIVE_WORK_FILE:-.context/active_work.yaml}"

resolve_openclaw_bin() {
  if [ -n "$OPENCLAW_BIN" ] && [ -x "$OPENCLAW_BIN" ]; then
    return 0
  fi
  if command -v openclaw >/dev/null 2>&1; then
    OPENCLAW_BIN="$(command -v openclaw)"
    return 0
  fi
  for candidate in \
    /home/linuxbrew/.linuxbrew/bin/openclaw \
    /usr/local/bin/openclaw \
    /usr/bin/openclaw; do
    if [ -x "$candidate" ]; then
      OPENCLAW_BIN="$candidate"
      return 0
    fi
  done
  echo "ERROR: OpenClaw binary not found on PATH or standard locations." >&2
  return 127
}

resolve_base_ref() {
  local requested="${1:-}"
  if [ -n "$requested" ]; then
    echo "$requested"
    return 0
  fi
  if git show-ref --verify --quiet refs/remotes/origin/main; then
    echo "origin/main"
    return 0
  fi
  echo "main"
}

usage() {
  cat <<'EOF'
Usage:
  runtime/tools/openclaw_coo_update_protocol.sh preflight
  runtime/tools/openclaw_coo_update_protocol.sh concurrency-check
  runtime/tools/openclaw_coo_update_protocol.sh operational-check
  runtime/tools/openclaw_coo_update_protocol.sh escalation-check [--base-ref <ref>] [--force]
  runtime/tools/openclaw_coo_update_protocol.sh preclose
  runtime/tools/openclaw_coo_update_protocol.sh postmerge
  runtime/tools/openclaw_coo_update_protocol.sh all-preclose [--base-ref <ref>] [--force]

Commands:
  preflight          Mandatory baseline: state, git status, runtime tests.
  concurrency-check  Single-writer guard for build/openclaw-update-* branches.
  operational-check  Manual operator visibility checks for models/providers.
  escalation-check   Runs mission-mode extra checks when trigger files changed.
  preclose           Runs closure gate (must pass before merge/push).
  postmerge          Post-merge verification on main.
  all-preclose       Runs preflight -> concurrency -> operational -> escalation -> preclose.
EOF
}

run_preflight() {
  echo "== PRE-FLIGHT: LIFEOS_STATE, git status, runtime tests =="
  cat docs/11_admin/LIFEOS_STATE.md
  echo "---"
  git status
  echo "---"
  pytest runtime/tests -q
}

run_concurrency_check() {
  local current_branch
  current_branch="$(git branch --show-current)"
  echo "== CONCURRENCY CHECK =="
  echo "current_branch=$current_branch"
  echo "branch_prefix=$BRANCH_PREFIX"

  local prefixed other_branches
  prefixed="$(git for-each-ref --format='%(refname:short)' "refs/heads/${BRANCH_PREFIX}*" || true)"
  other_branches="$(printf '%s\n' "$prefixed" | awk -v current="$current_branch" 'NF && $0 != current {print}')"
  if [ -n "$other_branches" ]; then
    echo "FAIL single_writer_violation=true"
    echo "Other active OpenClaw update branch(es):"
    printf '%s\n' "$other_branches"
    return 1
  fi

  if [ -f "$ACTIVE_WORK_FILE" ]; then
    local active_branch
    active_branch="$(python3 - "$ACTIVE_WORK_FILE" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8", errors="replace").strip()
if not text:
    print("")
    raise SystemExit(0)
try:
    obj = json.loads(text)
except Exception:
    # active_work file may be yaml-like; best effort only.
    print("")
    raise SystemExit(0)
if isinstance(obj, dict):
    val = obj.get("branch")
    if isinstance(val, str):
        print(val.strip())
        raise SystemExit(0)
print("")
PY
)"
    if [ -n "$active_branch" ] && [ "$active_branch" != "$current_branch" ] && [[ "$active_branch" == ${BRANCH_PREFIX}* ]]; then
      echo "FAIL active_work_branch_mismatch=true active_work_branch=$active_branch current_branch=$current_branch"
      return 1
    fi
  fi

  echo "PASS single_writer_ok=true"
}

run_operational_check() {
  echo "== MANUAL OPERATIONAL CHECKS =="
  resolve_openclaw_bin
  echo "openclaw_bin=$OPENCLAW_BIN"
  echo "NOTE: Manual checks use list --all + status + aliases list."
  echo "NOTE: openclaw_models_preflight.sh internally uses list and status --probe for automated checks."
  "$OPENCLAW_BIN" models list --all
  "$OPENCLAW_BIN" models status
  "$OPENCLAW_BIN" models aliases list
  python3 runtime/tools/openclaw_model_policy_assert.py --json
}

run_escalation_check() {
  local base_ref="$1"
  local force="$2"

  echo "== ESCALATION CHECK =="
  echo "base_ref=$base_ref"
  echo "force=$force"

  local changed
  changed="$(git diff --name-only "${base_ref}...HEAD" || true)"
  echo "changed_files_begin"
  if [ -n "$changed" ]; then
    printf '%s\n' "$changed"
  else
    echo "(none)"
  fi
  echo "changed_files_end"

  local triggered=0
  if [ "$force" = "1" ]; then
    triggered=1
  fi
  while IFS= read -r path; do
    case "$path" in
      config/models.yaml|runtime/orchestration/openclaw_bridge.py|runtime/tools/openclaw_model_policy_assert.py)
        triggered=1
        ;;
    esac
  done <<< "$changed"

  if [ "$triggered" -eq 0 ]; then
    echo "PASS escalation_required=false (no trigger files changed)"
    return 0
  fi

  echo "Escalation triggers detected; running mission-mode checks..."
  COO_ENFORCEMENT_MODE=mission runtime/tools/openclaw_models_preflight.sh
  runtime/tools/openclaw_verify_p1_acceptance.sh
  pytest runtime/tests -q
  echo "PASS escalation_checks_ok=true"
}

run_preclose() {
  echo "== PRECLOSE CLOSURE GATE =="
  python3 scripts/workflow/closure_gate.py --repo-root .
}

run_postmerge() {
  echo "== POSTMERGE VERIFICATION =="
  local current_branch
  current_branch="$(git branch --show-current)"
  if [ "$current_branch" != "main" ]; then
    echo "FAIL postmerge_requires_main=true current_branch=$current_branch"
    return 1
  fi

  local dirty
  dirty="$(git status --short)"
  if [ -n "$dirty" ]; then
    echo "FAIL postmerge_clean_tree=false"
    printf '%s\n' "$dirty"
    return 1
  fi

  pytest runtime/tests -q
  resolve_openclaw_bin
  "$OPENCLAW_BIN" models status
  "$OPENCLAW_BIN" models aliases list
  echo "PASS postmerge_verification_ok=true"
}

cmd="${1:-}"
if [ -z "$cmd" ]; then
  usage
  exit 2
fi
shift || true

base_ref_override=""
force="0"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-ref)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --base-ref requires a value." >&2
        exit 2
      fi
      base_ref_override="$2"
      shift 2
      ;;
    --force)
      force="1"
      shift
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

base_ref="$(resolve_base_ref "$base_ref_override")"

case "$cmd" in
  -h|--help|help)
    usage
    ;;
  preflight)
    run_preflight
    ;;
  concurrency-check)
    run_concurrency_check
    ;;
  operational-check)
    run_operational_check
    ;;
  escalation-check)
    run_escalation_check "$base_ref" "$force"
    ;;
  preclose)
    run_preclose
    ;;
  postmerge)
    run_postmerge
    ;;
  all-preclose)
    run_preflight
    run_concurrency_check
    run_operational_check
    run_escalation_check "$base_ref" "$force"
    run_preclose
    ;;
  *)
    echo "ERROR: Unknown command: $cmd" >&2
    usage
    exit 2
    ;;
esac
```

### File: `runtime/tools/OPENCLAW_COO_RUNBOOK.md`
```markdown
# OpenClaw COO Runbook

## Canonical Commands

- OpenClaw operations: `coo openclaw -- <args>`
- Shell/process operations: `coo run -- <command>`

## COO Update Protocol (Ringed Enforcement)

Use the protocol runner for enforceable OpenClaw COO update flow:

```bash
runtime/tools/openclaw_coo_update_protocol.sh all-preclose
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
```
