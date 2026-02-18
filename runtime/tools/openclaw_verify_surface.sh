#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CFG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$STATE_DIR/verify/$TS_UTC"
VERIFY_CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_CMD_TIMEOUT_SEC:-6}"
SECURITY_FALLBACK_TIMEOUT_SEC="${OPENCLAW_SECURITY_FALLBACK_TIMEOUT_SEC:-14}"
RECEIPT_CMD_TIMEOUT_SEC="${OPENCLAW_RECEIPT_CMD_TIMEOUT_SEC:-1}"
KNOWN_UV_IFADDR='uv_interface_addresses returned Unknown system error 1'
GATE_STATUS_PATH="${OPENCLAW_GATE_STATUS_PATH:-$STATE_DIR/runtime/gates/gate_status.json}"

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

if ! mkdir -p "$(dirname "$GATE_STATUS_PATH")" 2>/dev/null; then
  GATE_STATUS_PATH="/tmp/openclaw-runtime/gates/gate_status.json"
  mkdir -p "$(dirname "$GATE_STATUS_PATH")"
fi

PASS=1
WARNINGS=0
declare -A CMD_RC
SECURITY_AUDIT_MODE="unknown"
CONFINEMENT_FLAG=""
declare -a BLOCKING_REASONS=()

add_blocking_reason() {
  local reason="$1"
  BLOCKING_REASONS+=("$reason")
  PASS=0
}

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
      SECURITY_AUDIT_MODE="blocked_fallback_failed"
      add_blocking_reason "security_audit_fallback_failed"
    fi
  else
    SECURITY_AUDIT_MODE="blocked_unknown_deep_error"
    add_blocking_reason "security_audit_deep_failed"
  fi
fi

to_file cron_delivery_guard python3 runtime/tools/openclaw_cron_delivery_guard.py --json
to_file models_status_probe coo openclaw -- models status
to_file sandbox_explain_json coo openclaw -- sandbox explain --json
to_file gateway_probe_json coo openclaw -- gateway probe --json
to_file policy_assert python3 runtime/tools/openclaw_policy_assert.py --json
to_file model_ladder_policy_assert python3 runtime/tools/openclaw_model_policy_assert.py --json
to_file multiuser_posture_assert python3 runtime/tools/openclaw_multiuser_posture_assert.py --json
to_file interfaces_policy_assert python3 runtime/tools/openclaw_interfaces_policy_assert.py --json

SECURITY_FILE="$OUT_DIR/security_audit_deep.txt"
if [ "$SECURITY_AUDIT_MODE" = "non_deep_fallback_due_uv_interface_addresses" ]; then
  SECURITY_FILE="$OUT_DIR/security_audit_fallback.txt"
fi

if [ ! -f "$SECURITY_FILE" ]; then
  add_blocking_reason "security_audit_output_missing"
elif ! rg -q 'Summary:\s*0 critical\s*·\s*0 warn' "$SECURITY_FILE"; then
  add_blocking_reason "security_audit_summary_not_clean"
fi

if [ "${CMD_RC[cron_delivery_guard]:-1}" -ne 0 ]; then add_blocking_reason "cron_delivery_guard_failed"; fi
if [ "${CMD_RC[sandbox_explain_json]:-1}" -ne 0 ]; then add_blocking_reason "sandbox_explain_failed"; fi
if [ "${CMD_RC[gateway_probe_json]:-1}" -ne 0 ]; then add_blocking_reason "gateway_probe_failed"; fi
if [ "${CMD_RC[policy_assert]:-1}" -ne 0 ]; then add_blocking_reason "policy_assert_failed"; fi
if [ "${CMD_RC[model_ladder_policy_assert]:-1}" -ne 0 ]; then add_blocking_reason "model_ladder_policy_failed"; fi
if [ "${CMD_RC[multiuser_posture_assert]:-1}" -ne 0 ]; then add_blocking_reason "multiuser_posture_failed"; fi
if [ "${CMD_RC[interfaces_policy_assert]:-1}" -ne 0 ]; then add_blocking_reason "interfaces_policy_failed"; fi

if ! rg -q '"mode":\s*"non-main"' "$OUT_DIR/sandbox_explain_json.txt"; then
  add_blocking_reason "sandbox_mode_not_non_main"
fi
if rg -q '"elevated":\s*\{[^}]*"enabled":\s*true' "$OUT_DIR/sandbox_explain_json.txt"; then
  add_blocking_reason "sandbox_elevated_enabled"
fi

receipt_gen="$OUT_DIR/receipt_generation.txt"
set +e
OPENCLAW_CMD_TIMEOUT_SEC="$RECEIPT_CMD_TIMEOUT_SEC" \
OPENCLAW_SECURITY_AUDIT_MODE="$SECURITY_AUDIT_MODE" \
OPENCLAW_CONFINEMENT_FLAG="$CONFINEMENT_FLAG" \
runtime/tools/openclaw_receipts_bundle.sh > "$receipt_gen" 2>&1
rc_receipt=$?
set -e
if [ "$rc_receipt" -ne 0 ]; then
  add_blocking_reason "receipt_generation_failed"
fi

runtime_receipt="$(sed -n '1p' "$receipt_gen" | tr -d '\r')"
runtime_manifest="$(sed -n '2p' "$receipt_gen" | tr -d '\r')"
runtime_ledger_entry="$(sed -n '3p' "$receipt_gen" | tr -d '\r')"
ledger_path="$(sed -n '4p' "$receipt_gen" | tr -d '\r')"

leak_out="$OUT_DIR/leak_scan_output.txt"
set +e
runtime/tools/openclaw_leak_scan.sh "$runtime_receipt" "$runtime_ledger_entry" > "$leak_out" 2>&1
rc_leak=$?
set -e
if [ "$rc_leak" -ne 0 ]; then
  add_blocking_reason "leak_scan_failed"
fi

policy_fingerprint="missing_config"
if [ -f "$CFG_PATH" ]; then
  policy_fingerprint="$(sha256sum "$CFG_PATH" | awk '{print $1}')"
fi

{
  echo "ts_utc=$TS_UTC"
  echo "verify_out_dir=$OUT_DIR"
  echo "gate_status_path=$GATE_STATUS_PATH"
  echo "runtime_receipt=$runtime_receipt"
  echo "runtime_manifest=$runtime_manifest"
  echo "runtime_ledger_entry=$runtime_ledger_entry"
  echo "ledger_path=$ledger_path"
  echo "receipt_generation_exit=$rc_receipt"
  echo "leak_scan_exit=$rc_leak"
  echo "security_audit_mode=$SECURITY_AUDIT_MODE"
  echo "security_audit_deep_exit=${CMD_RC[security_audit_deep]:-1}"
  echo "security_audit_fallback_exit=${CMD_RC[security_audit_fallback]:-NA}"
  echo "cron_delivery_guard_exit=${CMD_RC[cron_delivery_guard]:-1}"
  echo "models_status_probe_exit=${CMD_RC[models_status_probe]:-1}"
  echo "sandbox_explain_json_exit=${CMD_RC[sandbox_explain_json]:-1}"
  echo "gateway_probe_json_exit=${CMD_RC[gateway_probe_json]:-1}"
  echo "policy_assert_exit=${CMD_RC[policy_assert]:-1}"
  echo "model_ladder_policy_assert_exit=${CMD_RC[model_ladder_policy_assert]:-1}"
  echo "multiuser_posture_assert_exit=${CMD_RC[multiuser_posture_assert]:-1}"
  echo "interfaces_policy_assert_exit=${CMD_RC[interfaces_policy_assert]:-1}"
  echo "warnings_present=$WARNINGS"
  echo "policy_fingerprint=$policy_fingerprint"
  if [ -n "$CONFINEMENT_FLAG" ]; then
    echo "confinement_detected=true"
    echo "confinement_flag=$CONFINEMENT_FLAG"
  else
    echo "confinement_detected=false"
  fi
} > "$OUT_DIR/summary.txt"

reasons_file="$OUT_DIR/blocking_reasons.txt"
if [ "${#BLOCKING_REASONS[@]}" -gt 0 ]; then
  printf '%s\n' "${BLOCKING_REASONS[@]}" > "$reasons_file"
else
  : > "$reasons_file"
fi

export CHECK_SECURITY_AUDIT_CLEAN="$([ "$SECURITY_AUDIT_MODE" != "blocked_fallback_failed" ] && [ "$SECURITY_AUDIT_MODE" != "blocked_unknown_deep_error" ] && [ -f "$SECURITY_FILE" ] && rg -q 'Summary:\s*0 critical\s*·\s*0 warn' "$SECURITY_FILE" && echo true || echo false)"
export CHECK_CRON_DELIVERY_GUARD="$([ "${CMD_RC[cron_delivery_guard]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_MODELS_STATUS_PROBE="$([ "${CMD_RC[models_status_probe]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_SANDBOX_EXPLAIN="$([ "${CMD_RC[sandbox_explain_json]:-1}" -eq 0 ] && rg -q '"mode":\s*"non-main"' "$OUT_DIR/sandbox_explain_json.txt" && ! rg -q '"elevated":\s*\{[^}]*"enabled":\s*true' "$OUT_DIR/sandbox_explain_json.txt" && echo true || echo false)"
export CHECK_GATEWAY_PROBE="$([ "${CMD_RC[gateway_probe_json]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_POLICY_ASSERT="$([ "${CMD_RC[policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_MODEL_LADDER_POLICY="$([ "${CMD_RC[model_ladder_policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_MULTIUSER_POSTURE="$([ "${CMD_RC[multiuser_posture_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_INTERFACES_POLICY="$([ "${CMD_RC[interfaces_policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_RECEIPT_GENERATION="$([ "$rc_receipt" -eq 0 ] && echo true || echo false)"
export CHECK_LEAK_SCAN="$([ "$rc_leak" -eq 0 ] && echo true || echo false)"

python3 - <<'PY' "$GATE_STATUS_PATH" "$TS_UTC" "$policy_fingerprint" "$SECURITY_AUDIT_MODE" "$CONFINEMENT_FLAG" "$OUT_DIR" "$reasons_file"
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

gate_status_path = Path(sys.argv[1])
ts_utc = sys.argv[2]
policy_fingerprint = sys.argv[3]
security_audit_mode = sys.argv[4]
confinement_flag = sys.argv[5]
out_dir = Path(sys.argv[6])
reasons_file = Path(sys.argv[7])

def env_bool(key: str) -> bool:
    return str(os.environ.get(key, "")).strip().lower() == "true"

def first_line(path: Path) -> str:
    if not path.exists():
        return "output_missing"
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not text:
        return "empty_output"
    return text[0][:260]

checks: List[Dict[str, Any]] = [
    {"name": "security_audit_clean", "pass": env_bool("CHECK_SECURITY_AUDIT_CLEAN"), "mode": security_audit_mode, "detail": first_line(out_dir / "security_audit_deep.txt")},
    {"name": "cron_delivery_guard", "pass": env_bool("CHECK_CRON_DELIVERY_GUARD"), "mode": "required", "detail": first_line(out_dir / "cron_delivery_guard.txt")},
    {"name": "models_status_probe", "pass": env_bool("CHECK_MODELS_STATUS_PROBE"), "mode": "required", "detail": first_line(out_dir / "models_status_probe.txt")},
    {"name": "sandbox_explain", "pass": env_bool("CHECK_SANDBOX_EXPLAIN"), "mode": "required", "detail": first_line(out_dir / "sandbox_explain_json.txt")},
    {"name": "gateway_probe", "pass": env_bool("CHECK_GATEWAY_PROBE"), "mode": "required", "detail": first_line(out_dir / "gateway_probe_json.txt")},
    {"name": "policy_assert", "pass": env_bool("CHECK_POLICY_ASSERT"), "mode": "required", "detail": first_line(out_dir / "policy_assert.txt")},
    {"name": "model_ladder_policy_assert", "pass": env_bool("CHECK_MODEL_LADDER_POLICY"), "mode": "required", "detail": first_line(out_dir / "model_ladder_policy_assert.txt")},
    {"name": "multiuser_posture_assert", "pass": env_bool("CHECK_MULTIUSER_POSTURE"), "mode": "required", "detail": first_line(out_dir / "multiuser_posture_assert.txt")},
    {"name": "interfaces_policy_assert", "pass": env_bool("CHECK_INTERFACES_POLICY"), "mode": "required", "detail": first_line(out_dir / "interfaces_policy_assert.txt")},
    {"name": "receipt_generation", "pass": env_bool("CHECK_RECEIPT_GENERATION"), "mode": "required", "detail": first_line(out_dir / "receipt_generation.txt")},
    {"name": "leak_scan", "pass": env_bool("CHECK_LEAK_SCAN"), "mode": "required", "detail": first_line(out_dir / "leak_scan_output.txt")},
]

blocking_reasons: List[str] = []
if reasons_file.exists():
    blocking_reasons = [line.strip() for line in reasons_file.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]

payload: Dict[str, Any] = {
    "ts_utc": ts_utc,
    "pass": all(bool(item.get("pass")) for item in checks) and not blocking_reasons,
    "blocking_reasons": blocking_reasons,
    "checks": checks,
    "security_audit_mode": security_audit_mode,
    "confinement_detected": bool(confinement_flag),
    "policy_fingerprint": policy_fingerprint,
}
if confinement_flag:
    payload["confinement_flag"] = confinement_flag

gate_status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
PY

if [ "$PASS" -eq 1 ]; then
  if [ "$WARNINGS" -eq 1 ]; then
    if [ -n "$CONFINEMENT_FLAG" ]; then
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=true confinement_flag=$CONFINEMENT_FLAG notes=command_warnings_present gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    else
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=false notes=command_warnings_present gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    fi
  else
    if [ -n "$CONFINEMENT_FLAG" ]; then
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=true confinement_flag=$CONFINEMENT_FLAG gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    else
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=false gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    fi
  fi
  exit 0
fi

if [ -n "$CONFINEMENT_FLAG" ]; then
  echo "FAIL security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=true confinement_flag=$CONFINEMENT_FLAG gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
else
  echo "FAIL security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=false gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
fi
exit 1
