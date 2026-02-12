#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  runtime/tools/openclaw_slack_launch.sh [--mode socket|http] [--apply]

Default behavior is dry-run only.
With --apply, generates env-only overlay config and launches gateway with overlay config path.
USAGE
}

APPLY=0
MODE="${OPENCLAW_SLACK_MODE:-socket}"
STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OVERLAY_DIR="${OPENCLAW_SLACK_OVERLAY_DIR:-$STATE_DIR/runtime/slack_overlay/$TS_UTC}"
QUARANTINE_DIR="${OPENCLAW_SLACK_QUARANTINE_DIR:-$STATE_DIR/runtime/slack_overlay_quarantine/$TS_UTC}"
GEN_OUT_JSON="/tmp/openclaw-slack-overlay-${TS_UTC}.json"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode)
      MODE="${2:?missing mode}"
      shift 2
      ;;
    --apply)
      APPLY=1
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

required_env_socket=(OPENCLAW_SLACK_APP_TOKEN OPENCLAW_SLACK_BOT_TOKEN)
required_env_http=(OPENCLAW_SLACK_BOT_TOKEN OPENCLAW_SLACK_SIGNING_SECRET)

env_present=false
if [ "$MODE" = "socket" ]; then
  env_present=true
  for k in "${required_env_socket[@]}"; do
    if [ -z "${!k:-}" ]; then env_present=false; fi
  done
elif [ "$MODE" = "http" ]; then
  env_present=true
  for k in "${required_env_http[@]}"; do
    if [ -z "${!k:-}" ]; then env_present=false; fi
  done
else
  echo "ERROR: mode must be socket or http" >&2
  exit 2
fi

if [ "$APPLY" -ne 1 ]; then
  echo "DRY_RUN slack_launch mode=$MODE would_generate_overlay=$env_present overlay_dir=$OVERLAY_DIR"
  exit 0
fi

cleanup_overlay() {
  local overlay_path="$1"
  local metadata_path="$2"
  if rm -f "$overlay_path" "$metadata_path" 2>/dev/null; then
    rmdir "$OVERLAY_DIR" 2>/dev/null || true
    echo "overlay_cleanup=deleted"
    return 0
  fi
  mkdir -p "$QUARANTINE_DIR"
  mv -f "$overlay_path" "$metadata_path" "$QUARANTINE_DIR/" 2>/dev/null || true
  echo "overlay_cleanup=quarantined quarantine_dir=$QUARANTINE_DIR"
  return 0
}

python3 runtime/tools/openclaw_slack_overlay.py \
  --mode "$MODE" \
  --output-dir "$OVERLAY_DIR" \
  --json > "$GEN_OUT_JSON"

overlay_path="$(python3 - <<'PY' "$GEN_OUT_JSON"
import json,sys
obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
print(obj["overlay_config_path"])
PY
)"
metadata_path="$(python3 - <<'PY' "$GEN_OUT_JSON"
import json,sys
obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
print(obj["overlay_metadata_path"])
PY
)"

trap 'cleanup_overlay "$overlay_path" "$metadata_path"' EXIT

export OPENCLAW_STATE_DIR="$STATE_DIR"
export OPENCLAW_CONFIG_PATH="$overlay_path"
export OPENCLAW_SLACK_OVERLAY_LAST_MODE="$MODE"

echo "APPLY slack_launch mode=$MODE overlay_generated=true overlay_path=$overlay_path"
echo "Launching: coo openclaw -- gateway run"
coo openclaw -- gateway run

