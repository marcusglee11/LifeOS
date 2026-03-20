# Review Packet OpenClaw Gate A-P0.2 v1.0

## Mission
Gate A-P0.2: gateway kill switch + deterministic lifecycle for WSL/no-systemd + receipts.

## Scope Outcome
- Implemented process-managed gateway lifecycle scripts for WSL without systemd user bus.
- Added deterministic panic stop and reversible recovery path.
- Updated runbook and receipts bundle with gateway lifecycle surfaces.

## Evidence Directory
`artifacts/evidence/openclaw/p0_2/20260210T081346Z`

## Key Evidence Files
- `pre_gateway_status_deep_json.md`
- `pre_gateway_probe_json.md`
- `pre_health_json.md`
- `pre_status_all_deep.md`
- `pre_systemctl_user_status.md`
- `pre_gateway_start_attempt.md`
- `pre_gateway_stop_attempt.md`
- `post_start_stop_restart_transcript_v2.md`
- `post_panic_cycle_v2.md`
- `post_gateway_status_deep_json_v2.md`
- `post_gateway_probe_json_v2.md`
- `post_gateway_health_json_v2.md`
- `post_status_all_deep_v2.md`
- `post_security_audit_deep_v2.txt`
- `post_daemon_log_tail_v2.txt`
- `post_receipts_bundle_path.txt`

## Acceptance
- Start/stop/restart cycle completed with expected health transitions.
- Bind remains loopback.
- Security audit remains 0 critical / 0 warn.
- tools.elevated/browser remain disabled.

## Appendix A: Flattened Changed Files

### File: runtime/tools/openclaw_gateway_daemon.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-start}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$HOME/.openclaw/run/gateway.pid"
LOG_FILE="$HOME/.openclaw/logs/gateway-daemon.log"
CFG="$HOME/.openclaw/openclaw.json"

read_cfg() {
  local key="$1" default="$2"
  if [ -f "$CFG" ] && command -v jq >/dev/null 2>&1; then
    jq -r "$key // \"$default\"" "$CFG" 2>/dev/null || echo "$default"
  else
    echo "$default"
  fi
}

PORT="$(read_cfg '.gateway.port' '18789')"
BIND="$(read_cfg '.gateway.bind' 'loopback')"

if [ "$BIND" != "loopback" ]; then
  echo "ERROR: fail-closed refusing gateway start because gateway.bind=$BIND (expected loopback)" >&2
  exit 2
fi

mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"
chmod 700 "$HOME/.openclaw" "$HOME/.openclaw/run" "$HOME/.openclaw/logs" 2>/dev/null || true

is_running_pid() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

listener_pid_on_port() {
  ss -ltnp "sport = :$PORT" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -n1
}

start_gateway() {
  if [ -f "$PID_FILE" ]; then
    existing_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if is_running_pid "$existing_pid"; then
      echo "already_running pid=$existing_pid port=$PORT"
      exit 0
    fi
    rm -f "$PID_FILE"
  fi

  listener_pid="$(listener_pid_on_port || true)"
  if [ -n "$listener_pid" ]; then
    cmdline="$(ps -p "$listener_pid" -o args= 2>/dev/null || true)"
    echo "ERROR: port $PORT already busy by pid=$listener_pid cmd=$cmdline" >&2
    echo "Run runtime/tools/openclaw_gateway_stop.sh first." >&2
    exit 3
  fi

  nohup coo openclaw -- gateway run --bind loopback --port "$PORT" --verbose --ws-log compact \
    >>"$LOG_FILE" 2>&1 &
  new_pid=$!
  echo "$new_pid" > "$PID_FILE"

  ready=0
  for _ in $(seq 1 25); do
    if ! is_running_pid "$new_pid"; then
      break
    fi
    if coo openclaw -- gateway health --json >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 1
  done

  if [ "$ready" -ne 1 ]; then
    echo "ERROR: gateway failed to become healthy; see $LOG_FILE" >&2
    tail -n 40 "$LOG_FILE" >&2 || true
    exit 4
  fi

  echo "started pid=$new_pid port=$PORT bind=loopback"
  echo "pid_file=$PID_FILE"
  echo "log_file=$LOG_FILE"
}

case "$ACTION" in
  start)
    start_gateway
    ;;
  restart)
    "$SCRIPT_DIR/openclaw_gateway_stop.sh"
    start_gateway
    ;;
  *)
    echo "Usage: runtime/tools/openclaw_gateway_daemon.sh [start|restart]" >&2
    exit 2
    ;;
esac
```

### File: runtime/tools/openclaw_gateway_stop.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

PANIC="${1:-}"
PID_FILE="$HOME/.openclaw/run/gateway.pid"
CFG="$HOME/.openclaw/openclaw.json"
CB_DIR="$HOME/.openclaw/run"
CB_BACKUP="$CB_DIR/openclaw.json.circuit-breaker.bak"
CB_MARKER="$CB_DIR/circuit_breaker.active"

read_cfg() {
  local key="$1" default="$2"
  if [ -f "$CFG" ] && command -v jq >/dev/null 2>&1; then
    jq -r "$key // \"$default\"" "$CFG" 2>/dev/null || echo "$default"
  else
    echo "$default"
  fi
}

PORT="$(read_cfg '.gateway.port' '18789')"

is_running_pid() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

stop_pid() {
  local pid="$1"
  local label="$2"
  if ! is_running_pid "$pid"; then
    return 0
  fi

  kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 12); do
    if ! is_running_pid "$pid"; then
      echo "stopped $label pid=$pid via SIGTERM"
      return 0
    fi
    sleep 1
  done

  kill -KILL "$pid" 2>/dev/null || true
  for _ in $(seq 1 5); do
    if ! is_running_pid "$pid"; then
      echo "stopped $label pid=$pid via SIGKILL"
      return 0
    fi
    sleep 1
  done

  echo "failed_to_stop $label pid=$pid" >&2
  return 1
}

listener_pid_on_port() {
  ss -ltnp "sport = :$PORT" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -n1
}

apply_circuit_breaker() {
  mkdir -p "$CB_DIR"
  if [ ! -f "$CB_BACKUP" ]; then
    cp "$CFG" "$CB_BACKUP"
  fi
  python3 - <<'PY'
import json
from pathlib import Path
cfg = Path.home() / ".openclaw" / "openclaw.json"
data = json.loads(cfg.read_text())
commands = data.setdefault("commands", {})
commands["native"] = False
commands["nativeSkills"] = False
plugins = data.setdefault("plugins", {}).setdefault("entries", {})
for key in ("whatsapp", "telegram"):
    entry = plugins.setdefault(key, {})
    if isinstance(entry, dict):
        entry["enabled"] = False
channels = data.setdefault("channels", {})
telegram = channels.get("telegram")
if isinstance(telegram, dict):
    telegram["enabled"] = False
cfg.write_text(json.dumps(data, indent=2, sort_keys=True))
PY
  date -u +%Y-%m-%dT%H:%M:%SZ > "$CB_MARKER"
  echo "circuit_breaker_applied backup=$CB_BACKUP marker=$CB_MARKER"
}

rc=0

if [ -f "$PID_FILE" ]; then
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  stop_pid "$pid" "pidfile" || rc=1
  rm -f "$PID_FILE"
fi

listener_pid="$(listener_pid_on_port || true)"
if [ -n "$listener_pid" ]; then
  cmdline="$(ps -p "$listener_pid" -o args= 2>/dev/null || true)"
  if echo "$cmdline" | grep -Eiq 'openclaw|clawdbot-gateway'; then
    stop_pid "$listener_pid" "listener" || rc=1
  else
    echo "refusing_to_kill_unknown_listener pid=$listener_pid cmd=$cmdline" >&2
    rc=1
  fi
fi

if coo openclaw -- gateway health --json >/dev/null 2>&1; then
  rc=1
fi

if [ "$PANIC" = "--panic" ] && [ "$rc" -ne 0 ]; then
  apply_circuit_breaker
fi

if [ "$rc" -eq 0 ]; then
  echo "gateway_stopped"
else
  echo "gateway_stop_incomplete" >&2
fi

exit "$rc"
```

### File: runtime/tools/openclaw_gateway_status.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

PID_FILE="$HOME/.openclaw/run/gateway.pid"
LOG_FILE="$HOME/.openclaw/logs/gateway-daemon.log"
CFG="$HOME/.openclaw/openclaw.json"

read_cfg() {
  local key="$1" default="$2"
  if [ -f "$CFG" ] && command -v jq >/dev/null 2>&1; then
    jq -r "$key // \"$default\"" "$CFG" 2>/dev/null || echo "$default"
  else
    echo "$default"
  fi
}

PORT="$(read_cfg '.gateway.port' '18789')"
BIND="$(read_cfg '.gateway.bind' 'loopback')"

echo "gateway_status"
echo "pid_file=$PID_FILE"
if [ -f "$PID_FILE" ]; then
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if kill -0 "$pid" 2>/dev/null; then
    echo "pid=$pid running=true"
  else
    echo "pid=$pid running=false (stale pid file)"
  fi
else
  echo "pid=(none) running=false"
fi

echo "bind=$BIND"
echo "port=$PORT"

echo "listener:"
ss -ltnp "sport = :$PORT" 2>/dev/null || true

echo "gateway_health_json:"
set +e
coo openclaw -- gateway health --json
health_rc=$?
set -e
echo "gateway_health_exit=$health_rc"

echo "log_file=$LOG_FILE"
if [ -f "$LOG_FILE" ]; then
  echo "log_tail_begin"
  tail -n 30 "$LOG_FILE" || true
  echo "log_tail_end"
else
  echo "log_missing=true"
fi
```

### File: runtime/tools/openclaw_gateway_recover.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

CFG="$HOME/.openclaw/openclaw.json"
CB_BACKUP="$HOME/.openclaw/run/openclaw.json.circuit-breaker.bak"
CB_MARKER="$HOME/.openclaw/run/circuit_breaker.active"

if [ ! -f "$CB_BACKUP" ]; then
  echo "no_circuit_breaker_backup_found"
  exit 1
fi

cp "$CB_BACKUP" "$CFG"
rm -f "$CB_MARKER"
echo "circuit_breaker_recovered restored_from=$CB_BACKUP"
```

### File: runtime/tools/openclaw_receipts_bundle.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

BUILD_REPO="$(git rev-parse --show-toplevel)"
OUT_DIR_DEFAULT="$BUILD_REPO/artifacts/evidence/openclaw/receipts"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="${1:-$OUT_DIR_DEFAULT/Receipt_Bundle_OpenClaw_P0_${TS}.md}"

mkdir -p "$(dirname "$OUT_FILE")"

redact_stream() {
  sed -E \
    -e 's/(sk-[A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]+/\1...[REDACTED]/g' \
    -e 's/(ghu_[A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]+/\1...[REDACTED]/g' \
    -e 's/([0-9]{8,}):[A-Za-z0-9_\-]{16,}/\1:[REDACTED]/g' \
    -e 's/(token[:=][[:space:]]*)[^[:space:]]+/\1[REDACTED]/Ig' \
    -e 's/(api[_-]?key[:=][[:space:]]*)[^[:space:]]+/\1[REDACTED]/Ig'
}

write_block() {
  local title="$1"
  shift
  {
    echo "### ${title}"
    echo '```bash'
    printf '%q ' "$@"
    echo
    echo '```'
    echo '```text'
  } >>"$OUT_FILE"

  set +e
  "$@" 2>&1 | redact_stream >>"$OUT_FILE"
  rc=${PIPESTATUS[0]}
  set -e

  {
    echo "[exit_code]=$rc"
    echo '```'
    echo
  } >>"$OUT_FILE"
}

{
  echo "# OpenClaw P0 Receipts Bundle"
  echo
  echo "- generated_utc: $TS"
  echo "- build_repo: $BUILD_REPO"
  echo "- canonical_command: coo openclaw -- <args>"
  echo
} >"$OUT_FILE"

write_block "which coo" which coo
write_block "coo symlink" bash -lc 'ls -l "$(which coo)"'
write_block "which openclaw" which openclaw
write_block "openclaw version" openclaw --version
write_block "coo status all usage" coo openclaw -- status --all --usage
write_block "coo security audit deep" coo openclaw -- security audit --deep
write_block "coo models status probe" coo openclaw -- models status --probe
write_block "coo sandbox explain" coo openclaw -- sandbox explain
write_block "coo gateway status deep json" coo openclaw -- gateway status --deep --json
write_block "coo gateway probe json" coo openclaw -- gateway probe --json
write_block "coo gateway health json" coo openclaw -- gateway health --json
write_block "gateway daemon path receipt" bash -lc 'echo PID_FILE=~/.openclaw/run/gateway.pid; test -f ~/.openclaw/run/gateway.pid && echo PID=$(cat ~/.openclaw/run/gateway.pid) || echo PID=(missing); echo LOG_FILE=~/.openclaw/logs/gateway-daemon.log; test -f ~/.openclaw/logs/gateway-daemon.log && echo LOG_TAIL_SOURCE=~/.openclaw/logs/gateway-daemon.log || echo LOG_TAIL_SOURCE=(missing)'

printf '%s\n' "$OUT_FILE"
```

### File: runtime/tools/OPENCLAW_COO_RUNBOOK.md

```markdown
# OpenClaw COO Runbook (Canonical Path)

## Canonical Commands

Use `coo openclaw -- <openclaw-args>` for OpenClaw operations.

Use `coo run -- <shell command>` for shell/process actions.

## WSL Lifecycle (No systemd bus)

When `systemctl --user` is unavailable, use process-managed scripts:

- `runtime/tools/openclaw_gateway_daemon.sh`
- `runtime/tools/openclaw_gateway_stop.sh`
- `runtime/tools/openclaw_gateway_status.sh`
- `runtime/tools/openclaw_gateway_recover.sh`

Deterministic runtime paths:

- PID: `~/.openclaw/run/gateway.pid`
- Log: `~/.openclaw/logs/gateway-daemon.log`

## Operator Lifecycle

Status:

```bash
runtime/tools/openclaw_gateway_status.sh
coo openclaw -- gateway probe --json
```

Start:

```bash
runtime/tools/openclaw_gateway_daemon.sh start
```

Stop:

```bash
runtime/tools/openclaw_gateway_stop.sh
```

Restart:

```bash
runtime/tools/openclaw_gateway_daemon.sh restart
```

Panic stop:

```bash
runtime/tools/openclaw_gateway_stop.sh --panic
```

Recover from panic circuit breaker:

```bash
runtime/tools/openclaw_gateway_recover.sh
runtime/tools/openclaw_gateway_daemon.sh start
```

## Panic Circuit Breaker

If stop fails, panic mode applies a reversible config breaker:

- `commands.native=false`
- `commands.nativeSkills=false`
- disable Telegram/WhatsApp plugin entries
- disable `channels.telegram.enabled`

Backup and marker files:

- `~/.openclaw/run/openclaw.json.circuit-breaker.bak`
- `~/.openclaw/run/circuit_breaker.active`

## Safety Invariants

- Loopback bind only (fail-closed if config bind is not `loopback`).
- Do not enable `exec`, `browser`, `web search`, or `web fetch` for inbox-facing agents.
- Keep `coo openclaw -- security audit --deep` at 0 critical / 0 warn.
```
