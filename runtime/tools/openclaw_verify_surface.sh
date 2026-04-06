#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CFG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$STATE_DIR/verify/$TS_UTC"
VERIFY_CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_CMD_TIMEOUT_SEC:-35}"
CRON_DELIVERY_GUARD_TIMEOUT_SEC="${OPENCLAW_CRON_DELIVERY_GUARD_TIMEOUT_SEC:-40}"
HOST_CRON_PARITY_GUARD_TIMEOUT_SEC="${OPENCLAW_HOST_CRON_PARITY_GUARD_TIMEOUT_SEC:-25}"
SECURITY_FALLBACK_TIMEOUT_SEC="${OPENCLAW_SECURITY_FALLBACK_TIMEOUT_SEC:-20}"
RECEIPT_CMD_TIMEOUT_SEC="${OPENCLAW_RECEIPT_CMD_TIMEOUT_SEC:-1}"
GATEWAY_PROBE_RETRIES="${OPENCLAW_GATEWAY_PROBE_RETRIES:-3}"
GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
HOST_CRON_PARITY_GUARD_REQUIRED="${OPENCLAW_HOST_CRON_PARITY_GUARD_REQUIRED:-1}"
POLICY_PHASE="${OPENCLAW_POLICY_PHASE:-burnin}"
INSTANCE_PROFILE_PATH="${OPENCLAW_INSTANCE_PROFILE_PATH:-config/openclaw/instance_profiles/coo.json}"
GATE_REASON_CATALOG_PATH="${OPENCLAW_GATE_REASON_CATALOG_PATH:-config/openclaw/gate_reason_catalog.json}"
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
AUTH_HEALTH_STATE="unknown"
AUTH_HEALTH_REASON="auth_health_unavailable"
SECURITY_AUDIT_CLEAN="false"
GATEWAY_PROBE_PASS="false"
SANDBOX_POLICY_TARGET="unknown"
SANDBOX_POLICY_ALLOWED_MODES=""
SANDBOX_POLICY_OBSERVED_MODE="unknown"
SANDBOX_POLICY_SESSION_IS_SANDBOXED="false"
SANDBOX_POLICY_ELEVATED_ENABLED="false"
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

port_reachable() {
  python3 - <<'PY' "$GATEWAY_PORT"
import socket
import sys

port = int(sys.argv[1])
s = socket.socket()
s.settimeout(0.75)
try:
    s.connect(("127.0.0.1", port))
except Exception:
    raise SystemExit(1)
finally:
    s.close()
PY
}

# Validate INSTANCE_PROFILE_PATH is within the repo-controlled profile directory (Gov F3 / CWE-15).
# Environment override to an out-of-allowlist path is a hard block.
# Anchor allowlist to SCRIPT_DIR so the check is CWD-independent (Arch C-6).
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PROFILE_ALLOWLIST="$(realpath --canonicalize-missing "${_SCRIPT_DIR}/../../config/openclaw/instance_profiles")"
_PROFILE_RESOLVED="$(realpath --canonicalize-missing "$INSTANCE_PROFILE_PATH" 2>/dev/null || echo "")"
if [[ -z "$_PROFILE_RESOLVED" ]] || [[ "$_PROFILE_RESOLVED" != "$_PROFILE_ALLOWLIST/"* && "$_PROFILE_RESOLVED" != "$_PROFILE_ALLOWLIST" ]]; then
  add_blocking_reason "instance_profile_path_outside_allowlist"
fi

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

to_file_with_timeout "$CRON_DELIVERY_GUARD_TIMEOUT_SEC" cron_delivery_guard python3 runtime/tools/openclaw_cron_delivery_guard.py --json
to_file_with_timeout "$HOST_CRON_PARITY_GUARD_TIMEOUT_SEC" host_cron_parity_guard python3 runtime/tools/openclaw_host_cron_parity_guard.py --instance-profile "$INSTANCE_PROFILE_PATH" --json
to_file models_status_probe coo openclaw -- models status
to_file sandbox_explain_json coo openclaw -- sandbox explain --json
for attempt in $(seq 1 "$GATEWAY_PROBE_RETRIES"); do
  to_file gateway_probe_json coo openclaw -- gateway probe --json
  if [ "${CMD_RC[gateway_probe_json]:-1}" -eq 0 ]; then
    GATEWAY_PROBE_PASS="true"
    break
  fi
  if [ "$attempt" -lt "$GATEWAY_PROBE_RETRIES" ]; then
    sleep 1
  fi
done
if [ "$GATEWAY_PROBE_PASS" != "true" ]; then
  if port_reachable >/dev/null 2>&1 && rg -q "$KNOWN_UV_IFADDR|connect EPERM 127\\.0\\.0\\.1:${GATEWAY_PORT}|gateway closed" "$OUT_DIR/gateway_probe_json.txt"; then
    GATEWAY_PROBE_PASS="true"
    WARNINGS=1
  fi
fi
to_file policy_assert python3 runtime/tools/openclaw_policy_assert.py --config "$CFG_PATH" --policy-phase "$POLICY_PHASE" --json
mlpa_models_list_raw="$OUT_DIR/models_list_raw.txt"
mlpa_policy_json="$OUT_DIR/model_ladder_policy_assert.json"
mlpa_out="$OUT_DIR/model_ladder_policy_assert.txt"
set +e
timeout "$VERIFY_CMD_TIMEOUT_SEC" "${OPENCLAW_BIN:-openclaw}" models list > "$mlpa_models_list_raw" 2>&1
rc_mlpa_models_list=$?
python3 runtime/tools/openclaw_model_policy_assert.py --config "$CFG_PATH" --models-list-file "$mlpa_models_list_raw" --json > "$mlpa_policy_json" 2>/dev/null
rc_mlpa=$?
set -e
CMD_RC["model_ladder_policy_assert"]="$rc_mlpa"
if [ "$rc_mlpa_models_list" -ne 0 ] || [ "$rc_mlpa" -ne 0 ]; then
  WARNINGS=1
fi
python3 - "$mlpa_policy_json" > "$mlpa_out" 2>/dev/null <<'PY' || true
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
except Exception:
    print("policy_ok=unknown")
    print("auth_missing_providers=")
    print("violations_count=0")
    raise SystemExit(0)

violations = data.get("violations") or []
providers = data.get("auth_missing_providers") or []
print(f"policy_ok={'true' if data.get('policy_ok') else 'false'}")
print("auth_missing_providers=" + ",".join(str(item) for item in providers if str(item)))
print(f"violations_count={len(violations)}")
for violation in violations[:10]:
    print(f"- {violation}")
PY
to_file multiuser_posture_assert python3 runtime/tools/openclaw_multiuser_posture_assert.py --config "$CFG_PATH" --json
to_file interfaces_policy_assert python3 runtime/tools/openclaw_interfaces_policy_assert.py --config "$CFG_PATH" --json
to_file sandbox_policy_assert python3 runtime/tools/openclaw_sandbox_policy_assert.py --config "$CFG_PATH" --instance-profile "$INSTANCE_PROFILE_PATH" --sandbox-explain-file "$OUT_DIR/sandbox_explain_json.txt"
# Extract profile_name and target_posture from the active instance profile.
# Output format: "<profile_name>|<target_posture>" — pipe-delimited, single line.
_PROFILE_META="$(python3 - "$INSTANCE_PROFILE_PATH" <<'_PYEOF' 2>/dev/null || true
import sys, json
p = json.load(open(sys.argv[1]))
name = p.get('profile_name', '')
posture = p.get('sandbox_policy', {}).get('target_posture', 'sandboxed')
print(name + '|' + posture)
_PYEOF
)"
PROFILE_NAME="${_PROFILE_META%%|*}"
PROFILE_TARGET_POSTURE="${_PROFILE_META##*|}"
# Validate profile_name is safe before use in shell/Python path construction.
# Empty profile_name is fail-closed for unsandboxed posture (no governance bypass via config-shape drift).
if [ -z "$PROFILE_NAME" ]; then
  if [ "$PROFILE_TARGET_POSTURE" = "unsandboxed" ]; then
    add_blocking_reason "approval_manifest_missing_profile_name_for_unsandboxed_posture"
  fi
  # sandboxed/shared_ingress: no promotion profile active — vacuously OK
elif [[ "$PROFILE_NAME" =~ ^[A-Za-z0-9_-]+$ ]]; then
  to_file approval_manifest_check python3 -m runtime.orchestration.coo.promotion_guard --repo-root "$(pwd)" --profile-name "$PROFILE_NAME" --json
  if [ "${CMD_RC[approval_manifest_check]:-1}" -ne 0 ]; then
    add_blocking_reason "approval_manifest_check_failed"
  fi
else
  add_blocking_reason "approval_manifest_profile_name_invalid_format"
fi

auth_health_raw="$OUT_DIR/auth_health_raw.json"
auth_health_out="$OUT_DIR/auth_health.txt"
set +e
timeout "$VERIFY_CMD_TIMEOUT_SEC" python3 runtime/tools/openclaw_auth_health.py --json > "$auth_health_raw" 2>&1
rc_auth_health=$?
set -e
CMD_RC["auth_health"]="$rc_auth_health"
if [ "$rc_auth_health" -ne 0 ]; then
  WARNINGS=1
fi
{
  echo '```bash'
  printf '%q ' python3 runtime/tools/openclaw_auth_health.py --json
  echo
  echo '```'
  echo '```text'
  cat "$auth_health_raw" 2>/dev/null || true
  echo
  echo "[exit_code]=$rc_auth_health"
  echo '```'
} > "$auth_health_out"

if [ "$rc_auth_health" -eq 0 ] && [ -s "$auth_health_raw" ]; then
  auth_health_parse_out="$(python3 - <<'PY' "$auth_health_raw"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
except Exception:
    print("unknown\tauth_health_parse_failed")
    raise SystemExit(0)

state = str(obj.get("state") or "unknown").strip() or "unknown"
reason = str(obj.get("reason_code") or "auth_health_reason_missing").strip() or "auth_health_reason_missing"
print(f"{state}\t{reason}")
PY
)"
  AUTH_HEALTH_STATE="$(printf '%s' "$auth_health_parse_out" | awk -F'\t' '{print $1}')"
  AUTH_HEALTH_REASON="$(printf '%s' "$auth_health_parse_out" | awk -F'\t' '{print $2}')"
fi

SECURITY_FILE="$OUT_DIR/security_audit_deep.txt"
if [ "$SECURITY_AUDIT_MODE" = "non_deep_fallback_due_uv_interface_addresses" ]; then
  SECURITY_FILE="$OUT_DIR/security_audit_fallback.txt"
fi

if [ ! -f "$SECURITY_FILE" ]; then
  add_blocking_reason "security_audit_output_missing"
else
  allow_multiuser_heuristic=0
  # Accept the shared-ingress heuristic only when explicit posture and
  # interface policy checks already pass. Any other warn remains hard-fail.
  if [ "${CMD_RC[multiuser_posture_assert]:-1}" -eq 0 ] && [ "${CMD_RC[interfaces_policy_assert]:-1}" -eq 0 ]; then
    allow_multiuser_heuristic=1
  fi
  security_audit_eval="$(
    python3 - <<'PY' "$SECURITY_FILE" "$allow_multiuser_heuristic"
import sys

from runtime.tools.openclaw_security_audit_gate import assess_security_audit_file

result = assess_security_audit_file(
    sys.argv[1],
    allow_multiuser_heuristic=sys.argv[2] == "1",
)
print(f"clean={'true' if result.clean else 'false'}")
print("warn_codes=" + ",".join(result.warn_codes))
print("unexpected_warn_codes=" + ",".join(result.unexpected_warn_codes))
PY
)"
  SECURITY_AUDIT_CLEAN="$(printf '%s\n' "$security_audit_eval" | sed -n 's/^clean=//p' | tail -n 1)"
  warn_codes_csv="$(printf '%s\n' "$security_audit_eval" | sed -n 's/^warn_codes=//p' | tail -n 1)"
  if [ "$SECURITY_AUDIT_CLEAN" = "true" ]; then
    if [ -n "$warn_codes_csv" ]; then
      WARNINGS=1
    fi
  else
    add_blocking_reason "security_audit_summary_not_clean"
  fi
fi

# The gateway probe command can be flaky on some hosts even when deep audit is fully clean.
if [ "$GATEWAY_PROBE_PASS" != "true" ] && [ "${CMD_RC[security_audit_deep]:-1}" -eq 0 ] && rg -q 'Summary:\s*0 critical\s*·\s*0 warn' "$OUT_DIR/security_audit_deep.txt"; then
  GATEWAY_PROBE_PASS="true"
  WARNINGS=1
fi

if [ "${CMD_RC[cron_delivery_guard]:-1}" -ne 0 ]; then add_blocking_reason "cron_delivery_guard_failed"; fi
if [ "${CMD_RC[host_cron_parity_guard]:-1}" -ne 0 ]; then
  if [ "$HOST_CRON_PARITY_GUARD_REQUIRED" = "1" ]; then
    add_blocking_reason "host_cron_parity_guard_failed"
  else
    WARNINGS=1
  fi
fi
if [ "${CMD_RC[sandbox_explain_json]:-1}" -ne 0 ]; then add_blocking_reason "sandbox_explain_failed"; fi
if [ "$GATEWAY_PROBE_PASS" != "true" ]; then add_blocking_reason "gateway_probe_failed"; fi
if [ "${CMD_RC[policy_assert]:-1}" -ne 0 ]; then add_blocking_reason "policy_assert_failed"; fi
if [ "${CMD_RC[model_ladder_policy_assert]:-1}" -ne 0 ]; then
  if [ -f "$mlpa_policy_json" ] && [ -f "$mlpa_models_list_raw" ] && python3 -c \
      "import json,re,sys; model_re=re.compile(r'^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)+$', re.IGNORECASE); d=json.load(open(sys.argv[1], encoding='utf-8', errors='replace')); lines=open(sys.argv[2], encoding='utf-8', errors='replace').read().splitlines(); has_rows=any((cols:=line.strip().split()) and len(cols) >= 5 and model_re.match(cols[0]) for line in lines if line.strip() and not line.startswith('Model ') and not line.startswith('rc=') and not line.startswith('BUILD_REPO=')); sys.exit(0 if d.get('auth_missing_providers') and has_rows else 1)" \
      "$mlpa_policy_json" "$mlpa_models_list_raw" 2>/dev/null; then
    add_blocking_reason "model_ladder_auth_failed"
  else
    add_blocking_reason "model_ladder_policy_failed"
  fi
fi
if [ "${CMD_RC[multiuser_posture_assert]:-1}" -ne 0 ]; then add_blocking_reason "multiuser_posture_failed"; fi
if [ "${CMD_RC[interfaces_policy_assert]:-1}" -ne 0 ]; then add_blocking_reason "interfaces_policy_failed"; fi
if [ "${CMD_RC[sandbox_policy_assert]:-1}" -ne 0 ]; then
  violations_csv="$(sed -n 's/^violations=//p' "$OUT_DIR/sandbox_policy_assert.txt" | tail -n 1)"
  if [ -n "$violations_csv" ]; then
    OLD_IFS="$IFS"
    IFS=','
    for reason in $violations_csv; do
      reason="$(printf '%s' "$reason" | tr -d '[:space:]')"
      if [ -n "$reason" ]; then
        add_blocking_reason "$reason"
      fi
    done
    IFS="$OLD_IFS"
  else
    add_blocking_reason "sandbox_explain_parse_failed"
  fi
fi

SANDBOX_POLICY_TARGET="$(sed -n 's/^target_posture=//p' "$OUT_DIR/sandbox_policy_assert.txt" | tail -n 1)"
SANDBOX_POLICY_ALLOWED_MODES="$(sed -n 's/^allowed_modes=//p' "$OUT_DIR/sandbox_policy_assert.txt" | tail -n 1)"
SANDBOX_POLICY_OBSERVED_MODE="$(sed -n 's/^observed_mode=//p' "$OUT_DIR/sandbox_policy_assert.txt" | tail -n 1)"
SANDBOX_POLICY_SESSION_IS_SANDBOXED="$(sed -n 's/^session_is_sandboxed=//p' "$OUT_DIR/sandbox_policy_assert.txt" | tail -n 1)"
SANDBOX_POLICY_ELEVATED_ENABLED="$(sed -n 's/^elevated_enabled=//p' "$OUT_DIR/sandbox_policy_assert.txt" | tail -n 1)"

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
  echo "security_audit_clean=$SECURITY_AUDIT_CLEAN"
  echo "security_audit_deep_exit=${CMD_RC[security_audit_deep]:-1}"
  echo "security_audit_fallback_exit=${CMD_RC[security_audit_fallback]:-NA}"
  echo "cron_delivery_guard_exit=${CMD_RC[cron_delivery_guard]:-1}"
  echo "host_cron_parity_guard_exit=${CMD_RC[host_cron_parity_guard]:-1}"
  echo "host_cron_parity_guard_required=$HOST_CRON_PARITY_GUARD_REQUIRED"
  echo "models_status_probe_exit=${CMD_RC[models_status_probe]:-1}"
  echo "auth_health_exit=${CMD_RC[auth_health]:-1}"
  echo "auth_health_state=$AUTH_HEALTH_STATE"
  echo "auth_health_reason=$AUTH_HEALTH_REASON"
  echo "sandbox_explain_json_exit=${CMD_RC[sandbox_explain_json]:-1}"
  echo "sandbox_policy_assert_exit=${CMD_RC[sandbox_policy_assert]:-1}"
  echo "expected_sandbox_posture=$SANDBOX_POLICY_TARGET"
  echo "allowed_sandbox_modes=$SANDBOX_POLICY_ALLOWED_MODES"
  echo "observed_sandbox_mode=$SANDBOX_POLICY_OBSERVED_MODE"
  echo "sandbox_session_is_sandboxed=$SANDBOX_POLICY_SESSION_IS_SANDBOXED"
  echo "sandbox_elevated_enabled=$SANDBOX_POLICY_ELEVATED_ENABLED"
  echo "gateway_probe_json_exit=${CMD_RC[gateway_probe_json]:-1}"
  echo "gateway_probe_pass=$GATEWAY_PROBE_PASS"
  echo "gateway_probe_retries=$GATEWAY_PROBE_RETRIES"
  echo "policy_assert_exit=${CMD_RC[policy_assert]:-1}"
  echo "policy_phase=$POLICY_PHASE"
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
catalog_json="$(python3 runtime/tools/openclaw_gate_reason_catalog.py --catalog "$GATE_REASON_CATALOG_PATH" --reasons "${BLOCKING_REASONS[@]}" --json 2>/dev/null || true)"
catalog_eval="$(python3 - <<'PY' "$catalog_json"
import json
import sys

raw = str(sys.argv[1] or "").strip()
if not raw:
    print("catalog_ok=false")
    print("unknown_count=0")
    raise SystemExit(0)

try:
    obj = json.loads(raw)
except Exception:
    print("catalog_ok=false")
    print("unknown_count=0")
    raise SystemExit(0)

catalog_ok = bool(obj.get("catalog_ok"))
unknown = obj.get("unknown") or []
if not isinstance(unknown, list):
    unknown = []

print(f"catalog_ok={'true' if catalog_ok else 'false'}")
print(f"unknown_count={len([u for u in unknown if str(u).strip()])}")
PY
)"
catalog_ok="$(printf '%s\n' "$catalog_eval" | sed -n 's/^catalog_ok=//p' | tail -n 1)"
unknown_count="$(printf '%s\n' "$catalog_eval" | sed -n 's/^unknown_count=//p' | tail -n 1)"
if [ "$catalog_ok" != "true" ]; then
  add_blocking_reason "gate_reason_catalog_failed"
fi
if [ "${unknown_count:-0}" -gt 0 ]; then
  add_blocking_reason "gate_reason_unknown"
fi

if [ "${#BLOCKING_REASONS[@]}" -gt 0 ]; then
  printf '%s\n' "${BLOCKING_REASONS[@]}" | awk '!seen[$0]++' > "$reasons_file"
else
  : > "$reasons_file"
fi

export CHECK_SECURITY_AUDIT_CLEAN="$SECURITY_AUDIT_CLEAN"
export CHECK_CRON_DELIVERY_GUARD="$([ "${CMD_RC[cron_delivery_guard]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_HOST_CRON_PARITY_GUARD="$([ "${CMD_RC[host_cron_parity_guard]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_MODELS_STATUS_PROBE="$([ "${CMD_RC[models_status_probe]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_SANDBOX_EXPLAIN="$([ "${CMD_RC[sandbox_policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_GATEWAY_PROBE="$GATEWAY_PROBE_PASS"
export CHECK_POLICY_ASSERT="$([ "${CMD_RC[policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_MODEL_LADDER_POLICY="$([ "${CMD_RC[model_ladder_policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_MULTIUSER_POSTURE="$([ "${CMD_RC[multiuser_posture_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_INTERFACES_POLICY="$([ "${CMD_RC[interfaces_policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_APPROVAL_MANIFEST="$(
  if [ -z "$PROFILE_NAME" ]; then
    # Unsandboxed posture without profile_name is already blocked above; here it's false.
    # Sandboxed/shared_ingress without profile_name: no promotion profile active, vacuously true.
    if [ "$PROFILE_TARGET_POSTURE" = "unsandboxed" ]; then
      echo false
    else
      echo true
    fi
  elif [ "${CMD_RC[approval_manifest_check]:-1}" -eq 0 ]; then
    echo true
  else
    echo false
  fi
)"
export CHECK_RECEIPT_GENERATION="$([ "$rc_receipt" -eq 0 ] && echo true || echo false)"
export CHECK_LEAK_SCAN="$([ "$rc_leak" -eq 0 ] && echo true || echo false)"
export SANDBOX_POLICY_TARGET
export SANDBOX_POLICY_ALLOWED_MODES
export SANDBOX_POLICY_OBSERVED_MODE
export SANDBOX_POLICY_SESSION_IS_SANDBOXED
export SANDBOX_POLICY_ELEVATED_ENABLED

python3 - <<'PY' "$GATE_STATUS_PATH" "$TS_UTC" "$policy_fingerprint" "$SECURITY_AUDIT_MODE" "$CONFINEMENT_FLAG" "$OUT_DIR" "$reasons_file" "$AUTH_HEALTH_STATE" "$AUTH_HEALTH_REASON"
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
auth_health_state = str(sys.argv[8] or "unknown")
auth_health_reason = str(sys.argv[9] or "auth_health_unavailable")

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
    {"name": "host_cron_parity_guard", "pass": env_bool("CHECK_HOST_CRON_PARITY_GUARD"), "mode": "required", "detail": first_line(out_dir / "host_cron_parity_guard.txt")},
    {"name": "models_status_probe", "pass": env_bool("CHECK_MODELS_STATUS_PROBE"), "mode": "required", "detail": first_line(out_dir / "models_status_probe.txt")},
    {"name": "sandbox_explain", "pass": env_bool("CHECK_SANDBOX_EXPLAIN"), "mode": "required", "detail": first_line(out_dir / "sandbox_explain_json.txt")},
    {"name": "gateway_probe", "pass": env_bool("CHECK_GATEWAY_PROBE"), "mode": "required", "detail": first_line(out_dir / "gateway_probe_json.txt")},
    {"name": "policy_assert", "pass": env_bool("CHECK_POLICY_ASSERT"), "mode": "required", "detail": first_line(out_dir / "policy_assert.txt")},
    {"name": "model_ladder_policy_assert", "pass": env_bool("CHECK_MODEL_LADDER_POLICY"), "mode": "required", "detail": first_line(out_dir / "model_ladder_policy_assert.txt")},
    {"name": "multiuser_posture_assert", "pass": env_bool("CHECK_MULTIUSER_POSTURE"), "mode": "required", "detail": first_line(out_dir / "multiuser_posture_assert.txt")},
    {"name": "interfaces_policy_assert", "pass": env_bool("CHECK_INTERFACES_POLICY"), "mode": "required", "detail": first_line(out_dir / "interfaces_policy_assert.txt")},
    {"name": "approval_manifest", "pass": env_bool("CHECK_APPROVAL_MANIFEST"), "mode": "required", "detail": first_line(out_dir / "approval_manifest_check.txt")},
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
    "auth_health_state": auth_health_state,
    "auth_health_reason": auth_health_reason,
    "expected_sandbox_posture": str(os.environ.get("SANDBOX_POLICY_TARGET") or "unknown"),
    "allowed_sandbox_modes": [item for item in str(os.environ.get("SANDBOX_POLICY_ALLOWED_MODES") or "").split(",") if item],
    "observed_sandbox_mode": str(os.environ.get("SANDBOX_POLICY_OBSERVED_MODE") or "unknown"),
    "sandbox_session_is_sandboxed": env_bool("SANDBOX_POLICY_SESSION_IS_SANDBOXED"),
    "sandbox_elevated_enabled": env_bool("SANDBOX_POLICY_ELEVATED_ENABLED"),
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
