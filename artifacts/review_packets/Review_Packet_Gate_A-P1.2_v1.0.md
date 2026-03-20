# Review Packet — Gate A-P1.2 v1.0

## Summary
Gate A-P1.2 is implemented with Telegram hardening + deterministic interface verification, and Slack scaffolded in secure-by-default blocked mode.

Implemented outcomes:
- Telegram posture hardened:
  - explicit DM allowlist (`allowFrom`, no `"*"`)
  - explicit group allowlist object (`groups`, no `"*"`)
  - `requireMention: true` on configured groups
  - `agents.list[].groupChat.mentionPatterns` set
  - `replyToMode: "first"`
  - conservative `messages.groupChat.historyLimit=40`
- Slack scaffolded but blocked:
  - `channels.slack.enabled=false`
  - no Slack secrets in config
  - template manifest added for future provisioning
- New verifier: `runtime/tools/openclaw_verify_interfaces.sh`
- Receipts now capture non-deep channels status safely.

## Security Posture Invariants
- Telegram trigger surface is allowlist-only, mention-gated for groups.
- Command path remains closed with `commands.useAccessGroups=true`.
- Slack remains disabled and tokenless.
- Interface verifier is fail-closed on posture violations.

## Acceptance Evidence Pointers
Evidence directory:
- `artifacts/evidence/openclaw/p1_2/20260210T233902Z`

Key files:
- `repo_state_before.txt`
- `openclaw_version.txt`
- `pre_channels_status.json`
- `pre_security_audit.txt`
- `post_config_redacted.txt`
- `openclaw_config_redacted.diff`
- `post_channels_status.json`
- `post_security_audit.txt`
- `acceptance_verify_interfaces_1.txt`
- `acceptance_verify_interfaces_2.txt`
- `acceptance_verify_interfaces_3.txt`
- `pytest_interfaces_policy_assert.txt`
- `decision_note.md`

Acceptance result:
- 3/3 PASS under exact command:
  - `timeout 45s coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && runtime/tools/openclaw_verify_interfaces.sh'`

## Slack BLOCKED Until Tokens Provisioned
- Slack is intentionally not operational in this gate.
- Future enablement requires provisioning `botToken` + `signingSecret` (and optional app/user tokens) outside repo evidence artifacts.
- Template manifest for app setup is provided at:
  - `artifacts/templates/openclaw/slack_app_manifest.json`

## Appendix A — Flattened Code (All Changed Files)

### File: runtime/tools/openclaw_interfaces_policy_assert.py
```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

KNOWN_TELEGRAM_REPLY_MODES = {"first", "all", "off"}
SLACK_SECRET_KEYS = {"botToken", "appToken", "userToken", "signingSecret", "token", "webhookSecret"}


def _must_list(value: Any, path: str) -> List[str]:
    if not isinstance(value, list):
        raise AssertionError(f"{path} must be a list")
    return [str(x) for x in value]


def _assert_telegram(cfg: Dict[str, Any]) -> Dict[str, Any]:
    channels = cfg.get("channels") or {}
    telegram = channels.get("telegram")
    if not isinstance(telegram, dict):
        raise AssertionError("channels.telegram must exist")
    if telegram.get("enabled") is not True:
        raise AssertionError("channels.telegram.enabled must be true")

    allow_from = _must_list(telegram.get("allowFrom"), "channels.telegram.allowFrom")
    if not allow_from:
        raise AssertionError("channels.telegram.allowFrom must be non-empty")
    if "*" in allow_from:
        raise AssertionError('channels.telegram.allowFrom must not include "*"')

    groups = telegram.get("groups")
    if not isinstance(groups, dict) or not groups:
        raise AssertionError("channels.telegram.groups must be a non-empty object allowlist")
    if "*" in groups:
        raise AssertionError('channels.telegram.groups must not contain "*" at P1.2')
    for group_id, group_cfg in sorted(groups.items()):
        if not isinstance(group_cfg, dict):
            raise AssertionError(f"channels.telegram.groups.{group_id} must be an object")
        if group_cfg.get("requireMention") is not True:
            raise AssertionError(f"channels.telegram.groups.{group_id}.requireMention must be true")

    reply_mode = str(telegram.get("replyToMode") or "")
    if reply_mode not in KNOWN_TELEGRAM_REPLY_MODES:
        raise AssertionError(f"channels.telegram.replyToMode must be one of {sorted(KNOWN_TELEGRAM_REPLY_MODES)}")
    if reply_mode != "first":
        raise AssertionError(f'channels.telegram.replyToMode must be "first" at P1.2, got {reply_mode}')

    agents = ((cfg.get("agents") or {}).get("list")) or []
    if not isinstance(agents, list) or not agents:
        raise AssertionError("agents.list must be configured")
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        agent_id = str(agent.get("id") or "<unknown>")
        group_chat = agent.get("groupChat") or {}
        patterns = group_chat.get("mentionPatterns")
        if not isinstance(patterns, list) or not [p for p in patterns if str(p).strip()]:
            raise AssertionError(f"agents.list[{agent_id}].groupChat.mentionPatterns must be non-empty")

    commands = cfg.get("commands") or {}
    if commands.get("useAccessGroups") is not True:
        raise AssertionError("commands.useAccessGroups must be true")

    return {
        "allow_from_count": len(allow_from),
        "group_count": len(groups),
        "reply_to_mode": reply_mode,
        "posture": "allowlist+requireMention",
    }


def _assert_slack(cfg: Dict[str, Any]) -> Dict[str, Any]:
    channels = cfg.get("channels") or {}
    slack = channels.get("slack")
    if not isinstance(slack, dict):
        return {"enabled": False, "blocked": True}

    if slack.get("enabled") is not False:
        raise AssertionError("channels.slack.enabled must be false at P1.2")

    mode = str(slack.get("mode") or "")
    if mode and mode != "http":
        raise AssertionError('channels.slack.mode must be "http" when set')
    if mode == "http":
        webhook_path = str(slack.get("webhookPath") or "")
        if webhook_path != "/slack/events":
            raise AssertionError('channels.slack.webhookPath must be "/slack/events" when mode=http')

    for key in SLACK_SECRET_KEYS:
        if key in slack and str(slack.get(key) or "").strip():
            raise AssertionError(f"channels.slack.{key} must not be set at P1.2")

    return {"enabled": False, "blocked": True, "mode": mode or "unset"}


def assert_interfaces_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    telegram = _assert_telegram(cfg)
    slack = _assert_slack(cfg)
    return {"telegram": telegram, "slack": slack}


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert OpenClaw interfaces hardening policy invariants.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    result = assert_interfaces_policy(cfg)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print("INTERFACES_POLICY_ASSERT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### File: runtime/tools/openclaw_verify_interfaces.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_INTERFACES_OUT_DIR:-$STATE_DIR/verify-interfaces/$TS_UTC}"
VERIFY_CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_INTERFACES_TIMEOUT_SEC:-10}"
SECURITY_FALLBACK_TIMEOUT_SEC="${OPENCLAW_VERIFY_INTERFACES_SECURITY_FALLBACK_TIMEOUT_SEC:-14}"
RECEIPT_CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_INTERFACES_RECEIPT_TIMEOUT_SEC:-3}"
KNOWN_UV_IFADDR='uv_interface_addresses returned Unknown system error 1'

mkdir -p "$OUT_DIR"

PASS=1
declare -A CMD_RC
SECURITY_AUDIT_MODE="unknown"
CONFINEMENT_FLAG=""

to_file_with_timeout() {
  local timeout_sec="$1"
  shift
  local name="$1"
  shift
  local out="$OUT_DIR/${name}.txt"
  {
    echo '```bash'
    printf '%q ' "$@"
    echo
    echo '```'
    echo '```text'
    set +e
    timeout "$timeout_sec" "$@"
    rc=$?
    set -e
    echo "[exit_code]=$rc"
    echo '```'
  } > "$out" 2>&1
  CMD_RC["$name"]="$rc"
}

to_file() {
  local name="$1"
  shift
  to_file_with_timeout "$VERIFY_CMD_TIMEOUT_SEC" "$name" "$@"
}

to_file channels_status_json coo openclaw -- channels status --json

to_file security_audit_deep coo openclaw -- security audit --deep
if [ "${CMD_RC[security_audit_deep]:-1}" -eq 0 ]; then
  SECURITY_AUDIT_MODE="deep"
else
  if rg -q "$KNOWN_UV_IFADDR" "$OUT_DIR/security_audit_deep.txt"; then
    to_file_with_timeout "$SECURITY_FALLBACK_TIMEOUT_SEC" security_audit_fallback coo openclaw -- security audit
    if [ "${CMD_RC[security_audit_fallback]:-1}" -eq 0 ]; then
      SECURITY_AUDIT_MODE="non_deep_fallback_due_uv_interface_addresses"
      CONFINEMENT_FLAG="uv_interface_addresses_unknown_system_error_1"
    else
      PASS=0
      SECURITY_AUDIT_MODE="blocked_fallback_failed"
    fi
  else
    PASS=0
    SECURITY_AUDIT_MODE="blocked_unknown_deep_error"
  fi
fi

to_file interfaces_policy_assert python3 runtime/tools/openclaw_interfaces_policy_assert.py --json
if [ "${CMD_RC[interfaces_policy_assert]:-1}" -ne 0 ]; then
  PASS=0
fi

SECURITY_FILE="$OUT_DIR/security_audit_deep.txt"
if [ "$SECURITY_AUDIT_MODE" = "non_deep_fallback_due_uv_interface_addresses" ]; then
  SECURITY_FILE="$OUT_DIR/security_audit_fallback.txt"
fi
if [ ! -f "$SECURITY_FILE" ]; then PASS=0; fi
if ! rg -q 'Summary:\s*0 critical\s*·\s*0 warn' "$SECURITY_FILE"; then PASS=0; fi

reply_mode="unknown"
if [ -f "$OUT_DIR/interfaces_policy_assert.txt" ]; then
  reply_mode="$(python3 - <<'PY' "$OUT_DIR/interfaces_policy_assert.txt"
import json,sys
p=sys.argv[1]
text=open(p,encoding='utf-8',errors='replace').read()
start=text.find('{')
end=text.rfind('}')
if start == -1 or end == -1 or end < start:
    print("unknown")
else:
    try:
        obj=json.loads(text[start:end+1])
        print(((obj.get("telegram") or {}).get("reply_to_mode")) or "unknown")
    except Exception:
        print("unknown")
PY
)"
fi

receipt_gen="$OUT_DIR/receipt_generation.txt"
set +e
OPENCLAW_CMD_TIMEOUT_SEC="$RECEIPT_CMD_TIMEOUT_SEC" \
OPENCLAW_SECURITY_AUDIT_MODE="$SECURITY_AUDIT_MODE" \
OPENCLAW_CONFINEMENT_FLAG="$CONFINEMENT_FLAG" \
runtime/tools/openclaw_receipts_bundle.sh > "$receipt_gen" 2>&1
rc_receipt=$?
set -e
if [ "$rc_receipt" -ne 0 ]; then PASS=0; fi

runtime_receipt="$(sed -n '1p' "$receipt_gen" | tr -d '\r')"
runtime_manifest="$(sed -n '2p' "$receipt_gen" | tr -d '\r')"
runtime_ledger_entry="$(sed -n '3p' "$receipt_gen" | tr -d '\r')"
ledger_path="$(sed -n '4p' "$receipt_gen" | tr -d '\r')"

{
  echo "ts_utc=$TS_UTC"
  echo "verify_out_dir=$OUT_DIR"
  echo "security_audit_mode=$SECURITY_AUDIT_MODE"
  echo "confinement_flag=${CONFINEMENT_FLAG:-}"
  echo "reply_to_mode=$reply_mode"
  echo "receipt_generation_exit=$rc_receipt"
  echo "runtime_receipt=$runtime_receipt"
  echo "runtime_manifest=$runtime_manifest"
  echo "runtime_ledger_entry=$runtime_ledger_entry"
  echo "ledger_path=$ledger_path"
} > "$OUT_DIR/summary.txt"

if [ "$PASS" -eq 1 ]; then
  echo "PASS telegram_posture=allowlist+requireMention replyToMode=$reply_mode security_audit_mode=$SECURITY_AUDIT_MODE runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
  exit 0
fi

echo "FAIL telegram_posture=allowlist+requireMention replyToMode=$reply_mode security_audit_mode=$SECURITY_AUDIT_MODE runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
exit 1
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
export CAPTURE_models_status_probe="${CMD_CAPTURE[models_status_probe]:-}"
export CAPTURE_status_all_usage="${CMD_CAPTURE[status_all_usage]:-}"

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

- `PASS provider=local fallback=none ...`
- or `FAIL provider=<x> fallback=<y> ...`

Optional interfaces verifier (Telegram hardening posture):

```bash
runtime/tools/openclaw_verify_interfaces.sh
```

Expected output:

- `PASS telegram_posture=allowlist+requireMention replyToMode=first ...`
- or `FAIL telegram_posture=allowlist+requireMention replyToMode=<x> ...`

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
- Receipts include a non-deep channels status capture and never include Slack secrets.
```

### File: runtime/tests/test_openclaw_interfaces_policy_assert.py
```python
from runtime.tools.openclaw_interfaces_policy_assert import assert_interfaces_policy


def _cfg():
    return {
        "commands": {
            "ownerAllowFrom": ["7054951144"],
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
                "allowFrom": ["7054951144"],
                "replyToMode": "first",
                "groups": {
                    "-1000000000000": {
                        "requireMention": True,
                        "groupPolicy": "allowlist",
                        "allowFrom": ["7054951144"],
                    }
                },
            },
            "slack": {
                "enabled": False,
                "mode": "http",
                "webhookPath": "/slack/events",
                "groupPolicy": "disabled",
            },
        },
    }


def test_interfaces_policy_passes_with_hardened_telegram_and_disabled_slack():
    result = assert_interfaces_policy(_cfg())
    assert result["telegram"]["posture"] == "allowlist+requireMention"
    assert result["telegram"]["reply_to_mode"] == "first"
    assert result["slack"]["enabled"] is False
    assert result["slack"]["blocked"] is True


def test_interfaces_policy_rejects_telegram_wildcard_allowlist():
    cfg = _cfg()
    cfg["channels"]["telegram"]["allowFrom"] = ["*"]
    try:
        assert_interfaces_policy(cfg)
    except AssertionError as exc:
        assert "allowFrom must not include" in str(exc)
    else:
        raise AssertionError("expected wildcard allowlist assertion")


def test_interfaces_policy_rejects_missing_mention_patterns():
    cfg = _cfg()
    cfg["agents"]["list"][0]["groupChat"]["mentionPatterns"] = []
    try:
        assert_interfaces_policy(cfg)
    except AssertionError as exc:
        assert "mentionPatterns must be non-empty" in str(exc)
    else:
        raise AssertionError("expected mention patterns assertion")


def test_interfaces_policy_rejects_slack_secret_presence():
    cfg = _cfg()
    cfg["channels"]["slack"]["botToken"] = "xoxb-test"
    try:
        assert_interfaces_policy(cfg)
    except AssertionError as exc:
        assert "must not be set" in str(exc)
    else:
        raise AssertionError("expected slack secret assertion")
```

### File: artifacts/templates/openclaw/slack_app_manifest.json
```json
{
  "display_information": {
    "name": "OpenClaw",
    "description": "Slack connector for OpenClaw"
  },
  "features": {
    "bot_user": {
      "display_name": "OpenClaw",
      "always_online": false
    },
    "app_home": {
      "messages_tab_enabled": true,
      "messages_tab_read_only_enabled": false
    },
    "slash_commands": [
      {
        "command": "/openclaw",
        "description": "Send a message to OpenClaw",
        "should_escape": false
      }
    ]
  },
  "oauth_config": {
    "scopes": {
      "bot": [
        "chat:write",
        "channels:history",
        "channels:read",
        "groups:history",
        "groups:read",
        "groups:write",
        "im:history",
        "im:read",
        "im:write",
        "mpim:history",
        "mpim:read",
        "mpim:write",
        "users:read",
        "app_mentions:read",
        "reactions:read",
        "reactions:write",
        "pins:read",
        "pins:write",
        "emoji:read",
        "commands",
        "files:read",
        "files:write"
      ],
      "user": [
        "channels:history",
        "channels:read",
        "groups:history",
        "groups:read",
        "im:history",
        "im:read",
        "mpim:history",
        "mpim:read",
        "users:read",
        "reactions:read",
        "pins:read",
        "emoji:read",
        "search:read"
      ]
    }
  },
  "settings": {
    "socket_mode_enabled": true,
    "event_subscriptions": {
      "bot_events": [
        "app_mention",
        "message.channels",
        "message.groups",
        "message.im",
        "message.mpim",
        "reaction_added",
        "reaction_removed",
        "member_joined_channel",
        "member_left_channel",
        "channel_rename",
        "pin_added",
        "pin_removed"
      ]
    }
  }
}
```
