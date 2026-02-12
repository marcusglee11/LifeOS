#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODEL="${OPENCODE_MODEL:-opencode/kimi-k2.5-free}"
PORT="${OPENCODE_PORT:-4096}"
URL="http://127.0.0.1:${PORT}"

KEY="${ZEN_STEWARD_KEY:-${OPENROUTER_API_KEY:-${ZEN_API_KEY:-}}}"
if [[ -z "$KEY" ]]; then
  echo "ERROR: Missing API key. Set one of: ZEN_STEWARD_KEY, OPENROUTER_API_KEY, ZEN_API_KEY" >&2
  exit 2
fi

if ! command -v opencode >/dev/null 2>&1; then
  echo "ERROR: 'opencode' CLI not found in PATH." >&2
  exit 3
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "ERROR: .venv is missing. Create/activate it first (python3 -m venv .venv)." >&2
  exit 4
fi

TMP_CFG="$(mktemp -d -t opencode_steward_smoke_XXXXXX)"
cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_CFG"
}
trap cleanup EXIT

mkdir -p "$TMP_CFG/opencode" "$TMP_CFG/.local/share/opencode"
cat > "$TMP_CFG/opencode/opencode.json" <<JSON
{
  "model": "${MODEL}",
  "$schema": "https://opencode.ai/config.json"
}
JSON

cat > "$TMP_CFG/.local/share/opencode/auth.json" <<JSON
{
  "zen": {"type": "api", "key": "${KEY}"},
  "openrouter": {"type": "api", "key": "${KEY}"}
}
JSON

export OPENCODE_URL="$URL"
export OPENCODE_MODEL="$MODEL"
export OPENROUTER_API_KEY="$KEY"
export ZEN_API_KEY="$KEY"
export ZEN_STEWARD_KEY="$KEY"
export APPDATA="$TMP_CFG"
export XDG_CONFIG_HOME="$TMP_CFG"
export USERPROFILE="$TMP_CFG"
export HOME="$TMP_CFG"

opencode serve --port "$PORT" >/tmp/opencode_steward_smoke.log 2>&1 &
SERVER_PID=$!

for _ in {1..60}; do
  if curl -fsS "$URL/global/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    echo "ERROR: opencode server exited early. See /tmp/opencode_steward_smoke.log" >&2
    exit 5
  fi
  done

if ! curl -fsS "$URL/global/health" >/dev/null 2>&1; then
  echo "ERROR: opencode health check timed out. See /tmp/opencode_steward_smoke.log" >&2
  exit 6
fi

.venv/bin/python scripts/delegate_to_doc_steward.py \
  --mission INDEX_UPDATE \
  --dry-run \
  --trial-type smoke_test
