#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_RECALL_OUT_DIR:-$STATE_DIR/verify-recall/$TS_UTC}"
GUARD_TIMEOUT_SEC="${OPENCLAW_VERIFY_RECALL_GUARD_TIMEOUT_SEC:-15}"
SEARCH_TIMEOUT_SEC="${OPENCLAW_VERIFY_RECALL_SEARCH_TIMEOUT_SEC:-20}"
RECEIPT_TIMEOUT_SEC="${OPENCLAW_VERIFY_RECALL_RECEIPT_TIMEOUT_SEC:-3}"
QUERY="${OPENCLAW_VERIFY_RECALL_QUERY:-what did we decide last week about lobster-memory-seed-001?}"

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify-recall/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

guard_summary="$OUT_DIR/guard_summary.json"
guard_out="$OUT_DIR/guard_output.txt"
search_out="$OUT_DIR/memory_search_output.txt"
contract_out="$OUT_DIR/contract_response.json"
summary_out="$OUT_DIR/summary.txt"

set +e
timeout "$GUARD_TIMEOUT_SEC" python3 runtime/tools/openclaw_memory_policy_guard.py --json-summary --summary-out "$guard_summary" > "$guard_out" 2>&1
rc_guard=$?
timeout "$SEARCH_TIMEOUT_SEC" coo openclaw -- memory search "lobster-memory-seed-001" --agent main > "$search_out" 2>&1
rc_search=$?
set -e

if [ "$rc_guard" -ne 0 ] || [ "$rc_search" -ne 0 ]; then
  echo "FAIL recall_mode=cli_only sources_present=false MANUAL_SMOKE_REQUIRED=true guard_exit=$rc_guard search_exit=$rc_search summary=$summary_out" >&2
  exit 1
fi

python3 runtime/tools/openclaw_recall_contract.py --query "$QUERY" --search-output-file "$search_out" --json > "$contract_out"

query_hash="$(python3 - <<'PY' "$contract_out"
import json,sys
obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
print(obj.get("query_hash",""))
PY
)"
hit_count="$(python3 - <<'PY' "$contract_out"
import json,sys
obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
print(int(obj.get("hit_count",0)))
PY
)"
sources_joined="$(python3 - <<'PY' "$contract_out"
import json,sys
obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
print(",".join(obj.get("sources",[])))
PY
)"
sources_present="$(python3 - <<'PY' "$contract_out"
import json,re,sys
obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
sources=obj.get("sources",[])
ok=bool(sources) and all(re.match(r'^[^:\s]+:[0-9]+-[0-9]+$', str(s)) for s in sources)
print("true" if ok else "false")
PY
)"

if [ "$sources_present" != "true" ]; then
  echo "FAIL recall_mode=cli_only sources_present=false MANUAL_SMOKE_REQUIRED=true query_hash=$query_hash summary=$summary_out" >&2
  exit 1
fi

receipt_gen="$OUT_DIR/receipt_generation.txt"
set +e
OPENCLAW_CMD_TIMEOUT_SEC="$RECEIPT_TIMEOUT_SEC" \
OPENCLAW_RECALL_TRACE_ENABLED="true" \
OPENCLAW_LAST_RECALL_QUERY_HASH="$query_hash" \
OPENCLAW_LAST_RECALL_HIT_COUNT="$hit_count" \
OPENCLAW_LAST_RECALL_SOURCES="$sources_joined" \
OPENCLAW_LAST_RECALL_TIMESTAMP_UTC="$TS_UTC" \
runtime/tools/openclaw_receipts_bundle.sh > "$receipt_gen" 2>&1
rc_receipt=$?
set -e
if [ "$rc_receipt" -ne 0 ]; then
  echo "FAIL recall_mode=cli_only sources_present=true MANUAL_SMOKE_REQUIRED=true query_hash=$query_hash receipt_exit=$rc_receipt summary=$summary_out" >&2
  exit 1
fi

runtime_receipt="$(sed -n '1p' "$receipt_gen" | tr -d '\r')"
runtime_manifest="$(sed -n '2p' "$receipt_gen" | tr -d '\r')"
runtime_ledger_entry="$(sed -n '3p' "$receipt_gen" | tr -d '\r')"
ledger_path="$(sed -n '4p' "$receipt_gen" | tr -d '\r')"

{
  echo "ts_utc=$TS_UTC"
  echo "recall_mode=cli_only"
  echo "manual_smoke_required=true"
  echo "memory_policy_ok=true"
  echo "query_hash=$query_hash"
  echo "hit_count=$hit_count"
  echo "sources=$sources_joined"
  echo "guard_summary=$guard_summary"
  echo "runtime_receipt=$runtime_receipt"
  echo "runtime_manifest=$runtime_manifest"
  echo "runtime_ledger_entry=$runtime_ledger_entry"
  echo "ledger_path=$ledger_path"
} > "$summary_out"

echo "PASS recall_mode=cli_only sources_present=true MANUAL_SMOKE_REQUIRED=true memory_policy_ok=true query_hash=$query_hash runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
exit 0
