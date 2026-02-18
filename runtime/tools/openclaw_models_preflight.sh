#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_MODELS_PREFLIGHT_OUT_DIR:-$STATE_DIR/runtime/models_preflight/$TS_UTC}"
LIST_TIMEOUT_SEC="${OPENCLAW_MODELS_LIST_TIMEOUT_SEC:-20}"
PROBE_TIMEOUT_SEC="${OPENCLAW_MODELS_PROBE_TIMEOUT_SEC:-70}"
ENABLE_PROBE="${OPENCLAW_MODELS_PREFLIGHT_ENABLE_PROBE:-0}"
ENFORCEMENT_MODE="${COO_ENFORCEMENT_MODE:-interactive}"

if [ -z "$OPENCLAW_BIN" ] || [ ! -x "$OPENCLAW_BIN" ]; then
  echo "ERROR: OPENCLAW_BIN is not executable." >&2
  exit 127
fi

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-models-preflight/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

models_list_out="$OUT_DIR/models_list.txt"
probe_raw="$OUT_DIR/models_probe_raw.txt"
probe_sanitized="$OUT_DIR/models_probe_sanitized.txt"
policy_json="$OUT_DIR/model_policy_assert.json"
summary_out="$OUT_DIR/summary.txt"

gateway_reachable=false
if python3 - <<'PY' "$PORT"
import socket,sys
port=int(sys.argv[1])
s=socket.socket()
s.settimeout(0.75)
try:
    s.connect(("127.0.0.1", port))
except Exception:
    raise SystemExit(1)
finally:
    s.close()
PY
then
  gateway_reachable=true
fi

set +e
timeout "$LIST_TIMEOUT_SEC" "$OPENCLAW_BIN" models list > "$models_list_out" 2>&1
rc_list=$?
if [ "$ENABLE_PROBE" = "1" ]; then
  timeout "$PROBE_TIMEOUT_SEC" "$OPENCLAW_BIN" models status --probe > "$probe_raw" 2>&1
  probe_mode="probe"
else
  timeout "$PROBE_TIMEOUT_SEC" "$OPENCLAW_BIN" models status > "$probe_raw" 2>&1
  probe_mode="status"
fi
rc_probe=$?
set -e

python3 - <<'PY' "$probe_raw" "$probe_sanitized"
import re,sys
inp=open(sys.argv[1],encoding='utf-8',errors='replace').read()
text=inp
text=re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}','[REDACTED_EMAIL]',text)
text=re.sub(r'Authorization\s*:\s*Bearer\s+\S+','Authorization: Bearer [REDACTED]',text,flags=re.I)
text=re.sub(r'\bxapp-[A-Za-z0-9-]{6,}\b','xapp-[REDACTED]',text)
text=re.sub(r'\bxox[aboprs]-[A-Za-z0-9-]{6,}\b','xox?-[REDACTED]',text)
text=re.sub(r'\bsk-[A-Za-z0-9_-]{8,}\b','sk-[REDACTED]',text)
text=re.sub(r'\bsk-ant-[A-Za-z0-9_-]{8,}\b','sk-ant-[REDACTED]',text)
text=re.sub(r'\bgh[opurs]_[A-Za-z0-9]{12,}\b','gh*_[REDACTED]',text)
text=re.sub(r'\bAIza[0-9A-Za-z_-]{10,}\b','AIza[REDACTED]',text)
text=re.sub(r'\bya29\.[0-9A-Za-z._-]{12,}\b','ya29.[REDACTED]',text)
text=re.sub(r'[A-Za-z0-9+/_=-]{80,}','[REDACTED_LONG]',text)
open(sys.argv[2],'w',encoding='utf-8').write(text)
PY

set +e
python3 runtime/tools/openclaw_model_policy_assert.py --models-list-file "$models_list_out" --json > "$policy_json"
rc_policy=$?
set -e

policy_ok="$(python3 - <<'PY' "$policy_json"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    print("true" if obj.get("policy_ok") else "false")
except Exception:
    print("false")
PY
)"
missing_auth_agents="$(python3 - <<'PY' "$policy_json"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    names=[]
    for aid in ("main","quick","think"):
        ladder=(obj.get("ladders") or {}).get(aid) or {}
        if ladder.get("top_rung_auth_missing") is True:
            names.append(aid)
    print(",".join(names))
except Exception:
    print("main,quick,think")
PY
)"
working_ok="$(python3 - <<'PY' "$policy_json"
import json,sys
ok=True
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    for aid in ("main","quick","think"):
        ladder=(obj.get("ladders") or {}).get(aid) or {}
        if int(ladder.get("working_count") or 0) < 1:
            ok=False
except Exception:
    ok=False
print("true" if ok else "false")
PY
)"
providers_referenced="$(python3 - <<'PY' "$policy_json"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    p=[str(x) for x in (obj.get("providers_referenced") or []) if str(x)]
    print(",".join(sorted(p)))
except Exception:
    print("")
PY
)"

pass=true
reason=""
degraded_reason=""
if [ "$gateway_reachable" != "true" ]; then
  pass=false
  reason="gateway_unreachable"
elif [ "$policy_ok" != "true" ] || [ "$rc_policy" -ne 0 ]; then
  pass=false
  reason="policy_violated"
elif [ "$working_ok" != "true" ]; then
  pass=false
  reason="no_working_model_for_agent"
elif [ -n "$missing_auth_agents" ]; then
  degraded_reason="top_rung_auth_missing"
fi

{
  echo "ts_utc=$TS_UTC"
  echo "gateway_reachable=$gateway_reachable"
  echo "policy_ok=$policy_ok"
  echo "working_ok=$working_ok"
  echo "missing_auth_agents=$missing_auth_agents"
  echo "providers_referenced=$providers_referenced"
  echo "rc_list=$rc_list"
  echo "rc_probe=$rc_probe"
  echo "probe_mode=$probe_mode"
  echo "rc_policy=$rc_policy"
  echo "degraded_reason=$degraded_reason"
  echo "models_list_out=$models_list_out"
  echo "models_probe_sanitized=$probe_sanitized"
  echo "policy_json=$policy_json"
} > "$summary_out"

if [ "$pass" = true ]; then
  if [ -n "$degraded_reason" ]; then
    echo "PASS models_preflight=true reason=$degraded_reason degraded=true summary=$summary_out"
    if [ "$degraded_reason" = "top_rung_auth_missing" ]; then
      echo "WARN: Top rung auth missing for agents=$missing_auth_agents; fallback routing remains available." >&2
      echo "NEXT: Re-auth top provider(s) to restore preferred routing order." >&2
    fi
  else
    echo "PASS models_preflight=true reason=ok summary=$summary_out"
  fi
  exit 0
fi

# Enforcement mode: interactive = warn and continue, mission = block
if [ "$ENFORCEMENT_MODE" = "interactive" ]; then
  echo "WARNING models_preflight=false reason=$reason summary=$summary_out enforcement_mode=interactive" >&2
  echo "WARNING: Model ladder preflight failed, but continuing in interactive mode." >&2
  if [ "$reason" = "policy_violated" ]; then
    echo "NEXT: Fix ladder ordering/fallback policy in $OPENCLAW_CONFIG_PATH" >&2
    echo "NEXT: Run 'coo models status' to see details." >&2
    echo "NEXT: Run 'coo models fix' for guided repair." >&2
    python3 - <<'PY' "$policy_json" >&2
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    for v in obj.get("violations") or []:
        print(f"- {v}")
except Exception:
    print("- Unable to parse policy violation details.")
PY
  elif [ "$reason" = "no_working_model_for_agent" ]; then
    echo "NEXT: Verify provider auth and model availability; ensure at least one working model per agent." >&2
  elif [ "$reason" = "gateway_unreachable" ]; then
    echo "NEXT: Check OpenClaw gateway is running or start it with 'coo start'" >&2
  fi
  exit 0
fi

# Mission mode: fail-closed
echo "FAIL models_preflight=false reason=$reason summary=$summary_out enforcement_mode=mission" >&2
if [ "$reason" = "policy_violated" ]; then
  echo "NEXT: Fix ladder ordering/fallback policy in $OPENCLAW_CONFIG_PATH and re-run preflight." >&2
  python3 - <<'PY' "$policy_json" >&2
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    for v in obj.get("violations") or []:
        print(f"- {v}")
except Exception:
    print("- Unable to parse policy violation details.")
PY
elif [ "$reason" = "no_working_model_for_agent" ]; then
  echo "NEXT: Verify provider auth and model availability; ensure at least one working model per agent." >&2
fi
exit 1
