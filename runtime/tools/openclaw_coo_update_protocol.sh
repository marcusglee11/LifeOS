#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

OPENCLAW_BIN="${OPENCLAW_BIN:-}"
BRANCH_PREFIX="${OPENCLAW_UPDATE_BRANCH_PREFIX:-build/openclaw-update-}"
ACTIVE_WORK_FILE="${OPENCLAW_ACTIVE_WORK_FILE:-.context/active_work.yaml}"
OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
PROMOTION_ATTESTATION_TTL_SEC="${OPENCLAW_PROMOTION_ATTESTATION_TTL_SEC:-600}"

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
  runtime/tools/openclaw_coo_update_protocol.sh promotion-seq-allocate --instance <id>
  runtime/tools/openclaw_coo_update_protocol.sh promotion-verify --packet-dir <dir>
  runtime/tools/openclaw_coo_update_protocol.sh promotion-run --packet-dir <dir> [--base-ref <ref>] [--force]
  runtime/tools/openclaw_coo_update_protocol.sh promotion-record --packet-dir <dir>

Commands:
  preflight          Mandatory baseline: state, git status, runtime tests.
  concurrency-check  Single-writer guard for build/openclaw-update-* branches.
  operational-check  Manual operator visibility checks for models/providers.
  escalation-check   Runs mission-mode extra checks when trigger files changed.
  preclose           Runs closure gate (must pass before merge/push).
  postmerge          Post-merge verification on main.
  all-preclose       Runs preflight -> concurrency -> operational -> escalation -> preclose.
  promotion-seq-allocate  Allocates monotonic promotion sequence ticket (COO issuer only).
  promotion-verify   Verifies packet structure, sequence and trust checks (read-only).
  promotion-run      Records a completed upgrade via the mutating promotion entrypoint with preclose attestation.
  promotion-record   Writes non-authoritative promotion evidence mirror.
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

_ensure_packet_dir() {
  local packet_dir="$1"
  if [ -z "$packet_dir" ]; then
    echo "ERROR: --packet-dir is required." >&2
    return 2
  fi
  if [ ! -d "$packet_dir" ]; then
    echo "ERROR: packet dir not found: $packet_dir" >&2
    return 2
  fi
}

run_promotion_seq_allocate() {
  local instance_id="$1"
  if [ -z "$instance_id" ]; then
    echo "ERROR: --instance is required for promotion-seq-allocate." >&2
    return 2
  fi
  python3 runtime/tools/openclaw_promotion_state.py seq-allocate --instance "$instance_id"
}

run_promotion_verify() {
  local packet_dir="$1"
  _ensure_packet_dir "$packet_dir"
  python3 runtime/tools/openclaw_promotion_state.py verify --packet-dir "$packet_dir"
}

run_promotion_apply_internal() {
  local packet_dir="$1"
  local attestation_path="$2"
  if [ "${OPENCLAW_ORCHESTRATED_MODE:-0}" != "1" ]; then
    echo "FAIL promotion_apply_requires_orchestration=true reason=orchestrated_mode_missing" >&2
    return 1
  fi
  if [ ! -f "$attestation_path" ]; then
    echo "FAIL promotion_apply_requires_orchestration=true reason=attestation_missing" >&2
    return 1
  fi
  python3 runtime/tools/openclaw_promotion_state.py apply --packet-dir "$packet_dir" --attestation "$attestation_path"
}

run_promotion_run() {
  local packet_dir="$1"
  _ensure_packet_dir "$packet_dir"

  echo "NOTE: promotion-run does not install OpenClaw." >&2
  echo "NOTE: Install the target package first and ensure 'openclaw --version' matches promotion_packet.json target_version." >&2

  run_preflight
  run_concurrency_check
  run_operational_check
  run_escalation_check "$base_ref" "$force"
  run_preclose

  local attest_dir attestation_path
  attest_dir="$OPENCLAW_STATE_DIR/runtime/parity/attestations"
  mkdir -p "$attest_dir"
  attestation_path="$attest_dir/preclose_attestation_$(date -u +%Y%m%dT%H%M%SZ).json"
  python3 - <<'PY' "$attestation_path" "$PROMOTION_ATTESTATION_TTL_SEC" "$base_ref"
import json
import os
import sys
import time
from pathlib import Path

out = Path(sys.argv[1])
ttl_sec = int(sys.argv[2])
base_ref = str(sys.argv[3])
issued = int(time.time())
payload = {
    "attestation_type": "preclose",
    "issued_unix": issued,
    "expires_unix": issued + ttl_sec,
    "base_ref": base_ref,
    "head_sha": os.popen("git rev-parse HEAD").read().strip(),
    "generated_by": "openclaw_coo_update_protocol.sh",
}
out.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
PY

  export OPENCLAW_ORCHESTRATED_MODE=1
  run_promotion_apply_internal "$packet_dir" "$attestation_path"
  python3 runtime/tools/openclaw_promotion_state.py record --packet-dir "$packet_dir" --attestation "$attestation_path"
}

run_promotion_record() {
  local packet_dir="$1"
  _ensure_packet_dir "$packet_dir"
  python3 runtime/tools/openclaw_promotion_state.py record --packet-dir "$packet_dir"
}

cmd="${1:-}"
if [ -z "$cmd" ]; then
  usage
  exit 2
fi
shift || true

base_ref_override=""
force="0"
packet_dir=""
instance_id=""
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
    --packet-dir)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --packet-dir requires a value." >&2
        exit 2
      fi
      packet_dir="$2"
      shift 2
      ;;
    --instance)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --instance requires a value." >&2
        exit 2
      fi
      instance_id="$2"
      shift 2
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
  promotion-seq-allocate)
    run_promotion_seq_allocate "$instance_id"
    ;;
  promotion-verify)
    run_promotion_verify "$packet_dir"
    ;;
  promotion-run)
    run_promotion_run "$packet_dir"
    ;;
  promotion-record)
    run_promotion_record "$packet_dir"
    ;;
  promotion-apply)
    echo "ERROR: promotion-apply is internal-only. Use promotion-run." >&2
    exit 2
    ;;
  *)
    echo "ERROR: Unknown command: $cmd" >&2
    usage
    exit 2
    ;;
esac
