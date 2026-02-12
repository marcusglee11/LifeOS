#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_SLACK_OUT_DIR:-$STATE_DIR/verify-slack/$TS_UTC}"
TIMEOUT_SEC="${OPENCLAW_VERIFY_SLACK_TIMEOUT_SEC:-20}"
RECEIPT_TIMEOUT_SEC="${OPENCLAW_VERIFY_SLACK_RECEIPT_TIMEOUT_SEC:-3}"

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify-slack/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

PASS=1
base_posture="$OUT_DIR/base_posture.json"
missing_env_out="$OUT_DIR/overlay_missing_env.txt"
dummy_overlay_out="$OUT_DIR/overlay_dummy.json"
leak_scan_out="$OUT_DIR/leak_scan.txt"
receipt_gen="$OUT_DIR/receipt_generation.txt"
summary_out="$OUT_DIR/summary.txt"

set +e
timeout "$TIMEOUT_SEC" python3 runtime/tools/openclaw_slack_overlay.py --check-base --json > "$base_posture" 2>&1
rc_base=$?
set -e
if [ "$rc_base" -ne 0 ]; then
  PASS=0
fi

slack_base_disabled="$(python3 - <<'PY' "$base_posture"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8',errors='replace').read())
    print("true" if obj.get("slack_base_disabled") else "false")
except Exception:
    print("false")
PY
)"
slack_secrets_in_base="$(python3 - <<'PY' "$base_posture"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8',errors='replace').read())
    print("true" if obj.get("slack_secrets_in_base") else "false")
except Exception:
    print("true")
PY
)"
if [ "$slack_base_disabled" != "true" ] || [ "$slack_secrets_in_base" != "false" ]; then
  PASS=0
fi

set +e
env -u OPENCLAW_SLACK_APP_TOKEN -u OPENCLAW_SLACK_BOT_TOKEN -u OPENCLAW_SLACK_SIGNING_SECRET \
  timeout "$TIMEOUT_SEC" python3 runtime/tools/openclaw_slack_overlay.py --mode socket --output-dir "$OUT_DIR/noenv" --json > "$missing_env_out" 2>&1
rc_missing=$?
set -e
overlay_missing_env_failclosed=false
if [ "$rc_missing" -ne 0 ] && rg -q "missing required env" "$missing_env_out"; then
  overlay_missing_env_failclosed=true
else
  PASS=0
fi

set +e
OPENCLAW_SLACK_APP_TOKEN="xapp-TEST-DUMMY-TOKEN" \
OPENCLAW_SLACK_BOT_TOKEN="xoxb-TEST-DUMMY-TOKEN" \
timeout "$TIMEOUT_SEC" python3 runtime/tools/openclaw_slack_overlay.py --mode socket --output-dir "$OUT_DIR/dummy" --json > "$dummy_overlay_out" 2>&1
rc_dummy=$?
set -e
overlay_generation_ok_with_dummy=false
if [ "$rc_dummy" -eq 0 ]; then
  overlay_generation_ok_with_dummy=true
else
  PASS=0
fi

overlay_path="$(python3 - <<'PY' "$dummy_overlay_out"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8',errors='replace').read())
    print(obj.get("overlay_config_path",""))
except Exception:
    print("")
PY
)"
overlay_meta_path="$(python3 - <<'PY' "$dummy_overlay_out"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8',errors='replace').read())
    print(obj.get("overlay_metadata_path",""))
except Exception:
    print("")
PY
)"
overlay_deleted=false
if [ -n "$overlay_path" ]; then
  rm -f "$overlay_path"
fi
if [ -n "$overlay_meta_path" ]; then
  rm -f "$overlay_meta_path"
fi
rmdir "$OUT_DIR/dummy" 2>/dev/null || true
if [ -n "$overlay_path" ] && [ ! -e "$overlay_path" ]; then
  overlay_deleted=true
fi
if [ "$overlay_deleted" != "true" ]; then
  PASS=0
fi

set +e
OPENCLAW_CMD_TIMEOUT_SEC="$RECEIPT_TIMEOUT_SEC" \
OPENCLAW_SLACK_OVERLAY_LAST_MODE="socket" \
runtime/tools/openclaw_receipts_bundle.sh > "$receipt_gen" 2>&1
rc_receipt=$?
set -e
if [ "$rc_receipt" -ne 0 ]; then
  PASS=0
fi

runtime_receipt="$(sed -n '1p' "$receipt_gen" | tr -d '\r')"
runtime_manifest="$(sed -n '2p' "$receipt_gen" | tr -d '\r')"
runtime_ledger_entry="$(sed -n '3p' "$receipt_gen" | tr -d '\r')"
ledger_path="$(sed -n '4p' "$receipt_gen" | tr -d '\r')"

set +e
python3 - <<'PY' "$leak_scan_out" "$dummy_overlay_out" "$missing_env_out" "$receipt_gen" "$runtime_receipt" "$runtime_manifest" "$runtime_ledger_entry"
import re
import sys
from pathlib import Path

out = Path(sys.argv[1])
paths = [Path(p) for p in sys.argv[2:] if p]
patterns = [
    re.compile(r"xapp-TEST-DUMMY-TOKEN"),
    re.compile(r"xoxb-TEST-DUMMY-TOKEN"),
    re.compile(r"\bxapp-[A-Za-z0-9-]{8,}\b"),
    re.compile(r"\bxoxb-[A-Za-z0-9-]{8,}\b"),
]
hits = []
for p in paths:
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    for rgx in patterns:
        if rgx.search(text):
            hits.append(f"{p}:pattern={rgx.pattern}")
            break
if hits:
    out.write_text("\n".join(hits) + "\n", encoding="utf-8")
    raise SystemExit(1)
out.write_text("STRICT_SECRET_SCAN_PASS\n", encoding="utf-8")
PY
rc_strict_scan=$?
set -e

if [ "$rc_strict_scan" -ne 0 ]; then
  PASS=0
fi

{
  echo "ts_utc=$TS_UTC"
  echo "slack_base_disabled=$slack_base_disabled"
  echo "slack_secrets_in_base=$slack_secrets_in_base"
  echo "overlay_missing_env_failclosed=$overlay_missing_env_failclosed"
  echo "overlay_generation_ok_with_dummy=$overlay_generation_ok_with_dummy"
  echo "overlay_deleted=$overlay_deleted"
  echo "runtime_receipt=$runtime_receipt"
  echo "runtime_manifest=$runtime_manifest"
  echo "runtime_ledger_entry=$runtime_ledger_entry"
  echo "ledger_path=$ledger_path"
} > "$summary_out"

if [ "$PASS" -eq 1 ]; then
  echo "PASS slack_base_disabled=true slack_secrets_in_base=false overlay_missing_env_failclosed=true overlay_generation_ok_with_dummy=true overlay_deleted=true runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
  exit 0
fi

echo "FAIL slack_base_disabled=$slack_base_disabled slack_secrets_in_base=$slack_secrets_in_base overlay_missing_env_failclosed=$overlay_missing_env_failclosed overlay_generation_ok_with_dummy=$overlay_generation_ok_with_dummy overlay_deleted=$overlay_deleted runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
exit 1
