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
  multiuser_posture_assert
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
    -e 's/\b(gh[opurs]_[A-Za-z0-9]{6})[A-Za-z0-9]+/\1...[REDACTED]/g' \
    -e 's/\b(sk-[A-Za-z0-9_-]{6})[A-Za-z0-9_-]+/\1...[REDACTED]/g' \
    -e 's/\b(sk-ant-[A-Za-z0-9_-]{6})[A-Za-z0-9_-]+/\1...[REDACTED]/g' \
    -e 's/\b(AIza[0-9A-Za-z_-]{6})[0-9A-Za-z_-]+/\1...[REDACTED]/g' \
    -e 's/\b(ya29\.[0-9A-Za-z._-]{6})[0-9A-Za-z._-]+/\1...[REDACTED]/g' \
    -e 's/\b(xox[aboprs]-[A-Za-z0-9-]{6})[A-Za-z0-9-]+/\1...[REDACTED]/g' \
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
run_capture multiuser_posture_assert python3 runtime/tools/openclaw_multiuser_posture_assert.py --json
run_capture memory_status_main coo openclaw -- memory status --agent main
run_capture channels_status_json coo openclaw -- channels status --json
run_capture models_status_probe coo openclaw -- models status
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
export CAPTURE_multiuser_posture_assert="${CMD_CAPTURE[multiuser_posture_assert]:-}"

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
multiuser_summary = read_json_from_capture("CAPTURE_multiuser_posture_assert")
multiuser_posture_ok = bool(multiuser_summary.get("multiuser_posture_ok", False))
multiuser_enabled_channels = [str(x) for x in (multiuser_summary.get("enabled_channels") or [])]
multiuser_allowlist_sizes = {
    str(k): int(v)
    for k, v in sorted((multiuser_summary.get("allowlist_sizes") or {}).items())
    if str(k).strip()
}
multiuser_violations_count = len(list(multiuser_summary.get("violations") or []))
slack_cfg = {}
if isinstance(cfg_obj, dict):
    channels_obj = cfg_obj.get("channels") or {}
    if isinstance(channels_obj, dict):
        raw_slack = channels_obj.get("slack")
        if isinstance(raw_slack, dict):
            slack_cfg = raw_slack
slack_base_enabled = bool(slack_cfg.get("enabled") is True)
slack_secret_keys = [
    key for key in ("appToken", "botToken", "signingSecret")
    if str(slack_cfg.get(key) or "").strip()
]
slack_secrets_in_base = bool(slack_secret_keys)
slack_overlay_last_mode = str(os.environ.get("OPENCLAW_SLACK_OVERLAY_LAST_MODE") or slack_cfg.get("mode") or "unknown")
if slack_overlay_last_mode == "http":
    slack_env_present = bool(os.environ.get("OPENCLAW_SLACK_BOT_TOKEN")) and bool(os.environ.get("OPENCLAW_SLACK_SIGNING_SECRET"))
elif slack_overlay_last_mode == "socket":
    slack_env_present = bool(os.environ.get("OPENCLAW_SLACK_APP_TOKEN")) and bool(os.environ.get("OPENCLAW_SLACK_BOT_TOKEN"))
else:
    slack_env_present = False
slack_ready_to_enable = (not slack_base_enabled) and (not slack_secrets_in_base)
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
    "multiuser_posture_assert",
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
entry["multiuser_posture_ok"] = multiuser_posture_ok
entry["multiuser_enabled_channels"] = multiuser_enabled_channels
entry["multiuser_allowlist_sizes"] = multiuser_allowlist_sizes
entry["multiuser_violations_count"] = multiuser_violations_count
entry["slack_ready_to_enable"] = slack_ready_to_enable
entry["slack_base_enabled"] = slack_base_enabled
entry["slack_env_present"] = slack_env_present
entry["slack_overlay_last_mode"] = slack_overlay_last_mode
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
manifest["multiuser_posture_ok"] = multiuser_posture_ok
manifest["multiuser_enabled_channels"] = multiuser_enabled_channels
manifest["multiuser_allowlist_sizes"] = multiuser_allowlist_sizes
manifest["multiuser_violations_count"] = multiuser_violations_count
manifest["slack_ready_to_enable"] = slack_ready_to_enable
manifest["slack_base_enabled"] = slack_base_enabled
manifest["slack_env_present"] = slack_env_present
manifest["slack_overlay_last_mode"] = slack_overlay_last_mode
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
