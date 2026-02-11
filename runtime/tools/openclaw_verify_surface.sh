#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$STATE_DIR/verify/$TS_UTC"
VERIFY_CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_CMD_TIMEOUT_SEC:-6}"
SECURITY_FALLBACK_TIMEOUT_SEC="${OPENCLAW_SECURITY_FALLBACK_TIMEOUT_SEC:-14}"
RECEIPT_CMD_TIMEOUT_SEC="${OPENCLAW_RECEIPT_CMD_TIMEOUT_SEC:-1}"
KNOWN_UV_IFADDR='uv_interface_addresses returned Unknown system error 1'

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

PASS=1
WARNINGS=0
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
  if [ "$rc" -ne 0 ]; then
    WARNINGS=1
  fi
}

to_file() {
  local name="$1"
  shift
  to_file_with_timeout "$VERIFY_CMD_TIMEOUT_SEC" "$name" "$@"
}

# Required order with signature-gated fallback.
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

to_file models_status_probe coo openclaw -- models status --probe
to_file sandbox_explain_json coo openclaw -- sandbox explain --json
to_file gateway_probe_json coo openclaw -- gateway probe --json
to_file policy_assert python3 runtime/tools/openclaw_policy_assert.py --json

SECURITY_FILE="$OUT_DIR/security_audit_deep.txt"
if [ "$SECURITY_AUDIT_MODE" = "non_deep_fallback_due_uv_interface_addresses" ]; then
  SECURITY_FILE="$OUT_DIR/security_audit_fallback.txt"
fi

if [ ! -f "$SECURITY_FILE" ]; then PASS=0; fi
if ! rg -q 'Summary:\s*0 critical\s*·\s*0 warn' "$SECURITY_FILE"; then PASS=0; fi
if [ "${CMD_RC[sandbox_explain_json]:-1}" -ne 0 ]; then PASS=0; fi
if [ "${CMD_RC[policy_assert]:-1}" -ne 0 ]; then PASS=0; fi
if ! rg -q '"mode":\s*"non-main"' "$OUT_DIR/sandbox_explain_json.txt"; then PASS=0; fi
if rg -q '"elevated":\s*\{[^}]*"enabled":\s*true' "$OUT_DIR/sandbox_explain_json.txt"; then PASS=0; fi

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

leak_out="$OUT_DIR/leak_scan_output.txt"
set +e
runtime/tools/openclaw_leak_scan.sh "$runtime_receipt" "$runtime_ledger_entry" > "$leak_out" 2>&1
rc_leak=$?
set -e
if [ "$rc_leak" -ne 0 ]; then PASS=0; fi

{
  echo "ts_utc=$TS_UTC"
  echo "verify_out_dir=$OUT_DIR"
  echo "runtime_receipt=$runtime_receipt"
  echo "runtime_manifest=$runtime_manifest"
  echo "runtime_ledger_entry=$runtime_ledger_entry"
  echo "ledger_path=$ledger_path"
  echo "receipt_generation_exit=$rc_receipt"
  echo "leak_scan_exit=$rc_leak"
  echo "security_audit_mode=$SECURITY_AUDIT_MODE"
  echo "security_audit_deep_exit=${CMD_RC[security_audit_deep]:-1}"
  echo "security_audit_fallback_exit=${CMD_RC[security_audit_fallback]:-NA}"
  echo "models_status_probe_exit=${CMD_RC[models_status_probe]:-1}"
  echo "sandbox_explain_json_exit=${CMD_RC[sandbox_explain_json]:-1}"
  echo "gateway_probe_json_exit=${CMD_RC[gateway_probe_json]:-1}"
  echo "policy_assert_exit=${CMD_RC[policy_assert]:-1}"
  echo "warnings_present=$WARNINGS"
  if [ -n "$CONFINEMENT_FLAG" ]; then
    echo "confinement_detected=true"
    echo "confinement_flag=$CONFINEMENT_FLAG"
  else
    echo "confinement_detected=false"
  fi
} > "$OUT_DIR/summary.txt"

if [ "$PASS" -eq 1 ]; then
  if [ "$WARNINGS" -eq 1 ]; then
    if [ -n "$CONFINEMENT_FLAG" ]; then
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=true confinement_flag=$CONFINEMENT_FLAG notes=command_warnings_present runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    else
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=false notes=command_warnings_present runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    fi
  else
    if [ -n "$CONFINEMENT_FLAG" ]; then
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=true confinement_flag=$CONFINEMENT_FLAG runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    else
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=false runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    fi
  fi
  exit 0
fi

if [ -n "$CONFINEMENT_FLAG" ]; then
  echo "FAIL security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=true confinement_flag=$CONFINEMENT_FLAG runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
else
  echo "FAIL security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=false runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
fi
exit 1
