#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_MEMORY_INDEX_SAFE_OUT_DIR:-$STATE_DIR/memory-index-safe/$TS_UTC}"
INDEX_TIMEOUT_SEC="${OPENCLAW_MEMORY_INDEX_TIMEOUT_SEC:-70}"
AGENT_ID="${OPENCLAW_MEMORY_INDEX_AGENT:-main}"

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-memory-index-safe/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

guard_summary="$OUT_DIR/guard_summary.json"
guard_out="$OUT_DIR/guard_output.txt"
index_out="$OUT_DIR/memory_index_verbose.txt"

set +e
python3 runtime/tools/openclaw_memory_policy_guard.py --json-summary --summary-out "$guard_summary" > "$guard_out" 2>&1
rc_guard=$?
set -e
if [ "$rc_guard" -ne 0 ]; then
  echo "FAIL memory_policy_ok=false guard_summary=$guard_summary guard_output=$guard_out" >&2
  exit 1
fi

set +e
timeout "$INDEX_TIMEOUT_SEC" coo openclaw -- memory index --agent "$AGENT_ID" --verbose > "$index_out" 2>&1
rc_index=$?
set -e
if [ "$rc_index" -ne 0 ]; then
  echo "FAIL memory_policy_ok=true index_exit=$rc_index guard_summary=$guard_summary index_output=$index_out" >&2
  exit 1
fi

echo "PASS memory_policy_ok=true guard_summary=$guard_summary index_output=$index_out"
exit 0
