# Review Packet — Gate A-P1.3 v1.0

## Summary
Gate A-P1.3 adds fail-closed data lifecycle enforcement for OpenClaw memory and wires policy status into verification/receipts.

Implemented controls:
- Memory schema template with classification + retention metadata.
- Policy guard (`openclaw_memory_policy_guard.py`) enforcing:
  - front matter presence for `memory/**/*.md`
  - allowed classifications only: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`
  - `SECRET` disallowed
  - explicit retention format (`^\d+(d|w|m|y)$|^permanent$`)
  - secret/token-like content blocking with redacted violations
- Safe index wrapper (`openclaw_memory_index_safe.sh`) runs guard first.
- `openclaw_verify_memory.sh` now guard-first and outputs `memory_policy_ok=true|false`.
- Receipts/ledger include `memory_policy_ok` and `memory_policy_violations_count`.
- Test coverage added for guard rules and redaction behavior.

## Enforcement Points
- `runtime/tools/openclaw_memory_policy_guard.py`
- `runtime/tools/openclaw_memory_index_safe.sh`
- `runtime/tools/openclaw_verify_memory.sh`
- `runtime/tools/openclaw_receipts_bundle.sh`
- `runtime/tests/test_openclaw_memory_policy_guard.py`

## Acceptance Evidence
Evidence directory:
- `artifacts/evidence/openclaw/p1_3/20260211T022709Z`

Required artifacts:
- `repo_state_before.txt`
- `guard_summary_ok.json`
- `guard_summary_fail_sample.json`
- `pytest_memory_policy_guard.txt`
- `acceptance_verify_memory_1.txt`
- `acceptance_verify_memory_2.txt`
- `acceptance_verify_memory_3.txt`
- `decision_note.md`

Acceptance result:
- 3/3 PASS within 45s envelope with `memory_policy_ok=true`.

## Known Limits
- Guard currently requires explicit retention in each memory entry.
- Receipts capture policy summary only (no memory file dumps).
- Session indexing remains disabled; sources remain memory-only.

## Appendix A — Flattened Code (All Changed Files)

### File: runtime/tools/openclaw_memory_policy_guard.py
```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

ALLOWED_CLASSIFICATIONS = {"PUBLIC", "INTERNAL", "CONFIDENTIAL"}
RETENTION_RE = re.compile(r"^(?:\d+(?:d|w|m|y)|permanent)$", re.IGNORECASE)

KEYWORD_PATTERNS = [
    re.compile(r"\bapiKey\b", re.IGNORECASE),
    re.compile(r"\bbotToken\b", re.IGNORECASE),
    re.compile(r"\bsigningSecret\b", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*Bearer\s+\S+", re.IGNORECASE),
]
TOKEN_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{8,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
]
LONG_BLOB_RE = re.compile(r"[A-Za-z0-9+/_=-]{80,}")


@dataclass
class Violation:
    file: str
    line: int
    rule: str
    message: str
    snippet: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "rule": self.rule,
            "message": self.message,
            "snippet": self.snippet,
        }


def redact_line(line: str) -> str:
    out = line.rstrip("\n")
    out = re.sub(r"Authorization\s*:\s*Bearer\s+\S+", "Authorization: Bearer [REDACTED]", out, flags=re.IGNORECASE)
    out = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "sk-[REDACTED]", out)
    out = re.sub(r"\bxox[baprs]-[A-Za-z0-9-]{8,}\b", "xox?- [REDACTED]", out)
    out = re.sub(r"\bghp_[A-Za-z0-9]{20,}\b", "ghp_[REDACTED]", out)
    out = re.sub(r"\bAIza[0-9A-Za-z_-]{20,}\b", "AIza[REDACTED]", out)
    out = LONG_BLOB_RE.sub("[REDACTED_LONG_BLOB]", out)
    out = re.sub(r"\b(apiKey|botToken|signingSecret)\b\s*[:=]\s*\S+", r"\1=[REDACTED]", out, flags=re.IGNORECASE)
    return out


def parse_front_matter(lines: List[str]) -> Tuple[Optional[Dict[str, str]], int]:
    if not lines or lines[0].strip() != "---":
        return None, 0
    fm: Dict[str, str] = {}
    idx = 1
    while idx < len(lines):
        raw = lines[idx]
        if raw.strip() == "---":
            return fm, idx + 1
        if ":" in raw:
            key, value = raw.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key:
                fm[key] = value
        idx += 1
    return None, 0


def iter_memory_files(workspace: Path) -> Iterable[Path]:
    memory_md = workspace / "MEMORY.md"
    if memory_md.exists():
        yield memory_md
    memory_dir = workspace / "memory"
    if memory_dir.exists():
        for path in sorted(memory_dir.rglob("*.md")):
            if path.is_file():
                yield path


def detect_secret_like(text: str, line: str) -> bool:
    return any(p.search(text) for p in KEYWORD_PATTERNS + TOKEN_PATTERNS) or bool(LONG_BLOB_RE.search(line))


def scan_workspace(workspace: Path) -> Dict[str, object]:
    violations: List[Violation] = []
    scanned_files = 0
    memory_entry_files = 0

    for path in iter_memory_files(workspace):
        scanned_files += 1
        rel = str(path.relative_to(workspace))
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        # Secret/token-like detection applies to all memory files, including MEMORY.md.
        for i, line in enumerate(lines, start=1):
            if detect_secret_like(line, line):
                violations.append(
                    Violation(
                        file=rel,
                        line=i,
                        rule="SECRET_PATTERN_BLOCKED",
                        message="Secret-like content detected; memory indexing is blocked.",
                        snippet=redact_line(line),
                    )
                )

        # Enforce metadata schema for memory entry files only.
        if rel.startswith("memory/"):
            memory_entry_files += 1
            fm, _ = parse_front_matter(lines)
            if fm is None:
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="MISSING_FRONT_MATTER",
                        message="Memory entry must start with YAML front matter.",
                        snippet=redact_line(lines[0] if lines else ""),
                    )
                )
                continue

            classification = (fm.get("classification") or "").strip().upper()
            if not classification:
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="MISSING_CLASSIFICATION",
                        message="classification is required in front matter.",
                        snippet="classification: [MISSING]",
                    )
                )
            elif classification == "SECRET":
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="CLASSIFICATION_SECRET_DISALLOWED",
                        message="classification SECRET is disallowed for memory storage.",
                        snippet="classification: SECRET",
                    )
                )
            elif classification not in ALLOWED_CLASSIFICATIONS:
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="INVALID_CLASSIFICATION",
                        message=f"classification must be one of {sorted(ALLOWED_CLASSIFICATIONS)}.",
                        snippet=f"classification: {classification}",
                    )
                )

            retention = (fm.get("retention") or "").strip()
            if not retention:
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="MISSING_RETENTION",
                        message="retention is required in front matter.",
                        snippet="retention: [MISSING]",
                    )
                )
            elif not RETENTION_RE.match(retention):
                violations.append(
                    Violation(
                        file=rel,
                        line=1,
                        rule="INVALID_RETENTION",
                        message='retention must match ^\\d+(d|w|m|y)$ or "permanent".',
                        snippet=f"retention: {retention}",
                    )
                )

    summary = {
        "workspace": str(workspace),
        "scanned_files": scanned_files,
        "memory_entry_files": memory_entry_files,
        "violations_count": len(violations),
        "policy_ok": len(violations) == 0,
        "violations": [v.to_dict() for v in violations],
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw memory policy guard.")
    parser.add_argument("--workspace", default=str(Path.home() / ".openclaw" / "workspace"))
    parser.add_argument("--json-summary", action="store_true", help="Print JSON summary only.")
    parser.add_argument("--summary-out", help="Write JSON summary to this path.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser()
    summary = scan_workspace(workspace)

    if args.summary_out:
        out = Path(args.summary_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if args.json_summary:
        print(json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(
            f"memory_policy_ok={'true' if summary['policy_ok'] else 'false'} "
            f"scanned_files={summary['scanned_files']} "
            f"memory_entry_files={summary['memory_entry_files']} "
            f"violations={summary['violations_count']}"
        )
        for v in summary["violations"]:
            print(f"- {v['file']}:{v['line']} [{v['rule']}] {v['message']} :: {v['snippet']}")

    return 0 if summary["policy_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

### File: runtime/tools/openclaw_memory_index_safe.sh
```bash
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
```

### File: runtime/tools/openclaw_verify_memory.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_MEMORY_OUT_DIR:-$STATE_DIR/verify-memory/$TS_UTC}"
STATUS_TIMEOUT_SEC="${OPENCLAW_VERIFY_MEMORY_STATUS_TIMEOUT_SEC:-20}"
SEARCH_TIMEOUT_SEC="${OPENCLAW_VERIFY_MEMORY_SEARCH_TIMEOUT_SEC:-20}"
GUARD_TIMEOUT_SEC="${OPENCLAW_VERIFY_MEMORY_GUARD_TIMEOUT_SEC:-15}"
SEED_QUERY="${OPENCLAW_VERIFY_MEMORY_QUERY:-lobster-memory-seed-001}"
AGENT_ID="${OPENCLAW_VERIFY_MEMORY_AGENT:-main}"

mkdir -p "$OUT_DIR"

status_out="$OUT_DIR/memory_status_deep.txt"
search_out="$OUT_DIR/memory_search_seed.txt"
guard_out="$OUT_DIR/memory_policy_guard.txt"
guard_summary="$OUT_DIR/memory_policy_guard_summary.json"
summary_out="$OUT_DIR/summary.txt"

set +e
timeout "$GUARD_TIMEOUT_SEC" python3 runtime/tools/openclaw_memory_policy_guard.py --json-summary --summary-out "$guard_summary" > "$guard_out" 2>&1
rc_guard=$?
timeout "$STATUS_TIMEOUT_SEC" coo openclaw -- memory status --deep --agent "$AGENT_ID" > "$status_out" 2>&1
rc_status=$?
timeout "$SEARCH_TIMEOUT_SEC" coo openclaw -- memory search "$SEED_QUERY" --agent "$AGENT_ID" > "$search_out" 2>&1
rc_search=$?
set -e

provider="$(rg -o 'Provider:\s*[^[:space:]]+' "$status_out" | head -n1 | awk '{print $2}')"
requested="$(rg -o 'requested:\s*[^)]+' "$status_out" | head -n1 | awk -F': ' '{print $2}')"
hits="$(rg -c '(^|[[:space:]])[^[:space:]]+:[0-9]+-[0-9]+' "$search_out" || true)"

fallback="unknown"
if [ -f "${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}" ]; then
  fallback="$(python3 - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ.get("OPENCLAW_CONFIG_PATH", str(Path.home()/".openclaw"/"openclaw.json")))
try:
    cfg = json.loads(p.read_text(encoding="utf-8"))
    print((((cfg.get("agents") or {}).get("defaults") or {}).get("memorySearch") or {}).get("fallback") or "unknown")
except Exception:
    print("unknown")
PY
)"
fi

pass=1
if [ "$rc_status" -ne 0 ] || [ "$rc_search" -ne 0 ]; then
  pass=0
fi
if [ "$rc_guard" -ne 0 ]; then
  pass=0
fi
if [ "${provider:-}" != "local" ] && [ "${requested:-}" != "local" ]; then
  pass=0
fi
if [ "$fallback" != "none" ]; then
  pass=0
fi
if [ "${hits:-0}" -lt 1 ]; then
  pass=0
fi

{
  echo "ts_utc=$TS_UTC"
  echo "out_dir=$OUT_DIR"
  echo "agent=$AGENT_ID"
  echo "query=$SEED_QUERY"
  echo "guard_exit=$rc_guard"
  echo "status_exit=$rc_status"
  echo "search_exit=$rc_search"
  echo "provider=${provider:-unknown}"
  echo "requested=${requested:-unknown}"
  echo "fallback=$fallback"
  echo "hits=$hits"
  echo "guard_out=$guard_out"
  echo "guard_summary=$guard_summary"
  echo "status_out=$status_out"
  echo "search_out=$search_out"
} > "$summary_out"

if [ "$pass" -eq 1 ]; then
  echo "PASS memory_policy_ok=true provider=local fallback=none guard_summary=$guard_summary status_out=$status_out search_out=$search_out summary=$summary_out"
  exit 0
fi

echo "FAIL memory_policy_ok=false provider=${provider:-unknown} fallback=$fallback guard_summary=$guard_summary status_out=$status_out search_out=$search_out summary=$summary_out" >&2
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
- Receipts include a non-deep channels status capture and never include Slack secrets.
```

### File: runtime/tests/test_openclaw_memory_policy_guard.py
```python
from pathlib import Path

from runtime.tools.openclaw_memory_policy_guard import scan_workspace


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_missing_front_matter_fails(tmp_path: Path):
    _write(tmp_path / "MEMORY.md", "# Memory\n")
    _write(tmp_path / "memory" / "daily.md", "# no front matter\n")
    summary = scan_workspace(tmp_path)
    assert summary["policy_ok"] is False
    assert any(v["rule"] == "MISSING_FRONT_MATTER" for v in summary["violations"])


def test_secret_classification_fails(tmp_path: Path):
    _write(tmp_path / "MEMORY.md", "# Memory\n")
    _write(
        tmp_path / "memory" / "entry.md",
        "---\nclassification: SECRET\nretention: 30d\n---\nbody\n",
    )
    summary = scan_workspace(tmp_path)
    assert summary["policy_ok"] is False
    assert any(v["rule"] == "CLASSIFICATION_SECRET_DISALLOWED" for v in summary["violations"])


def test_token_like_string_fails_and_is_redacted(tmp_path: Path):
    _write(tmp_path / "MEMORY.md", "# Memory\n")
    _write(
        tmp_path / "memory" / "entry.md",
        "---\nclassification: INTERNAL\nretention: 180d\n---\napiKey: sk-abcdefghijklmnop\n",
    )
    summary = scan_workspace(tmp_path)
    assert summary["policy_ok"] is False
    token_violations = [v for v in summary["violations"] if v["rule"] == "SECRET_PATTERN_BLOCKED"]
    assert token_violations
    assert "abcdefghijklmnop" not in token_violations[0]["snippet"]
    assert "[REDACTED]" in token_violations[0]["snippet"]


def test_valid_entry_passes(tmp_path: Path):
    _write(tmp_path / "MEMORY.md", "# OpenClaw Memory\nNo secrets.\n")
    _write(
        tmp_path / "memory" / "daily" / "2026-02-11.md",
        "---\n"
        "title: Daily note\n"
        "classification: INTERNAL\n"
        "retention: 180d\n"
        "created_utc: 2026-02-11T00:00:00Z\n"
        "sources:\n"
        "  - seeded by test\n"
        "---\n"
        "seed phrase lobster-memory-seed-001\n",
    )
    summary = scan_workspace(tmp_path)
    assert summary["policy_ok"] is True
    assert summary["violations_count"] == 0
```

### File: artifacts/templates/openclaw/memory_entry_template.md
```markdown
---
title: ""
classification: INTERNAL
retention: 180d
created_utc: 2026-01-01T00:00:00Z
sources:
  - ""
---

# Memory Entry

## Summary

- Briefly describe the fact/decision being stored.

## Evidence

- Provide source pointers that justify this memory (file path, command output, or ticket reference).

## Rules

- Never include secrets, tokens, API keys, passwords, signing secrets, or bearer values.
- Classification must be one of: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`.
- `SECRET` content is disallowed for memory storage.
- Retention must be explicit (`30d`, `180d`, `1y`, or `permanent`).
```
