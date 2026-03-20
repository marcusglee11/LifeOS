---
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
mission_ref: "Gate A-P0.3 — Receipts + run ledger + no-repo-dirt by default"
version: "1.0"
status: "COMPLETE"
---

# Review_Packet_Gate_A-P0.3_v1.0

## Scope Envelope

- Allowed:
  -     `runtime/tools/openclaw_receipts_bundle.sh`
  -     `runtime/tools/openclaw_verify_surface.sh`
  -     `runtime/tools/openclaw_leak_scan.sh`
  -     `runtime/tools/OPENCLAW_COO_RUNBOOK.md`
- Evidence root: `artifacts/evidence/openclaw/p0_3/20260210T114516Z/`
- Forbidden observed: none

## Summary

Implemented runtime-default receipts (outside repo), explicit optional export mode, deterministic append-only runtime ledger with redacted config fingerprint, dedicated leak scanner, and verify surface flow that produces PASS/FAIL with runtime receipt/ledger pointers. Added per-command timeouts to prevent indefinite probe hangs.

## Acceptance Mapping

- P0.1 baseline and current behavior capture: PASS
- P0.2 runtime-default vs export mode: PASS
- P0.3 append-only deterministic ledger: PASS
- P0.4 leak scan + verify script fail-closed on receipts/ledger invariants: PASS
- P0.5 git hygiene/export ignore check: PASS

## Key Evidence

- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/git_status_before.txt`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/verify_surface_output.txt`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/leak_scan_output.txt`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/git_status_after.txt`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/git_status_after_export.txt`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/status_diff_note.txt`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/check_ignore_export_path.txt`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/export_mode_output.txt`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/sample_runtime_receipt.md`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/sample_ledger_first3.jsonl`
- `artifacts/evidence/openclaw/p0_3/20260210T114516Z/config_fingerprint_method_note.md`

## Why this closes dirty-repo risk

Default operation writes receipts/ledger to runtime state paths (or `/tmp/openclaw-runtime` fallback), not the repository. Any repo export is explicit (`--export-repo`) and copied into an ignored path (`artifacts/evidence/openclaw/receipts`). Evidence shows unchanged `git status --porcelain` before/after verify and after explicit export in this run.

## Changed Files

- `runtime/tools/openclaw_receipts_bundle.sh`
- `runtime/tools/openclaw_verify_surface.sh`
- `runtime/tools/openclaw_leak_scan.sh`
- `runtime/tools/OPENCLAW_COO_RUNBOOK.md`
- `artifacts/review_packets/Review_Packet_Gate_A-P0.3_v1.0.md`

## Appendix A — Flattened Code

### File: `runtime/tools/openclaw_receipts_bundle.sh`

````bash
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
  local tmp rc
  tmp="$(mktemp)"
  set +e
  timeout "$CMD_TIMEOUT_SEC" "$@" >"$tmp" 2>&1
  rc=$?
  set -e
  CMD_RC["$id"]="$rc"

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

declare -A CMD_RC
CMD_IDS=(
  coo_path
  coo_symlink
  openclaw_version
  security_audit_deep
  models_status_probe
  sandbox_explain_json
  gateway_probe_json
)

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
run_capture models_status_probe coo openclaw -- models status --probe
run_capture sandbox_explain_json coo openclaw -- sandbox explain --json
run_capture gateway_probe_json coo openclaw -- gateway probe --json

for id in "${CMD_IDS[@]}"; do
  export "RC_${id}=${CMD_RC[$id]:-1}"
done
export TS_UTC
export CFG_PATH
export ROOT
export runtime_receipt
export ledger_file
export NOTES

python3 - "$runtime_manifest" "$runtime_ledger_entry" <<'PY'
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
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
    think_level = str((((cfg_obj.get("agents") or {}).get("defaults") or {}).get("model") or {}).get("thinkLevel") or "unknown")
    channels = [k for k, v in sorted((cfg_obj.get("channels") or {}).items()) if not isinstance(v, dict) or v.get("enabled", True) is not False]
    surface = channels[0] if channels else "unknown"
    gateway_mode = str((((cfg_obj.get("gateway") or {}).get("mode")) or "unknown"))

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
    "models_status_probe",
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
if os.environ.get("NOTES"):
    entry["notes"] = os.environ["NOTES"]

manifest = OrderedDict()
manifest["ts_utc"] = os.environ["TS_UTC"]
manifest["mode"] = "runtime-default"
manifest["runtime_receipt"] = os.environ["runtime_receipt"]
manifest["ledger_path"] = os.environ["ledger_file"]
manifest["guardrails_fingerprint"] = guardrails_fingerprint
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
````

### File: `runtime/tools/openclaw_verify_surface.sh`

````bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$STATE_DIR/verify/$TS_UTC"
VERIFY_CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_CMD_TIMEOUT_SEC:-30}"
if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

PASS=1
WARNINGS=0

to_file() {
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
    timeout "$VERIFY_CMD_TIMEOUT_SEC" "$@"
    rc=$?
    set -e
    echo "[exit_code]=$rc"
    echo '```'
  } > "$out" 2>&1
  if [ "$rc" -ne 0 ]; then
    WARNINGS=1
  fi
}

# required order
to_file security_audit_deep coo openclaw -- security audit --deep
to_file models_status_probe coo openclaw -- models status --probe
to_file sandbox_explain_json coo openclaw -- sandbox explain --json
to_file gateway_probe_json coo openclaw -- gateway probe --json

receipt_gen="$OUT_DIR/receipt_generation.txt"
set +e
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

leak_out="$OUT_DIR/leak_scan_output.txt"
set +e
runtime/tools/openclaw_leak_scan.sh "$runtime_receipt" "$runtime_ledger_entry" > "$leak_out" 2>&1
rc_leak=$?
set -e
if [ "$rc_leak" -ne 0 ]; then
  PASS=0
fi

{
  echo "ts_utc=$TS_UTC"
  echo "verify_out_dir=$OUT_DIR"
  echo "runtime_receipt=$runtime_receipt"
  echo "runtime_manifest=$runtime_manifest"
  echo "runtime_ledger_entry=$runtime_ledger_entry"
  echo "ledger_path=$ledger_path"
  echo "receipt_generation_exit=$rc_receipt"
  echo "leak_scan_exit=$rc_leak"
  echo "warnings_present=$WARNINGS"
} > "$OUT_DIR/summary.txt"

if [ "$PASS" -eq 1 ]; then
  if [ "$WARNINGS" -eq 1 ]; then
    echo "PASS runtime_receipt=$runtime_receipt ledger_path=$ledger_path notes=command_warnings_present"
  else
    echo "PASS runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
  fi
  exit 0
fi

echo "FAIL runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
exit 1
````

### File: `runtime/tools/openclaw_leak_scan.sh`

````bash
#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: runtime/tools/openclaw_leak_scan.sh <path...>" >&2
  exit 2
fi

python3 - "$@" <<'PY'
from __future__ import annotations
import re
import sys
from pathlib import Path

patterns = [
    ("apiKey", re.compile(r"apiKey\s*[:=]\s*[\"']?[^\"'\s]+", re.I)),
    ("botToken", re.compile(r"botToken\s*[:=]\s*[\"']?[^\"'\s]+", re.I)),
    ("Authorization: Bearer", re.compile(r"Authorization:\s*Bearer\s+\S+", re.I)),
    ("sk-", re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")),
    ("AIza", re.compile(r"\bAIza[0-9A-Za-z_-]{8,}")),
    ("base64-ish", re.compile(r"\b[A-Za-z0-9+/=_-]{80,}\b")),
]

failed = False
for raw in sys.argv[1:]:
    path = Path(raw)
    if not path.exists():
        print(f"LEAK_SCAN_MISSING file={path}")
        failed = True
        continue

    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    local_hits = 0
    for lineno, line in enumerate(content, start=1):
        for name, rgx in patterns:
            match = rgx.search(line)
            if not match:
                continue
            local_hits += 1
            failed = True
            redacted = line[: match.start()] + "[REDACTED_MATCH]" + line[match.end() :]
            print(f"LEAK_SCAN_HIT file={path} line={lineno} pattern={name} text={redacted[:220]}")
            break

    if local_hits == 0:
        print(f"LEAK_SCAN_PASS file={path}")

if failed:
    sys.exit(1)
PY
````

### File: `runtime/tools/OPENCLAW_COO_RUNBOOK.md`

````markdown
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

- `PASS runtime_receipt=<path> ledger_path=<path>`
- or `FAIL runtime_receipt=<path> ledger_path=<path>`

## Safety Invariants

- Default receipt generation must not write to repo paths.
- Ledger and receipts must remain redacted-safe.
- Leak scan must pass for runtime receipt + runtime ledger entry.
````
