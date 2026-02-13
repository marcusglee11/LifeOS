#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
RUNTIME_DIR="$STATE_DIR/runtime"
PIDFILE="$RUNTIME_DIR/openclaw-gateway.pid"

activate_fallback_runtime_dir() {
  RUNTIME_DIR="/tmp/openclaw-runtime"
  mkdir -p "$RUNTIME_DIR"
  PIDFILE="$RUNTIME_DIR/openclaw-gateway.pid"
}

if ! mkdir -p "$RUNTIME_DIR" 2>/dev/null; then
  activate_fallback_runtime_dir
else
  probe="$(mktemp "$RUNTIME_DIR/.write-probe.XXXXXX" 2>/dev/null || true)"
  if [ -z "$probe" ]; then
    activate_fallback_runtime_dir
  else
    rm -f "$probe"
  fi
fi

stopped=false

if command -v tmux >/dev/null 2>&1; then
  if tmux has-session -t openclaw-gateway >/dev/null 2>&1; then
    tmux kill-session -t openclaw-gateway >/dev/null 2>&1 || true
    stopped=true
  fi
fi

if [ -f "$PIDFILE" ]; then
  pid="$(sed -n '1p' "$PIDFILE" | tr -d '[:space:]')"
  if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    stopped=true
  fi
  rm -f "$PIDFILE"
fi

if [ "$stopped" = true ]; then
  echo "GATEWAY_STOP=local_process_stopped"
else
  echo "GATEWAY_STOP=no_local_gateway_process"
fi
