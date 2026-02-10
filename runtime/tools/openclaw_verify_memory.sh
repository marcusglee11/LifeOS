#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_MEMORY_OUT_DIR:-$STATE_DIR/verify-memory/$TS_UTC}"
STATUS_TIMEOUT_SEC="${OPENCLAW_VERIFY_MEMORY_STATUS_TIMEOUT_SEC:-20}"
SEARCH_TIMEOUT_SEC="${OPENCLAW_VERIFY_MEMORY_SEARCH_TIMEOUT_SEC:-20}"
SEED_QUERY="${OPENCLAW_VERIFY_MEMORY_QUERY:-lobster-memory-seed-001}"
AGENT_ID="${OPENCLAW_VERIFY_MEMORY_AGENT:-main}"

mkdir -p "$OUT_DIR"

status_out="$OUT_DIR/memory_status_deep.txt"
search_out="$OUT_DIR/memory_search_seed.txt"
summary_out="$OUT_DIR/summary.txt"

set +e
timeout "$STATUS_TIMEOUT_SEC" coo openclaw -- memory status --deep --agent "$AGENT_ID" > "$status_out" 2>&1
rc_status=$?
timeout "$SEARCH_TIMEOUT_SEC" coo openclaw -- memory search "$SEED_QUERY" --agent "$AGENT_ID" > "$search_out" 2>&1
rc_search=$?
set -e

provider="$(rg -o 'Provider:\s*[^[:space:]]+' "$status_out" | head -n1 | awk '{print $2}')"
requested="$(rg -o 'requested:\s*[^)]+' "$status_out" | head -n1 | awk -F': ' '{print $2}')"
hits="$(rg -c '(^|[[:space:]])[^[:space:]]+:[0-9]+-[0-9]+' "$search_out" || true)"

fallback="unknown"
if [ -f "${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}" ]; then
  fallback="$(python3 - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ.get("OPENCLAW_CONFIG_PATH", str(Path.home()/".openclaw"/"openclaw.json")))
try:
    cfg = json.loads(p.read_text(encoding="utf-8"))
    print((((cfg.get("agents") or {}).get("defaults") or {}).get("memorySearch") or {}).get("fallback") or "unknown")
except Exception:
    print("unknown")
PY
)"
fi

pass=1
if [ "$rc_status" -ne 0 ] || [ "$rc_search" -ne 0 ]; then
  pass=0
fi
if [ "${provider:-}" != "local" ] && [ "${requested:-}" != "local" ]; then
  pass=0
fi
if [ "$fallback" != "none" ]; then
  pass=0
fi
if [ "${hits:-0}" -lt 1 ]; then
  pass=0
fi

{
  echo "ts_utc=$TS_UTC"
  echo "out_dir=$OUT_DIR"
  echo "agent=$AGENT_ID"
  echo "query=$SEED_QUERY"
  echo "status_exit=$rc_status"
  echo "search_exit=$rc_search"
  echo "provider=${provider:-unknown}"
  echo "requested=${requested:-unknown}"
  echo "fallback=$fallback"
  echo "hits=$hits"
  echo "status_out=$status_out"
  echo "search_out=$search_out"
} > "$summary_out"

if [ "$pass" -eq 1 ]; then
  echo "PASS provider=local fallback=none status_out=$status_out search_out=$search_out summary=$summary_out"
  exit 0
fi

echo "FAIL provider=${provider:-unknown} fallback=$fallback status_out=$status_out search_out=$search_out summary=$summary_out" >&2
exit 1
