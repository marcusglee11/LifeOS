#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_INTERFACES_OUT_DIR:-$STATE_DIR/verify-interfaces/$TS_UTC}"
VERIFY_CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_INTERFACES_TIMEOUT_SEC:-10}"
SECURITY_FALLBACK_TIMEOUT_SEC="${OPENCLAW_VERIFY_INTERFACES_SECURITY_FALLBACK_TIMEOUT_SEC:-14}"
RECEIPT_CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_INTERFACES_RECEIPT_TIMEOUT_SEC:-3}"
KNOWN_UV_IFADDR='uv_interface_addresses returned Unknown system error 1'

mkdir -p "$OUT_DIR"

PASS=1
declare -A CMD_RC
SECURITY_AUDIT_MODE="unknown"
CONFINEMENT_FLAG=""

to_file_with_timeout() {
  local timeout_sec="$1"
  shift
  local name="$1"
  shift
  local out="$OUT_DIR/${name}.txt"
  {
    echo '```bash'
    printf '%q ' "$@"
    echo
    echo '```'
    echo '```text'
    set +e
    timeout "$timeout_sec" "$@"
    rc=$?
    set -e
    echo "[exit_code]=$rc"
    echo '```'
  } > "$out" 2>&1
  CMD_RC["$name"]="$rc"
}

to_file() {
  local name="$1"
  shift
  to_file_with_timeout "$VERIFY_CMD_TIMEOUT_SEC" "$name" "$@"
}

to_file channels_status_json coo openclaw -- channels status --json

to_file security_audit_deep coo openclaw -- security audit --deep
if [ "${CMD_RC[security_audit_deep]:-1}" -eq 0 ]; then
  SECURITY_AUDIT_MODE="deep"
else
  if rg -q "$KNOWN_UV_IFADDR" "$OUT_DIR/security_audit_deep.txt"; then
    to_file_with_timeout "$SECURITY_FALLBACK_TIMEOUT_SEC" security_audit_fallback coo openclaw -- security audit
    if [ "${CMD_RC[security_audit_fallback]:-1}" -eq 0 ]; then
      SECURITY_AUDIT_MODE="non_deep_fallback_due_uv_interface_addresses"
      CONFINEMENT_FLAG="uv_interface_addresses_unknown_system_error_1"
    else
      PASS=0
      SECURITY_AUDIT_MODE="blocked_fallback_failed"
    fi
  else
    PASS=0
    SECURITY_AUDIT_MODE="blocked_unknown_deep_error"
  fi
fi

to_file interfaces_policy_assert python3 runtime/tools/openclaw_interfaces_policy_assert.py --json
if [ "${CMD_RC[interfaces_policy_assert]:-1}" -ne 0 ]; then
  PASS=0
fi

SECURITY_FILE="$OUT_DIR/security_audit_deep.txt"
if [ "$SECURITY_AUDIT_MODE" = "non_deep_fallback_due_uv_interface_addresses" ]; then
  SECURITY_FILE="$OUT_DIR/security_audit_fallback.txt"
fi
if [ ! -f "$SECURITY_FILE" ]; then PASS=0; fi
if ! rg -q 'Summary:\s*0 critical\s*·\s*0 warn' "$SECURITY_FILE"; then PASS=0; fi

reply_mode="unknown"
if [ -f "$OUT_DIR/interfaces_policy_assert.txt" ]; then
  reply_mode="$(python3 - <<'PY' "$OUT_DIR/interfaces_policy_assert.txt"
import json,sys
p=sys.argv[1]
text=open(p,encoding='utf-8',errors='replace').read()
start=text.find('{')
end=text.rfind('}')
if start == -1 or end == -1 or end < start:
    print("unknown")
else:
    try:
        obj=json.loads(text[start:end+1])
        print(((obj.get("telegram") or {}).get("reply_to_mode")) or "unknown")
    except Exception:
        print("unknown")
PY
)"
fi

receipt_gen="$OUT_DIR/receipt_generation.txt"
set +e
OPENCLAW_CMD_TIMEOUT_SEC="$RECEIPT_CMD_TIMEOUT_SEC" \
OPENCLAW_SECURITY_AUDIT_MODE="$SECURITY_AUDIT_MODE" \
OPENCLAW_CONFINEMENT_FLAG="$CONFINEMENT_FLAG" \
runtime/tools/openclaw_receipts_bundle.sh > "$receipt_gen" 2>&1
rc_receipt=$?
set -e
if [ "$rc_receipt" -ne 0 ]; then PASS=0; fi

runtime_receipt="$(sed -n '1p' "$receipt_gen" | tr -d '\r')"
runtime_manifest="$(sed -n '2p' "$receipt_gen" | tr -d '\r')"
runtime_ledger_entry="$(sed -n '3p' "$receipt_gen" | tr -d '\r')"
ledger_path="$(sed -n '4p' "$receipt_gen" | tr -d '\r')"

{
  echo "ts_utc=$TS_UTC"
  echo "verify_out_dir=$OUT_DIR"
  echo "security_audit_mode=$SECURITY_AUDIT_MODE"
  echo "confinement_flag=${CONFINEMENT_FLAG:-}"
  echo "reply_to_mode=$reply_mode"
  echo "receipt_generation_exit=$rc_receipt"
  echo "runtime_receipt=$runtime_receipt"
  echo "runtime_manifest=$runtime_manifest"
  echo "runtime_ledger_entry=$runtime_ledger_entry"
  echo "ledger_path=$ledger_path"
} > "$OUT_DIR/summary.txt"

if [ "$PASS" -eq 1 ]; then
  echo "PASS telegram_posture=allowlist+requireMention replyToMode=$reply_mode security_audit_mode=$SECURITY_AUDIT_MODE runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
  exit 0
fi

echo "FAIL telegram_posture=allowlist+requireMention replyToMode=$reply_mode security_audit_mode=$SECURITY_AUDIT_MODE runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
exit 1
