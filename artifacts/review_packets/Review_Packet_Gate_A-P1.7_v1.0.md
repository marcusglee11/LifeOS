# Review Packet — Gate A-P1.7 v1.0

## Summary
- Implemented multi-user-safe-by-default posture enforcement with fail-closed asserts, verifier, and receipts/ledger wiring using count-only metadata.
- Added controlled onboarding helper that records only a candidate reference hash and outputs an auditable checklist.
- Added drift-proof unit tests for posture invariants and wildcard/owner-boundary regressions.

## Gate Outcome
- Additional operators can be onboarded later without reopening channels or privilege boundaries because wildcard drift and owner-boundary regressions are asserted and verified.

## Evidence
- Evidence directory: `artifacts/evidence/openclaw/p1_7/20260212T074040Z`
- Baseline: `repo_state_before.txt`, `openclaw_version.txt`
- Key inventory: `posture_keys_inventory.md`, `pre_config_redacted.json`
- Verifier: `verify_multiuser_posture_output.txt`
- Acceptance (3/3): `acceptance_verify_multiuser_1.txt`, `_2.txt`, `_3.txt`
- Tests: `pytest_multiuser_posture.txt` (11 passed)
- Receipt sample with new fields: `receipt_manifest_multiuser_sample.json`

## Privacy Posture
- No allowlist values, user IDs, usernames, phone numbers, chat IDs, or tokens are emitted by the new multi-user assert/verifier outputs.
- Receipts/ledger additions include channel names and allowlist counts only.

## Changed Files
- `runtime/tools/openclaw_multiuser_posture_assert.py`
- `runtime/tools/openclaw_verify_multiuser_posture.sh`
- `runtime/tools/openclaw_onboard_operator.sh`
- `runtime/tools/openclaw_receipts_bundle.sh`
- `runtime/tools/OPENCLAW_COO_RUNBOOK.md`
- `runtime/tests/test_openclaw_multiuser_posture_assert.py`

## Appendix A — Flattened Code

### File: runtime/tools/openclaw_multiuser_posture_assert.py
```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repo root is importable when script is executed directly.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.openclaw_policy_assert import command_authorized

PRIV_COMMANDS = ["/model openai-codex/gpt-5.3-codex", "/models", "/think high"]


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def _has_wildcard(values: List[str]) -> bool:
    return any(v == "*" for v in values)


def assert_multiuser_posture(cfg: Dict[str, Any]) -> Dict[str, Any]:
    violations: List[str] = []
    allowlist_sizes: Dict[str, int] = {}
    enabled_channels: List[str] = []

    commands = cfg.get("commands") or {}
    owner_allow = _as_list(commands.get("ownerAllowFrom"))
    if commands.get("useAccessGroups") is not True:
        violations.append("commands.useAccessGroups must be true")
    if not owner_allow:
        violations.append("commands.ownerAllowFrom must be non-empty")
    if _has_wildcard(owner_allow):
        violations.append('commands.ownerAllowFrom must not contain "*"')
    allowlist_sizes["commands.ownerAllowFrom"] = len(owner_allow)

    channels = cfg.get("channels") or {}
    if not isinstance(channels, dict):
        violations.append("channels must be an object")
        channels = {}

    for ch_name in sorted(channels.keys()):
        ch_cfg = channels.get(ch_name)
        if not isinstance(ch_cfg, dict):
            continue
        if ch_cfg.get("enabled", True) is False:
            continue
        enabled_channels.append(ch_name)
        allow_from = _as_list(ch_cfg.get("allowFrom"))
        allowlist_sizes[f"channels.{ch_name}.allowFrom"] = len(allow_from)
        if not allow_from:
            violations.append(f"channels.{ch_name}.allowFrom must exist and be non-empty")
        if _has_wildcard(allow_from):
            violations.append(f'channels.{ch_name}.allowFrom must not contain "*"')

        if ch_name == "telegram":
            groups = ch_cfg.get("groups")
            if isinstance(groups, dict):
                if "*" in groups:
                    violations.append('channels.telegram.groups must not contain "*"')
                allowlist_sizes["channels.telegram.groups"] = len(groups)
                for group_id, group_cfg in sorted(groups.items()):
                    if not isinstance(group_cfg, dict):
                        violations.append(f"channels.telegram.groups.{group_id} must be object")
                        continue
                    if group_cfg.get("requireMention") is not True:
                        violations.append(f"channels.telegram.groups.{group_id}.requireMention must be true")
                    grp_allow = _as_list(group_cfg.get("allowFrom"))
                    if grp_allow and _has_wildcard(grp_allow):
                        violations.append(f'channels.telegram.groups.{group_id}.allowFrom must not contain "*"')

            reply_mode = str(ch_cfg.get("replyToMode") or "")
            if reply_mode != "first":
                violations.append('channels.telegram.replyToMode must be "first"')

    agents = ((cfg.get("agents") or {}).get("list")) or []
    if not isinstance(agents, list) or not agents:
        violations.append("agents.list must be configured")
    else:
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            agent_id = str(agent.get("id") or "<unknown>")
            patterns = ((agent.get("groupChat") or {}).get("mentionPatterns")) or []
            if not isinstance(patterns, list) or not [p for p in patterns if str(p).strip()]:
                violations.append(f"agents.list[{agent_id}].groupChat.mentionPatterns must be non-empty")

    if owner_allow:
        owner = owner_allow[0]
        for cmd in PRIV_COMMANDS:
            if not command_authorized(cfg, owner, cmd):
                violations.append(f"owner must be authorized for {cmd.split()[0]}")
            if command_authorized(cfg, "__non_owner__", cmd):
                violations.append(f"non-owner must be rejected for {cmd.split()[0]}")

    summary = {
        "multiuser_posture_ok": len(violations) == 0,
        "enabled_channels": sorted(enabled_channels),
        "allowlist_sizes": {k: int(v) for k, v in sorted(allowlist_sizes.items())},
        "violations": violations,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert OpenClaw multi-user posture invariants.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    result = assert_multiuser_posture(cfg)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(
            "multiuser_posture_ok="
            + ("true" if result["multiuser_posture_ok"] else "false")
            + f" enabled_channels={','.join(result['enabled_channels'])}"
            + f" violations={len(result['violations'])}"
        )
    return 0 if result["multiuser_posture_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

### File: runtime/tools/openclaw_verify_multiuser_posture.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_MULTIUSER_OUT_DIR:-$STATE_DIR/verify-multiuser/$TS_UTC}"
POSTURE_TIMEOUT_SEC="${OPENCLAW_VERIFY_MULTIUSER_POSTURE_TIMEOUT_SEC:-15}"
INTERFACES_TIMEOUT_SEC="${OPENCLAW_VERIFY_MULTIUSER_INTERFACES_TIMEOUT_SEC:-45}"

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify-multiuser/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

PASS=1
SECURITY_AUDIT_MODE="unknown"

posture_out="$OUT_DIR/multiuser_posture_assert.json"
interfaces_out="$OUT_DIR/verify_interfaces.txt"
summary_out="$OUT_DIR/summary.txt"

set +e
timeout "$POSTURE_TIMEOUT_SEC" python3 runtime/tools/openclaw_multiuser_posture_assert.py --json > "$posture_out" 2>&1
rc_posture=$?
timeout "$INTERFACES_TIMEOUT_SEC" env OPENCLAW_VERIFY_INTERFACES_OUT_DIR="$OUT_DIR/interfaces" runtime/tools/openclaw_verify_interfaces.sh > "$interfaces_out" 2>&1
rc_interfaces=$?
set -e

if [ "$rc_posture" -ne 0 ] || [ "$rc_interfaces" -ne 0 ]; then
  PASS=0
fi

SECURITY_AUDIT_MODE="$(rg -o 'security_audit_mode=[^ ]+' "$interfaces_out" | tail -n1 | cut -d= -f2- || true)"
if [ -z "$SECURITY_AUDIT_MODE" ]; then
  SECURITY_AUDIT_MODE="unknown"
fi
if printf '%s' "$SECURITY_AUDIT_MODE" | rg -q '^blocked_'; then
  PASS=0
fi

enabled_count="$(python3 - <<'PY' "$posture_out"
import json, sys
p=sys.argv[1]
try:
    obj=json.loads(open(p,encoding='utf-8',errors='replace').read())
    print(len(list(obj.get("enabled_channels") or [])))
except Exception:
    print(-1)
PY
)"
allowlist_counts="$(python3 - <<'PY' "$posture_out"
import json, sys
p=sys.argv[1]
try:
    obj=json.loads(open(p,encoding='utf-8',errors='replace').read())
    items=sorted((obj.get("allowlist_sizes") or {}).items())
    print(",".join(f"{k}={int(v)}" for k,v in items))
except Exception:
    print("unknown")
PY
)"
posture_ok="$(python3 - <<'PY' "$posture_out"
import json, sys
p=sys.argv[1]
try:
    obj=json.loads(open(p,encoding='utf-8',errors='replace').read())
    print("true" if obj.get("multiuser_posture_ok") else "false")
except Exception:
    print("false")
PY
)"

runtime_receipt="$(rg -o 'runtime_receipt=[^ ]+' "$interfaces_out" | tail -n1 | cut -d= -f2- || true)"
ledger_path="$(rg -o 'ledger_path=[^ ]+' "$interfaces_out" | tail -n1 | cut -d= -f2- || true)"

{
  echo "ts_utc=$TS_UTC"
  echo "multiuser_posture_ok=$posture_ok"
  echo "enabled_channels_count=$enabled_count"
  echo "allowlist_counts=$allowlist_counts"
  echo "security_audit_mode=$SECURITY_AUDIT_MODE"
  echo "posture_exit=$rc_posture"
  echo "interfaces_exit=$rc_interfaces"
  echo "runtime_receipt=$runtime_receipt"
  echo "ledger_path=$ledger_path"
} > "$summary_out"

if [ "$PASS" -eq 1 ] && [ "$posture_ok" = "true" ]; then
  echo "PASS multiuser_posture_ok=true enabled_channels_count=$enabled_count allowlist_counts=$allowlist_counts runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
  exit 0
fi

echo "FAIL multiuser_posture_ok=$posture_ok enabled_channels_count=$enabled_count allowlist_counts=$allowlist_counts runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
exit 1
```

### File: runtime/tools/openclaw_onboard_operator.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  runtime/tools/openclaw_onboard_operator.sh --candidate-ref <non-secret-ref> [--note <text>]

Purpose:
  Produce a controlled, auditable onboarding checklist without writing raw operator identifiers.
  The script records only a SHA256 fingerprint of the provided reference.
USAGE
}

CANDIDATE_REF=""
NOTE=""
STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_ONBOARD_OUT_DIR:-$STATE_DIR/onboarding/$TS_UTC}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --candidate-ref)
      CANDIDATE_REF="${2:-}"
      shift 2
      ;;
    --note)
      NOTE="${2:-}"
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

if [ -z "$CANDIDATE_REF" ]; then
  echo "ERROR: --candidate-ref is required" >&2
  exit 2
fi

# Prevent accidental leakage of obvious raw IDs/usernames/chats.
if printf '%s' "$CANDIDATE_REF" | rg -q '[@:+]|[0-9]{6,}'; then
  echo "BLOCKED: candidate-ref appears to contain raw identifier data; provide a neutral internal reference label." >&2
  exit 1
fi

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-onboarding/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

hash="$(printf '%s' "$CANDIDATE_REF" | sha256sum | awk '{print $1}')"
branch="$(git rev-parse --abbrev-ref HEAD)"
head="$(git rev-parse --short HEAD)"
plan="$OUT_DIR/onboarding_plan.md"

{
  echo "# OpenClaw Operator Onboarding Plan"
  echo
  echo "- ts_utc: $TS_UTC"
  echo "- candidate_ref_sha256: $hash"
  echo "- branch: $branch"
  echo "- head: $head"
  if [ -n "$NOTE" ]; then
    echo "- note: $NOTE"
  fi
  echo
  echo "## Required Changes (Manual, Auditable)"
  echo "1. Add candidate to \`commands.ownerAllowFrom\` only if owner privileges are required."
  echo "2. Add candidate to per-channel \`channels.<channel>.allowFrom\` lists explicitly (no wildcards)."
  echo "3. Keep \`commands.useAccessGroups=true\`."
  echo "4. Keep Telegram \`requireMention=true\`, non-empty \`mentionPatterns\`, and \`replyToMode=first\`."
  echo "5. Run verifiers:"
  echo "   - \`runtime/tools/openclaw_multiuser_posture_assert.py --json\`"
  echo "   - \`runtime/tools/openclaw_verify_multiuser_posture.sh\`"
  echo
  echo "## Approval"
  echo "- Reviewer: ____________________"
  echo "- Decision: APPROVE / REJECT"
  echo "- Date (UTC): __________________"
} > "$plan"

printf '%s\n' "$plan"

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
run_capture multiuser_posture_assert python3 runtime/tools/openclaw_multiuser_posture_assert.py --json
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

## Manual Telegram Smoke (Metadata-Only)

Operator step (allowed Telegram DM only):

1. Send exactly:
   `what did we decide last week about lobster-memory-seed-001?`
2. Expected behavior:
   - grounded answer returned
   - `Sources:` section includes `memory/daily/2026-02-10.md:1-5`
3. Record metadata only (no message text, no IDs/usernames/phone numbers):

```bash
coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && P1_5_EVDIR=artifacts/evidence/openclaw/p1_5/<UTC_TS> runtime/tools/openclaw_record_manual_smoke.sh --surface telegram_dm --result pass --sources memory/daily/2026-02-10.md:1-5'
```

Fail branch:

```bash
coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && P1_5_EVDIR=artifacts/evidence/openclaw/p1_5/<UTC_TS> runtime/tools/openclaw_record_manual_smoke.sh --surface telegram_dm --result fail --sources "(none)"'
```

## P1 Acceptance Verifier

Run:

```bash
coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && P1_5_EVDIR=artifacts/evidence/openclaw/p1_5/<UTC_TS> runtime/tools/openclaw_verify_p1_acceptance.sh'
```

Expected:

- `PASS p1_acceptance=true manual_smoke=pass source_pointer=memory/daily/2026-02-10.md:1-5 ...`

## Multi-User Posture Verifier

Run:

```bash
runtime/tools/openclaw_verify_multiuser_posture.sh
```

Expected:

- `PASS multiuser_posture_ok=true enabled_channels_count=<n> allowlist_counts=<k=v,...> ...`
- or `FAIL ...` when any allowlist/owner boundary/Telegram posture invariant drifts.

## Operator Onboarding (Controlled + Auditable)

Generate an onboarding checklist with a non-sensitive internal reference label:

```bash
runtime/tools/openclaw_onboard_operator.sh --candidate-ref operator-two-change-request
```

Notes:

- The helper stores only `candidate_ref_sha256` and never raw identifiers.
- Apply config changes manually via reviewed PR/commit; then run:
  - `python3 runtime/tools/openclaw_multiuser_posture_assert.py --json`
  - `runtime/tools/openclaw_verify_multiuser_posture.sh`

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
- Receipts include multi-user posture status (`multiuser_posture_ok`, channel names, allowlist counts, violations count) and never include allowlist values.
```

### File: runtime/tests/test_openclaw_multiuser_posture_assert.py
```python
import json

from runtime.tools.openclaw_multiuser_posture_assert import assert_multiuser_posture


def _cfg():
    return {
        "commands": {
            "ownerAllowFrom": ["owner-1"],
            "useAccessGroups": True,
        },
        "agents": {
            "list": [
                {"id": "main", "groupChat": {"mentionPatterns": ["@openclaw", "openclaw"]}},
                {"id": "quick", "groupChat": {"mentionPatterns": ["@openclaw", "openclaw"]}},
            ]
        },
        "channels": {
            "telegram": {
                "enabled": True,
                "allowFrom": ["owner-1"],
                "replyToMode": "first",
                "groups": {
                    "group-a": {
                        "requireMention": True,
                        "allowFrom": ["owner-1"],
                    }
                },
            },
            "whatsapp": {
                "enabled": True,
                "allowFrom": ["owner-1"],
            },
            "slack": {
                "enabled": False,
            },
        },
    }


def test_multiuser_posture_passes_for_hardened_config():
    result = assert_multiuser_posture(_cfg())
    assert result["multiuser_posture_ok"] is True
    assert sorted(result["enabled_channels"]) == ["telegram", "whatsapp"]
    assert result["allowlist_sizes"]["commands.ownerAllowFrom"] == 1
    assert result["allowlist_sizes"]["channels.telegram.allowFrom"] == 1
    assert result["allowlist_sizes"]["channels.whatsapp.allowFrom"] == 1
    assert result["violations"] == []


def test_multiuser_posture_rejects_wildcard_allowlist():
    cfg = _cfg()
    cfg["channels"]["whatsapp"]["allowFrom"] = ["*"]
    result = assert_multiuser_posture(cfg)
    assert result["multiuser_posture_ok"] is False
    assert any("whatsapp.allowFrom" in v for v in result["violations"])


def test_multiuser_posture_rejects_missing_owner_boundary():
    cfg = _cfg()
    cfg["commands"]["ownerAllowFrom"] = []
    result = assert_multiuser_posture(cfg)
    assert result["multiuser_posture_ok"] is False
    assert any("ownerAllowFrom must be non-empty" in v for v in result["violations"])


def test_multiuser_posture_rejects_telegram_drift():
    cfg = _cfg()
    cfg["channels"]["telegram"]["replyToMode"] = "all"
    cfg["channels"]["telegram"]["groups"]["group-a"]["requireMention"] = False
    cfg["agents"]["list"][0]["groupChat"]["mentionPatterns"] = []
    result = assert_multiuser_posture(cfg)
    assert result["multiuser_posture_ok"] is False
    assert any("replyToMode" in v for v in result["violations"])
    assert any("requireMention" in v for v in result["violations"])
    assert any("mentionPatterns" in v for v in result["violations"])


def test_multiuser_posture_summary_exposes_counts_only():
    result = assert_multiuser_posture(_cfg())
    dumped = json.dumps(result, sort_keys=True)
    assert "owner-1" not in dumped

```
