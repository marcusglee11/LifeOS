#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_MULTIUSER_OUT_DIR:-$STATE_DIR/verify-multiuser/$TS_UTC}"
POSTURE_TIMEOUT_SEC="${OPENCLAW_VERIFY_MULTIUSER_POSTURE_TIMEOUT_SEC:-15}"
INTERFACES_TIMEOUT_SEC="${OPENCLAW_VERIFY_MULTIUSER_INTERFACES_TIMEOUT_SEC:-45}"

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify-multiuser/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

PASS=1
SECURITY_AUDIT_MODE="unknown"

posture_out="$OUT_DIR/multiuser_posture_assert.json"
interfaces_out="$OUT_DIR/verify_interfaces.txt"
summary_out="$OUT_DIR/summary.txt"

set +e
timeout "$POSTURE_TIMEOUT_SEC" python3 runtime/tools/openclaw_multiuser_posture_assert.py --json > "$posture_out" 2>&1
rc_posture=$?
timeout "$INTERFACES_TIMEOUT_SEC" env OPENCLAW_VERIFY_INTERFACES_OUT_DIR="$OUT_DIR/interfaces" runtime/tools/openclaw_verify_interfaces.sh > "$interfaces_out" 2>&1
rc_interfaces=$?
set -e

if [ "$rc_posture" -ne 0 ] || [ "$rc_interfaces" -ne 0 ]; then
  PASS=0
fi

SECURITY_AUDIT_MODE="$(rg -o 'security_audit_mode=[^ ]+' "$interfaces_out" | tail -n1 | cut -d= -f2- || true)"
if [ -z "$SECURITY_AUDIT_MODE" ]; then
  SECURITY_AUDIT_MODE="unknown"
fi
if printf '%s' "$SECURITY_AUDIT_MODE" | rg -q '^blocked_'; then
  PASS=0
fi

enabled_count="$(python3 - <<'PY' "$posture_out"
import json, sys
p=sys.argv[1]
try:
    obj=json.loads(open(p,encoding='utf-8',errors='replace').read())
    print(len(list(obj.get("enabled_channels") or [])))
except Exception:
    print(-1)
PY
)"
allowlist_counts="$(python3 - <<'PY' "$posture_out"
import json, sys
p=sys.argv[1]
try:
    obj=json.loads(open(p,encoding='utf-8',errors='replace').read())
    items=sorted((obj.get("allowlist_sizes") or {}).items())
    print(",".join(f"{k}={int(v)}" for k,v in items))
except Exception:
    print("unknown")
PY
)"
posture_ok="$(python3 - <<'PY' "$posture_out"
import json, sys
p=sys.argv[1]
try:
    obj=json.loads(open(p,encoding='utf-8',errors='replace').read())
    print("true" if obj.get("multiuser_posture_ok") else "false")
except Exception:
    print("false")
PY
)"

runtime_receipt="$(rg -o 'runtime_receipt=[^ ]+' "$interfaces_out" | tail -n1 | cut -d= -f2- || true)"
ledger_path="$(rg -o 'ledger_path=[^ ]+' "$interfaces_out" | tail -n1 | cut -d= -f2- || true)"

{
  echo "ts_utc=$TS_UTC"
  echo "multiuser_posture_ok=$posture_ok"
  echo "enabled_channels_count=$enabled_count"
  echo "allowlist_counts=$allowlist_counts"
  echo "security_audit_mode=$SECURITY_AUDIT_MODE"
  echo "posture_exit=$rc_posture"
  echo "interfaces_exit=$rc_interfaces"
  echo "runtime_receipt=$runtime_receipt"
  echo "ledger_path=$ledger_path"
} > "$summary_out"

if [ "$PASS" -eq 1 ] && [ "$posture_ok" = "true" ]; then
  echo "PASS multiuser_posture_ok=true enabled_channels_count=$enabled_count allowlist_counts=$allowlist_counts runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
  exit 0
fi

echo "FAIL multiuser_posture_ok=$posture_ok enabled_channels_count=$enabled_count allowlist_counts=$allowlist_counts runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
exit 1
