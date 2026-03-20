# Review Packet — Gate A-P1.4 v1.0

## Summary
Gate A-P1.4 implements a grounded recall contract for decision/recall intents, adds deterministic E2E verification, and records privacy-safe recall trace metadata in receipts/ledger.

## Contract
For recall intents (e.g., "what did we decide", "last week", "decision", "agreed"):
1. Run memory search first.
2. Answer only from retrieved memory evidence.
3. Include a `Sources:` section with `file:line-range` pointers.
4. If no hits, respond exactly:
   `No grounded memory found. Which timeframe or document should I check?`

## Enforcement Points
- `runtime/tools/openclaw_recall_contract.py`
  - intent detection
  - source parsing from memory search
  - fail-closed no-hit response
- `runtime/tools/openclaw_verify_recall_e2e.sh`
  - guard-first recall verification
  - deterministic CLI recall assertion (`cli_only` mode)
  - receipt generation with metadata-only recall trace
- `runtime/tools/openclaw_receipts_bundle.sh`
  - adds `recall_trace_enabled` + `last_recall` metadata fields
- Telegram hook (host config):
  - group-level `systemPrompt` added in `~/.openclaw/openclaw.json` for grounded recall behavior

## Privacy Posture
- No raw Telegram message content is persisted in evidence.
- Receipts/ledger store only metadata:
  - query hash
  - hit count
  - source pointers
  - timestamp

## Acceptance Evidence
Evidence directory:
- `artifacts/evidence/openclaw/p1_4/20260211T053544`

Required files:
- `repo_state_before.txt`
- `openclaw_help_channels.txt`
- `recall_contract_note.md`
- `acceptance_verify_recall_1.txt`
- `acceptance_verify_recall_2.txt`
- `acceptance_verify_recall_3.txt`
- `pytest_recall_contract.txt`
- `manual_smoke_note.md`
- `decision_note.md`

Acceptance result:
- 3/3 PASS for:
  - `timeout 45s coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && runtime/tools/openclaw_verify_recall_e2e.sh'`
- Mode: `recall_mode=cli_only`
- Output includes `MANUAL_SMOKE_REQUIRED=true` and source pointers.

## Known Limits
- Current OpenClaw CLI exposes no dedicated Telegram simulation/injection subcommand in this environment.
- Verifier therefore uses deterministic CLI recall and emits a minimal manual Telegram smoke step (metadata-only evidence capture).

## Appendix A — Flattened Code (All Changed Files)

### File: runtime/tools/openclaw_recall_contract.py
```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Dict, List

RECALL_INTENT_RE = re.compile(
    r"\b(what\s+did\s+we\s+decide|last\s+week|decision|decide|agreed|recall)\b",
    re.IGNORECASE,
)
HIT_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)?)\s+([^\s:]+:[0-9]+-[0-9]+)\s*$")


def normalize_query(query: str) -> str:
    return " ".join(query.strip().split()).lower()


def query_hash(query: str) -> str:
    return hashlib.sha256(normalize_query(query).encode("utf-8")).hexdigest()


def is_recall_intent(query: str) -> bool:
    return bool(RECALL_INTENT_RE.search(query or ""))


def parse_sources(search_output: str) -> List[str]:
    sources: List[str] = []
    for line in (search_output or "").splitlines():
        m = HIT_RE.match(line)
        if not m:
            continue
        src = m.group(1)
        if src not in sources:
            sources.append(src)
    return sources


def build_contract_response(query: str, search_output: str) -> Dict[str, object]:
    sources = parse_sources(search_output)
    qh = query_hash(query)
    if not is_recall_intent(query):
        return {
            "query_hash": qh,
            "recall_intent": False,
            "hit_count": len(sources),
            "sources": sources,
            "response": "Recall contract not triggered for non-recall intent.",
        }
    if not sources:
        return {
            "query_hash": qh,
            "recall_intent": True,
            "hit_count": 0,
            "sources": [],
            "response": "No grounded memory found. Which timeframe or document should I check?",
        }
    lines = [
        "Grounded recall: available memory evidence indicates this decision was recorded.",
        "",
        "Sources:",
    ]
    lines.extend(f"- {s}" for s in sources)
    return {
        "query_hash": qh,
        "recall_intent": True,
        "hit_count": len(sources),
        "sources": sources,
        "response": "\n".join(lines),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw grounded recall contract helper.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--search-output-file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.search_output_file:
        search_output = open(args.search_output_file, "r", encoding="utf-8", errors="replace").read()
    else:
        search_output = sys.stdin.read()
    result = build_contract_response(args.query, search_output)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(result["response"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### File: runtime/tools/openclaw_verify_recall_e2e.sh
```bash
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
```

### File: runtime/tools/openclaw_receipts_bundle.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  runtime/tools/openclaw_receipts_bundle.sh [--export-repo] [--timestamp <UTC_TS>]

Modes:
  default        Write runtime-only receipts to $OPENCLAW_STATE_DIR/receipts/<UTC_TS>/
  --export-repo  Copy redacted-safe receipt to artifacts/evidence/openclaw/receipts/Receipt_Bundle_OpenClaw_<UTC_TS>.md
USAGE
}

ROOT="$(git rev-parse --show-toplevel)"
REQ_STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
STATE_DIR="$REQ_STATE_DIR"
CFG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
EXPORT_REPO=0
NOTES=""
CMD_TIMEOUT_SEC="${OPENCLAW_CMD_TIMEOUT_SEC:-25}"
SECURITY_AUDIT_MODE="${OPENCLAW_SECURITY_AUDIT_MODE:-unknown}"
CONFINEMENT_FLAG="${OPENCLAW_CONFINEMENT_FLAG:-}"
RECALL_TRACE_ENABLED="${OPENCLAW_RECALL_TRACE_ENABLED:-false}"
LAST_RECALL_QUERY_HASH="${OPENCLAW_LAST_RECALL_QUERY_HASH:-}"
LAST_RECALL_HIT_COUNT="${OPENCLAW_LAST_RECALL_HIT_COUNT:-0}"
LAST_RECALL_SOURCES="${OPENCLAW_LAST_RECALL_SOURCES:-}"
LAST_RECALL_TIMESTAMP_UTC="${OPENCLAW_LAST_RECALL_TIMESTAMP_UTC:-}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --export-repo)
      EXPORT_REPO=1
      shift
      ;;
    --timestamp)
      TS_UTC="${2:?missing timestamp}"
      shift 2
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

if ! mkdir -p "$STATE_DIR/receipts/$TS_UTC" "$STATE_DIR/ledger" 2>/dev/null; then
  STATE_DIR="/tmp/openclaw-runtime"
  mkdir -p "$STATE_DIR/receipts/$TS_UTC" "$STATE_DIR/ledger"
  NOTES="state_dir_fallback:/tmp/openclaw-runtime"
fi

runtime_dir="$STATE_DIR/receipts/$TS_UTC"
runtime_receipt="$runtime_dir/Receipt_Bundle_OpenClaw.md"
runtime_manifest="$runtime_dir/receipt_manifest.json"
ledger_file="$STATE_DIR/ledger/openclaw_run_ledger.jsonl"
runtime_ledger_entry="$runtime_dir/openclaw_run_ledger_entry.jsonl"
export_receipt="$ROOT/artifacts/evidence/openclaw/receipts/Receipt_Bundle_OpenClaw_${TS_UTC}.md"

mkdir -p "$runtime_dir" "$(dirname "$ledger_file")"

declare -A CMD_RC
declare -A CMD_CAPTURE
CMD_IDS=(
  coo_path
  coo_symlink
  openclaw_version
  security_audit_deep
  memory_policy_guard_summary
  memory_status_main
  channels_status_json
  models_status_probe
  status_all_usage
  sandbox_explain_json
  gateway_probe_json
)

redact_stream() {
  sed -E \
    -e 's/(Authorization:[[:space:]]*Bearer[[:space:]]+)[^[:space:]]+/\1[REDACTED]/Ig' \
    -e 's/\b(sk-[A-Za-z0-9_-]{6})[A-Za-z0-9_-]+/\1...[REDACTED]/g' \
    -e 's/\b(AIza[0-9A-Za-z_-]{6})[0-9A-Za-z_-]+/\1...[REDACTED]/g' \
    -e 's/(("|\x27)?(apiKey|botToken|token|Authorization|password|secret)("|\x27)?[[:space:]]*[:=][[:space:]]*("|\x27)?)[^",\x27[:space:]]+/\1[REDACTED]/Ig' \
    -e 's/[A-Za-z0-9+\/_=-]{80,}/[REDACTED_LONG]/g'
}

run_capture() {
  local id="$1"
  shift
  local tmp rc cap
  tmp="$(mktemp)"
  cap="$runtime_dir/${id}.capture.txt"
  set +e
  timeout "$CMD_TIMEOUT_SEC" "$@" >"$tmp" 2>&1
  rc=$?
  set -e
  CMD_RC["$id"]="$rc"
  cp "$tmp" "$cap"
  CMD_CAPTURE["$id"]="$cap"

  {
    echo "### $id"
    echo '```bash'
    printf '%q ' "$@"
    echo
    echo '```'
    echo '```text'
    redact_stream < "$tmp"
    echo "[exit_code]=$rc"
    echo '```'
    echo
  } >> "$runtime_receipt"

  rm -f "$tmp"
}

{
  echo "# OpenClaw Receipt Bundle"
  echo
  echo "- ts_utc: $TS_UTC"
  echo "- mode: runtime-default"
  echo "- state_dir_requested: $REQ_STATE_DIR"
  echo "- state_dir_effective: $STATE_DIR"
  echo "- runtime_receipt: $runtime_receipt"
  echo
} > "$runtime_receipt"

run_capture coo_path which coo
run_capture coo_symlink bash -lc 'ls -l "$(which coo)"'
run_capture openclaw_version openclaw --version
run_capture security_audit_deep coo openclaw -- security audit --deep
run_capture memory_policy_guard_summary python3 runtime/tools/openclaw_memory_policy_guard.py --json-summary
run_capture memory_status_main coo openclaw -- memory status --agent main
run_capture channels_status_json coo openclaw -- channels status --json
run_capture models_status_probe coo openclaw -- models status --probe
run_capture status_all_usage coo openclaw -- status --all --usage
run_capture sandbox_explain_json coo openclaw -- sandbox explain --json
run_capture gateway_probe_json coo openclaw -- gateway probe --json

for id in "${CMD_IDS[@]}"; do
  export "RC_${id}=${CMD_RC[$id]:-1}"
done
export TS_UTC CFG_PATH ROOT runtime_receipt ledger_file NOTES SECURITY_AUDIT_MODE CONFINEMENT_FLAG
export RECALL_TRACE_ENABLED LAST_RECALL_QUERY_HASH LAST_RECALL_HIT_COUNT LAST_RECALL_SOURCES LAST_RECALL_TIMESTAMP_UTC
export CAPTURE_models_status_probe="${CMD_CAPTURE[models_status_probe]:-}"
export CAPTURE_status_all_usage="${CMD_CAPTURE[status_all_usage]:-}"
export CAPTURE_memory_policy_guard_summary="${CMD_CAPTURE[memory_policy_guard_summary]:-}"

python3 - "$runtime_manifest" "$runtime_ledger_entry" <<'PY'
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

manifest_path = Path(sys.argv[1])
runtime_ledger_entry_path = Path(sys.argv[2])

cfg_path = Path(os.environ["CFG_PATH"])
root = Path(os.environ["ROOT"])

secret_key = re.compile(r"(api[_-]?key|token|authorization|password|secret|botToken)", re.I)
long_opaque = re.compile(r"[A-Za-z0-9+/_=-]{24,}")

redaction_count = 0

def redact(value, key=""):
    global redaction_count
    if isinstance(value, dict):
        out = OrderedDict()
        for k in sorted(value.keys()):
            out[k] = redact(value[k], k)
        return out
    if isinstance(value, list):
        return [redact(x, key) for x in value]
    if isinstance(value, str):
        if secret_key.search(key):
            redaction_count += 1
            return "[REDACTED]"
        replaced, n = long_opaque.subn("[REDACTED_LONG]", value)
        redaction_count += n
        return replaced
    return value

def read_capture(env_name: str) -> str:
    path = os.environ.get(env_name, "")
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")

def read_json_from_capture(env_name: str) -> dict:
    raw = read_capture(env_name)
    if not raw:
        return {}
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}
    try:
        return json.loads(raw[start:end + 1])
    except Exception:
        return {}

cfg_obj = {}
if cfg_path.exists():
    try:
        cfg_obj = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        cfg_obj = {}

redacted_cfg = redact(cfg_obj)
norm = json.dumps(redacted_cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
guardrails_fingerprint = hashlib.sha256(norm.encode("utf-8")).hexdigest()

agent = "main"
surface = "unknown"
model = "unknown"
think_level = "unknown"
gateway_mode = "unknown"
if isinstance(cfg_obj, dict):
    agent = str((((cfg_obj.get("agents") or {}).get("defaults") or {}).get("agent")) or "main")
    model = str((((cfg_obj.get("agents") or {}).get("defaults") or {}).get("model") or {}).get("primary") or "unknown")
    think_level = str((((cfg_obj.get("agents") or {}).get("defaults") or {}).get("thinkingDefault")) or "unknown")
    channels = [k for k, v in sorted((cfg_obj.get("channels") or {}).items()) if not isinstance(v, dict) or v.get("enabled", True) is not False]
    surface = channels[0] if channels else "unknown"
    gateway_mode = str((((cfg_obj.get("gateway") or {}).get("mode")) or "unknown"))

usage_re = re.compile(r"^\s*-\s*([a-z0-9-]+)\s+usage:\s*(.+)$", re.I)
pct_re = re.compile(r"(\d{1,3})%\s+left", re.I)
budget_snapshot = OrderedDict()
for line in "\n".join([read_capture("CAPTURE_models_status_probe"), read_capture("CAPTURE_status_all_usage")]).splitlines():
    m = usage_re.search(line)
    if not m:
        continue
    provider = m.group(1).lower()
    summary = m.group(2).strip()
    pcts = [int(x) for x in pct_re.findall(summary)]
    budget_snapshot[provider] = OrderedDict([
        ("summary", summary),
        ("min_percent_left", min(pcts) if pcts else None),
    ])

tripwire_min_percent = int(os.environ.get("OPENCLAW_BUDGET_MIN_PERCENT_LEFT", "20"))
tripwire_triggered = any(v.get("min_percent_left") is not None and v["min_percent_left"] < tripwire_min_percent for v in budget_snapshot.values())
memory_policy_summary = read_json_from_capture("CAPTURE_memory_policy_guard_summary")
memory_policy_ok = bool(memory_policy_summary.get("policy_ok", False))
memory_policy_violations_count = int(memory_policy_summary.get("violations_count", 0) or 0)
last_recall_sources = [s for s in os.environ.get("LAST_RECALL_SOURCES", "").split(",") if s]
last_recall = OrderedDict([
    ("query_hash", os.environ.get("LAST_RECALL_QUERY_HASH", "")),
    ("hit_count", int(os.environ.get("LAST_RECALL_HIT_COUNT", "0") or 0)),
    ("sources", last_recall_sources),
    ("timestamp_utc", os.environ.get("LAST_RECALL_TIMESTAMP_UTC", "")),
])

try:
    coo_wrapper_version = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], text=True).strip()
except Exception:
    coo_wrapper_version = "unknown"

try:
    openclaw_version = subprocess.check_output(["openclaw", "--version"], text=True).strip()
except Exception:
    openclaw_version = "unknown"

exit_codes = OrderedDict()
for key in [
    "coo_path",
    "coo_symlink",
    "openclaw_version",
    "security_audit_deep",
    "memory_policy_guard_summary",
    "memory_status_main",
    "channels_status_json",
    "models_status_probe",
    "status_all_usage",
    "sandbox_explain_json",
    "gateway_probe_json",
]:
    exit_codes[key] = int(os.environ.get(f"RC_{key}", "1"))

exit_code = 0 if all(v == 0 for v in exit_codes.values()) else 1

entry = OrderedDict()
entry["ts_utc"] = os.environ["TS_UTC"]
entry["coo_wrapper_version"] = coo_wrapper_version
entry["openclaw_version"] = openclaw_version
entry["gateway_mode"] = gateway_mode
entry["agent"] = agent
entry["surface"] = surface
entry["model"] = model
entry["think_level"] = think_level
entry["guardrails_fingerprint"] = guardrails_fingerprint
entry["receipt_path_runtime"] = os.environ["runtime_receipt"]
entry["exit_code"] = exit_code
entry["redactions_applied"] = redaction_count > 0
entry["redaction_count"] = redaction_count
entry["budget_tripwire_min_percent_left"] = tripwire_min_percent
entry["budget_tripwire_triggered"] = tripwire_triggered
entry["budget_snapshot"] = budget_snapshot
entry["memory_policy_ok"] = memory_policy_ok
entry["memory_policy_violations_count"] = memory_policy_violations_count
entry["recall_trace_enabled"] = str(os.environ.get("RECALL_TRACE_ENABLED", "false")).lower() == "true"
entry["last_recall"] = last_recall
entry["security_audit_mode"] = os.environ.get("SECURITY_AUDIT_MODE", "unknown")
entry["confinement_detected"] = bool(os.environ.get("CONFINEMENT_FLAG", ""))
if os.environ.get("CONFINEMENT_FLAG"):
    entry["confinement_flag"] = os.environ["CONFINEMENT_FLAG"]
if os.environ.get("NOTES"):
    entry["notes"] = os.environ["NOTES"]

manifest = OrderedDict()
manifest["ts_utc"] = os.environ["TS_UTC"]
manifest["mode"] = "runtime-default"
manifest["runtime_receipt"] = os.environ["runtime_receipt"]
manifest["ledger_path"] = os.environ["ledger_file"]
manifest["guardrails_fingerprint"] = guardrails_fingerprint
manifest["budget_tripwire_min_percent_left"] = tripwire_min_percent
manifest["budget_tripwire_triggered"] = tripwire_triggered
manifest["budget_snapshot"] = budget_snapshot
manifest["memory_policy_ok"] = memory_policy_ok
manifest["memory_policy_violations_count"] = memory_policy_violations_count
manifest["recall_trace_enabled"] = str(os.environ.get("RECALL_TRACE_ENABLED", "false")).lower() == "true"
manifest["last_recall"] = last_recall
manifest["security_audit_mode"] = os.environ.get("SECURITY_AUDIT_MODE", "unknown")
manifest["confinement_detected"] = bool(os.environ.get("CONFINEMENT_FLAG", ""))
if os.environ.get("CONFINEMENT_FLAG"):
    manifest["confinement_flag"] = os.environ["CONFINEMENT_FLAG"]
manifest["exit_codes"] = exit_codes

manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
runtime_ledger_entry_path.write_text(json.dumps(entry, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")
PY

cat "$runtime_ledger_entry" >> "$ledger_file"

runtime/tools/openclaw_leak_scan.sh "$runtime_receipt" "$runtime_ledger_entry" >/dev/null

if [ "$EXPORT_REPO" -eq 1 ]; then
  mkdir -p "$(dirname "$export_receipt")"
  cp "$runtime_receipt" "$export_receipt"
  runtime/tools/openclaw_leak_scan.sh "$export_receipt" >/dev/null
fi

printf '%s\n' "$runtime_receipt"
printf '%s\n' "$runtime_manifest"
printf '%s\n' "$runtime_ledger_entry"
printf '%s\n' "$ledger_file"
if [ "$EXPORT_REPO" -eq 1 ]; then
  printf '%s\n' "$export_receipt"
fi
```

### File: runtime/tools/OPENCLAW_COO_RUNBOOK.md
```markdown
# OpenClaw COO Runbook

## Canonical Commands

- OpenClaw operations: `coo openclaw -- <args>`
- Shell/process operations: `coo run -- <command>`

## Receipts (Runtime Default)

Canonical operator path is runtime-only receipts (no repo writes by default):

- `$OPENCLAW_STATE_DIR/receipts/<UTC_TS>/Receipt_Bundle_OpenClaw.md`
- `$OPENCLAW_STATE_DIR/receipts/<UTC_TS>/receipt_manifest.json`
- `$OPENCLAW_STATE_DIR/receipts/<UTC_TS>/openclaw_run_ledger_entry.jsonl`
- `$OPENCLAW_STATE_DIR/ledger/openclaw_run_ledger.jsonl`

If `$OPENCLAW_STATE_DIR` is not writable, scripts fall back to `/tmp/openclaw-runtime/...`.

Run default mode:

```bash
runtime/tools/openclaw_receipts_bundle.sh
```

Optional explicit repo export (copy-only):

```bash
runtime/tools/openclaw_receipts_bundle.sh --export-repo
```

Export path:

- `artifacts/evidence/openclaw/receipts/Receipt_Bundle_OpenClaw_<UTC_TS>.md`

Export is optional and should only be used when a repo-local evidence copy is required.

## Verify Surface

Run full verify flow (security/model/sandbox/gateway checks + receipt generation + ledger append + leak scan):

```bash
runtime/tools/openclaw_verify_surface.sh
```

Expected output:

- `PASS security_audit_mode=<mode> confinement_detected=<true|false> ... runtime_receipt=<path> ledger_path=<path>`
- or `FAIL security_audit_mode=<mode> confinement_detected=<true|false> ... runtime_receipt=<path> ledger_path=<path>`

Security audit strategy:

- `security audit --deep` is attempted first.
- If deep fails with known host confinement signature
  `uv_interface_addresses returned Unknown system error 1`,
  verify runs bounded fallback `security audit` (non-deep).
- Any other deep failure remains fail-closed and verify returns non-zero.
- When fallback triggers, verify and ledger include:
  `confinement_detected=true` and
  `confinement_flag=uv_interface_addresses_unknown_system_error_1`.

Model policy assertion:

```bash
python3 runtime/tools/openclaw_policy_assert.py --json
```

Optional memory verifier (not part of P0 security PASS path):

```bash
runtime/tools/openclaw_verify_memory.sh
```

Expected output:

- `PASS memory_policy_ok=true provider=local fallback=none ...`
- or `FAIL memory_policy_ok=false provider=<x> fallback=<y> ...`

Safe memory indexing wrapper (guarded):

```bash
runtime/tools/openclaw_memory_index_safe.sh
```

Behavior:

- Runs `runtime/tools/openclaw_memory_policy_guard.py` first (fail-closed).
- Runs `coo openclaw -- memory index --agent main --verbose` only when guard passes.

Optional interfaces verifier (Telegram hardening posture):

```bash
runtime/tools/openclaw_verify_interfaces.sh
```

Expected output:

- `PASS telegram_posture=allowlist+requireMention replyToMode=first ...`
- or `FAIL telegram_posture=allowlist+requireMention replyToMode=<x> ...`

Grounded recall verifier (memory ↔ interface contract):

```bash
runtime/tools/openclaw_verify_recall_e2e.sh
```

Expected output:

- `PASS recall_mode=telegram_sim|cli_only sources_present=true MANUAL_SMOKE_REQUIRED=<true|false> ...`
- or `FAIL recall_mode=... sources_present=false ...`

Recall contract:

- Recall/decision intents must use memory search first.
- Answers must include a `Sources:` section with `file:line-range` pointers.
- If no hits, response must be: `No grounded memory found. Which timeframe or document should I check?`
- Receipts/ledger store recall metadata only (`query_hash`, hit count, sources), never raw query content.

## Telegram Hardening

- `channels.telegram.allowFrom` must be non-empty and must not include `"*"`.
- `channels.telegram.groups` must use explicit group IDs (no `"*"`), with `requireMention: true`.
- `agents.list[].groupChat.mentionPatterns` should include stable mention triggers (for example `@openclaw`, `openclaw`).
- `messages.groupChat.historyLimit` should stay conservative (30-50).
- `channels.telegram.replyToMode` uses `first` for predictable threading.

## Slack Scaffold (Blocked Until Tokens)

Slack is scaffolded in secure-by-default mode only:

- `channels.slack.enabled=false`
- optional HTTP wiring keys only (`mode="http"`, `webhookPath="/slack/events"`)
- no `botToken`, `appToken`, or `signingSecret` in config

HTTP mode setup (when provisioning is approved):

1. Create Slack app and copy Signing Secret + Bot Token.
2. Configure `channels.slack.mode="http"` and `channels.slack.webhookPath="/slack/events"`.
3. Set Slack Event Subscriptions, Interactivity, and Slash Command Request URL to `/slack/events`.
4. Keep channel disabled until tokens are injected and validated.

## Safety Invariants

- Default receipt generation must not write to repo paths.
- Ledger and receipts must remain redacted-safe.
- Leak scan must pass for runtime receipt + runtime ledger entry.
- Verify is fail-closed on security audit, sandbox invariants, and policy assertion.
- Receipts include a non-deep memory status capture; they do not run memory index by default.
- Receipts include memory policy guard summary status (`memory_policy_ok`, violation count).
- Receipts include recall trace metadata (`recall_trace_enabled`, `last_recall`).
- Receipts include a non-deep channels status capture and never include Slack secrets.
```

### File: runtime/tests/test_openclaw_recall_contract.py
```python
from runtime.tools.openclaw_recall_contract import (
    build_contract_response,
    is_recall_intent,
    parse_sources,
)


def test_recall_intent_detected():
    assert is_recall_intent("what did we decide last week?")
    assert is_recall_intent("please recall the decision")
    assert not is_recall_intent("say hello")


def test_sources_parsed_from_memory_search_output():
    output = """
0.854 memory/daily/2026-02-10.md:1-5
snippet text
0.458 MEMORY.md:1-10
"""
    sources = parse_sources(output)
    assert sources == ["memory/daily/2026-02-10.md:1-5", "MEMORY.md:1-10"]


def test_contract_response_includes_sources_for_recall_with_hits():
    output = "0.854 memory/daily/2026-02-10.md:1-5\n"
    result = build_contract_response("what did we decide last week?", output)
    assert result["recall_intent"] is True
    assert result["hit_count"] == 1
    assert "Sources:" in result["response"]
    assert "memory/daily/2026-02-10.md:1-5" in result["response"]


def test_contract_response_fails_closed_for_no_hits():
    result = build_contract_response("what did we decide last week?", "")
    assert result["recall_intent"] is True
    assert result["hit_count"] == 0
    assert result["response"] == "No grounded memory found. Which timeframe or document should I check?"
```
