# Review Packet — Gate A-P1.6 v1.0

## Summary
- Implemented Slack enablement guards with fail-closed env-only overlay generation, dry-run/apply launcher, strict verifier, and tests.
- Base config remains Slack-disabled and secret-free; no Slack token values are stored in repo/evidence/receipts.
- Receipts/ledger now include Slack readiness booleans only (`slack_ready_to_enable`, `slack_base_enabled`, `slack_env_present`, `slack_overlay_last_mode`).

## Threat Model
- Risk: Slack secrets accidentally persisted in canonical config/repo/evidence/logs.
- Mitigation: env-only overlay file generation (`0600`) in runtime path (`0700`), strict missing-env fail-close, and deletion on verifier path.
- Risk: posture drift enables Slack in base config or introduces secret keys in base config.
- Mitigation: base posture asserts + verifier hard-fails when `slack_base_disabled!=true` or secret keys are present.

## Fail-Closed Guarantees
- Overlay generation fails when required env is absent or malformed (`xapp-`/`xoxb-` prefix checks).
- Verifier enforces missing-env failure, dummy overlay generation, overlay deletion, and strict token leak scan on outputs.
- Base config is checked for `enabled=false` and zero Slack secret keys before any overlay action.

## Acceptance Pointers
- Evidence directory: `artifacts/evidence/openclaw/p1_6/20260212T084225Z`
- Verifier: `verify_slack_guards_output.txt` (PASS)
- Acceptance (3/3): `acceptance_verify_slack_1.txt`, `_2.txt`, `_3.txt` (all PASS)
- Tests: `pytest_slack_guards.txt` (7 passed)
- Base posture snapshot: `base_config_slack_posture.json`
- Overlay metadata sample: `overlay_metadata_sample.json` (no secrets)

## No-Secrets-Stored Proof Notes
- `base_config_slack_posture.json` contains booleans/counts only.
- `overlay_metadata_sample.json` contains mode + presence booleans only; no token values.
- Verifier strict scan confirms dummy tokens are absent from logs/evidence/receipt outputs.

## Appendix A — Flattened Code

### File: runtime/tools/openclaw_slack_overlay.py
```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping

SLACK_SECRET_KEYS = ("appToken", "botToken", "signingSecret")
MODE_SOCKET = "socket"
MODE_HTTP = "http"


def utc_ts_compact() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_config(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir_0700(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def write_json_0600(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def slack_base_posture(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    channels = cfg.get("channels") if isinstance(cfg, Mapping) else {}
    slack = channels.get("slack") if isinstance(channels, Mapping) else None
    if not isinstance(slack, Mapping):
        return {
            "slack_base_present": False,
            "slack_base_enabled": False,
            "slack_base_disabled": True,
            "slack_secrets_in_base": False,
            "slack_secret_key_count": 0,
        }

    secrets = [k for k in SLACK_SECRET_KEYS if str(slack.get(k) or "").strip()]
    enabled = bool(slack.get("enabled") is True)
    return {
        "slack_base_present": True,
        "slack_base_enabled": enabled,
        "slack_base_disabled": not enabled,
        "slack_secrets_in_base": len(secrets) > 0,
        "slack_secret_key_count": len(secrets),
    }


def _required_env(mode: str) -> Dict[str, str]:
    if mode == MODE_SOCKET:
        return {
            "OPENCLAW_SLACK_APP_TOKEN": "xapp-",
            "OPENCLAW_SLACK_BOT_TOKEN": "xoxb-",
        }
    if mode == MODE_HTTP:
        return {
            "OPENCLAW_SLACK_BOT_TOKEN": "xoxb-",
            "OPENCLAW_SLACK_SIGNING_SECRET": "",
        }
    raise ValueError(f"unsupported mode: {mode}")


def validate_env(mode: str, env: Mapping[str, str]) -> Dict[str, bool]:
    required = _required_env(mode)
    presence = {k: bool(str(env.get(k, "")).strip()) for k in required}
    missing = [k for k, present in presence.items() if not present]
    if missing:
        raise ValueError("missing required env: " + ",".join(sorted(missing)))

    malformed = []
    for key, prefix in required.items():
        val = str(env.get(key, ""))
        if prefix and not val.startswith(prefix):
            malformed.append(f"{key}:expected_prefix:{prefix}")
    if malformed:
        raise ValueError("malformed env: " + ",".join(malformed))

    return presence


def generate_overlay_config(base_cfg: Mapping[str, Any], mode: str, env: Mapping[str, str]) -> Dict[str, Any]:
    cfg = copy.deepcopy(dict(base_cfg))
    channels = cfg.get("channels")
    if not isinstance(channels, dict):
        channels = {}
        cfg["channels"] = channels

    slack = channels.get("slack")
    if not isinstance(slack, dict):
        slack = {}
    else:
        slack = dict(slack)

    # Clear any pre-existing secret keys in working copy before injecting env values.
    for key in SLACK_SECRET_KEYS:
        slack.pop(key, None)

    slack["enabled"] = True
    if mode == MODE_SOCKET:
        slack["mode"] = MODE_SOCKET
        slack["appToken"] = str(env["OPENCLAW_SLACK_APP_TOKEN"])
        slack["botToken"] = str(env["OPENCLAW_SLACK_BOT_TOKEN"])
    elif mode == MODE_HTTP:
        slack["mode"] = MODE_HTTP
        slack["webhookPath"] = str(slack.get("webhookPath") or "/slack/events")
        slack["botToken"] = str(env["OPENCLAW_SLACK_BOT_TOKEN"])
        slack["signingSecret"] = str(env["OPENCLAW_SLACK_SIGNING_SECRET"])
    else:
        raise ValueError(f"unsupported mode: {mode}")

    channels["slack"] = slack
    return cfg


def generate_overlay_files(
    base_config_path: Path,
    output_dir: Path,
    mode: str,
    env: Mapping[str, str],
    *,
    created_utc: str | None = None,
) -> Dict[str, Any]:
    base_cfg = load_config(base_config_path)
    posture = slack_base_posture(base_cfg)
    if not posture["slack_base_disabled"]:
        raise ValueError("base config must keep Slack disabled")
    if posture["slack_secrets_in_base"]:
        raise ValueError("base config contains Slack secret fields")

    env_presence = validate_env(mode, env)
    overlay_cfg = generate_overlay_config(base_cfg, mode, env)

    ensure_dir_0700(output_dir)
    ts = created_utc or utc_ts_compact()
    overlay_path = output_dir / "openclaw_slack_overlay.json"
    metadata_path = output_dir / "overlay_metadata.json"

    write_json_0600(overlay_path, overlay_cfg)
    metadata = {
        "created_utc": ts,
        "mode": mode,
        "base_config_path": str(base_config_path),
        "overlay_config_path": str(overlay_path),
        "env_present": env_presence,
        "slack_base_disabled": bool(posture["slack_base_disabled"]),
        "slack_secrets_in_base": bool(posture["slack_secrets_in_base"]),
    }
    write_json_0600(metadata_path, metadata)
    return {
        "overlay_config_path": str(overlay_path),
        "overlay_metadata_path": str(metadata_path),
        "mode": mode,
        "env_present": env_presence,
        "slack_base_disabled": bool(posture["slack_base_disabled"]),
        "slack_secrets_in_base": bool(posture["slack_secrets_in_base"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Slack-enabled OpenClaw overlay config from env-only secrets.")
    parser.add_argument("--base-config", default=os.environ.get("OPENCLAW_CONFIG_PATH", str(Path.home() / ".openclaw" / "openclaw.json")))
    parser.add_argument("--output-dir")
    parser.add_argument("--mode", choices=[MODE_SOCKET, MODE_HTTP], default=None)
    parser.add_argument("--check-base", action="store_true", help="Check base Slack posture only and print redacted-safe summary.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    mode = (args.mode or os.environ.get("OPENCLAW_SLACK_MODE") or MODE_SOCKET).strip().lower()
    base_config_path = Path(args.base_config).expanduser()
    ts = utc_ts_compact()
    default_out = Path.home() / ".openclaw" / "runtime" / "slack_overlay" / ts
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else default_out

    if not base_config_path.exists():
        print(f"ERROR: base config not found: {base_config_path}")
        return 1

    base_cfg = load_config(base_config_path)
    posture = slack_base_posture(base_cfg)
    if args.check_base:
        out = dict(posture)
        out["mode"] = mode
        print(json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 0

    try:
        result = generate_overlay_files(base_config_path, output_dir, mode, os.environ, created_utc=ts)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(result["overlay_config_path"])
        print(result["overlay_metadata_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

### File: runtime/tools/openclaw_slack_launch.sh
```bash
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

```

### File: runtime/tools/openclaw_verify_slack_guards.sh
```bash
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

Slack enablement uses env-only overlay generation. Tokens are never written into
`~/.openclaw/openclaw.json`, repo files, or evidence artifacts.

Socket mode enablement (when provisioning is approved):

1. Export env vars in shell/session only:
   - `OPENCLAW_SLACK_MODE=socket`
   - `OPENCLAW_SLACK_APP_TOKEN`
   - `OPENCLAW_SLACK_BOT_TOKEN`
2. Launch with overlay:
   - `runtime/tools/openclaw_slack_launch.sh --apply`
3. Run post-enable checks:
   - `runtime/tools/openclaw_verify_interfaces.sh`
   - `runtime/tools/openclaw_verify_multiuser_posture.sh`
   - `runtime/tools/openclaw_verify_slack_guards.sh`

HTTP mode enablement (when provisioning is approved):

1. Export env vars in shell/session only:
   - `OPENCLAW_SLACK_MODE=http`
   - `OPENCLAW_SLACK_BOT_TOKEN`
   - `OPENCLAW_SLACK_SIGNING_SECRET`
2. Ensure request URL uses `/slack/events` and signature verification remains enabled.
3. Launch with overlay:
   - `runtime/tools/openclaw_slack_launch.sh --apply`
4. Run same post-enable checks as socket mode.

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
- Receipts include Slack guard posture (`slack_ready_to_enable`, `slack_base_enabled`, `slack_env_present`, `slack_overlay_last_mode`) with booleans/counts only.
```

### File: runtime/tests/test_openclaw_slack_overlay.py
```python
import json
import os
import subprocess
import sys
from pathlib import Path

from runtime.tools.openclaw_slack_overlay import generate_overlay_files, slack_base_posture


def _base_cfg() -> dict:
    return {
        "channels": {
            "slack": {
                "enabled": False,
                "mode": "socket",
            }
        }
    }


def _write_cfg(path: Path, cfg: dict) -> None:
    path.write_text(json.dumps(cfg), encoding="utf-8")


def test_socket_mode_missing_env_fails(tmp_path: Path):
    cfg_path = tmp_path / "openclaw.json"
    _write_cfg(cfg_path, _base_cfg())
    try:
        generate_overlay_files(cfg_path, tmp_path / "out", "socket", {})
    except ValueError as exc:
        assert "missing required env" in str(exc)
    else:
        raise AssertionError("expected missing env failure")


def test_http_mode_missing_signing_secret_fails(tmp_path: Path):
    cfg_path = tmp_path / "openclaw.json"
    _write_cfg(cfg_path, _base_cfg())
    env = {"OPENCLAW_SLACK_BOT_TOKEN": "xoxb-TEST-DUMMY"}
    try:
        generate_overlay_files(cfg_path, tmp_path / "out", "http", env)
    except ValueError as exc:
        assert "missing required env" in str(exc)
    else:
        raise AssertionError("expected missing signing secret failure")


def test_socket_dummy_env_generates_overlay_metadata_without_secrets(tmp_path: Path):
    cfg_path = tmp_path / "openclaw.json"
    _write_cfg(cfg_path, _base_cfg())
    env = {
        "OPENCLAW_SLACK_APP_TOKEN": "xapp-TEST-DUMMY-TOKEN",
        "OPENCLAW_SLACK_BOT_TOKEN": "xoxb-TEST-DUMMY-TOKEN",
    }
    result = generate_overlay_files(cfg_path, tmp_path / "out", "socket", env)
    meta = Path(result["overlay_metadata_path"]).read_text(encoding="utf-8")
    assert '"OPENCLAW_SLACK_APP_TOKEN":true' in meta
    assert '"OPENCLAW_SLACK_BOT_TOKEN":true' in meta
    assert "xapp-TEST-DUMMY-TOKEN" not in meta
    assert "xoxb-TEST-DUMMY-TOKEN" not in meta


def test_cli_output_never_logs_token_values(tmp_path: Path):
    cfg_path = tmp_path / "openclaw.json"
    _write_cfg(cfg_path, _base_cfg())
    out_dir = tmp_path / "out"
    env = os.environ.copy()
    env.update(
        {
            "OPENCLAW_CONFIG_PATH": str(cfg_path),
            "OPENCLAW_SLACK_APP_TOKEN": "xapp-TEST-DUMMY-TOKEN",
            "OPENCLAW_SLACK_BOT_TOKEN": "xoxb-TEST-DUMMY-TOKEN",
        }
    )
    proc = subprocess.run(
        [
            sys.executable,
            "runtime/tools/openclaw_slack_overlay.py",
            "--mode",
            "socket",
            "--output-dir",
            str(out_dir),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    joined = proc.stdout + proc.stderr
    assert "xapp-TEST-DUMMY-TOKEN" not in joined
    assert "xoxb-TEST-DUMMY-TOKEN" not in joined

```

### File: runtime/tests/test_openclaw_slack_guards.py
```python
from runtime.tools.openclaw_slack_overlay import slack_base_posture


def test_base_posture_slack_disabled_without_secrets():
    cfg = {"channels": {"slack": {"enabled": False, "mode": "socket"}}}
    result = slack_base_posture(cfg)
    assert result["slack_base_disabled"] is True
    assert result["slack_base_enabled"] is False
    assert result["slack_secrets_in_base"] is False
    assert result["slack_secret_key_count"] == 0


def test_base_posture_detects_secret_keys_in_base():
    cfg = {"channels": {"slack": {"enabled": False, "botToken": "xoxb-unsafe"}}}
    result = slack_base_posture(cfg)
    assert result["slack_base_disabled"] is True
    assert result["slack_secrets_in_base"] is True
    assert result["slack_secret_key_count"] == 1


def test_base_posture_detects_enabled_slack():
    cfg = {"channels": {"slack": {"enabled": True}}}
    result = slack_base_posture(cfg)
    assert result["slack_base_enabled"] is True
    assert result["slack_base_disabled"] is False

```
