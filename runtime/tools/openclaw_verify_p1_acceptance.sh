#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_P1_ACCEPTANCE_OUT_DIR:-$STATE_DIR/verify-p1-acceptance/$TS_UTC}"
CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_P1_ACCEPTANCE_TIMEOUT_SEC:-45}"

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify-p1-acceptance/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

MEM_OUT="$OUT_DIR/verify_memory.txt"
IFACE_OUT="$OUT_DIR/verify_interfaces.txt"
RECALL_OUT="$OUT_DIR/verify_recall.txt"
SUMMARY_OUT="$OUT_DIR/summary.txt"

set +e
timeout "$CMD_TIMEOUT_SEC" runtime/tools/openclaw_verify_memory.sh > "$MEM_OUT" 2>&1
RC_MEM=$?
timeout "$CMD_TIMEOUT_SEC" runtime/tools/openclaw_verify_interfaces.sh > "$IFACE_OUT" 2>&1
RC_IFACE=$?
timeout "$CMD_TIMEOUT_SEC" runtime/tools/openclaw_verify_recall_e2e.sh > "$RECALL_OUT" 2>&1
RC_RECALL=$?
set -e

PASS=1
if [ "$RC_MEM" -ne 0 ] || [ "$RC_IFACE" -ne 0 ] || [ "$RC_RECALL" -ne 0 ]; then
  PASS=0
fi

if ! rg -q '^PASS ' "$MEM_OUT"; then PASS=0; fi
if ! rg -q '^PASS ' "$IFACE_OUT"; then PASS=0; fi
if ! rg -q '^PASS .*sources_present=true' "$RECALL_OUT"; then PASS=0; fi

EVDIR="${P1_5_EVDIR:-}"
if [ -z "$EVDIR" ]; then
  latest="$(ls -1dt artifacts/evidence/openclaw/p1_5/* 2>/dev/null | head -n1 || true)"
  EVDIR="$latest"
fi
NOTE="$EVDIR/manual_smoke_note.md"

if [ -z "$EVDIR" ] || [ ! -f "$NOTE" ]; then
  PASS=0
else
  rg -q '^surface: telegram_dm$' "$NOTE" || PASS=0
  rg -q '^result: pass$' "$NOTE" || PASS=0
  rg -q '^sources: memory/daily/2026-02-10.md:1-5$' "$NOTE" || PASS=0
fi

{
  echo "ts_utc=$TS_UTC"
  echo "verify_memory_exit=$RC_MEM"
  echo "verify_interfaces_exit=$RC_IFACE"
  echo "verify_recall_exit=$RC_RECALL"
  echo "manual_note=$NOTE"
  echo "memory_out=$MEM_OUT"
  echo "interfaces_out=$IFACE_OUT"
  echo "recall_out=$RECALL_OUT"
} > "$SUMMARY_OUT"

if [ "$PASS" -eq 1 ]; then
  echo "PASS p1_acceptance=true manual_smoke=pass source_pointer=memory/daily/2026-02-10.md:1-5 summary=$SUMMARY_OUT"
  exit 0
fi

echo "FAIL p1_acceptance=false manual_smoke_note=$NOTE summary=$SUMMARY_OUT" >&2
exit 1
