# Review Packet — Gate A-P1.1 v1.0

## Summary
Gate A-P1.1 is implemented with local-first, fail-closed memory behavior:
- `memorySearch.provider=local`
- `memorySearch.fallback=none`
- sources restricted to `memory` (sessions excluded)
- workspace anchored under `~/.openclaw/workspace` (outside LifeOS repo)
- deterministic smoke checks now pass with source-cited recall

## Config Deltas (Redacted)
- Pre/post redacted config captures:
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/pre_config_redacted.txt`
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/post_config_redacted.txt`
- Redacted diff:
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/openclaw_config_redacted.diff`

## Smoke Outputs
- Memory status pre:
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/pre_memory_status.txt`
- Memory status deep post:
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/post_memory_status_deep.txt`
- Index verbose:
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/memory_index_verbose.txt`
- Seed search:
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/memory_search_seed.txt`

## PASS Criteria Evidence
- Recall hit includes file + line range for seed phrase:
  - `memory/daily/2026-02-10.md:1-5`
- Optional verifier (`runtime/tools/openclaw_verify_memory.sh`) 3/3 PASS within 45s envelope:
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/acceptance_verify_memory_1.txt`
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/acceptance_verify_memory_2.txt`
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/acceptance_verify_memory_3.txt`
- Unit tests:
  - `artifacts/evidence/openclaw/p1_1/20260210T232358Z/pytest_memory_policy_assert.txt`

## Known Limits
- Session indexing remains disabled at P1.1 by policy (`sources` excludes `sessions`).
- Receipts only capture non-deep memory status and do not trigger indexing by default.
- Local model download/warmup may emit host runtime logs (e.g., CPU fallback), but policy remains local-only with no remote fallback.

## Appendix A — Flattened Code (All Changed Files)

### File: runtime/tools/openclaw_policy_assert.py
```python
#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from pathlib import Path
from typing import Any, Dict, List
DAILY_PRIMARY='openai-codex/gpt-5.3-codex'
DAILY_FALLBACKS=['google-gemini-cli/gemini-3-flash-preview']
REVIEW_PRIMARY='openai-codex/gpt-5.3-codex'
REVIEW_FALLBACKS=['github-copilot/claude-opus-4.6']
MANUAL_ONLY_MODELS=['openrouter/pony-alpha','openrouter/deepseek-v3.2','opencode/kimi-k2.5-free']
OWNER_ONLY_COMMANDS={'/model','/models','/think'}
MEMORY_PROVIDER='local'
MEMORY_FALLBACK='none'

def _agent_by_id(cfg: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    for item in ((cfg.get('agents') or {}).get('list') or []):
        if isinstance(item, dict) and item.get('id') == agent_id:
            return item
    return {}

def _owner_allow_from(cfg: Dict[str, Any]) -> List[str]:
    raw = (((cfg.get('commands') or {}).get('ownerAllowFrom')) or [])
    if not isinstance(raw, list):
        return []
    return sorted({str(x).strip() for x in raw if str(x).strip()})

def _model_cfg(entry: Dict[str, Any]) -> Dict[str, Any]:
    model = entry.get('model')
    return model if isinstance(model, dict) else {}

def _assert_ladder(entry: Dict[str, Any], primary: str, fallbacks: List[str], label: str) -> None:
    model = _model_cfg(entry)
    got_primary = str(model.get('primary', ''))
    got_fallbacks = model.get('fallbacks')
    if not isinstance(got_fallbacks, list):
        got_fallbacks = []
    if got_primary != primary:
        raise AssertionError(f'{label} primary mismatch: {got_primary} != {primary}')
    if got_fallbacks != fallbacks:
        raise AssertionError(f'{label} fallbacks mismatch: {got_fallbacks} != {fallbacks}')

def _assert_manual_models_not_in_fallbacks(cfg: Dict[str, Any]) -> None:
    all_fallbacks: set[str] = set()
    defaults = ((cfg.get('agents') or {}).get('defaults') or {})
    default_fallbacks = (((defaults.get('model') or {}).get('fallbacks')) or [])
    if isinstance(default_fallbacks, list):
        all_fallbacks.update(str(x) for x in default_fallbacks)
    for agent_id in ('main', 'quick', 'think'):
        model = _model_cfg(_agent_by_id(cfg, agent_id))
        fallbacks = model.get('fallbacks')
        if isinstance(fallbacks, list):
            all_fallbacks.update(str(x) for x in fallbacks)
    for model_id in MANUAL_ONLY_MODELS:
        if model_id in all_fallbacks:
            raise AssertionError(f'manual-only model present in fallback list: {model_id}')

def command_authorized(cfg: Dict[str, Any], sender: str, command: str) -> bool:
    cmd = command.strip().split(' ', 1)[0].lower()
    if cmd not in OWNER_ONLY_COMMANDS:
        return True
    owners = _owner_allow_from(cfg)
    if not owners:
        return False
    return sender in owners

def _assert_memory_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    defaults = ((cfg.get('agents') or {}).get('defaults') or {})
    workspace_raw = str(defaults.get('workspace') or '')
    if not workspace_raw:
        raise AssertionError('agents.defaults.workspace must be set')

    workspace = os.path.abspath(os.path.expanduser(workspace_raw))
    openclaw_home = os.path.abspath(os.path.expanduser('~/.openclaw'))
    if not (workspace == openclaw_home or workspace.startswith(openclaw_home + os.sep)):
        raise AssertionError(f'agents.defaults.workspace must be under ~/.openclaw, got {workspace_raw}')

    memory = defaults.get('memorySearch')
    if not isinstance(memory, dict):
        raise AssertionError('agents.defaults.memorySearch must be configured')
    if memory.get('enabled') is not True:
        raise AssertionError('agents.defaults.memorySearch.enabled must be true')

    provider = str(memory.get('provider') or '')
    fallback = str(memory.get('fallback') or '')
    if provider != MEMORY_PROVIDER:
        raise AssertionError(f'agents.defaults.memorySearch.provider must be {MEMORY_PROVIDER}, got {provider}')
    if fallback != MEMORY_FALLBACK:
        raise AssertionError(f'agents.defaults.memorySearch.fallback must be {MEMORY_FALLBACK}, got {fallback}')

    sources = memory.get('sources')
    if not isinstance(sources, list):
        raise AssertionError('agents.defaults.memorySearch.sources must be a list')
    normalized_sources = [str(x) for x in sources]
    if 'memory' not in normalized_sources:
        raise AssertionError('agents.defaults.memorySearch.sources must include "memory"')
    if 'sessions' in normalized_sources:
        raise AssertionError('agents.defaults.memorySearch.sources must not include "sessions" at P1.1')

    return {
        'workspace': workspace_raw,
        'provider': provider,
        'fallback': fallback,
        'sources': normalized_sources,
    }

def assert_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    defaults = ((cfg.get('agents') or {}).get('defaults') or {})
    defaults_think = str(defaults.get('thinkingDefault') or 'unknown')
    if defaults_think not in {'low', 'off'}:
        raise AssertionError(f'agents.defaults.thinkingDefault must be low/off, got {defaults_think}')
    _assert_ladder(_agent_by_id(cfg, 'main'), DAILY_PRIMARY, DAILY_FALLBACKS, 'main')
    _assert_ladder(_agent_by_id(cfg, 'quick'), DAILY_PRIMARY, DAILY_FALLBACKS, 'quick')
    _assert_ladder(_agent_by_id(cfg, 'think'), REVIEW_PRIMARY, REVIEW_FALLBACKS, 'think')
    _assert_manual_models_not_in_fallbacks(cfg)
    owners = _owner_allow_from(cfg)
    if not owners:
        raise AssertionError('commands.ownerAllowFrom must be non-empty')
    owner = owners[0]
    if not command_authorized(cfg, owner, '/model openai-codex/gpt-5.3-codex'):
        raise AssertionError('owner must be authorized for /model')
    if command_authorized(cfg, '__non_owner__', '/model openai-codex/gpt-5.3-codex'):
        raise AssertionError('non-owner must be rejected for /model')
    if command_authorized(cfg, '__non_owner__', '/think high'):
        raise AssertionError('non-owner must be rejected for /think')
    memory = _assert_memory_policy(cfg)
    return {
        'daily_ladder': {'primary': DAILY_PRIMARY, 'fallbacks': DAILY_FALLBACKS},
        'review_ladder': {'primary': REVIEW_PRIMARY, 'fallbacks': REVIEW_FALLBACKS},
        'manual_only_models': MANUAL_ONLY_MODELS,
        'owners': owners,
        'defaults_thinking': defaults_think,
        'memory': memory,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description='Assert OpenClaw model policy invariants.')
    parser.add_argument('--config', default=str(Path.home() / '.openclaw' / 'openclaw.json'))
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    result = assert_policy(cfg)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=True))
    else:
        print(f'POLICY_ASSERT_PASS config={args.config}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
```

### File: runtime/tests/test_openclaw_policy_assert.py
```python
from runtime.tools.openclaw_policy_assert import assert_policy, command_authorized
from pathlib import Path

def _cfg():
    return {
        'commands': {'ownerAllowFrom': ['owner-1']},
        'agents': {
            'defaults': {
                'workspace': '/home/tester/.openclaw/workspace',
                'thinkingDefault': 'low',
                'model': {
                    'primary': 'openai-codex/gpt-5.3-codex',
                    'fallbacks': ['google-gemini-cli/gemini-3-flash-preview'],
                },
                'memorySearch': {
                    'enabled': True,
                    'provider': 'local',
                    'fallback': 'none',
                    'sources': ['memory'],
                },
            },
            'list': [
                {'id': 'main', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['google-gemini-cli/gemini-3-flash-preview']}},
                {'id': 'quick', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['google-gemini-cli/gemini-3-flash-preview']}},
                {'id': 'think', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/claude-opus-4.6']}},
            ],
        },
    }

def test_assert_policy_passes_for_expected_ladders():
    cfg = _cfg()
    cfg['agents']['defaults']['workspace'] = str(Path.home() / '.openclaw' / 'workspace')
    result = assert_policy(cfg)
    assert result['owners'] == ['owner-1']
    assert result['defaults_thinking'] == 'low'
    assert result['memory']['provider'] == 'local'
    assert result['memory']['fallback'] == 'none'

def test_non_owner_cannot_model_or_think_switch():
    cfg = _cfg()
    assert command_authorized(cfg, 'owner-1', '/model openai-codex/gpt-5.3-codex')
    assert not command_authorized(cfg, 'outsider', '/model openai-codex/gpt-5.3-codex')
    assert not command_authorized(cfg, 'outsider', '/think high')
```

### File: runtime/tests/test_openclaw_memory_policy_assert.py
```python
from runtime.tools.openclaw_policy_assert import assert_policy
from pathlib import Path


def _base_cfg():
    return {
        "commands": {"ownerAllowFrom": ["owner-1"]},
        "agents": {
            "defaults": {
                "workspace": "/home/tester/.openclaw/workspace",
                "thinkingDefault": "low",
                "model": {
                    "primary": "openai-codex/gpt-5.3-codex",
                    "fallbacks": ["google-gemini-cli/gemini-3-flash-preview"],
                },
                "memorySearch": {
                    "enabled": True,
                    "provider": "local",
                    "fallback": "none",
                    "sources": ["memory"],
                },
            },
            "list": [
                {"id": "main", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["google-gemini-cli/gemini-3-flash-preview"]}},
                {"id": "quick", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["google-gemini-cli/gemini-3-flash-preview"]}},
                {"id": "think", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["github-copilot/claude-opus-4.6"]}},
            ],
        },
    }


def test_memory_policy_accepts_local_no_fallback_and_memory_source_only():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    result = assert_policy(cfg)
    assert result["memory"]["provider"] == "local"
    assert result["memory"]["fallback"] == "none"
    assert result["memory"]["sources"] == ["memory"]


def test_memory_policy_rejects_non_local_provider():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["agents"]["defaults"]["memorySearch"]["provider"] = "openai"
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert "memorySearch.provider must be local" in str(exc)
    else:
        raise AssertionError("expected memory provider assertion")


def test_memory_policy_rejects_sessions_source():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["agents"]["defaults"]["memorySearch"]["sources"] = ["memory", "sessions"]
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert 'must not include "sessions"' in str(exc)
    else:
        raise AssertionError("expected sessions source assertion")


def test_memory_policy_rejects_workspace_outside_openclaw_home():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = "/mnt/c/Users/cabra/Projects/LifeOS"
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert "workspace must be under ~/.openclaw" in str(exc)
    else:
        raise AssertionError("expected workspace boundary assertion")
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
SEED_QUERY="${OPENCLAW_VERIFY_MEMORY_QUERY:-lobster-memory-seed-001}"
AGENT_ID="${OPENCLAW_VERIFY_MEMORY_AGENT:-main}"

mkdir -p "$OUT_DIR"

status_out="$OUT_DIR/memory_status_deep.txt"
search_out="$OUT_DIR/memory_search_seed.txt"
summary_out="$OUT_DIR/summary.txt"

set +e
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
  echo "status_exit=$rc_status"
  echo "search_exit=$rc_search"
  echo "provider=${provider:-unknown}"
  echo "requested=${requested:-unknown}"
  echo "fallback=$fallback"
  echo "hits=$hits"
  echo "status_out=$status_out"
  echo "search_out=$search_out"
} > "$summary_out"

if [ "$pass" -eq 1 ]; then
  echo "PASS provider=local fallback=none status_out=$status_out search_out=$search_out summary=$summary_out"
  exit 0
fi

echo "FAIL provider=${provider:-unknown} fallback=$fallback status_out=$status_out search_out=$search_out summary=$summary_out" >&2
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

## Safety Invariants

- Default receipt generation must not write to repo paths.
- Ledger and receipts must remain redacted-safe.
- Leak scan must pass for runtime receipt + runtime ledger entry.
- Verify is fail-closed on security audit, sandbox invariants, and policy assertion.
- Receipts include a non-deep memory status capture; they do not run memory index by default.
```
