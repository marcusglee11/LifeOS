#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CFG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
CHECK_ONLY=0
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
RECEIPT_DIR="$STATE_DIR/runtime"
RECEIPT_PATH="$RECEIPT_DIR/gateway_last_start.json"
PIDFILE="$RECEIPT_DIR/openclaw-gateway.pid"
NOHUP_LOG="$RECEIPT_DIR/openclaw-gateway.nohup.log"
KNOWN_UV_IFADDR='uv_interface_addresses returned Unknown system error 1'

usage() {
  cat <<'USAGE'
Usage:
  runtime/tools/openclaw_gateway_ensure.sh [--check-only]
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$OPENCLAW_BIN" ] || [ ! -x "$OPENCLAW_BIN" ]; then
  echo "ERROR: OPENCLAW_BIN is not executable. Resolve OpenClaw binary first." >&2
  exit 127
fi

if ! mkdir -p "$RECEIPT_DIR" 2>/dev/null; then
  RECEIPT_DIR="/tmp/openclaw-runtime"
  mkdir -p "$RECEIPT_DIR"
  RECEIPT_PATH="$RECEIPT_DIR/gateway_last_start.json"
  PIDFILE="$RECEIPT_DIR/openclaw-gateway.pid"
  NOHUP_LOG="$RECEIPT_DIR/openclaw-gateway.nohup.log"
fi

port_reachable() {
  python3 - <<'PY' "$PORT"
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
s.settimeout(0.75)
try:
    s.connect(("127.0.0.1", port))
except Exception:
    print("false")
    raise SystemExit(1)
print("true")
PY
}

run_probe() {
  local out rc_file rc
  out="$(mktemp)"
  rc_file="${out}.rc"
  (
    set +e
    timeout 10s "$OPENCLAW_BIN" gateway --port "$PORT" probe --json >"$out" 2>&1
    echo "$?" >"$rc_file"
  )
  rc="$(sed -n '1p' "$rc_file" | tr -d '[:space:]')"
  rm -f "$rc_file"
  if [ "$rc" -eq 0 ]; then
    rm -f "$out"
    return 0
  fi
  if rg -q "$KNOWN_UV_IFADDR" "$out"; then
    rm -f "$out"
    return 2
  fi
  rm -f "$out"
  return 1
}

write_receipt() {
  local started_via="$1"
  local reachable="$2"
  python3 - <<'PY' "$RECEIPT_PATH" "$TS_UTC" "$PORT" "$OPENCLAW_BIN" "$CFG_PATH" "$started_via" "$reachable"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "ts_utc": sys.argv[2],
    "port": int(sys.argv[3]),
    "openclaw_bin": sys.argv[4],
    "openclaw_config_path": sys.argv[5],
    "started_via": sys.argv[6],
    "reachable": sys.argv[7].lower() == "true",
}
path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")
PY
}

reachable=false
if run_probe; then
  reachable=true
elif port_reachable >/dev/null 2>&1; then
  reachable=true
fi

if [ "$reachable" = true ]; then
  write_receipt "already_up" "true"
  echo "GATEWAY_STATUS=already_up PORT=$PORT"
  exit 0
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  write_receipt "check_only_unreachable" "false"
  echo "GATEWAY_STATUS=unreachable PORT=$PORT"
  exit 1
fi

started_via="none"

if [ -n "${XDG_RUNTIME_DIR:-}" ] && command -v systemctl >/dev/null 2>&1; then
  set +e
  timeout 20s "$OPENCLAW_BIN" gateway --port "$PORT" start >/dev/null 2>&1
  rc_start=$?
  set -e
  if [ "$rc_start" -eq 0 ]; then
    started_via="systemd_user_best_effort"
  fi
fi

if [ "$started_via" = "none" ]; then
  if command -v tmux >/dev/null 2>&1; then
    if tmux has-session -t openclaw-gateway >/dev/null 2>&1; then
      started_via="tmux_existing"
    else
      set +e
      tmux new-session -d -s openclaw-gateway \
        "OPENCLAW_STATE_DIR='$STATE_DIR' OPENCLAW_CONFIG_PATH='$CFG_PATH' OPENCLAW_GATEWAY_PORT='$PORT' '$OPENCLAW_BIN' gateway run --port '$PORT' --verbose" >/dev/null 2>&1
      rc_tmux_new=$?
      set -e
      if [ "$rc_tmux_new" -eq 0 ]; then
        started_via="tmux_started"
      fi
    fi
  fi
fi

if [ "$started_via" = "none" ]; then
  set +e
  nohup env OPENCLAW_STATE_DIR="$STATE_DIR" OPENCLAW_CONFIG_PATH="$CFG_PATH" OPENCLAW_GATEWAY_PORT="$PORT" \
    "$OPENCLAW_BIN" gateway run --port "$PORT" --verbose >"$NOHUP_LOG" 2>&1 &
  pid=$!
  rc_nohup=$?
  set -e
  if [ "$rc_nohup" -eq 0 ] && [ -n "${pid:-}" ]; then
    printf '%s\n' "$pid" >"$PIDFILE"
    started_via="nohup_started"
  else
    echo "ERROR: unable to start gateway via tmux or nohup." >&2
    write_receipt "start_failed" "false"
    exit 1
  fi
fi

for _ in $(seq 1 20); do
  set +e
  run_probe
  probe_rc=$?
  set -e
  if [ "$probe_rc" -eq 0 ]; then
    write_receipt "$started_via" "true"
    echo "GATEWAY_STATUS=up PORT=$PORT STARTED_VIA=$started_via"
    exit 0
  fi
  if [ "$probe_rc" -eq 2 ] && [ -f "$NOHUP_LOG" ] && rg -q "$KNOWN_UV_IFADDR" "$NOHUP_LOG"; then
    write_receipt "$started_via" "false"
    echo "ERROR: gateway start blocked by environment confinement ($KNOWN_UV_IFADDR)." >&2
    echo "NEXT: run outside restricted sandbox or use a host context where interface enumeration is permitted." >&2
    exit 1
  fi
  if port_reachable >/dev/null 2>&1; then
    write_receipt "$started_via" "true"
    echo "GATEWAY_STATUS=up PORT=$PORT STARTED_VIA=$started_via"
    exit 0
  fi
  sleep 1
done

write_receipt "$started_via" "false"
echo "ERROR: gateway still unreachable after startup attempt (started_via=$started_via port=$PORT)." >&2
exit 1
