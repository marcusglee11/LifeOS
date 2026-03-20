# Review Packet: OpenClaw COO Security Privacy Hardening Implementation v1.0

- Date (UTC): 2026-02-18T02:31:24Z
- Mission: Implement security/privacy stabilization hardening for OpenClaw COO runtime
- Plan Source: artifacts/plans/Plan_OpenClaw_COO_Security_Privacy_Audit_v1.0.md
- Review Source: artifacts/plans/Review_Plan_OpenClaw_COO_Security_Privacy_Audit_v1.0.md

## Scope
Implemented fail-closed startup gates, token-safe dashboard handling, cron egress parking guard, gate status artifact output, policy alignment to subscription-first ladder, redaction expansion, Slack overlay stale-file scavenger, and targeted regression tests.

## Changed Files
- `runtime/tests/test_openclaw_cron_delivery_guard.py`
- `runtime/tests/test_openclaw_egress_policy.py`
- `runtime/tests/test_openclaw_memory_policy_assert.py`
- `runtime/tests/test_openclaw_model_policy_assert.py`
- `runtime/tests/test_openclaw_policy_assert.py`
- `runtime/tools/coo_worktree.sh`
- `runtime/tools/openclaw_cron_delivery_guard.py`
- `runtime/tools/openclaw_egress_policy.py`
- `runtime/tools/openclaw_leak_scan.sh`
- `runtime/tools/openclaw_model_ladder_fix.py`
- `runtime/tools/openclaw_model_policy_assert.py`
- `runtime/tools/openclaw_models_preflight.sh`
- `runtime/tools/openclaw_policy_assert.py`
- `runtime/tools/openclaw_receipts_bundle.sh`
- `runtime/tools/openclaw_slack_launch.sh`
- `runtime/tools/openclaw_verify_surface.sh`

## Verification
- `pytest -q runtime/tests/test_openclaw_policy_assert.py runtime/tests/test_openclaw_memory_policy_assert.py runtime/tests/test_openclaw_model_policy_assert.py runtime/tests/test_openclaw_egress_policy.py runtime/tests/test_openclaw_cron_delivery_guard.py runtime/tests/test_openclaw_multiuser_posture_assert.py runtime/tests/test_openclaw_interfaces_policy_assert.py`
- `bash -n runtime/tools/coo_worktree.sh runtime/tools/openclaw_models_preflight.sh runtime/tools/openclaw_verify_surface.sh runtime/tools/openclaw_slack_launch.sh runtime/tools/openclaw_receipts_bundle.sh runtime/tools/openclaw_leak_scan.sh`
- `python3 -m py_compile runtime/tools/openclaw_policy_assert.py runtime/tools/openclaw_model_policy_assert.py runtime/tools/openclaw_egress_policy.py runtime/tools/openclaw_cron_delivery_guard.py runtime/tools/openclaw_model_ladder_fix.py`

## Appendix A: Flattened Changed Code

### File: `runtime/tests/test_openclaw_cron_delivery_guard.py`
```python
from runtime.tools.openclaw_cron_delivery_guard import evaluate_jobs


def test_require_parked_blocks_enabled_non_none_delivery():
    jobs = [
        {
            "id": "1",
            "name": "burnin-probe-t-30m",
            "enabled": True,
            "request": {"delivery": {"mode": "announce"}},
        }
    ]
    result = evaluate_jobs(jobs, require_parked=True)
    assert result["pass"] is False
    assert result["violations"]
    assert "delivery.mode=announce" in result["violations"][0]


def test_non_parked_mode_allows_metadata_payload():
    jobs = [
        {
            "id": "1",
            "name": "burnin-probe-u-60m",
            "enabled": True,
            "request": {
                "delivery": {
                    "mode": "announce",
                    "payload": {
                        "status": "ok",
                        "summary": "probe-u ok",
                        "sources": ["probes/run#1"],
                        "counts": {"success": 1},
                    },
                }
            },
        }
    ]
    result = evaluate_jobs(jobs, require_parked=False)
    assert result["pass"] is True
    assert result["violations"] == []


def test_non_parked_mode_blocks_contentful_payload():
    jobs = [
        {
            "id": "1",
            "name": "coo-brief-trial",
            "enabled": True,
            "request": {
                "delivery": {
                    "mode": "announce",
                    "payload": "TOP_3_ACTIONS:\n- ...",
                }
            },
        }
    ]
    result = evaluate_jobs(jobs, require_parked=False)
    assert result["pass"] is False
    assert result["violations"]
    assert "classified contentful" in result["violations"][0]
```

### File: `runtime/tests/test_openclaw_egress_policy.py`
```python
from runtime.tools.openclaw_egress_policy import classify_payload, classify_payload_text


def test_metadata_payload_is_allowed_for_scheduled():
    payload = {
        "status": "ok",
        "summary": "probe completed",
        "sources": ["probes/burnin-probe-t-30m#run-123"],
        "counts": {"success": 1, "failure": 0},
    }
    result = classify_payload(payload)
    assert result["classification"] == "metadata_only"
    assert result["allowed_for_scheduled"] is True
    assert result["reasons"] == []


def test_payload_with_extra_content_field_is_blocked():
    payload = {
        "status": "ok",
        "summary": "probe completed",
        "sources": [],
        "counts": {},
        "content": "raw memory excerpt",
    }
    result = classify_payload(payload)
    assert result["classification"] == "contentful"
    assert result["allowed_for_scheduled"] is False
    assert any("extra_keys" in reason for reason in result["reasons"])


def test_payload_text_not_json_is_blocked():
    result = classify_payload_text("This is a plain narrative response.")
    assert result["classification"] == "contentful"
    assert result["allowed_for_scheduled"] is False
    assert "payload_not_json" in result["reasons"]


def test_multiline_summary_is_blocked():
    payload = {
        "status": "ok",
        "summary": "line 1\nline 2",
        "sources": [],
        "counts": {},
    }
    result = classify_payload(payload)
    assert result["classification"] == "contentful"
    assert result["allowed_for_scheduled"] is False
    assert "summary_not_single_line" in result["reasons"]
```

### File: `runtime/tests/test_openclaw_memory_policy_assert.py`
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
                    "fallbacks": ["github-copilot/claude-opus-4.6", "google-gemini-cli/gemini-3-flash-preview"],
                },
                "memorySearch": {
                    "enabled": False,
                    "provider": "local",
                    "fallback": "none",
                    "sources": ["memory"],
                },
            },
            "list": [
                {"id": "main", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["github-copilot/claude-opus-4.6", "google-gemini-cli/gemini-3-flash-preview"]}},
                {"id": "quick", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["github-copilot/claude-opus-4.6", "google-gemini-cli/gemini-3-flash-preview"]}},
                {"id": "think", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["github-copilot/claude-opus-4.6", "google-gemini-cli/gemini-3-flash-preview"]}},
            ],
        },
    }


def test_memory_policy_accepts_local_no_fallback_and_memory_source_only():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    result = assert_policy(cfg)
    assert result["memory"]["enabled"] is False
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


def test_memory_policy_rejects_enabled_true_during_burn_in():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["agents"]["defaults"]["memorySearch"]["enabled"] = True
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert "memorySearch.enabled must be false during burn-in" in str(exc)
    else:
        raise AssertionError("expected memory enabled assertion")


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

### File: `runtime/tests/test_openclaw_model_policy_assert.py`
```python
from runtime.tools.openclaw_model_policy_assert import (
    _discover_kimi_id,
    _parse_models_list_text,
    assert_policy,
)


def _cfg() -> dict:
    return {
        "agents": {
            "list": [
                {
                    "id": "main",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "github-copilot/claude-opus-4.6",
                            "google-gemini-cli/gemini-3-flash-preview",
                            "openrouter/openai/gpt-4.1-mini",
                        ],
                    },
                },
                {
                    "id": "quick",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "github-copilot/claude-opus-4.6",
                            "google-gemini-cli/gemini-3-flash-preview",
                        ],
                    },
                },
                {
                    "id": "think",
                    "thinking": "extra_high",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "github-copilot/claude-opus-4.6",
                            "google-gemini-cli/gemini-3-flash-preview",
                            "openrouter/openai/gpt-4.1-mini",
                        ],
                    },
                },
            ]
        }
    }


def _models_list_text() -> str:
    return """\
Model                                      Input      Ctx      Local Auth  Tags
openai-codex/gpt-5.3-codex                 text+image 266k     no    yes   configured
github-copilot/claude-opus-4.6             text+image 125k     no    yes   configured
google-gemini-cli/gemini-3-flash-preview   text+image 1024k    no    yes   configured
openrouter/openai/gpt-4.1-mini             text+image 200k     no    yes   configured
opencode/kimi-k2.5-free                    text+image 256k     no    yes   configured
"""


def test_policy_assert_passes_for_subscription_prefix_and_api_standby_tail():
    cfg = _cfg()
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is True
    assert result["ladders"]["main"]["working_count"] >= 1
    assert result["ladders"]["quick"]["working_count"] >= 1
    assert result["ladders"]["think"]["working_count"] >= 1


def test_policy_assert_fails_on_wrong_prefix_order():
    cfg = _cfg()
    cfg["agents"]["list"][0]["model"]["fallbacks"] = [
        "google-gemini-cli/gemini-3-flash-preview",
        "github-copilot/claude-opus-4.6",
    ]
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is False
    assert any("prefix mismatch" in v for v in result["violations"])


def test_policy_assert_fails_on_disallowed_haiku():
    cfg = _cfg()
    cfg["agents"]["list"][1]["model"]["fallbacks"] = [
        "github-copilot/claude-opus-4.6",
        "google-gemini-cli/gemini-3-flash-preview",
        "anthropic/claude-3-haiku-20240307",
    ]
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is False
    assert any("disallowed fallback" in v for v in result["violations"])


def test_policy_assert_fails_when_agent_has_no_working_models():
    cfg = _cfg()
    status = _parse_models_list_text(_models_list_text())
    for model_id in list(status.keys()):
        status[model_id]["working"] = False
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is False
    assert any("no working model detected" in v for v in result["violations"])


def test_discover_kimi_id_retained_for_backward_compat():
    kimi = _discover_kimi_id([], ["opencode/kimi-k2.5-free"])
    assert kimi == "opencode/kimi-k2.5-free"
```

### File: `runtime/tests/test_openclaw_policy_assert.py`
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
                    'fallbacks': ['github-copilot/claude-opus-4.6', 'google-gemini-cli/gemini-3-flash-preview'],
                },
                'memorySearch': {
                    'enabled': False,
                    'provider': 'local',
                    'fallback': 'none',
                    'sources': ['memory'],
                },
            },
            'list': [
                {'id': 'main', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/claude-opus-4.6', 'google-gemini-cli/gemini-3-flash-preview']}},
                {'id': 'quick', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/claude-opus-4.6', 'google-gemini-cli/gemini-3-flash-preview']}},
                {'id': 'think', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/claude-opus-4.6', 'google-gemini-cli/gemini-3-flash-preview']}},
            ],
        },
    }

def test_assert_policy_passes_for_expected_ladders():
    cfg = _cfg()
    cfg['agents']['defaults']['workspace'] = str(Path.home() / '.openclaw' / 'workspace')
    result = assert_policy(cfg)
    assert result['owners'] == ['owner-1']
    assert result['defaults_thinking'] == 'low'
    assert result['required_subscription_fallbacks'] == ['github-copilot/claude-opus-4.6', 'google-gemini-cli/gemini-3-flash-preview']
    assert result['memory']['enabled'] is False
    assert result['memory']['provider'] == 'local'
    assert result['memory']['fallback'] == 'none'

def test_non_owner_cannot_model_or_think_switch():
    cfg = _cfg()
    assert command_authorized(cfg, 'owner-1', '/model openai-codex/gpt-5.3-codex')
    assert not command_authorized(cfg, 'outsider', '/model openai-codex/gpt-5.3-codex')
    assert not command_authorized(cfg, 'outsider', '/think high')
```

### File: `runtime/tools/coo_worktree.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

BUILD_REPO="$(git rev-parse --show-toplevel)"
TRAIN_WT="$(dirname "$BUILD_REPO")/LifeOS__wt_coo_training"
TRAIN_BRANCH="coo/training"
OPENCLAW_PROFILE="${OPENCLAW_PROFILE:-}"
OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_STATE_DIR/openclaw.json}"
OPENCLAW_GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
OPENCLAW_BIN="${OPENCLAW_BIN:-}"

print_header() {
  local profile_label="(default)"
  if [ -n "$OPENCLAW_PROFILE" ]; then
    profile_label="$OPENCLAW_PROFILE"
  fi
  echo "BUILD_REPO=$BUILD_REPO"
  echo "TRAIN_WT=$TRAIN_WT"
  echo "TRAIN_BRANCH=$TRAIN_BRANCH"
  echo "OPENCLAW_PROFILE=$profile_label"
  echo "OPENCLAW_STATE_DIR=$OPENCLAW_STATE_DIR"
  echo "OPENCLAW_CONFIG_PATH=$OPENCLAW_CONFIG_PATH"
  if [ -n "$OPENCLAW_BIN" ]; then
    echo "OPENCLAW_BIN=$OPENCLAW_BIN"
  fi
}

ensure_openclaw_surface() {
  mkdir -p "$OPENCLAW_STATE_DIR"
  export OPENCLAW_STATE_DIR
  export OPENCLAW_CONFIG_PATH
  resolve_openclaw_bin
  export OPENCLAW_BIN
  export OPENCLAW_GATEWAY_PORT
}

resolve_openclaw_bin() {
  if [ -n "$OPENCLAW_BIN" ] && [ -x "$OPENCLAW_BIN" ]; then
    return 0
  fi

  if command -v openclaw >/dev/null 2>&1; then
    OPENCLAW_BIN="$(command -v openclaw)"
    return 0
  fi

  for candidate in \
    /home/linuxbrew/.linuxbrew/bin/openclaw \
    /usr/local/bin/openclaw \
    /usr/bin/openclaw; do
    if [ -x "$candidate" ]; then
      OPENCLAW_BIN="$candidate"
      return 0
    fi
  done

  echo "ERROR: OpenClaw binary not found. Install OpenClaw or add it to PATH." >&2
  echo "Checked: PATH, /home/linuxbrew/.linuxbrew/bin/openclaw, /usr/local/bin/openclaw, /usr/bin/openclaw" >&2
  exit 127
}

run_openclaw() {
  ensure_openclaw_surface
  if [ -n "$OPENCLAW_PROFILE" ]; then
    "$OPENCLAW_BIN" --profile "$OPENCLAW_PROFILE" "$@"
    return
  fi
  "$OPENCLAW_BIN" "$@"
}

resolve_gateway_token_from_config() {
  local token
  token="$(python3 - "$OPENCLAW_CONFIG_PATH" <<'PY'
import json
import os
import sys

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = (((data or {}).get("gateway") or {}).get("auth") or {}).get("token")
    if isinstance(token, str) and token:
        print(token)
except Exception:
    pass
PY
)"
  printf '%s\n' "$token"
}

strip_dashboard_token_fragments() {
  sed -E \
    -e 's/#token=[^[:space:]#&?]+//g' \
    -e 's/([?&])token=[^[:space:]#&?]+/\1/g' \
    -e 's/[?&]+$//'
}

resolve_dashboard_url() {
  local include_token_url="${1:-0}"
  local fallback_url output parsed token
  fallback_url="http://127.0.0.1:${OPENCLAW_GATEWAY_PORT}/"
  output="$(run_openclaw dashboard --no-open 2>/dev/null || true)"
  parsed="$(printf '%s\n' "$output" | sed -n 's/.*Dashboard URL: \(http[^[:space:]]*\).*/\1/p' | tail -n 1)"
  if [ -n "$parsed" ]; then
    if [ "$include_token_url" = "1" ]; then
      printf '%s\n' "$parsed"
    else
      printf '%s\n' "$parsed" | strip_dashboard_token_fragments
    fi
    return 0
  fi
  token="$(resolve_gateway_token_from_config)"
  if [ "$include_token_url" = "1" ] && [ -n "$token" ]; then
    printf '%s#token=%s\n' "$fallback_url" "$token"
    return 0
  fi
  printf '%s\n' "$fallback_url"
  return 0
}

emit_gate_blocking_summary() {
  local gate_status_path="${OPENCLAW_GATE_STATUS_PATH:-$OPENCLAW_STATE_DIR/runtime/gates/gate_status.json}"
  if [ ! -f "$gate_status_path" ]; then
    echo "GATE_STATUS_PATH_MISSING=$gate_status_path"
    return 0
  fi

  echo "GATE_STATUS_PATH=$gate_status_path"
  python3 - <<'PY' "$gate_status_path"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    obj = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"GATE_STATUS_PARSE_ERROR={type(exc).__name__}:{exc}")
    raise SystemExit(0)

print(f"GATE_PASS={'true' if obj.get('pass') else 'false'}")
reasons = obj.get("blocking_reasons") or []
if isinstance(reasons, list) and reasons:
    print("GATE_BLOCKING_REASONS_BEGIN")
    for reason in reasons:
        print(f"- {reason}")
    print("GATE_BLOCKING_REASONS_END")
PY
}

ensure_worktree() {
  if [ ! -d "$TRAIN_WT" ]; then
    git -C "$BUILD_REPO" worktree add -B "$TRAIN_BRANCH" "$TRAIN_WT" HEAD
  fi

  local wt_top
  wt_top="$(git -C "$TRAIN_WT" rev-parse --show-toplevel 2>/dev/null || true)"
  if [ -z "$wt_top" ] || [ "$wt_top" != "$TRAIN_WT" ]; then
    echo "ERROR: $TRAIN_WT is not a valid git worktree top-level." >&2
    exit 2
  fi
}

enter_training_dir() {
  ensure_worktree
  # Guardrail: never run tooling inside the main build workspace.
  if [[ "$PWD" == "$BUILD_REPO"* ]] && [[ "$PWD" != "$TRAIN_WT"* ]]; then
    cd "$TRAIN_WT"
    return
  fi
  cd "$TRAIN_WT"
}

build_repo_clean() {
  local s d
  s="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
  d="$(git -C "$BUILD_REPO" diff --name-only || true)"
  if [ -n "$s" ] || [ -n "$d" ]; then
    return 1
  fi
  return 0
}

job_evidence_dir() {
  local ts
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  printf '%s\n' "$BUILD_REPO/artifacts/evidence/openclaw/jobs/$ts"
}

write_clean_marker() {
  local out_file="$1"
  local porcelain diffnames
  porcelain="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
  diffnames="$(git -C "$BUILD_REPO" diff --name-only || true)"
  if [ -z "$porcelain" ] && [ -z "$diffnames" ]; then
    printf '(empty)\n' >"$out_file"
    return
  fi
  {
    [ -n "$porcelain" ] && printf '%s\n' "$porcelain"
    [ -n "$diffnames" ] && printf '%s\n' "$diffnames"
  } >"$out_file"
}

print_clean_block() {
  local label="$1" status_text="$2" diff_text="$3"
  echo "${label}_STATUS_BEGIN"
  if [ -n "$status_text" ]; then
    printf '%s\n' "$status_text"
  else
    echo "(empty)"
  fi
  echo "${label}_STATUS_END"
  echo "${label}_DIFF_BEGIN"
  if [ -n "$diff_text" ]; then
    printf '%s\n' "$diff_text"
  else
    echo "(empty)"
  fi
  echo "${label}_DIFF_END"
}

safe_redact_file_head() {
  local file="$1"
  local lines="${2:-20}"
  if [ -f "$file" ]; then
    sed -n "1,${lines}p" "$file" | sed -E 's/[A-Za-z0-9_-]{24,}/[REDACTED]/g'
  fi
}

redact_sensitive_stream() {
  python3 - <<'PY'
import re
import sys

text = sys.stdin.read()
text = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '[REDACTED_EMAIL]', text)
text = re.sub(r'Authorization\s*:\s*Bearer\s+\S+', 'Authorization: Bearer [REDACTED]', text, flags=re.I)
text = re.sub(r'\bxapp-[A-Za-z0-9-]{6,}\b', 'xapp-[REDACTED]', text)
text = re.sub(r'\bxox[aboprs]-[A-Za-z0-9-]{6,}\b', 'xox?-[REDACTED]', text)
text = re.sub(r'\bsk-or-v1[a-zA-Z0-9._-]{6,}\b', 'sk-or-v1[REDACTED]', text)
text = re.sub(r'\bsk-[A-Za-z0-9_-]{8,}\b', 'sk-[REDACTED]', text)
text = re.sub(r'\bsk-ant-[A-Za-z0-9_-]{8,}\b', 'sk-ant-[REDACTED]', text)
text = re.sub(r'\bgh[opurs]_[A-Za-z0-9]{12,}\b', 'gh*_[REDACTED]', text)
text = re.sub(r'\bAIza[0-9A-Za-z_-]{10,}\b', 'AIza[REDACTED]', text)
text = re.sub(r'\bya29\.[0-9A-Za-z._-]{12,}\b', 'ya29.[REDACTED]', text)
text = re.sub(r'[A-Za-z0-9+/_=-]{80,}', '[REDACTED_LONG]', text)
sys.stdout.write(text)
PY
}

write_hashes() {
  local evid_dir="$1"
  (
    cd "$evid_dir"
    find . -maxdepth 1 -type f -printf '%P\n' | LC_ALL=C sort | while IFS= read -r f; do
      [ -n "$f" ] && sha256sum "$f"
    done
  ) > "$evid_dir/hashes.sha256"
}

latest_job_evidence_dir() {
  local root="$BUILD_REPO/artifacts/evidence/openclaw/jobs"
  if [ ! -d "$root" ]; then
    return 1
  fi
  local latest
  latest="$(find "$root" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | LC_ALL=C sort | tail -n 1)"
  if [ -z "$latest" ]; then
    return 1
  fi
  printf '%s\n' "$root/$latest"
}

resolve_baseline_ref() {
  local repo="$1"
  if git -C "$repo" show-ref --verify --quiet refs/remotes/origin/main; then
    printf '%s\n' "origin/main"
  elif git -C "$repo" show-ref --verify --quiet refs/heads/main; then
    printf '%s\n' "main"
  else
    printf '%s\n' ""
  fi
}

write_blocked_report() {
  local evid_dir="$1"
  local report_name="$2"
  if [ -z "$evid_dir" ] || [ ! -d "$evid_dir" ]; then
    echo "ERROR: BLOCKED_REPORT_EVID_UNKNOWN" >&2
    return 1
  fi
  cat > "$evid_dir/$report_name"
  write_hashes "$evid_dir"
  return 0
}

write_worktree_change_set() {
  local evid_dir="$1"
  local wt_repo="$2"
  local wt_head baseline_ref baseline_mode baseline_tip merge_base
  wt_head="$(git -C "$wt_repo" rev-parse HEAD)"
  baseline_ref="$(resolve_baseline_ref "$wt_repo")"
  baseline_mode="baseline_unavailable"
  if [ "$baseline_ref" = "origin/main" ]; then
    baseline_mode="origin_main"
  elif [ "$baseline_ref" = "main" ]; then
    baseline_mode="local_main_offline"
  fi
  baseline_tip=""
  if [ -n "$baseline_ref" ]; then
    baseline_tip="$(git -C "$wt_repo" rev-parse --verify --quiet "${baseline_ref}^{commit}" 2>/dev/null || true)"
  fi
  merge_base=""
  if [ -n "$baseline_tip" ]; then
    merge_base="$(git -C "$wt_repo" merge-base "$baseline_tip" "$wt_head" 2>/dev/null || true)"
  fi

  printf '%s\n' "$wt_head" > "$evid_dir/worktree_head.txt"
  git -C "$wt_repo" status --porcelain=v1 > "$evid_dir/worktree_status_porcelain.txt"
  {
    if [ -n "$baseline_ref" ]; then
      echo "BASELINE_REF=$baseline_ref"
    else
      echo "BASELINE_REF=(unavailable)"
    fi
    echo "BASELINE_MODE=$baseline_mode"
    if [ -n "$baseline_tip" ]; then
      echo "BASELINE_HEAD=$baseline_tip"
    else
      echo "BASELINE_HEAD=(unavailable)"
    fi
    if [ -n "$merge_base" ]; then
      echo "MERGE_BASE=$merge_base"
    else
      echo "MERGE_BASE=(unavailable)"
    fi
  } > "$evid_dir/worktree_baseline.txt"

  if [ -n "$merge_base" ]; then
    git -C "$wt_repo" diff --name-only "$merge_base" "$wt_head" | LC_ALL=C sort -u > "$evid_dir/worktree_diff_name_only.txt"
  elif [ -n "$baseline_tip" ]; then
    git -C "$wt_repo" diff --name-only "$baseline_tip" "$wt_head" | LC_ALL=C sort -u > "$evid_dir/worktree_diff_name_only.txt"
  else
    : > "$evid_dir/worktree_diff_name_only.txt"
  fi
}

render_capsule_marker() {
  local capsule_file="$1"
  local err_file="$2"
  python3 "$BUILD_REPO/runtime/tools/coo_capsule_render.py" \
    --capsule "$capsule_file" \
    --key HEAD \
    --key EVID \
    --key RESULT_PRETTY_ERR_BYTES \
    --key RC \
    --key DURATION_S \
    --key PYTEST_SUMMARY \
    2>"$err_file"
}

usage() {
  cat <<'EOF'
Usage:
  runtime/tools/coo_worktree.sh start [--show-token-url] [--unsafe-allow-drift]
  runtime/tools/coo_worktree.sh tui [--show-token-url] [--unsafe-allow-drift] [-- <tui-args...>]
  runtime/tools/coo_worktree.sh app [--show-token-url] [--unsafe-allow-drift]
  runtime/tools/coo_worktree.sh stop
  runtime/tools/coo_worktree.sh diag
  runtime/tools/coo_worktree.sh models {status|fix}
  runtime/tools/coo_worktree.sh ensure
  runtime/tools/coo_worktree.sh path
  runtime/tools/coo_worktree.sh cd
  runtime/tools/coo_worktree.sh shell
  runtime/tools/coo_worktree.sh brief
  runtime/tools/coo_worktree.sh job e2e
  runtime/tools/coo_worktree.sh run-job <job.json>
  runtime/tools/coo_worktree.sh e2e
  runtime/tools/coo_worktree.sh land [--evid <dir>] [--src <ref>] [--dest main] [--allow-eol-only] [--emergency] [--skip-e2e]
  runtime/tools/coo_worktree.sh tui -- <tui-args...>
  runtime/tools/coo_worktree.sh run -- <command...>
  runtime/tools/coo_worktree.sh openclaw -- <openclaw-args...>

Enforcement modes:
  - Default startup mode is fail-closed for security/model/posture gates.
  - Use --unsafe-allow-drift for local emergency startup bypass.
EOF
}

cmd="${1:-}"
case "$cmd" in
  -h|--help|help)
    usage
    ;;
  ensure)
    ensure_worktree
    ensure_openclaw_surface
    print_header
    ;;
  start)
    shift || true
    show_token_url=0
    unsafe_allow_drift=0
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --show-token-url)
          show_token_url=1
          shift
          ;;
        --redacted-dashboard)
          show_token_url=0
          shift
          ;;
        --unsafe-allow-drift)
          unsafe_allow_drift=1
          shift
          ;;
        *)
          echo "ERROR: unknown start argument: $1" >&2
          exit 2
          ;;
      esac
    done
    ensure_openclaw_surface
    print_header
    start_failed=0
    pushd "$BUILD_REPO" >/dev/null
    if ! runtime/tools/openclaw_gateway_ensure.sh; then
      start_failed=1
    fi
    export COO_ENFORCEMENT_MODE=mission
    if ! runtime/tools/openclaw_models_preflight.sh; then
      start_failed=1
    fi
    if ! runtime/tools/openclaw_verify_surface.sh; then
      start_failed=1
    fi
    popd >/dev/null
    if [ "$start_failed" -ne 0 ] && [ "$unsafe_allow_drift" -ne 1 ]; then
      emit_gate_blocking_summary
      echo "ERROR: startup blocked by fail-closed gate policy." >&2
      echo "NEXT: fix blocking reasons above, or re-run with --unsafe-allow-drift for emergency local use only." >&2
      exit 1
    fi
    if [ "$start_failed" -ne 0 ] && [ "$unsafe_allow_drift" -eq 1 ]; then
      emit_gate_blocking_summary
      echo "WARNING: --unsafe-allow-drift bypass active. Continuing despite startup gate failures." >&2
    fi
    dashboard_url="$(resolve_dashboard_url "$show_token_url")"
    echo "DASHBOARD_URL=$dashboard_url"
    ;;
  tui)
    shift || true
    show_token_url=0
    unsafe_allow_drift=0
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --show-token-url)
          show_token_url=1
          shift
          ;;
        --unsafe-allow-drift)
          unsafe_allow_drift=1
          shift
          ;;
        --)
          shift
          break
          ;;
        *)
          break
          ;;
      esac
    done
    start_args=()
    if [ "$show_token_url" -eq 1 ]; then
      start_args+=("--show-token-url")
    fi
    if [ "$unsafe_allow_drift" -eq 1 ]; then
      start_args+=("--unsafe-allow-drift")
    fi
    "$0" start "${start_args[@]}"
    ensure_openclaw_surface
    print_header
    enter_training_dir
    run_openclaw tui --deliver --session main "$@"
    ;;
  app)
    shift || true
    show_token_url=0
    unsafe_allow_drift=0
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --show-token-url)
          show_token_url=1
          shift
          ;;
        --unsafe-allow-drift)
          unsafe_allow_drift=1
          shift
          ;;
        *)
          echo "ERROR: unknown app argument: $1" >&2
          exit 2
          ;;
      esac
    done
    start_args=()
    if [ "$show_token_url" -eq 1 ]; then
      start_args+=("--show-token-url")
    fi
    if [ "$unsafe_allow_drift" -eq 1 ]; then
      start_args+=("--unsafe-allow-drift")
    fi
    "$0" start "${start_args[@]}"
    ensure_openclaw_surface
    print_header
    app_url="$(resolve_dashboard_url "$show_token_url")"
    if powershell.exe -NoProfile -Command "Start-Process '$app_url'" >/dev/null 2>&1; then
      echo "APP_OPENED=$app_url"
    else
      echo "APP_OPEN_FAILED URL=$app_url"
    fi
    ;;
  stop)
    shift || true
    ensure_openclaw_surface
    print_header
    (
      cd "$BUILD_REPO"
      runtime/tools/openclaw_gateway_stop_local.sh
    )
    ;;
  diag)
    shift || true
    ensure_openclaw_surface
    print_header
    (
      cd "$BUILD_REPO"
      echo "GATEWAY_PORT=$OPENCLAW_GATEWAY_PORT"
      runtime/tools/openclaw_gateway_ensure.sh --check-only || true
      echo "MODELS_STATUS_BEGIN"
      status_tmp="$(mktemp)"
      if run_openclaw models status >"$status_tmp" 2>&1; then
        redact_sensitive_stream <"$status_tmp"
      else
        redact_sensitive_stream <"$status_tmp"
      fi
      rm -f "$status_tmp"
      echo "MODELS_STATUS_END"
      echo "MODEL_POLICY_ASSERT_BEGIN"
      python3 runtime/tools/openclaw_model_policy_assert.py --json || true
      echo "MODEL_POLICY_ASSERT_END"
      echo "HINT=Run 'openclaw models status --probe' for deeper provider diagnostics."
    )
    ;;
  models)
    shift || true
    sub="${1:-}"
    case "$sub" in
      status)
        ensure_openclaw_surface
        print_header
        (
          cd "$BUILD_REPO"
          python3 runtime/tools/openclaw_model_policy_assert.py --json | python3 - <<'PY'
import json
import sys

try:
    result = json.loads(sys.stdin.read())
    policy_ok = result.get("policy_ok", False)
    violations = result.get("violations", [])
    ladders = result.get("ladders", {})

    print("=== Model Ladder Health Status ===\n")

    if policy_ok:
        print("STATUS: OK - All ladder policies satisfied")
    else:
        print(f"STATUS: INVALID - {len(violations)} violation(s) detected")

    print("\nLadder Details:")
    for agent_id in ("main", "quick", "think"):
        ladder = ladders.get(agent_id, {})
        actual = ladder.get("actual", [])
        expected = ladder.get("expected", [])
        working_count = ladder.get("working_count", 0)
        top_rung_auth_missing = ladder.get("top_rung_auth_missing", False)

        print(f"\n  {agent_id}:")
        if not actual:
            print("    ERROR: Ladder missing or empty")
            print(f"    Expected: {', '.join(expected[:3])}...")
        else:
            print(f"    Configured: {', '.join(actual[:3])}{'...' if len(actual) > 3 else ''}")
            print(f"    Working models: {working_count}/{len(actual)}")
            if top_rung_auth_missing:
                print(f"    WARNING: Top rung ({actual[0]}) not authenticated")

    if violations:
        print("\nViolations:")
        for v in violations[:10]:
            print(f"  - {v}")
        if len(violations) > 10:
            print(f"  ... and {len(violations) - 10} more")

    print("\nNext steps:")
    if not policy_ok:
        print("  - Run 'coo models fix' for guided repair")
        print("  - Or manually edit $OPENCLAW_CONFIG_PATH")
    else:
        print("  - All checks passed")

except Exception as e:
    print(f"ERROR: Could not parse policy status: {e}", file=sys.stderr)
    sys.exit(1)
PY
        )
        ;;
      fix)
        ensure_openclaw_surface
        print_header
        (
          cd "$BUILD_REPO"
          python3 runtime/tools/openclaw_model_ladder_fix.py
        )
        ;;
      *)
        echo "Usage: coo models {status|fix}" >&2
        exit 2
        ;;
    esac
    ;;
  path)
    echo "$TRAIN_WT"
    ;;
  cd)
    ensure_worktree
    echo "$TRAIN_WT"
    ;;
  shell)
    enter_training_dir
    print_header
    echo "PWD=$PWD"
    exec "${SHELL:-/bin/bash}"
    ;;
  brief)
    enter_training_dir
    prompt="$(cat <<'EOF'
Read docs/11_admin/LIFEOS_STATE.md and docs/11_admin/BACKLOG.md from the repo.
Return exactly these headings:
TOP_3_ACTIONS:
- ...
- ...
- ...
TOP_BLOCKERS:
- ...
- ...
CEO_QUESTION:
- ...
Do not propose edits or patches.
EOF
)"

    raw_json="$(mktemp)"
    raw_err="$(mktemp)"
    cleanup() {
      rm -f "$raw_json" "$raw_err"
    }
    trap cleanup EXIT

    if ! run_openclaw agent --local --agent main --message "$prompt" --json >"$raw_json" 2>"$raw_err"; then
      echo "ERROR: coo brief failed to run local agent turn." >&2
      sed -n '1,20p' "$raw_err" | sed -E 's/[A-Za-z0-9_-]{24,}/[REDACTED]/g' >&2
      exit 1
    fi

    text="$(python3 - "$raw_json" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
payloads = data.get("payloads") or []
parts = []
for item in payloads:
    t = item.get("text")
    if isinstance(t, str) and t.strip():
        parts.append(t.strip())
print("\n\n".join(parts))
PY
)"

    if [ -z "$text" ]; then
      echo "ERROR: coo brief returned no assistant text." >&2
      exit 1
    fi

    if printf '%s\n' "$text" | rg -q '^TOP_3_ACTIONS:' && \
      printf '%s\n' "$text" | rg -q '^TOP_BLOCKERS:' && \
      printf '%s\n' "$text" | rg -q '^CEO_QUESTION:'; then
      printf '%s\n' "$text"
    else
      echo "TOP_3_ACTIONS:"
      echo "- unavailable"
      echo "- unavailable"
      echo "- unavailable"
      echo "TOP_BLOCKERS:"
      echo "- unavailable"
      echo "- unavailable"
      echo "CEO_QUESTION:"
      echo "- unavailable"
      echo
      printf '%s\n' "$text"
    fi
    ;;
  job)
    shift || true
    sub="${1:-}"
    if [ "$sub" != "e2e" ]; then
      usage
      exit 2
    fi

    enter_training_dir
    evid_dir="$(job_evidence_dir)"
    mkdir -p "$evid_dir"
    git -C "$BUILD_REPO" check-ignore -v "$evid_dir" > "$evid_dir/git_check_ignore.txt" 2>&1 || true
    raw_json="$evid_dir/agent_raw.json"
    raw_err="$evid_dir/agent_raw.stderr"
    job_json="$evid_dir/job.json"
    blocked_reason="$evid_dir/blocked_reason.txt"

    prompt="$(cat <<'EOF'
You are preparing a LifeOS test execution job.
Choose ONE representative E2E-style pytest command for this repository.
Discovered candidates include:
- pytest -q tests_recursive/test_e2e_smoke_timeout.py
- pytest -q -k e2e
- pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py

Return STRICT JSON ONLY (no markdown, no prose), matching exactly:
{
  "kind": "lifeos.job.v0.1",
  "job_type": "e2e_test",
  "objective": "Run a representative E2E test in the LifeOS repo",
  "scope": ["run tests only", "no code edits"],
  "non_goals": ["no installs", "no network", "no git operations"],
  "workdir": ".",
  "command": ["pytest", "-q", "..."],
  "timeout_s": 1800,
  "expected_artifacts": ["stdout.txt","stderr.txt","rc.txt","duration_s.txt"],
  "clean_repo_required": true
}

Rules:
- command must be read-only.
- Do not include git/rm/sudo/curl/wget/pip/npm/brew/apt/sh/bash/powershell.
- output must be a single JSON object.
EOF
)"

    if ! run_openclaw agent --local --agent main --message "$prompt" --json >"$raw_json" 2>"$raw_err"; then
      echo "ERROR: coo job e2e failed to generate job request." >&2
      sed -n '1,20p' "$raw_err" | sed -E 's/[A-Za-z0-9_-]{24,}/[REDACTED]/g' >&2
      exit 1
    fi

    if ! python3 - "$raw_json" "$job_json" <<'PY'
import json
import re
import sys
from pathlib import Path

raw_path = Path(sys.argv[1])
job_path = Path(sys.argv[2])
raw = json.loads(raw_path.read_text(encoding="utf-8"))
payloads = raw.get("payloads") or []
texts = []
for item in payloads:
    if isinstance(item, dict):
        text = item.get("text")
        if isinstance(text, str):
            texts.append(text.strip())

def parse_obj(text: str):
    text = text.strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None

obj = None
for t in texts:
    obj = parse_obj(t)
    if obj and obj.get("kind") == "lifeos.job.v0.1":
        break

if not obj or obj.get("kind") != "lifeos.job.v0.1":
    raise SystemExit(1)

job_path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
PY
    then
      strict_prompt="$(cat <<'EOF'
Output ONLY this JSON object type, no markdown:
{
  "kind": "lifeos.job.v0.1",
  "job_type": "e2e_test",
  "objective": "Run a representative E2E test in the LifeOS repo",
  "scope": ["run tests only", "no code edits"],
  "non_goals": ["no installs", "no network", "no git operations"],
  "workdir": ".",
  "command": ["pytest", "-q", "tests_recursive/test_e2e_smoke_timeout.py"],
  "timeout_s": 1800,
  "expected_artifacts": ["stdout.txt","stderr.txt","rc.txt","duration_s.txt"],
  "clean_repo_required": true
}
EOF
)"
      if ! run_openclaw agent --local --agent main --message "$strict_prompt" --json >"$raw_json" 2>"$raw_err"; then
        echo "ERROR: coo job e2e retry failed." >&2
        sed -n '1,20p' "$raw_err" | sed -E 's/[A-Za-z0-9_-]{24,}/[REDACTED]/g' >&2
        exit 1
      fi
      python3 - "$raw_json" "$job_json" <<'PY'
import json
import re
import sys
from pathlib import Path

raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
job_path = Path(sys.argv[2])
payloads = raw.get("payloads") or []
text = ""
for item in payloads:
    if isinstance(item, dict) and isinstance(item.get("text"), str):
        text = item["text"].strip()
        if text:
            break
match = re.search(r"\{.*\}", text, flags=re.S)
if not match:
    raise SystemExit(1)
obj = json.loads(match.group(0))
if obj.get("kind") != "lifeos.job.v0.1":
    raise SystemExit(1)
job_path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
PY
    fi

    if ! python3 - "$job_json" "$blocked_reason" <<'PY'
import json
import os
import sys
from pathlib import Path

job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
blocked = Path(sys.argv[2])
required = {
    "kind": str,
    "job_type": str,
    "objective": str,
    "scope": list,
    "non_goals": list,
    "workdir": str,
    "command": list,
    "timeout_s": int,
    "expected_artifacts": list,
    "clean_repo_required": bool,
}
for k, t in required.items():
    if k not in job:
        blocked.write_text(f"missing required field: {k}\n", encoding="utf-8")
        raise SystemExit(1)
    if not isinstance(job[k], t):
        blocked.write_text(f"invalid type for field: {k}\n", encoding="utf-8")
        raise SystemExit(1)

cmd = job["command"]
if not cmd or not all(isinstance(x, str) for x in cmd):
    blocked.write_text("invalid command array\n", encoding="utf-8")
    raise SystemExit(1)

cmd0 = os.path.basename(cmd[0])
if cmd0 not in {"pytest", "python", "python3"}:
    blocked.write_text(f"command not allowlisted: {cmd0}\n", encoding="utf-8")
    raise SystemExit(1)

deny = ["git", "rm", "sudo", "curl", "wget", "pip", "npm", "brew", "apt", "sh", "bash", "powershell"]
for token in cmd:
    low = token.lower()
    if any(d in low for d in deny):
        blocked.write_text(f"denylisted token found: {token}\n", encoding="utf-8")
        raise SystemExit(1)

timeout_s = job["timeout_s"]
if timeout_s > 3600:
    blocked.write_text("timeout_s too large\n", encoding="utf-8")
    raise SystemExit(1)
PY
    then
      echo "ERROR: generated job.json failed validation." >&2
      safe_redact_file_head "$blocked_reason" 20 >&2
      exit 1
    fi

    if ! python3 -m json.tool "$job_json" > "$evid_dir/job.pretty.json" 2>"$evid_dir/job.pretty.err"; then
      printf 'invalid JSON in job.json\n' > "$blocked_reason"
      echo "ERROR: job.json is not strict JSON." >&2
      safe_redact_file_head "$evid_dir/job.pretty.err" 20 >&2
      exit 1
    fi
    if [ -s "$evid_dir/job.pretty.err" ]; then
      {
        echo "BLOCKED: job.pretty.err non-empty"
        safe_redact_file_head "$evid_dir/job.pretty.err" 40
      } > "$blocked_reason"
      echo "ERROR: job.pretty.err non-empty." >&2
      exit 22
    fi
    if [ ! -s "$evid_dir/job.pretty.json" ] || [ "$(wc -c <"$evid_dir/job.pretty.json" | tr -d ' ')" -lt 50 ]; then
      printf 'BLOCKED: job.pretty.json missing or too small\n' > "$blocked_reason"
      echo "ERROR: job.pretty.json missing or too small." >&2
      exit 22
    fi

    write_hashes "$evid_dir"
    echo "JOB_EVID_DIR=$evid_dir"
    echo "JOB_JSON_PATH=$job_json"
    ;;
  run-job)
    shift || true
    if [ "$#" -ne 1 ]; then
      usage
      exit 2
    fi
    job_path="$1"
    if [ ! -f "$job_path" ]; then
      echo "ERROR: job file not found: $job_path" >&2
      exit 2
    fi

    job_dir="$(cd "$(dirname "$job_path")" && pwd)"
    blocked_reason="$job_dir/blocked_reason.txt"

    # Mission mode preflight
    ensure_openclaw_surface
    if [ "${OPENCLAW_MODELS_PREFLIGHT_SKIP:-}" != "1" ]; then
      (
        cd "$BUILD_REPO"
        export COO_ENFORCEMENT_MODE=mission
        if ! runtime/tools/openclaw_models_preflight.sh >/dev/null 2>&1; then
          echo "ERROR: Model preflight failed in mission mode." >&2
          printf 'Model preflight failed in mission mode\n' > "$blocked_reason"
          exit 11
        fi
      )
    fi

    if ! build_repo_clean; then
      echo "ERROR: BUILD_REPO not clean before run-job." >&2
      mkdir -p "$job_dir"
      write_clean_marker "$job_dir/clean_pre.txt"
      printf 'BUILD_REPO not clean before run-job\n' > "$blocked_reason"
      git -C "$BUILD_REPO" status --porcelain=v1 || true
      git -C "$BUILD_REPO" diff --name-only || true
      exit 10
    fi

    meta_file="$(mktemp)"
    cleanup_meta() {
      rm -f "$meta_file"
    }
    trap cleanup_meta EXIT

    if ! python3 - "$job_path" "$meta_file" <<'PY'
import json
import os
import sys
from pathlib import Path

job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
meta_path = Path(sys.argv[2])

if job.get("kind") != "lifeos.job.v0.1":
    raise SystemExit("invalid kind")
cmd = job.get("command")
if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) for x in cmd):
    raise SystemExit("invalid command")

cmd0 = os.path.basename(cmd[0])
if cmd0 not in {"pytest", "python", "python3"}:
    raise SystemExit("command not in allowlist")

banned = ["git", "rm", "sudo", "curl", "wget", "pip", "npm", "brew", "apt", "sh", "bash", "powershell"]
for token in cmd:
    low = token.lower()
    if any(b in low for b in banned):
        raise SystemExit(f"banned token in command: {token}")

timeout_s = job.get("timeout_s")
if not isinstance(timeout_s, int) or timeout_s <= 0 or timeout_s > 3600:
    raise SystemExit("invalid timeout_s")

workdir = job.get("workdir", ".")
if not isinstance(workdir, str) or not workdir:
    raise SystemExit("invalid workdir")

meta = {
    "timeout_s": timeout_s,
    "workdir": workdir,
    "command": cmd,
}
meta_path.write_text(json.dumps(meta), encoding="utf-8")
PY
    then
      printf 'job validation failed for run-job\n' > "$blocked_reason"
      exit 3
    fi

    timeout_s="$(python3 - "$meta_file" <<'PY'
import json
import sys
print(json.loads(open(sys.argv[1], encoding="utf-8").read())["timeout_s"])
PY
)"
    job_workdir="$(python3 - "$meta_file" <<'PY'
import json
import sys
print(json.loads(open(sys.argv[1], encoding="utf-8").read())["workdir"])
PY
)"
    mapfile -d '' job_cmd < <(python3 - "$meta_file" <<'PY'
import json
import sys
cmd = json.loads(open(sys.argv[1], encoding="utf-8").read())["command"]
for part in cmd:
    sys.stdout.write(part)
    sys.stdout.write("\0")
PY
)

    enter_training_dir
    evid_dir="$(cd "$(dirname "$job_path")" && pwd)"
    mkdir -p "$evid_dir"
    stdout_file="$evid_dir/stdout.txt"
    stderr_file="$evid_dir/stderr.txt"
    rc_file="$evid_dir/rc.txt"
    dur_file="$evid_dir/duration_s.txt"
    result_file="$evid_dir/result.json"
    blocked_reason="$evid_dir/blocked_reason.txt"
    clean_pre_file="$evid_dir/clean_pre.txt"
    clean_post_file="$evid_dir/clean_post.txt"
    echo "EVID=$evid_dir"
    write_clean_marker "$clean_pre_file"

    start_s="$(date +%s)"
    set +e
    (
      cd "$TRAIN_WT/$job_workdir"
      timeout "$timeout_s" "${job_cmd[@]}"
    ) >"$stdout_file" 2>"$stderr_file"
    rc="$?"
    set -e
    end_s="$(date +%s)"
    duration_s="$((end_s - start_s))"

    printf '%s\n' "$rc" >"$rc_file"
    printf '%s\n' "$duration_s" >"$dur_file"

    clean_post=true
    if ! build_repo_clean; then
      clean_post=false
    fi
    write_clean_marker "$clean_post_file"

    python3 - "$job_path" "$result_file" "$rc" "$duration_s" "$evid_dir" "$clean_post" "$meta_file" <<'PY'
import json
import sys
from pathlib import Path

job_path, result_path, rc, duration_s, evid_dir, clean_post, meta_path = sys.argv[1:]
meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
result = {
    "kind": "lifeos.result.v0.1",
    "job_path": str(Path(job_path).resolve()),
    "command": meta["command"],
    "rc": int(rc),
    "duration_s": int(duration_s),
    "evid_dir": str(Path(evid_dir).resolve()),
    "clean_pre": True,
    "clean_post": clean_post.lower() == "true",
}
Path(result_path).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
PY

    if ! python3 -m json.tool "$result_file" > "$evid_dir/result.pretty.json" 2>"$evid_dir/result.pretty.err"; then
      printf 'invalid JSON in result.json\n' > "$blocked_reason"
      echo "ERROR: result.json failed strict JSON validation." >&2
      safe_redact_file_head "$evid_dir/result.pretty.err" 20 >&2
      exit 12
    fi
    if [ -s "$evid_dir/result.pretty.err" ]; then
      {
        echo "BLOCKED: result.pretty.err non-empty"
        safe_redact_file_head "$evid_dir/result.pretty.err" 40
      } > "$blocked_reason"
      echo "ERROR: result.pretty.err non-empty." >&2
      exit 23
    fi
    if [ ! -s "$evid_dir/result.pretty.json" ] || [ "$(wc -c <"$evid_dir/result.pretty.json" | tr -d ' ')" -lt 50 ]; then
      printf 'BLOCKED: result.pretty.json missing or too small\n' > "$blocked_reason"
      echo "ERROR: result.pretty.json missing or too small." >&2
      exit 23
    fi

    if [ "$clean_post" != "true" ]; then
      printf 'BUILD_REPO dirtied by run-job\n' > "$blocked_reason"
      echo "ERROR: BUILD_REPO dirtied by run-job." >&2
      git -C "$BUILD_REPO" status --porcelain=v1 || true
      git -C "$BUILD_REPO" diff --name-only || true
      exit 11
    fi

    write_worktree_change_set "$evid_dir" "$TRAIN_WT"
    write_hashes "$evid_dir"
    echo "RESULT_JSON_PATH=$result_file"
    echo "EVID_DIR=$evid_dir"
    echo "RC=$rc"
    echo "DURATION_S=$duration_s"
    ;;
  e2e)
    enter_training_dir
    e2e_tmp="$(mktemp)"
    e2e_tmp_run="$e2e_tmp.run"
    capsule_tmp="$(mktemp)"
    capsule_file=""
    capsule_missing="$(mktemp)"
    rc_e2e=0
    job_path=""
    result_path=""
    evid_dir=""
    rc_val=""
    dur_val=""
    summary_line=""
    job_err_size="0"
    result_err_size="0"
    cleanup_e2e() {
      rm -f "$e2e_tmp" "$e2e_tmp_run" "$capsule_tmp" "$capsule_missing"
    }
    trap cleanup_e2e EXIT
    append_capsule_line() {
      local line="$1"
      printf '%s\n' "$line" >> "$capsule_tmp"
    }

    emit_clean_block() {
      local label="$1" status_text="$2" diff_text="$3" line
      while IFS= read -r line; do
        append_capsule_line "$line"
      done < <(print_clean_block "$label" "$status_text" "$diff_text")
    }

    pre_status="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
    pre_diff="$(git -C "$BUILD_REPO" diff --name-only || true)"
    emit_clean_block PRE "$pre_status" "$pre_diff"

    set +e
    (
      cd "$BUILD_REPO"
      "$0" job e2e
    ) >"$e2e_tmp"
    rc_e2e=$?
    set -e
    if [ "$rc_e2e" -ne 0 ]; then
      echo "ERROR: coo e2e failed during job generation." >&2
      cat "$e2e_tmp" >&2
      exit "$rc_e2e"
    fi

    mid_status="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
    mid_diff="$(git -C "$BUILD_REPO" diff --name-only || true)"
    emit_clean_block MID "$mid_status" "$mid_diff"

    job_path="$(rg '^JOB_JSON_PATH=' "$e2e_tmp" | sed 's/^JOB_JSON_PATH=//')"
    if [ -z "$job_path" ] || [ ! -f "$job_path" ]; then
      echo "ERROR: coo e2e could not resolve job path." >&2
      exit 1
    fi

    set +e
    (
      cd "$BUILD_REPO"
      "$0" run-job "$job_path"
    ) | tee "$e2e_tmp_run"
    rc_e2e=$?
    set -e
    result_path="$(rg '^RESULT_JSON_PATH=' "$e2e_tmp_run" | sed 's/^RESULT_JSON_PATH=//')"
    evid_dir="$(rg '^EVID_DIR=' "$e2e_tmp_run" | sed 's/^EVID_DIR=//')"
    rc_val="$(rg '^RC=' "$e2e_tmp_run" | sed 's/^RC=//')"
    dur_val="$(rg '^DURATION_S=' "$e2e_tmp_run" | sed 's/^DURATION_S=//')"
    if [ -n "$evid_dir" ] && [ -f "$evid_dir/stdout.txt" ]; then
      summary_line="$(grep -E 'passed,.*deselected' "$evid_dir/stdout.txt" | tail -n 1 || true)"
    fi
    if [ -n "$evid_dir" ] && [ -f "$evid_dir/job.pretty.err" ]; then
      job_err_size="$(wc -c <"$evid_dir/job.pretty.err" | tr -d ' ')"
    fi
    if [ -n "$evid_dir" ] && [ -f "$evid_dir/result.pretty.err" ]; then
      result_err_size="$(wc -c <"$evid_dir/result.pretty.err" | tr -d ' ')"
    fi

    post_status="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
    post_diff="$(git -C "$BUILD_REPO" diff --name-only || true)"
    emit_clean_block POST "$post_status" "$post_diff"

    append_capsule_line "COO_E2E_MINI_CAPSULE_BEGIN"
    append_capsule_line "HEAD=$(git -C "$BUILD_REPO" rev-parse --short HEAD)"
    append_capsule_line "EVID=${evid_dir:-unknown}"
    append_capsule_line "JOB_PRETTY_ERR_BYTES=$job_err_size"
    append_capsule_line "RESULT_PRETTY_ERR_BYTES=$result_err_size"
    append_capsule_line "RC=${rc_val:-unknown}"
    append_capsule_line "DURATION_S=${dur_val:-unknown}"
    if [ -n "$summary_line" ]; then
      append_capsule_line "PYTEST_SUMMARY=$summary_line"
    else
      append_capsule_line "PYTEST_SUMMARY=(summary not found)"
    fi
    append_capsule_line "EVID_FILES_BEGIN"
    if [ -n "$evid_dir" ] && [ -d "$evid_dir" ]; then
      while IFS= read -r evid_file; do
        append_capsule_line "$evid_file"
      done < <(find "$evid_dir" -maxdepth 1 -type f -printf '%f\n' | sort)
    fi
    append_capsule_line "EVID_FILES_END"
    append_capsule_line "COO_E2E_MINI_CAPSULE_END"

    if [ -z "$evid_dir" ] || [ ! -d "$evid_dir" ]; then
      echo "INTERNAL_ERROR: CAPSULE_FORMAT" >&2
      echo "EVID_DIR_MISSING" >&2
      exit 24
    fi
    capsule_file="$evid_dir/capsule.txt"
    cp "$capsule_tmp" "$capsule_file"

    missing_evidence=""
    for required_file in clean_pre.txt clean_post.txt git_check_ignore.txt hashes.sha256 stdout.txt stderr.txt; do
      if [ ! -f "$evid_dir/$required_file" ]; then
        missing_evidence="${missing_evidence}${required_file}"$'\n'
      fi
    done
    if [ -n "$missing_evidence" ]; then
      echo "INTERNAL_ERROR: EVIDENCE_INCOMPLETE" >&2
      printf '%s' "$missing_evidence" | sed '/^$/d' >&2
      exit 25
    fi

    if ! python3 - "$capsule_file" "$capsule_missing" <<'PY'
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
missing_out = Path(sys.argv[2])

def count_exact(s):
    return sum(1 for l in lines if l == s)

def count_prefix(p):
    return sum(1 for l in lines if l.startswith(p))

required_exact = [
    "PRE_STATUS_BEGIN", "PRE_STATUS_END", "PRE_DIFF_BEGIN", "PRE_DIFF_END",
    "MID_STATUS_BEGIN", "MID_STATUS_END", "MID_DIFF_BEGIN", "MID_DIFF_END",
    "POST_STATUS_BEGIN", "POST_STATUS_END", "POST_DIFF_BEGIN", "POST_DIFF_END",
    "COO_E2E_MINI_CAPSULE_BEGIN", "EVID_FILES_BEGIN", "EVID_FILES_END",
    "COO_E2E_MINI_CAPSULE_END",
]
required_prefix = [
    "HEAD=", "EVID=", "JOB_PRETTY_ERR_BYTES=", "RESULT_PRETTY_ERR_BYTES=",
    "RC=", "PYTEST_SUMMARY=",
]

missing = []
for token in required_exact:
    if count_exact(token) != 1:
        missing.append(token)
for token in required_prefix:
    if count_prefix(token) != 1:
        missing.append(token)

# Explicit hard requirements requested for capsule format conformance.
if count_exact("EVID_FILES_BEGIN") != 1:
    missing.append("EVID_FILES_BEGIN")
if count_exact("EVID_FILES_END") != 1:
    missing.append("EVID_FILES_END")
if count_prefix("RESULT_PRETTY_ERR_BYTES=") != 1:
    missing.append("RESULT_PRETTY_ERR_BYTES=")

result_err_lines = [l for l in lines if l.startswith("RESULT_PRETTY_ERR_BYTES=")]
if len(result_err_lines) == 1:
    value = result_err_lines[0].split("=", 1)[1].strip()
    if not value.isdigit():
        missing.append("RESULT_PRETTY_ERR_BYTES_NOT_INT")
    elif int(value) < 0:
        missing.append("RESULT_PRETTY_ERR_BYTES_NEGATIVE")

job_err_lines = [l for l in lines if l.startswith("JOB_PRETTY_ERR_BYTES=")]
if len(job_err_lines) == 1:
    value = job_err_lines[0].split("=", 1)[1].strip()
    if not value.isdigit():
        missing.append("JOB_PRETTY_ERR_BYTES_NOT_INT")
    elif int(value) < 0:
        missing.append("JOB_PRETTY_ERR_BYTES_NEGATIVE")

rc_lines = [l for l in lines if l.startswith("RC=")]
if len(rc_lines) == 1:
    value = rc_lines[0].split("=", 1)[1].strip()
    if not value.isdigit():
        missing.append("RC_NOT_INT")
    elif int(value) < 0:
        missing.append("RC_NEGATIVE")

order_tokens = [
    "PRE_STATUS_BEGIN", "PRE_STATUS_END", "PRE_DIFF_BEGIN", "PRE_DIFF_END",
    "MID_STATUS_BEGIN", "MID_STATUS_END", "MID_DIFF_BEGIN", "MID_DIFF_END",
    "POST_STATUS_BEGIN", "POST_STATUS_END", "POST_DIFF_BEGIN", "POST_DIFF_END",
    "COO_E2E_MINI_CAPSULE_BEGIN",
    "HEAD=", "EVID=", "JOB_PRETTY_ERR_BYTES=", "RESULT_PRETTY_ERR_BYTES=",
    "RC=", "PYTEST_SUMMARY=",
    "EVID_FILES_BEGIN", "EVID_FILES_END", "COO_E2E_MINI_CAPSULE_END",
]

def first_index(token):
    for i, line in enumerate(lines):
        if token.endswith("="):
            if line.startswith(token):
                return i
        elif line == token:
            return i
    return -1

indices = [first_index(t) for t in order_tokens]
if any(i < 0 for i in indices):
    pass
else:
    for i in range(len(indices) - 1):
        if indices[i] >= indices[i + 1]:
            missing.append(f"ORDER:{order_tokens[i]}->{order_tokens[i+1]}")

for label in ("PRE", "MID", "POST"):
    status_begin = first_index(f"{label}_STATUS_BEGIN")
    status_end = first_index(f"{label}_STATUS_END")
    diff_begin = first_index(f"{label}_DIFF_BEGIN")
    diff_end = first_index(f"{label}_DIFF_END")
    if status_begin < 0 or status_end < 0:
        missing.append(f"{label}:STATUS_MARKERS_MISSING")
    elif status_begin >= status_end:
        missing.append(f"{label}:STATUS_ORDER")
    elif (status_end - status_begin) < 2:
        missing.append(f"{label}:STATUS_EMPTY_BLOCK")
    if diff_begin < 0 or diff_end < 0:
        missing.append(f"{label}:DIFF_MARKERS_MISSING")
    elif diff_begin >= diff_end:
        missing.append(f"{label}:DIFF_ORDER")
    elif (diff_end - diff_begin) < 2:
        missing.append(f"{label}:DIFF_EMPTY_BLOCK")

evid_begin = first_index("EVID_FILES_BEGIN")
evid_end = first_index("EVID_FILES_END")
if evid_begin < 0 or evid_end < 0:
    missing.append("EVID_FILES_BLOCK_MISSING")
elif evid_begin >= evid_end:
    missing.append("EVID_FILES_BLOCK_ORDER")
elif (evid_end - evid_begin) < 2:
    missing.append("EVID_FILES_BLOCK_EMPTY")

if missing:
    missing_out.write_text("\n".join(missing) + "\n", encoding="utf-8")
    raise SystemExit(1)
missing_out.write_text("", encoding="utf-8")
PY
    then
      echo "INTERNAL_ERROR: CAPSULE_FORMAT" >&2
      safe_redact_file_head "$capsule_missing" 20 >&2
      exit 24
    fi
    if ! marker_block="$(render_capsule_marker "$capsule_file" "$capsule_missing")"; then
      echo "INTERNAL_ERROR: CAPSULE_FORMAT" >&2
      safe_redact_file_head "$capsule_missing" 20 >&2
      exit 24
    fi
    printf '%s\n' "$marker_block" > "$evid_dir/marker_receipt.txt"
    write_hashes "$evid_dir"
    printf '%s\n' "$marker_block"
    echo "COO_E2E_JOB_PATH=$job_path"
    echo "COO_E2E_RESULT_PATH=$result_path"
    echo "COO_E2E_RC=${rc_val:-unknown}"
    echo "COO_E2E_DURATION_S=${dur_val:-unknown}"
    if [ -n "$summary_line" ]; then
      echo "COO_E2E_PYTEST_SUMMARY=$summary_line"
    else
      echo "COO_E2E_PYTEST_SUMMARY=(not found)"
    fi
    if [ "$rc_e2e" -ne 0 ]; then
      exit "$rc_e2e"
    fi
    ;;
  land)
    shift || true
    evid_dir_arg=""
    src_ref_arg=""
    dest_ref="main"
    allow_eol_only=false
    emergency=false
    skip_e2e=false
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --evid)
          shift || true
          evid_dir_arg="${1:-}"
          ;;
        --src)
          shift || true
          src_ref_arg="${1:-}"
          ;;
        --dest)
          shift || true
          dest_ref="${1:-}"
          ;;
        --allow-eol-only)
          allow_eol_only=true
          ;;
        --emergency)
          emergency=true
          ;;
        --skip-e2e)
          skip_e2e=true
          ;;
        *)
          usage
          exit 2
          ;;
      esac
      shift || true
    done

    if [ -n "$evid_dir_arg" ]; then
      if [[ "$evid_dir_arg" = /* ]]; then
        evid_dir="$evid_dir_arg"
      else
        evid_dir="$BUILD_REPO/$evid_dir_arg"
      fi
    else
      evid_dir="$(latest_job_evidence_dir || true)"
    fi

    if [ -z "${evid_dir:-}" ] || [ ! -d "$evid_dir" ]; then
      echo "ERROR: EVID_DIR_REQUIRED_FOR_COO_LAND" >&2
      exit 40
    fi

    pre_status="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
    pre_diff="$(git -C "$BUILD_REPO" diff --name-only || true)"
    if [ -n "$pre_status" ] || [ -n "$pre_diff" ]; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__PRE_DIRTY.md" <<EOF
# REPORT_BLOCKED__coo_land__PRE_DIRTY
REASON=BUILD_REPO_NOT_CLEAN
STATUS_PORCELAIN_BEGIN
${pre_status:-"(empty)"}
STATUS_PORCELAIN_END
DIFF_NAME_ONLY_BEGIN
${pre_diff:-"(empty)"}
DIFF_NAME_ONLY_END
EOF
      echo "ERROR: coo land preflight requires a clean BUILD_REPO." >&2
      exit 41
    fi

    # Config-aware clean-check gate (EOL config compliance + receipt)
    clean_receipt="$evid_dir/clean_check_preflight.json"
    if ! python3 "$BUILD_REPO/runtime/tools/coo_land_policy.py" \
         clean-check --repo "$BUILD_REPO" --receipt "$clean_receipt" 2>"$evid_dir/clean_check_preflight.err"; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__CLEAN_CHECK_FAILED.md" <<EOF
# REPORT_BLOCKED__coo_land__CLEAN_CHECK_FAILED
REASON=CLEAN_CHECK_GATE_FAILED
RECEIPT=$clean_receipt
STDERR_BEGIN
$(sed -n '1,20p' "$evid_dir/clean_check_preflight.err")
STDERR_END
EOF
      echo "ERROR: coo land clean-check gate failed (config non-compliant or dirty)." >&2
      exit 41
    fi

    src_ref="$src_ref_arg"
    if [ -z "$src_ref" ] && [ -f "$evid_dir/worktree_head.txt" ]; then
      src_ref="$(sed -n '1p' "$evid_dir/worktree_head.txt" | tr -d '[:space:]')"
    fi
    if [ -z "$src_ref" ] && [ -f "$evid_dir/job.json" ]; then
      src_ref="$(python3 - "$evid_dir/job.json" <<'PY'
import json
import sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
value = data.get("source_ref")
if isinstance(value, str):
    print(value.strip())
else:
    print("")
PY
)"
    fi
    if [ -z "$src_ref" ]; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__SRC_REF_MISSING.md" <<'EOF'
# REPORT_BLOCKED__coo_land__SRC_REF_MISSING
REASON=SRC_REF_UNRESOLVED
EOF
      echo "ERROR: coo land could not resolve --src or worktree_head.txt." >&2
      exit 41
    fi

    src_head="$(git -C "$BUILD_REPO" rev-parse --verify --quiet "${src_ref}^{commit}" 2>/dev/null || true)"
    if [ -z "$src_head" ]; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__SRC_REF_INVALID.md" <<EOF
# REPORT_BLOCKED__coo_land__SRC_REF_INVALID
REASON=SRC_REF_NOT_FOUND
SRC_REF=$src_ref
EOF
      echo "ERROR: coo land source ref not found: $src_ref" >&2
      exit 41
    fi

    baseline_ref="$(resolve_baseline_ref "$BUILD_REPO")"
    baseline_mode="baseline_unavailable"
    if [ "$baseline_ref" = "origin/main" ]; then
      baseline_mode="origin_main"
    elif [ "$baseline_ref" = "main" ]; then
      baseline_mode="local_main_offline"
    fi
    baseline_tip=""
    if [ -n "$baseline_ref" ]; then
      baseline_tip="$(git -C "$BUILD_REPO" rev-parse --verify --quiet "${baseline_ref}^{commit}" 2>/dev/null || true)"
    fi
    if [ -z "$baseline_tip" ]; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__BASELINE_MISSING.md" <<EOF
# REPORT_BLOCKED__coo_land__BASELINE_MISSING
REASON=BASELINE_REF_NOT_FOUND
BASELINE_REF=${baseline_ref:-"(unavailable)"}
EOF
      echo "ERROR: coo land baseline ref unavailable: $baseline_ref" >&2
      exit 41
    fi

    merge_base="$(git -C "$BUILD_REPO" merge-base "$baseline_tip" "$src_head" 2>/dev/null || true)"
    provenance_descended=0
    if [ -n "$merge_base" ] && [ "$merge_base" = "$baseline_tip" ]; then
      provenance_descended=1
    fi
    land_mode="path_transplant"

    allowlist_src="$evid_dir/worktree_diff_name_only.txt"
    if [ ! -f "$allowlist_src" ]; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__ALLOWLIST_MISSING.md" <<EOF
# REPORT_BLOCKED__coo_land__ALLOWLIST_MISSING
REASON=worktree_diff_name_only.txt_NOT_FOUND
ALLOWLIST_PATH=$allowlist_src
EOF
      echo "ERROR: coo land requires worktree_diff_name_only.txt in evidence dir." >&2
      exit 41
    fi

    allow_sorted="$(mktemp)"
    allow_hash_file="$(mktemp)"
    allow_err="$(mktemp)"
    actions_file="$(mktemp)"
    actual_sorted="$(mktemp)"
    path_mismatch="$(mktemp)"
    eol_err="$(mktemp)"
    cleanup_land_files() {
      rm -f "$allow_sorted" "$allow_hash_file" "$allow_err" "$actions_file" "$actual_sorted" "$path_mismatch" "$eol_err"
    }
    trap cleanup_land_files EXIT

    if ! python3 "$BUILD_REPO/runtime/tools/coo_land_policy.py" \
      allowlist \
      --input "$allowlist_src" \
      --output "$allow_sorted" \
      --hash-output "$allow_hash_file" \
      2>"$allow_err"; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__ALLOWLIST_INVALID.md" <<EOF
# REPORT_BLOCKED__coo_land__ALLOWLIST_INVALID
REASON=ALLOWLIST_POLICY_REJECTED
DETAIL_BEGIN
$(sed -n '1,40p' "$allow_err")
DETAIL_END
EOF
      echo "ERROR: coo land rejected allowlist from evidence." >&2
      exit 41
    fi

    allowlist_hash="$(sed -n '1p' "$allow_hash_file" | tr -d '[:space:]')"
    : > "$actions_file"
    while IFS= read -r allow_path; do
      [ -z "$allow_path" ] && continue
      if git -C "$BUILD_REPO" cat-file -e "${src_head}:${allow_path}" 2>/dev/null; then
        printf 'checkout\t%s\n' "$allow_path" >> "$actions_file"
      elif git -C "$BUILD_REPO" cat-file -e "${baseline_tip}:${allow_path}" 2>/dev/null; then
        printf 'delete\t%s\n' "$allow_path" >> "$actions_file"
      else
        write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__ALLOWLIST_UNEXPECTED_PATH.md" <<EOF
# REPORT_BLOCKED__coo_land__ALLOWLIST_UNEXPECTED_PATH
REASON=ALLOWLIST_PATH_NOT_IN_SRC_OR_BASELINE
PATH=$allow_path
SRC_HEAD=$src_head
BASELINE_HEAD=$baseline_tip
EOF
        echo "ERROR: coo land allowlist path not found in src or baseline: $allow_path" >&2
        exit 41
      fi
    done < "$allow_sorted"

    if ! git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__DEST_CHECKOUT_FAILED.md" <<EOF
# REPORT_BLOCKED__coo_land__DEST_CHECKOUT_FAILED
REASON=DEST_REF_NOT_FOUND
DEST_REF=$dest_ref
EOF
      echo "ERROR: coo land destination ref not found: $dest_ref" >&2
      exit 41
    fi
    dest_head_before="$(git -C "$BUILD_REPO" rev-parse "$dest_ref")"

    land_branch="land/$(date -u +%Y%m%dT%H%M%SZ)-${src_head:0:7}"
    if ! git -C "$BUILD_REPO" checkout -b "$land_branch" "$dest_ref" >/dev/null 2>&1; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__LAND_BRANCH_FAILED.md" <<EOF
# REPORT_BLOCKED__coo_land__LAND_BRANCH_FAILED
REASON=LAND_BRANCH_CREATE_FAILED
LAND_BRANCH=$land_branch
EOF
      echo "ERROR: coo land could not create temporary landing branch." >&2
      exit 41
    fi

    land_failed() {
      local report_name="$1"
      local reason="$2"
      git -C "$BUILD_REPO" merge --abort >/dev/null 2>&1 || true
      git -C "$BUILD_REPO" cherry-pick --abort >/dev/null 2>&1 || true
      git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || true
      git -C "$BUILD_REPO" branch -D "$land_branch" >/dev/null 2>&1 || true
      write_blocked_report "$evid_dir" "$report_name" <<EOF
# $report_name
REASON=$reason
SRC_REF=$src_ref
SRC_HEAD=$src_head
DEST_REF=$dest_ref
BASELINE_REF=$baseline_ref
EOF
      echo "ERROR: coo land blocked ($reason)." >&2
      exit 41
    }

    while IFS=$'\t' read -r action allow_path; do
      [ -z "$allow_path" ] && continue
      if [ "$action" = "checkout" ]; then
        git -C "$BUILD_REPO" checkout "$src_head" -- "$allow_path" || land_failed "REPORT_BLOCKED__coo_land__TRANSPLANT_FAILED.md" "CHECKOUT_PATH_FAILED:$allow_path"
      elif [ "$action" = "delete" ]; then
        git -C "$BUILD_REPO" rm -f -- "$allow_path" >/dev/null 2>&1 || land_failed "REPORT_BLOCKED__coo_land__TRANSPLANT_FAILED.md" "DELETE_PATH_FAILED:$allow_path"
      else
        land_failed "REPORT_BLOCKED__coo_land__TRANSPLANT_FAILED.md" "UNKNOWN_ACTION:$action"
      fi
    done < "$actions_file"

    git -C "$BUILD_REPO" diff --cached --name-only | LC_ALL=C sort -u > "$actual_sorted"
    if ! diff -u "$allow_sorted" "$actual_sorted" > "$path_mismatch"; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__PATH_MISMATCH.md" <<EOF
# REPORT_BLOCKED__coo_land__PATH_MISMATCH
REASON=ACTUAL_CHANGED_PATHS_NOT_EQUAL_ALLOWLIST
DIFF_BEGIN
$(cat "$path_mismatch")
DIFF_END
EOF
      git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || true
      git -C "$BUILD_REPO" branch -D "$land_branch" >/dev/null 2>&1 || true
      echo "ERROR: coo land changed-path set mismatches allowlist." >&2
      exit 41
    fi

    if ! eol_only_flag="$(python3 "$BUILD_REPO/runtime/tools/coo_land_policy.py" eol-only --repo "$BUILD_REPO" 2>"$eol_err")"; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__EOL_CHECK_FAILED.md" <<EOF
# REPORT_BLOCKED__coo_land__EOL_CHECK_FAILED
REASON=EOL_CHECK_ERROR
DETAIL_BEGIN
$(sed -n '1,40p' "$eol_err")
DETAIL_END
EOF
      git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || true
      git -C "$BUILD_REPO" branch -D "$land_branch" >/dev/null 2>&1 || true
      echo "ERROR: coo land could not evaluate EOL-only gate." >&2
      exit 41
    fi
    eol_only_allowed="0"
    if [ "$eol_only_flag" = "1" ]; then
      if [ "$allow_eol_only" = true ]; then
        eol_only_allowed="1"
      else
        write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__EOL_ONLY.md" <<EOF
# REPORT_BLOCKED__coo_land__EOL_ONLY
REASON=EOL_ONLY_CHANGESET
ALLOW_EOL_ONLY_FLAG=0
EOF
        git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || true
        git -C "$BUILD_REPO" branch -D "$land_branch" >/dev/null 2>&1 || true
        echo "ERROR: coo land blocked EOL-only changes; use --allow-eol-only to override." >&2
        exit 41
      fi
    fi

    verify_pytest_cmd="pytest -q runtime/tests/test_coo_capsule_render.py runtime/tests/test_coo_worktree_marker_receipt.py"
    verify_pytest_out="$evid_dir/land_verify_pytest.out"
    verify_pytest_err="$evid_dir/land_verify_pytest.err"
    set +e
    (
      cd "$BUILD_REPO"
      pytest -q runtime/tests/test_coo_capsule_render.py runtime/tests/test_coo_worktree_marker_receipt.py
    ) >"$verify_pytest_out" 2>"$verify_pytest_err"
    rc_pytest="$?"
    set -e
    if [ "$rc_pytest" -ne 0 ]; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__VERIFY_PYTEST.md" <<EOF
# REPORT_BLOCKED__coo_land__VERIFY_PYTEST
REASON=VERIFY_PYTEST_FAILED
COMMAND=$verify_pytest_cmd
RC=$rc_pytest
STDERR_HEAD_BEGIN
$(sed -n '1,40p' "$verify_pytest_err")
STDERR_HEAD_END
EOF
      git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || true
      git -C "$BUILD_REPO" branch -D "$land_branch" >/dev/null 2>&1 || true
      echo "ERROR: coo land verification pytest command failed." >&2
      exit 41
    fi

    verify_e2e_cmd="$0 e2e"
    verify_e2e_out="$evid_dir/land_verify_e2e.out"
    verify_e2e_err="$evid_dir/land_verify_e2e.err"
    rc_e2e="0"
    if [ "$skip_e2e" = false ]; then
      set +e
      (
        cd "$BUILD_REPO"
        "$0" e2e
      ) >"$verify_e2e_out" 2>"$verify_e2e_err"
      rc_e2e="$?"
      set -e
      if [ "$rc_e2e" -ne 0 ]; then
        write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__VERIFY_E2E.md" <<EOF
# REPORT_BLOCKED__coo_land__VERIFY_E2E
REASON=VERIFY_E2E_FAILED
COMMAND=$verify_e2e_cmd
RC=$rc_e2e
STDERR_HEAD_BEGIN
$(sed -n '1,40p' "$verify_e2e_err")
STDERR_HEAD_END
EOF
        git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || true
        git -C "$BUILD_REPO" branch -D "$land_branch" >/dev/null 2>&1 || true
        echo "ERROR: coo land verification e2e command failed." >&2
        exit 41
      fi
    else
      printf 'SKIPPED (--skip-e2e)\n' > "$verify_e2e_out"
      : > "$verify_e2e_err"
    fi

    land_commit_msg="land: coo path-transplant landing (from ${src_head:0:7})"
    if ! git -C "$BUILD_REPO" commit -m "$land_commit_msg" >/dev/null 2>&1; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__COMMIT_FAILED.md" <<EOF
# REPORT_BLOCKED__coo_land__COMMIT_FAILED
REASON=LAND_COMMIT_FAILED
EOF
      git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || true
      git -C "$BUILD_REPO" branch -D "$land_branch" >/dev/null 2>&1 || true
      echo "ERROR: coo land could not commit transplanted change set." >&2
      exit 41
    fi
    land_commit="$(git -C "$BUILD_REPO" rev-parse HEAD)"
    merge_method="git_workflow_merge"
    emergency_used="0"
    merge_reason=""

    merge_out="$evid_dir/land_merge.out"
    merge_err="$evid_dir/land_merge.err"
    if [ -f "$BUILD_REPO/scripts/git_workflow.py" ]; then
      set +e
      (
        cd "$BUILD_REPO"
        python3 scripts/git_workflow.py merge
      ) >"$merge_out" 2>"$merge_err"
      rc_merge="$?"
      set -e
      if [ "$rc_merge" -ne 0 ]; then
        if [ "$emergency" = true ]; then
          merge_method="manual_merge_emergency"
          emergency_used="1"
          merge_reason="git_workflow merge failed"
          (
            cd "$BUILD_REPO"
            python3 scripts/git_workflow.py --emergency 'coo-land-merge' --reason "$merge_reason"
          ) >>"$merge_out" 2>>"$merge_err" || true
          git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || land_failed "REPORT_BLOCKED__coo_land__MERGE_FAILED.md" "DEST_CHECKOUT_AFTER_WORKFLOW_FAILURE"
          git -C "$BUILD_REPO" merge --no-ff "$land_branch" -m "merge: coo land emergency integration (${src_head:0:7})" >>"$merge_out" 2>>"$merge_err" || land_failed "REPORT_BLOCKED__coo_land__MERGE_FAILED.md" "MANUAL_MERGE_FAILED_AFTER_WORKFLOW_FAILURE"
        else
          write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__MERGE_FAILED.md" <<EOF
# REPORT_BLOCKED__coo_land__MERGE_FAILED
REASON=GIT_WORKFLOW_MERGE_FAILED
RC=$rc_merge
STDERR_HEAD_BEGIN
$(sed -n '1,40p' "$merge_err")
STDERR_HEAD_END
EOF
          git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || true
          git -C "$BUILD_REPO" branch -D "$land_branch" >/dev/null 2>&1 || true
          echo "ERROR: coo land merge failed in non-emergency mode." >&2
          exit 41
        fi
      fi
    else
      merge_method="manual_merge"
      git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || land_failed "REPORT_BLOCKED__coo_land__MERGE_FAILED.md" "DEST_CHECKOUT_FAILED_BEFORE_MANUAL_MERGE"
      git -C "$BUILD_REPO" merge --no-ff "$land_branch" -m "merge: coo land integration (${src_head:0:7})" >"$merge_out" 2>"$merge_err" || land_failed "REPORT_BLOCKED__coo_land__MERGE_FAILED.md" "MANUAL_MERGE_FAILED"
    fi

    git -C "$BUILD_REPO" checkout "$dest_ref" >/dev/null 2>&1 || true
    dest_head_after="$(git -C "$BUILD_REPO" rev-parse "$dest_ref")"
    git -C "$BUILD_REPO" branch -D "$land_branch" >/dev/null 2>&1 || true

    post_status="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
    post_diff="$(git -C "$BUILD_REPO" diff --name-only || true)"
    if [ -n "$post_status" ] || [ -n "$post_diff" ]; then
      write_blocked_report "$evid_dir" "REPORT_BLOCKED__coo_land__POST_DIRTY.md" <<EOF
# REPORT_BLOCKED__coo_land__POST_DIRTY
REASON=BUILD_REPO_NOT_CLEAN_AFTER_LAND
STATUS_PORCELAIN_BEGIN
${post_status:-"(empty)"}
STATUS_PORCELAIN_END
DIFF_NAME_ONLY_BEGIN
${post_diff:-"(empty)"}
DIFF_NAME_ONLY_END
EOF
      echo "ERROR: coo land left BUILD_REPO dirty." >&2
      exit 41
    fi

    # Postflight config-aware clean-check receipt
    python3 "$BUILD_REPO/runtime/tools/coo_land_policy.py" \
        clean-check --repo "$BUILD_REPO" --receipt "$evid_dir/clean_check_postflight.json" \
        2>"$evid_dir/clean_check_postflight.err" || true

    receipt_file="$evid_dir/land_receipt.txt"
    {
      echo "BASELINE_REF=$baseline_ref"
      echo "BASELINE_MODE=$baseline_mode"
      echo "SRC_REF=$src_ref"
      echo "SRC_HEAD=$src_head"
      echo "DEST_REF=$dest_ref"
      echo "EVID_SELECTED=$evid_dir"
      echo "DEST_HEAD_BEFORE=$dest_head_before"
      echo "DEST_HEAD_AFTER=$dest_head_after"
      echo "MODE=$land_mode"
      echo "PROVENANCE_DESCENDED=$provenance_descended"
      echo "ALLOWLIST_HASH=$allowlist_hash"
      echo "LAND_COMMIT=$land_commit"
      echo "MERGE_METHOD=$merge_method"
      echo "EMERGENCY_USED=$emergency_used"
      echo "EOL_ONLY_ALLOWED=$eol_only_allowed"
      echo "VERIFICATION_PYTEST_CMD=$verify_pytest_cmd"
      echo "VERIFICATION_PYTEST_RC=$rc_pytest"
      if [ "$skip_e2e" = false ]; then
        echo "VERIFICATION_E2E_CMD=$verify_e2e_cmd"
      else
        echo "VERIFICATION_E2E_CMD=SKIPPED(--skip-e2e)"
      fi
      echo "VERIFICATION_E2E_RC=$rc_e2e"
      echo "CHANGED_PATHS_BEGIN"
      cat "$allow_sorted"
      echo "CHANGED_PATHS_END"
      echo "CLEAN_PROOF_PRE_STATUS_BEGIN"
      if [ -n "$pre_status" ]; then
        printf '%s\n' "$pre_status"
      else
        echo "(empty)"
      fi
      echo "CLEAN_PROOF_PRE_STATUS_END"
      echo "CLEAN_PROOF_PRE_DIFF_BEGIN"
      if [ -n "$pre_diff" ]; then
        printf '%s\n' "$pre_diff"
      else
        echo "(empty)"
      fi
      echo "CLEAN_PROOF_PRE_DIFF_END"
      echo "CLEAN_PROOF_POST_STATUS_BEGIN"
      if [ -n "$post_status" ]; then
        printf '%s\n' "$post_status"
      else
        echo "(empty)"
      fi
      echo "CLEAN_PROOF_POST_STATUS_END"
      echo "CLEAN_PROOF_POST_DIFF_BEGIN"
      if [ -n "$post_diff" ]; then
        printf '%s\n' "$post_diff"
      else
        echo "(empty)"
      fi
      echo "CLEAN_PROOF_POST_DIFF_END"
    } > "$receipt_file"
    write_hashes "$evid_dir"
    cat "$receipt_file"
    ;;
  run)
    shift || true
    if [ "${1:-}" != "--" ]; then
      usage
      exit 2
    fi
    shift || true
    if [ "$#" -eq 0 ]; then
      usage
      exit 2
    fi
    print_header
    enter_training_dir
    "$@"
    ;;
  openclaw)
    shift || true
    if [ "${1:-}" != "--" ]; then
      usage
      exit 2
    fi
    shift || true
    print_header
    enter_training_dir
    run_openclaw "$@"
    ;;
  *)
    usage
    exit 2
    ;;
esac
```

### File: `runtime/tools/openclaw_cron_delivery_guard.py`
```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.openclaw_egress_policy import classify_payload_text


def _ts_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_jobs(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [j for j in payload if isinstance(j, dict)]
    if isinstance(payload, dict):
        jobs = payload.get("jobs")
        if isinstance(jobs, list):
            return [j for j in jobs if isinstance(j, dict)]
    return []


def _job_enabled(job: Dict[str, Any]) -> bool:
    enabled = job.get("enabled")
    if isinstance(enabled, bool):
        return enabled
    if enabled is None:
        return True
    return bool(enabled)


def _delivery_obj(job: Dict[str, Any]) -> Dict[str, Any]:
    candidates: List[Any] = [
        job.get("delivery"),
        (job.get("request") or {}).get("delivery") if isinstance(job.get("request"), dict) else None,
        (job.get("job") or {}).get("delivery") if isinstance(job.get("job"), dict) else None,
        (job.get("spec") or {}).get("delivery") if isinstance(job.get("spec"), dict) else None,
        (job.get("schedule") or {}).get("delivery") if isinstance(job.get("schedule"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    return {}


def _delivery_mode(job: Dict[str, Any]) -> str:
    delivery = _delivery_obj(job)
    mode = delivery.get("mode")
    if isinstance(mode, str) and mode.strip():
        return mode.strip().lower()

    fallback = job.get("deliveryMode")
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip().lower()
    return "unknown"


def _payload_hint(job: Dict[str, Any]) -> str:
    candidates: List[Any] = [
        job.get("message"),
        job.get("prompt"),
        job.get("template"),
    ]
    request = job.get("request")
    if isinstance(request, dict):
        candidates.extend([request.get("message"), request.get("prompt"), request.get("template"), request.get("payload")])
        delivery = request.get("delivery")
        if isinstance(delivery, dict):
            candidates.extend([delivery.get("message"), delivery.get("payload"), delivery.get("template")])
    delivery = _delivery_obj(job)
    candidates.extend([delivery.get("message"), delivery.get("payload"), delivery.get("template")])

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        if isinstance(candidate, dict):
            try:
                return json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            except Exception:
                continue
    return ""


def evaluate_jobs(jobs: List[Dict[str, Any]], require_parked: bool) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    violations: List[str] = []

    for job in jobs:
        job_id = str(job.get("id") or "")
        name = str(job.get("name") or job_id or "<unnamed>")
        enabled = _job_enabled(job)
        mode = _delivery_mode(job)
        hint = _payload_hint(job)
        classify = classify_payload_text(hint) if hint else {
            "classification": "contentful",
            "allowed_for_scheduled": False,
            "reasons": ["payload_missing"],
        }

        row = {
            "id": job_id,
            "name": name,
            "enabled": enabled,
            "delivery_mode": mode,
            "payload_classification": classify["classification"],
            "payload_reasons": classify["reasons"],
        }
        rows.append(row)

        if not enabled:
            continue

        if require_parked and mode != "none":
            violations.append(f"{name}: enabled delivery.mode={mode} (must be none while cron egress is parked)")
        elif (not require_parked) and mode != "none" and not classify["allowed_for_scheduled"]:
            joined = ",".join(classify["reasons"]) if classify["reasons"] else "policy_rejected"
            violations.append(f"{name}: scheduled payload classified contentful ({joined})")

    return {
        "jobs": rows,
        "violations": violations,
        "pass": len(violations) == 0,
    }


def run_guard(openclaw_bin: str, marker_path: Path, ignore_marker: bool) -> Dict[str, Any]:
    cmd = [openclaw_bin, "cron", "list", "--all", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    result: Dict[str, Any] = {
        "ts_utc": _ts_utc(),
        "command": cmd,
        "command_exit_code": int(proc.returncode),
        "marker_path": str(marker_path),
        "marker_present": marker_path.exists(),
        "require_parked": True,
        "pass": False,
        "jobs": [],
        "violations": [],
    }

    if proc.returncode != 0:
        result["violations"] = ["cron_list_failed"]
        result["command_stderr"] = (proc.stderr or "").strip()[:1000]
        return result

    try:
        raw_payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        result["violations"] = ["cron_list_not_json"]
        result["command_stdout_head"] = (proc.stdout or "").strip()[:1000]
        return result

    jobs = _extract_jobs(raw_payload)
    if not jobs:
        result["pass"] = True
        result["jobs"] = []
        result["violations"] = []
        result["require_parked"] = False if (marker_path.exists() and not ignore_marker) else True
        return result

    require_parked = True
    if marker_path.exists() and not ignore_marker:
        require_parked = False
    evaluated = evaluate_jobs(jobs, require_parked=require_parked)

    result["jobs"] = evaluated["jobs"]
    result["violations"] = evaluated["violations"]
    result["pass"] = evaluated["pass"]
    result["require_parked"] = require_parked
    return result


def main() -> int:
    default_state_dir = Path(os.environ.get("OPENCLAW_STATE_DIR", str(Path.home() / ".openclaw")))
    default_marker = default_state_dir / "runtime" / "gates" / "cron_egress_policy_ready.marker"

    parser = argparse.ArgumentParser(description="Fail-closed cron delivery guard for OpenClaw COO startup.")
    parser.add_argument("--openclaw-bin", default=os.environ.get("OPENCLAW_BIN", "openclaw"))
    parser.add_argument("--marker-path", default=str(default_marker))
    parser.add_argument("--ignore-marker", action="store_true", help="Always require delivery.mode=none even if marker exists.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    marker_path = Path(args.marker_path).expanduser()
    result = run_guard(args.openclaw_bin, marker_path=marker_path, ignore_marker=bool(args.ignore_marker))

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        if result["pass"]:
            print(
                "PASS cron_delivery_guard=true "
                f"jobs={len(result['jobs'])} "
                f"require_parked={'true' if result['require_parked'] else 'false'}"
            )
        else:
            top = result["violations"][0] if result["violations"] else "unknown_violation"
            print(
                "FAIL cron_delivery_guard=false "
                f"require_parked={'true' if result['require_parked'] else 'false'} "
                f"reason={top}",
                flush=True,
            )

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

### File: `runtime/tools/openclaw_egress_policy.py`
```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ALLOWED_KEYS = {"status", "summary", "sources", "counts"}
ALLOWED_STATUS = {"ok", "warn", "fail", "error", "degraded"}
SOURCE_PTR_RE = re.compile(r"^[A-Za-z0-9_./:#@+\-]{1,220}$")
MAX_SUMMARY_CHARS = 280
MAX_SOURCES = 16
MAX_COUNTS = 32


def _metadata_schema_checks(payload: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    keys = set(payload.keys())
    extra = sorted(keys - ALLOWED_KEYS)
    if extra:
        reasons.append(f"extra_keys:{','.join(extra)}")

    status = payload.get("status")
    if not isinstance(status, str) or status.strip().lower() not in ALLOWED_STATUS:
        reasons.append("invalid_status")

    summary = payload.get("summary")
    if not isinstance(summary, str):
        reasons.append("summary_not_string")
    else:
        stripped = summary.strip()
        if not stripped:
            reasons.append("summary_empty")
        if len(stripped) > MAX_SUMMARY_CHARS:
            reasons.append("summary_too_long")
        if "\n" in stripped or "```" in stripped:
            reasons.append("summary_not_single_line")

    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        reasons.append("sources_not_list")
    else:
        if len(sources) > MAX_SOURCES:
            reasons.append("sources_too_many")
        for item in sources:
            if not isinstance(item, str) or not SOURCE_PTR_RE.match(item.strip()):
                reasons.append("invalid_source_pointer")
                break

    counts = payload.get("counts", {})
    if not isinstance(counts, dict):
        reasons.append("counts_not_object")
    else:
        if len(counts) > MAX_COUNTS:
            reasons.append("counts_too_many_keys")
        for key, value in counts.items():
            if not isinstance(key, str) or not key.strip():
                reasons.append("invalid_count_key")
                break
            if not isinstance(value, (int, float)):
                reasons.append("invalid_count_value")
                break
            if value < 0:
                reasons.append("invalid_count_negative")
                break

    return reasons


def classify_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "classification": "contentful",
            "allowed_for_scheduled": False,
            "reasons": ["payload_not_object"],
        }

    reasons = _metadata_schema_checks(payload)
    metadata_only = len(reasons) == 0
    return {
        "classification": "metadata_only" if metadata_only else "contentful",
        "allowed_for_scheduled": metadata_only,
        "reasons": reasons,
    }


def classify_payload_text(payload_text: str) -> Dict[str, Any]:
    raw = payload_text.strip()
    if not raw:
        return {
            "classification": "contentful",
            "allowed_for_scheduled": False,
            "reasons": ["payload_empty"],
        }
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "classification": "contentful",
            "allowed_for_scheduled": False,
            "reasons": ["payload_not_json"],
        }
    return classify_payload(parsed)


def _load_payload(args: argparse.Namespace) -> Tuple[str, str]:
    if args.payload_file:
        return Path(args.payload_file).read_text(encoding="utf-8"), args.payload_file
    if args.payload is not None:
        return args.payload, "inline"
    return sys.stdin.read(), "stdin"


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify outbound payloads for OpenClaw scheduled egress policy.")
    parser.add_argument("--payload", default=None, help="Raw payload text.")
    parser.add_argument("--payload-file", default="", help="Path to payload text file.")
    parser.add_argument("--scheduled", action="store_true", help="Fail closed unless payload is metadata_only.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload_text, payload_source = _load_payload(args)
    result = classify_payload_text(payload_text)
    result["payload_source"] = payload_source

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(
            f"classification={result['classification']} "
            f"allowed_for_scheduled={'true' if result['allowed_for_scheduled'] else 'false'} "
            f"reasons={','.join(result['reasons']) if result['reasons'] else 'none'} "
            f"payload_source={payload_source}"
        )

    if args.scheduled and not result["allowed_for_scheduled"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### File: `runtime/tools/openclaw_leak_scan.sh`
```bash
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
    ("sk-ant-", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{8,}")),
    ("ghu_/gho_/ghp_", re.compile(r"\bgh[opurs]_[A-Za-z0-9]{12,}\b")),
    ("xox*", re.compile(r"\bxox[aboprs]-[A-Za-z0-9-]{8,}\b")),
    ("AIza", re.compile(r"\bAIza[0-9A-Za-z_-]{8,}")),
    ("ya29.", re.compile(r"\bya29\.[0-9A-Za-z._-]{12,}\b")),
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
```

### File: `runtime/tools/openclaw_model_ladder_fix.py`
```python
#!/usr/bin/env python3
"""
Safe repair tool for OpenClaw model ladder configuration.
Creates backup, applies minimal fixes, generates audit capsule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


EXECUTION_BASE = [
    "openai-codex/gpt-5.3-codex",
    "github-copilot/claude-opus-4.6",
    "google-gemini-cli/gemini-3-flash-preview",
]
THINKING_BASE = list(EXECUTION_BASE)


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def redact_tokens(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Create a redacted copy of config for display (remove auth tokens)."""
    import copy
    redacted = copy.deepcopy(cfg)

    # Redact common token locations
    if isinstance(redacted, dict):
        for key in list(redacted.keys()):
            if any(x in key.lower() for x in ("token", "key", "secret", "password", "credential")):
                redacted[key] = "[REDACTED]"
            elif isinstance(redacted[key], dict):
                redacted[key] = redact_tokens(redacted[key])
            elif isinstance(redacted[key], list):
                redacted[key] = [redact_tokens(x) if isinstance(x, dict) else x for x in redacted[key]]

    return redacted


def apply_ladder_fixes(cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Apply minimal fixes to config to satisfy ladder policy.
    Returns (fixed_config, changes_made).
    """
    changes: List[str] = []

    # Ensure agents.list exists
    if "agents" not in cfg:
        cfg["agents"] = {}
        changes.append("Created agents section")

    if "list" not in cfg["agents"]:
        cfg["agents"]["list"] = []
        changes.append("Created agents.list array")

    agents_list = cfg["agents"]["list"]

    # Helper to find or create an agent
    def ensure_agent(agent_id: str, ladder_base: List[str]) -> None:
        for agent in agents_list:
            if isinstance(agent, dict) and agent.get("id") == agent_id:
                # Agent exists, update its ladder if invalid
                model = agent.get("model", {})
                if not isinstance(model, dict):
                    agent["model"] = {}
                    model = agent["model"]
                    changes.append(f"{agent_id}: created model section")

                primary = model.get("primary")
                fallbacks = model.get("fallbacks", [])

                if primary != ladder_base[0]:
                    model["primary"] = ladder_base[0]
                    changes.append(f"{agent_id}: set primary to {ladder_base[0]}")

                if not isinstance(fallbacks, list):
                    fallbacks = []

                required_prefix = ladder_base[1:]
                existing = [str(x) for x in fallbacks if isinstance(x, str) and str(x).strip()]
                filtered_existing = [
                    x
                    for x in existing
                    if ("haiku" not in x.lower()) and ("small" not in x.lower()) and (not x.lower().startswith("claude-max/"))
                ]
                extras = [x for x in filtered_existing if x not in required_prefix]
                normalized_fallbacks = required_prefix + extras
                if existing != normalized_fallbacks:
                    model["fallbacks"] = normalized_fallbacks
                    changes.append(f"{agent_id}: normalized fallback prefix to subscription-first ladder")

                return

        # Agent doesn't exist, create it
        new_agent: Dict[str, Any] = {
            "id": agent_id,
            "model": {
                "primary": ladder_base[0],
                "fallbacks": ladder_base[1:],
            }
        }
        if agent_id == "think":
            new_agent["thinking"] = "extra_high"

        agents_list.append(new_agent)
        changes.append(f"{agent_id}: created agent with policy ladder")

    ensure_agent("main", EXECUTION_BASE)
    ensure_agent("quick", EXECUTION_BASE)
    ensure_agent("think", THINKING_BASE)

    return cfg, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe repair tool for OpenClaw model ladder configuration.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without applying")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        print(f"NEXT: Run 'openclaw onboard' to initialize configuration", file=sys.stderr)
        return 1

    print("=== OpenClaw Model Ladder Fix ===\n")
    print(f"Config: {config_path}")

    # Load current config
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Config is not valid JSON: {e}", file=sys.stderr)
        return 1

    # Compute before hash
    hash_before = sha256_file(config_path)
    print(f"SHA256 (before): {hash_before[:16]}...")

    # Apply fixes
    fixed_cfg, changes = apply_ladder_fixes(cfg)

    if not changes:
        print("\nNo changes needed - ladder configuration is valid.")
        return 0

    print("\nProposed changes:")
    for i, change in enumerate(changes, 1):
        print(f"  {i}. {change}")

    if args.dry_run:
        print("\nDRY RUN - no changes applied.")
        return 0

    # Create backup
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_dir = config_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"openclaw.json.{timestamp}.backup"

    shutil.copy2(config_path, backup_path)
    print(f"\nBackup created: {backup_path}")

    # Write fixed config atomically
    temp_path = config_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(fixed_cfg, indent=2, sort_keys=False), encoding="utf-8")
    temp_path.replace(config_path)

    # Compute after hash
    hash_after = sha256_file(config_path)
    print(f"SHA256 (after):  {hash_after[:16]}...")

    # Write audit capsule
    capsule_path = backup_dir / f"ladder_fix_{timestamp}.audit.json"
    audit = {
        "timestamp": timestamp,
        "config_path": str(config_path),
        "backup_path": str(backup_path),
        "sha256_before": hash_before,
        "sha256_after": hash_after,
        "changes": changes,
        "execution_ladder": EXECUTION_BASE,
        "thinking_ladder": THINKING_BASE,
    }
    capsule_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Audit capsule: {capsule_path}")

    print("\nFix applied successfully.")
    print("NEXT: Run 'coo models status' to verify ladder health")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### File: `runtime/tools/openclaw_model_policy_assert.py`
```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REQUIRED_PREFIX = [
    "openai-codex/gpt-5.3-codex",
    "github-copilot/claude-opus-4.6",
    "google-gemini-cli/gemini-3-flash-preview",
]
DISALLOWED_FALLBACK_RE = re.compile(r"(haiku|small)", re.IGNORECASE)
QUARANTINED_PROVIDER_RE = re.compile(r"^claude-max/", re.IGNORECASE)
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)+$", re.IGNORECASE)
OPENCLAW_BIN = os.environ.get("OPENCLAW_BIN") or "openclaw"


def _safe_run(cmd: Sequence[str], timeout_s: int = 20) -> Tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
        return int(proc.returncode), proc.stdout
    except Exception:
        return 1, ""


def _collect_model_ids_from_config(cfg: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    defaults = (cfg.get("agents") or {}).get("defaults") or {}
    defaults_model = defaults.get("model") or {}
    if isinstance(defaults_model, dict):
        primary = defaults_model.get("primary")
        if isinstance(primary, str):
            out.append(primary)
        fb = defaults_model.get("fallbacks") or []
        if isinstance(fb, list):
            out.extend([str(x) for x in fb if isinstance(x, str)])

    defaults_models = defaults.get("models") or {}
    if isinstance(defaults_models, dict):
        out.extend([str(k) for k in defaults_models.keys()])

    for agent in ((cfg.get("agents") or {}).get("list") or []):
        if not isinstance(agent, dict):
            continue
        model = agent.get("model") or {}
        if not isinstance(model, dict):
            continue
        primary = model.get("primary")
        if isinstance(primary, str):
            out.append(primary)
        fb = model.get("fallbacks") or []
        if isinstance(fb, list):
            out.extend([str(x) for x in fb if isinstance(x, str)])

    return sorted({m for m in out if MODEL_ID_RE.match(m)})


def _parse_models_list_text(text: str) -> Dict[str, Dict[str, Any]]:
    status: Dict[str, Dict[str, Any]] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("Model ") or line.startswith("rc=") or line.startswith("BUILD_REPO="):
            continue
        cols = line.strip().split()
        if len(cols) < 5:
            continue
        model_id = cols[0].strip()
        if not MODEL_ID_RE.match(model_id):
            continue
        auth = cols[-2].strip().lower() if len(cols) >= 6 else "unknown"
        tags = cols[-1].strip().lower()
        missing = "missing" in tags
        working = (auth == "yes") and (not missing)
        status[model_id] = {
            "auth": auth == "yes",
            "missing": missing,
            "working": working,
            "tags": tags,
        }
    return status


def _discover_kimi_id(cfg_ids: Sequence[str], list_ids: Sequence[str]) -> Optional[str]:
    candidates: List[str] = []
    for mid in list(cfg_ids) + list(list_ids):
        low = str(mid).lower()
        if "kimi" in low and "/" in low:
            candidates.append(str(mid))
    if not candidates:
        return None
    return sorted(set(candidates))[0]


def _agent_ladder(cfg: Dict[str, Any], agent_id: str) -> List[str]:
    for agent in ((cfg.get("agents") or {}).get("list") or []):
        if not isinstance(agent, dict):
            continue
        if str(agent.get("id") or "") != agent_id:
            continue
        model = agent.get("model") or {}
        if not isinstance(model, dict):
            return []
        primary = model.get("primary")
        fallbacks = model.get("fallbacks") or []
        ladder: List[str] = []
        if isinstance(primary, str) and primary.strip():
            ladder.append(primary)
        if isinstance(fallbacks, list):
            ladder.extend([str(x) for x in fallbacks if isinstance(x, str) and str(x).strip()])
        return ladder
    return []


def _provider_of(model_id: str) -> str:
    return model_id.split("/", 1)[0].strip().lower() if "/" in model_id else "unknown"


def assert_policy(cfg: Dict[str, Any], models_status: Dict[str, Dict[str, Any]], kimi_id: Optional[str]) -> Dict[str, Any]:
    del kimi_id  # Optional Kimi rung is no longer part of the burn-in baseline policy.

    violations: List[str] = []
    ladders: Dict[str, Any] = {}

    def validate(agent_id: str) -> None:
        actual = _agent_ladder(cfg, agent_id)
        if not actual:
            violations.append(f"{agent_id}: ladder missing or empty")
            ladders[agent_id] = {
                "actual": [],
                "required_prefix": REQUIRED_PREFIX,
                "working_models": [],
                "working_count": 0,
                "top_rung_auth_missing": True,
            }
            return

        if actual[0] != REQUIRED_PREFIX[0]:
            violations.append(f"{agent_id}: primary must be {REQUIRED_PREFIX[0]}, got {actual[0]}")

        if len(actual) < len(REQUIRED_PREFIX):
            violations.append(f"{agent_id}: ladder must include subscription-first prefix {REQUIRED_PREFIX}")
        else:
            prefix = actual[: len(REQUIRED_PREFIX)]
            if prefix != REQUIRED_PREFIX:
                violations.append(f"{agent_id}: ladder prefix mismatch with policy {REQUIRED_PREFIX}")

        for model_id in actual:
            if not MODEL_ID_RE.match(model_id):
                violations.append(f"{agent_id}: invalid model id format: {model_id}")

        for fb in actual[1:]:
            if DISALLOWED_FALLBACK_RE.search(fb):
                violations.append(f"{agent_id}: disallowed fallback model id: {fb}")
            if QUARANTINED_PROVIDER_RE.search(fb):
                violations.append(f"{agent_id}: quarantined provider fallback disallowed: {fb}")

        working_models = [m for m in actual if bool((models_status.get(m) or {}).get("working", False))]
        working_count = len(working_models)
        if working_count < 1:
            violations.append(f"{agent_id}: no working model detected in configured ladder")

        top = actual[0]
        top_auth = bool((models_status.get(top) or {}).get("auth", False))
        top_working = bool((models_status.get(top) or {}).get("working", False))
        top_rung_auth_missing = not top_auth

        ladders[agent_id] = {
            "actual": actual,
            "required_prefix": REQUIRED_PREFIX,
            "working_models": working_models,
            "working_count": working_count,
            "top_rung_auth_missing": top_rung_auth_missing,
            "top_rung_working": top_working,
        }

    validate("main")
    validate("quick")
    validate("think")

    think_agent = None
    for item in ((cfg.get("agents") or {}).get("list") or []):
        if isinstance(item, dict) and str(item.get("id") or "") == "think":
            think_agent = item
            break
    if isinstance(think_agent, dict):
        think_level = think_agent.get("thinking") if "thinking" in think_agent else think_agent.get("thinkingDefault")
        if think_level is not None and str(think_level).lower() not in {"extra_high", "extra-high", "very_high"}:
            violations.append(f"think: thinking tier should be extra_high when configured, got {think_level}")

    all_model_ids: List[str] = []
    for aid in ("main", "quick", "think"):
        all_model_ids.extend([m for m in (ladders.get(aid) or {}).get("actual", []) if isinstance(m, str)])

    providers = sorted({_provider_of(m) for m in all_model_ids if "/" in m})
    auth_missing_providers = sorted(
        {
            _provider_of((ladders.get(aid) or {}).get("actual", [""])[0] or "")
            for aid in ("main", "quick", "think")
            if (ladders.get(aid) or {}).get("top_rung_auth_missing") is True
        }
    )

    return {
        "policy_ok": len(violations) == 0,
        "required_prefix": REQUIRED_PREFIX,
        "unresolved_optional_rungs": [],
        "providers_referenced": providers,
        "auth_missing_providers": [p for p in auth_missing_providers if p and p != "unknown"],
        "ladders": ladders,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert OpenClaw model policy for COO UX preflight.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--models-list-file", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        cfg_path = Path(args.config).expanduser()
        if not cfg_path.exists():
            error_result = {
                "policy_ok": False,
                "error": "config_not_found",
                "error_detail": f"Config file not found: {cfg_path}",
                "violations": ["config file missing"],
                "ladders": {},
                "required_prefix": REQUIRED_PREFIX,
                "unresolved_optional_rungs": [],
                "providers_referenced": [],
                "auth_missing_providers": [],
            }
            if args.json:
                print(json.dumps(error_result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
            else:
                print("policy_ok=false violations=1 error=config_not_found")
            return 1

        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

        list_text = ""
        if args.models_list_file:
            list_text = Path(args.models_list_file).read_text(encoding="utf-8", errors="replace")
        else:
            rc, out = _safe_run([OPENCLAW_BIN, "models", "list"], timeout_s=25)
            list_text = out if rc == 0 else ""

        models_status = _parse_models_list_text(list_text)
        cfg_ids = _collect_model_ids_from_config(cfg)
        list_ids = list(models_status.keys())
        kimi_id = _discover_kimi_id(cfg_ids, list_ids)

        result = assert_policy(cfg, models_status, kimi_id)
        if args.json:
            print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        else:
            print(f"policy_ok={'true' if result['policy_ok'] else 'false'} violations={len(result['violations'])}")
        return 0 if result["policy_ok"] else 1
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError, IndexError, TypeError) as e:
        error_result = {
            "policy_ok": False,
            "error": type(e).__name__.lower(),
            "error_detail": str(e),
            "violations": [f"preflight error: {type(e).__name__}: {str(e)}"],
            "ladders": {},
            "required_prefix": REQUIRED_PREFIX,
            "unresolved_optional_rungs": [],
            "providers_referenced": [],
            "auth_missing_providers": [],
        }
        if args.json:
            print(json.dumps(error_result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        else:
            print(f"policy_ok=false violations=1 error={type(e).__name__.lower()}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

### File: `runtime/tools/openclaw_models_preflight.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_MODELS_PREFLIGHT_OUT_DIR:-$STATE_DIR/runtime/models_preflight/$TS_UTC}"
LIST_TIMEOUT_SEC="${OPENCLAW_MODELS_LIST_TIMEOUT_SEC:-20}"
PROBE_TIMEOUT_SEC="${OPENCLAW_MODELS_PROBE_TIMEOUT_SEC:-70}"
ENABLE_PROBE="${OPENCLAW_MODELS_PREFLIGHT_ENABLE_PROBE:-0}"
ENFORCEMENT_MODE="${COO_ENFORCEMENT_MODE:-interactive}"

if [ -z "$OPENCLAW_BIN" ] || [ ! -x "$OPENCLAW_BIN" ]; then
  echo "ERROR: OPENCLAW_BIN is not executable." >&2
  exit 127
fi

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-models-preflight/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

models_list_out="$OUT_DIR/models_list.txt"
probe_raw="$OUT_DIR/models_probe_raw.txt"
probe_sanitized="$OUT_DIR/models_probe_sanitized.txt"
policy_json="$OUT_DIR/model_policy_assert.json"
summary_out="$OUT_DIR/summary.txt"

gateway_reachable=false
if python3 - <<'PY' "$PORT"
import socket,sys
port=int(sys.argv[1])
s=socket.socket()
s.settimeout(0.75)
try:
    s.connect(("127.0.0.1", port))
except Exception:
    raise SystemExit(1)
finally:
    s.close()
PY
then
  gateway_reachable=true
fi

set +e
timeout "$LIST_TIMEOUT_SEC" "$OPENCLAW_BIN" models list > "$models_list_out" 2>&1
rc_list=$?
if [ "$ENABLE_PROBE" = "1" ]; then
  timeout "$PROBE_TIMEOUT_SEC" "$OPENCLAW_BIN" models status --probe > "$probe_raw" 2>&1
  probe_mode="probe"
else
  timeout "$PROBE_TIMEOUT_SEC" "$OPENCLAW_BIN" models status > "$probe_raw" 2>&1
  probe_mode="status"
fi
rc_probe=$?
set -e

python3 - <<'PY' "$probe_raw" "$probe_sanitized"
import re,sys
inp=open(sys.argv[1],encoding='utf-8',errors='replace').read()
text=inp
text=re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}','[REDACTED_EMAIL]',text)
text=re.sub(r'Authorization\s*:\s*Bearer\s+\S+','Authorization: Bearer [REDACTED]',text,flags=re.I)
text=re.sub(r'\bxapp-[A-Za-z0-9-]{6,}\b','xapp-[REDACTED]',text)
text=re.sub(r'\bxox[aboprs]-[A-Za-z0-9-]{6,}\b','xox?-[REDACTED]',text)
text=re.sub(r'\bsk-[A-Za-z0-9_-]{8,}\b','sk-[REDACTED]',text)
text=re.sub(r'\bsk-ant-[A-Za-z0-9_-]{8,}\b','sk-ant-[REDACTED]',text)
text=re.sub(r'\bgh[opurs]_[A-Za-z0-9]{12,}\b','gh*_[REDACTED]',text)
text=re.sub(r'\bAIza[0-9A-Za-z_-]{10,}\b','AIza[REDACTED]',text)
text=re.sub(r'\bya29\.[0-9A-Za-z._-]{12,}\b','ya29.[REDACTED]',text)
text=re.sub(r'[A-Za-z0-9+/_=-]{80,}','[REDACTED_LONG]',text)
open(sys.argv[2],'w',encoding='utf-8').write(text)
PY

set +e
python3 runtime/tools/openclaw_model_policy_assert.py --models-list-file "$models_list_out" --json > "$policy_json"
rc_policy=$?
set -e

policy_ok="$(python3 - <<'PY' "$policy_json"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    print("true" if obj.get("policy_ok") else "false")
except Exception:
    print("false")
PY
)"
missing_auth_agents="$(python3 - <<'PY' "$policy_json"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    names=[]
    for aid in ("main","quick","think"):
        ladder=(obj.get("ladders") or {}).get(aid) or {}
        if ladder.get("top_rung_auth_missing") is True:
            names.append(aid)
    print(",".join(names))
except Exception:
    print("main,quick,think")
PY
)"
working_ok="$(python3 - <<'PY' "$policy_json"
import json,sys
ok=True
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    for aid in ("main","quick","think"):
        ladder=(obj.get("ladders") or {}).get(aid) or {}
        if int(ladder.get("working_count") or 0) < 1:
            ok=False
except Exception:
    ok=False
print("true" if ok else "false")
PY
)"
providers_referenced="$(python3 - <<'PY' "$policy_json"
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    p=[str(x) for x in (obj.get("providers_referenced") or []) if str(x)]
    print(",".join(sorted(p)))
except Exception:
    print("")
PY
)"

pass=true
reason=""
degraded_reason=""
if [ "$gateway_reachable" != "true" ]; then
  pass=false
  reason="gateway_unreachable"
elif [ "$policy_ok" != "true" ] || [ "$rc_policy" -ne 0 ]; then
  pass=false
  reason="policy_violated"
elif [ "$working_ok" != "true" ]; then
  pass=false
  reason="no_working_model_for_agent"
elif [ -n "$missing_auth_agents" ]; then
  degraded_reason="top_rung_auth_missing"
fi

{
  echo "ts_utc=$TS_UTC"
  echo "gateway_reachable=$gateway_reachable"
  echo "policy_ok=$policy_ok"
  echo "working_ok=$working_ok"
  echo "missing_auth_agents=$missing_auth_agents"
  echo "providers_referenced=$providers_referenced"
  echo "rc_list=$rc_list"
  echo "rc_probe=$rc_probe"
  echo "probe_mode=$probe_mode"
  echo "rc_policy=$rc_policy"
  echo "degraded_reason=$degraded_reason"
  echo "models_list_out=$models_list_out"
  echo "models_probe_sanitized=$probe_sanitized"
  echo "policy_json=$policy_json"
} > "$summary_out"

if [ "$pass" = true ]; then
  if [ -n "$degraded_reason" ]; then
    echo "PASS models_preflight=true reason=$degraded_reason degraded=true summary=$summary_out"
    if [ "$degraded_reason" = "top_rung_auth_missing" ]; then
      echo "WARN: Top rung auth missing for agents=$missing_auth_agents; fallback routing remains available." >&2
      echo "NEXT: Re-auth top provider(s) to restore preferred routing order." >&2
    fi
  else
    echo "PASS models_preflight=true reason=ok summary=$summary_out"
  fi
  exit 0
fi

# Enforcement mode: interactive = warn and continue, mission = block
if [ "$ENFORCEMENT_MODE" = "interactive" ]; then
  echo "WARNING models_preflight=false reason=$reason summary=$summary_out enforcement_mode=interactive" >&2
  echo "WARNING: Model ladder preflight failed, but continuing in interactive mode." >&2
  if [ "$reason" = "policy_violated" ]; then
    echo "NEXT: Fix ladder ordering/fallback policy in $OPENCLAW_CONFIG_PATH" >&2
    echo "NEXT: Run 'coo models status' to see details." >&2
    echo "NEXT: Run 'coo models fix' for guided repair." >&2
    python3 - <<'PY' "$policy_json" >&2
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    for v in obj.get("violations") or []:
        print(f"- {v}")
except Exception:
    print("- Unable to parse policy violation details.")
PY
  elif [ "$reason" = "no_working_model_for_agent" ]; then
    echo "NEXT: Verify provider auth and model availability; ensure at least one working model per agent." >&2
  elif [ "$reason" = "gateway_unreachable" ]; then
    echo "NEXT: Check OpenClaw gateway is running or start it with 'coo start'" >&2
  fi
  exit 0
fi

# Mission mode: fail-closed
echo "FAIL models_preflight=false reason=$reason summary=$summary_out enforcement_mode=mission" >&2
if [ "$reason" = "policy_violated" ]; then
  echo "NEXT: Fix ladder ordering/fallback policy in $OPENCLAW_CONFIG_PATH and re-run preflight." >&2
  python3 - <<'PY' "$policy_json" >&2
import json,sys
try:
    obj=json.loads(open(sys.argv[1],encoding='utf-8').read())
    for v in obj.get("violations") or []:
        print(f"- {v}")
except Exception:
    print("- Unable to parse policy violation details.")
PY
elif [ "$reason" = "no_working_model_for_agent" ]; then
  echo "NEXT: Verify provider auth and model availability; ensure at least one working model per agent." >&2
fi
exit 1
```

### File: `runtime/tools/openclaw_policy_assert.py`
```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

PRIMARY_MODEL = "openai-codex/gpt-5.3-codex"
SUBSCRIPTION_FALLBACKS = [
    "github-copilot/claude-opus-4.6",
    "google-gemini-cli/gemini-3-flash-preview",
]
OWNER_ONLY_COMMANDS = {"/model", "/models", "/think"}
MEMORY_PROVIDER = "local"
MEMORY_FALLBACK = "none"
DISALLOWED_FALLBACK_RE = re.compile(r"(haiku|small)", re.IGNORECASE)
QUARANTINED_PROVIDER_RE = re.compile(r"^claude-max/", re.IGNORECASE)


def _agent_by_id(cfg: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    for item in ((cfg.get("agents") or {}).get("list") or []):
        if isinstance(item, dict) and item.get("id") == agent_id:
            return item
    return {}


def _owner_allow_from(cfg: Dict[str, Any]) -> List[str]:
    raw = (((cfg.get("commands") or {}).get("ownerAllowFrom")) or [])
    if not isinstance(raw, list):
        return []
    return sorted({str(x).strip() for x in raw if str(x).strip()})


def _model_cfg(entry: Dict[str, Any]) -> Dict[str, Any]:
    model = entry.get("model")
    return model if isinstance(model, dict) else {}


def _assert_ladder_prefix(entry: Dict[str, Any], label: str) -> None:
    model = _model_cfg(entry)
    got_primary = str(model.get("primary", ""))
    got_fallbacks = model.get("fallbacks")
    if not isinstance(got_fallbacks, list):
        got_fallbacks = []

    if got_primary != PRIMARY_MODEL:
        raise AssertionError(f"{label} primary mismatch: {got_primary} != {PRIMARY_MODEL}")
    if len(got_fallbacks) < len(SUBSCRIPTION_FALLBACKS):
        raise AssertionError(
            f"{label} fallbacks must begin with {SUBSCRIPTION_FALLBACKS}; got too few entries: {got_fallbacks}"
        )
    prefix = [str(x) for x in got_fallbacks[: len(SUBSCRIPTION_FALLBACKS)]]
    if prefix != SUBSCRIPTION_FALLBACKS:
        raise AssertionError(f"{label} fallback prefix mismatch: {prefix} != {SUBSCRIPTION_FALLBACKS}")

    for fb in got_fallbacks:
        model_id = str(fb)
        if DISALLOWED_FALLBACK_RE.search(model_id):
            raise AssertionError(f"{label} disallowed fallback model id: {model_id}")
        if QUARANTINED_PROVIDER_RE.search(model_id):
            raise AssertionError(f"{label} quarantined provider fallback disallowed: {model_id}")


def command_authorized(cfg: Dict[str, Any], sender: str, command: str) -> bool:
    cmd = command.strip().split(" ", 1)[0].lower()
    if cmd not in OWNER_ONLY_COMMANDS:
        return True
    owners = _owner_allow_from(cfg)
    if not owners:
        return False
    return sender in owners


def _assert_memory_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    defaults = ((cfg.get("agents") or {}).get("defaults") or {})
    workspace_raw = str(defaults.get("workspace") or "")
    if not workspace_raw:
        raise AssertionError("agents.defaults.workspace must be set")

    workspace = os.path.abspath(os.path.expanduser(workspace_raw))
    openclaw_home = os.path.abspath(os.path.expanduser("~/.openclaw"))
    if not (workspace == openclaw_home or workspace.startswith(openclaw_home + os.sep)):
        raise AssertionError(f"agents.defaults.workspace must be under ~/.openclaw, got {workspace_raw}")

    memory = defaults.get("memorySearch")
    if not isinstance(memory, dict):
        raise AssertionError("agents.defaults.memorySearch must be configured")
    if memory.get("enabled") is not False:
        raise AssertionError("agents.defaults.memorySearch.enabled must be false during burn-in")

    provider = str(memory.get("provider") or "")
    fallback = str(memory.get("fallback") or "")
    if provider != MEMORY_PROVIDER:
        raise AssertionError(f"agents.defaults.memorySearch.provider must be {MEMORY_PROVIDER}, got {provider}")
    if fallback != MEMORY_FALLBACK:
        raise AssertionError(f"agents.defaults.memorySearch.fallback must be {MEMORY_FALLBACK}, got {fallback}")

    sources = memory.get("sources")
    if not isinstance(sources, list):
        raise AssertionError("agents.defaults.memorySearch.sources must be a list")
    normalized_sources = [str(x) for x in sources]
    if "memory" not in normalized_sources:
        raise AssertionError('agents.defaults.memorySearch.sources must include "memory"')
    if "sessions" in normalized_sources:
        raise AssertionError('agents.defaults.memorySearch.sources must not include "sessions" during burn-in')

    return {
        "enabled": False,
        "workspace": workspace_raw,
        "provider": provider,
        "fallback": fallback,
        "sources": normalized_sources,
    }


def assert_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    defaults = ((cfg.get("agents") or {}).get("defaults") or {})
    defaults_think = str(defaults.get("thinkingDefault") or "unknown")
    if defaults_think not in {"low", "off"}:
        raise AssertionError(f"agents.defaults.thinkingDefault must be low/off, got {defaults_think}")

    _assert_ladder_prefix({"model": (defaults.get("model") or {})}, "agents.defaults")
    _assert_ladder_prefix(_agent_by_id(cfg, "main"), "main")
    _assert_ladder_prefix(_agent_by_id(cfg, "quick"), "quick")
    _assert_ladder_prefix(_agent_by_id(cfg, "think"), "think")

    owners = _owner_allow_from(cfg)
    if not owners:
        raise AssertionError("commands.ownerAllowFrom must be non-empty")
    owner = owners[0]
    if not command_authorized(cfg, owner, "/model openai-codex/gpt-5.3-codex"):
        raise AssertionError("owner must be authorized for /model")
    if command_authorized(cfg, "__non_owner__", "/model openai-codex/gpt-5.3-codex"):
        raise AssertionError("non-owner must be rejected for /model")
    if command_authorized(cfg, "__non_owner__", "/think high"):
        raise AssertionError("non-owner must be rejected for /think")

    memory = _assert_memory_policy(cfg)
    return {
        "primary_model": PRIMARY_MODEL,
        "required_subscription_fallbacks": SUBSCRIPTION_FALLBACKS,
        "owners": owners,
        "defaults_thinking": defaults_think,
        "memory": memory,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert OpenClaw subscription-first policy invariants.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    result = assert_policy(cfg)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(f"POLICY_ASSERT_PASS config={args.config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### File: `runtime/tools/openclaw_receipts_bundle.sh`
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
```

### File: `runtime/tools/openclaw_slack_launch.sh`
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
OVERLAY_ROOT="${OPENCLAW_SLACK_OVERLAY_ROOT:-$STATE_DIR/runtime/slack_overlay}"
OVERLAY_DIR="${OPENCLAW_SLACK_OVERLAY_DIR:-$STATE_DIR/runtime/slack_overlay/$TS_UTC}"
QUARANTINE_DIR="${OPENCLAW_SLACK_QUARANTINE_DIR:-$STATE_DIR/runtime/slack_overlay_quarantine/$TS_UTC}"
GEN_OUT_JSON="/tmp/openclaw-slack-overlay-${TS_UTC}.json"
STALE_MINUTES="${OPENCLAW_SLACK_STALE_MINUTES:-10}"

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

sweep_stale_overlays() {
  local stale_root="$OVERLAY_ROOT"
  local quarantine_root
  quarantine_root="$(dirname "$QUARANTINE_DIR")/stale-$TS_UTC"
  local moved=0

  if [ ! -d "$stale_root" ]; then
    return 0
  fi

  while IFS= read -r stale_file; do
    [ -z "$stale_file" ] && continue
    mkdir -p "$quarantine_root"
    if mv -f "$stale_file" "$quarantine_root/" 2>/dev/null; then
      moved=1
    fi
  done < <(find "$stale_root" -type f \( -name 'openclaw_slack_overlay.json' -o -name 'overlay_metadata.json' \) -mmin +"$STALE_MINUTES" 2>/dev/null || true)

  if [ "$moved" -eq 1 ]; then
    find "$stale_root" -mindepth 1 -type d -empty -delete 2>/dev/null || true
    echo "overlay_stale_sweep=quarantined stale_minutes=$STALE_MINUTES quarantine_dir=$quarantine_root"
  fi
}

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

sweep_stale_overlays

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

### File: `runtime/tools/openclaw_verify_surface.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CFG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$STATE_DIR/verify/$TS_UTC"
VERIFY_CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_CMD_TIMEOUT_SEC:-6}"
SECURITY_FALLBACK_TIMEOUT_SEC="${OPENCLAW_SECURITY_FALLBACK_TIMEOUT_SEC:-14}"
RECEIPT_CMD_TIMEOUT_SEC="${OPENCLAW_RECEIPT_CMD_TIMEOUT_SEC:-1}"
KNOWN_UV_IFADDR='uv_interface_addresses returned Unknown system error 1'
GATE_STATUS_PATH="${OPENCLAW_GATE_STATUS_PATH:-$STATE_DIR/runtime/gates/gate_status.json}"

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-verify/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

if ! mkdir -p "$(dirname "$GATE_STATUS_PATH")" 2>/dev/null; then
  GATE_STATUS_PATH="/tmp/openclaw-runtime/gates/gate_status.json"
  mkdir -p "$(dirname "$GATE_STATUS_PATH")"
fi

PASS=1
WARNINGS=0
declare -A CMD_RC
SECURITY_AUDIT_MODE="unknown"
CONFINEMENT_FLAG=""
declare -a BLOCKING_REASONS=()

add_blocking_reason() {
  local reason="$1"
  BLOCKING_REASONS+=("$reason")
  PASS=0
}

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
  if [ "$rc" -ne 0 ]; then
    WARNINGS=1
  fi
}

to_file() {
  local name="$1"
  shift
  to_file_with_timeout "$VERIFY_CMD_TIMEOUT_SEC" "$name" "$@"
}

# Required order with signature-gated fallback.
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
      SECURITY_AUDIT_MODE="blocked_fallback_failed"
      add_blocking_reason "security_audit_fallback_failed"
    fi
  else
    SECURITY_AUDIT_MODE="blocked_unknown_deep_error"
    add_blocking_reason "security_audit_deep_failed"
  fi
fi

to_file cron_delivery_guard python3 runtime/tools/openclaw_cron_delivery_guard.py --json
to_file models_status_probe coo openclaw -- models status
to_file sandbox_explain_json coo openclaw -- sandbox explain --json
to_file gateway_probe_json coo openclaw -- gateway probe --json
to_file policy_assert python3 runtime/tools/openclaw_policy_assert.py --json
to_file model_ladder_policy_assert python3 runtime/tools/openclaw_model_policy_assert.py --json
to_file multiuser_posture_assert python3 runtime/tools/openclaw_multiuser_posture_assert.py --json
to_file interfaces_policy_assert python3 runtime/tools/openclaw_interfaces_policy_assert.py --json

SECURITY_FILE="$OUT_DIR/security_audit_deep.txt"
if [ "$SECURITY_AUDIT_MODE" = "non_deep_fallback_due_uv_interface_addresses" ]; then
  SECURITY_FILE="$OUT_DIR/security_audit_fallback.txt"
fi

if [ ! -f "$SECURITY_FILE" ]; then
  add_blocking_reason "security_audit_output_missing"
elif ! rg -q 'Summary:\s*0 critical\s*·\s*0 warn' "$SECURITY_FILE"; then
  add_blocking_reason "security_audit_summary_not_clean"
fi

if [ "${CMD_RC[cron_delivery_guard]:-1}" -ne 0 ]; then add_blocking_reason "cron_delivery_guard_failed"; fi
if [ "${CMD_RC[sandbox_explain_json]:-1}" -ne 0 ]; then add_blocking_reason "sandbox_explain_failed"; fi
if [ "${CMD_RC[gateway_probe_json]:-1}" -ne 0 ]; then add_blocking_reason "gateway_probe_failed"; fi
if [ "${CMD_RC[policy_assert]:-1}" -ne 0 ]; then add_blocking_reason "policy_assert_failed"; fi
if [ "${CMD_RC[model_ladder_policy_assert]:-1}" -ne 0 ]; then add_blocking_reason "model_ladder_policy_failed"; fi
if [ "${CMD_RC[multiuser_posture_assert]:-1}" -ne 0 ]; then add_blocking_reason "multiuser_posture_failed"; fi
if [ "${CMD_RC[interfaces_policy_assert]:-1}" -ne 0 ]; then add_blocking_reason "interfaces_policy_failed"; fi

if ! rg -q '"mode":\s*"non-main"' "$OUT_DIR/sandbox_explain_json.txt"; then
  add_blocking_reason "sandbox_mode_not_non_main"
fi
if rg -q '"elevated":\s*\{[^}]*"enabled":\s*true' "$OUT_DIR/sandbox_explain_json.txt"; then
  add_blocking_reason "sandbox_elevated_enabled"
fi

receipt_gen="$OUT_DIR/receipt_generation.txt"
set +e
OPENCLAW_CMD_TIMEOUT_SEC="$RECEIPT_CMD_TIMEOUT_SEC" \
OPENCLAW_SECURITY_AUDIT_MODE="$SECURITY_AUDIT_MODE" \
OPENCLAW_CONFINEMENT_FLAG="$CONFINEMENT_FLAG" \
runtime/tools/openclaw_receipts_bundle.sh > "$receipt_gen" 2>&1
rc_receipt=$?
set -e
if [ "$rc_receipt" -ne 0 ]; then
  add_blocking_reason "receipt_generation_failed"
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
  add_blocking_reason "leak_scan_failed"
fi

policy_fingerprint="missing_config"
if [ -f "$CFG_PATH" ]; then
  policy_fingerprint="$(sha256sum "$CFG_PATH" | awk '{print $1}')"
fi

{
  echo "ts_utc=$TS_UTC"
  echo "verify_out_dir=$OUT_DIR"
  echo "gate_status_path=$GATE_STATUS_PATH"
  echo "runtime_receipt=$runtime_receipt"
  echo "runtime_manifest=$runtime_manifest"
  echo "runtime_ledger_entry=$runtime_ledger_entry"
  echo "ledger_path=$ledger_path"
  echo "receipt_generation_exit=$rc_receipt"
  echo "leak_scan_exit=$rc_leak"
  echo "security_audit_mode=$SECURITY_AUDIT_MODE"
  echo "security_audit_deep_exit=${CMD_RC[security_audit_deep]:-1}"
  echo "security_audit_fallback_exit=${CMD_RC[security_audit_fallback]:-NA}"
  echo "cron_delivery_guard_exit=${CMD_RC[cron_delivery_guard]:-1}"
  echo "models_status_probe_exit=${CMD_RC[models_status_probe]:-1}"
  echo "sandbox_explain_json_exit=${CMD_RC[sandbox_explain_json]:-1}"
  echo "gateway_probe_json_exit=${CMD_RC[gateway_probe_json]:-1}"
  echo "policy_assert_exit=${CMD_RC[policy_assert]:-1}"
  echo "model_ladder_policy_assert_exit=${CMD_RC[model_ladder_policy_assert]:-1}"
  echo "multiuser_posture_assert_exit=${CMD_RC[multiuser_posture_assert]:-1}"
  echo "interfaces_policy_assert_exit=${CMD_RC[interfaces_policy_assert]:-1}"
  echo "warnings_present=$WARNINGS"
  echo "policy_fingerprint=$policy_fingerprint"
  if [ -n "$CONFINEMENT_FLAG" ]; then
    echo "confinement_detected=true"
    echo "confinement_flag=$CONFINEMENT_FLAG"
  else
    echo "confinement_detected=false"
  fi
} > "$OUT_DIR/summary.txt"

reasons_file="$OUT_DIR/blocking_reasons.txt"
if [ "${#BLOCKING_REASONS[@]}" -gt 0 ]; then
  printf '%s\n' "${BLOCKING_REASONS[@]}" > "$reasons_file"
else
  : > "$reasons_file"
fi

export CHECK_SECURITY_AUDIT_CLEAN="$([ "$SECURITY_AUDIT_MODE" != "blocked_fallback_failed" ] && [ "$SECURITY_AUDIT_MODE" != "blocked_unknown_deep_error" ] && [ -f "$SECURITY_FILE" ] && rg -q 'Summary:\s*0 critical\s*·\s*0 warn' "$SECURITY_FILE" && echo true || echo false)"
export CHECK_CRON_DELIVERY_GUARD="$([ "${CMD_RC[cron_delivery_guard]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_MODELS_STATUS_PROBE="$([ "${CMD_RC[models_status_probe]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_SANDBOX_EXPLAIN="$([ "${CMD_RC[sandbox_explain_json]:-1}" -eq 0 ] && rg -q '"mode":\s*"non-main"' "$OUT_DIR/sandbox_explain_json.txt" && ! rg -q '"elevated":\s*\{[^}]*"enabled":\s*true' "$OUT_DIR/sandbox_explain_json.txt" && echo true || echo false)"
export CHECK_GATEWAY_PROBE="$([ "${CMD_RC[gateway_probe_json]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_POLICY_ASSERT="$([ "${CMD_RC[policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_MODEL_LADDER_POLICY="$([ "${CMD_RC[model_ladder_policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_MULTIUSER_POSTURE="$([ "${CMD_RC[multiuser_posture_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_INTERFACES_POLICY="$([ "${CMD_RC[interfaces_policy_assert]:-1}" -eq 0 ] && echo true || echo false)"
export CHECK_RECEIPT_GENERATION="$([ "$rc_receipt" -eq 0 ] && echo true || echo false)"
export CHECK_LEAK_SCAN="$([ "$rc_leak" -eq 0 ] && echo true || echo false)"

python3 - <<'PY' "$GATE_STATUS_PATH" "$TS_UTC" "$policy_fingerprint" "$SECURITY_AUDIT_MODE" "$CONFINEMENT_FLAG" "$OUT_DIR" "$reasons_file"
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

gate_status_path = Path(sys.argv[1])
ts_utc = sys.argv[2]
policy_fingerprint = sys.argv[3]
security_audit_mode = sys.argv[4]
confinement_flag = sys.argv[5]
out_dir = Path(sys.argv[6])
reasons_file = Path(sys.argv[7])

def env_bool(key: str) -> bool:
    return str(os.environ.get(key, "")).strip().lower() == "true"

def first_line(path: Path) -> str:
    if not path.exists():
        return "output_missing"
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not text:
        return "empty_output"
    return text[0][:260]

checks: List[Dict[str, Any]] = [
    {"name": "security_audit_clean", "pass": env_bool("CHECK_SECURITY_AUDIT_CLEAN"), "mode": security_audit_mode, "detail": first_line(out_dir / "security_audit_deep.txt")},
    {"name": "cron_delivery_guard", "pass": env_bool("CHECK_CRON_DELIVERY_GUARD"), "mode": "required", "detail": first_line(out_dir / "cron_delivery_guard.txt")},
    {"name": "models_status_probe", "pass": env_bool("CHECK_MODELS_STATUS_PROBE"), "mode": "required", "detail": first_line(out_dir / "models_status_probe.txt")},
    {"name": "sandbox_explain", "pass": env_bool("CHECK_SANDBOX_EXPLAIN"), "mode": "required", "detail": first_line(out_dir / "sandbox_explain_json.txt")},
    {"name": "gateway_probe", "pass": env_bool("CHECK_GATEWAY_PROBE"), "mode": "required", "detail": first_line(out_dir / "gateway_probe_json.txt")},
    {"name": "policy_assert", "pass": env_bool("CHECK_POLICY_ASSERT"), "mode": "required", "detail": first_line(out_dir / "policy_assert.txt")},
    {"name": "model_ladder_policy_assert", "pass": env_bool("CHECK_MODEL_LADDER_POLICY"), "mode": "required", "detail": first_line(out_dir / "model_ladder_policy_assert.txt")},
    {"name": "multiuser_posture_assert", "pass": env_bool("CHECK_MULTIUSER_POSTURE"), "mode": "required", "detail": first_line(out_dir / "multiuser_posture_assert.txt")},
    {"name": "interfaces_policy_assert", "pass": env_bool("CHECK_INTERFACES_POLICY"), "mode": "required", "detail": first_line(out_dir / "interfaces_policy_assert.txt")},
    {"name": "receipt_generation", "pass": env_bool("CHECK_RECEIPT_GENERATION"), "mode": "required", "detail": first_line(out_dir / "receipt_generation.txt")},
    {"name": "leak_scan", "pass": env_bool("CHECK_LEAK_SCAN"), "mode": "required", "detail": first_line(out_dir / "leak_scan_output.txt")},
]

blocking_reasons: List[str] = []
if reasons_file.exists():
    blocking_reasons = [line.strip() for line in reasons_file.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]

payload: Dict[str, Any] = {
    "ts_utc": ts_utc,
    "pass": all(bool(item.get("pass")) for item in checks) and not blocking_reasons,
    "blocking_reasons": blocking_reasons,
    "checks": checks,
    "security_audit_mode": security_audit_mode,
    "confinement_detected": bool(confinement_flag),
    "policy_fingerprint": policy_fingerprint,
}
if confinement_flag:
    payload["confinement_flag"] = confinement_flag

gate_status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
PY

if [ "$PASS" -eq 1 ]; then
  if [ "$WARNINGS" -eq 1 ]; then
    if [ -n "$CONFINEMENT_FLAG" ]; then
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=true confinement_flag=$CONFINEMENT_FLAG notes=command_warnings_present gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    else
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=false notes=command_warnings_present gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    fi
  else
    if [ -n "$CONFINEMENT_FLAG" ]; then
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=true confinement_flag=$CONFINEMENT_FLAG gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    else
      echo "PASS security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=false gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path"
    fi
  fi
  exit 0
fi

if [ -n "$CONFINEMENT_FLAG" ]; then
  echo "FAIL security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=true confinement_flag=$CONFINEMENT_FLAG gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
else
  echo "FAIL security_audit_mode=$SECURITY_AUDIT_MODE confinement_detected=false gate_status=$GATE_STATUS_PATH runtime_receipt=$runtime_receipt ledger_path=$ledger_path" >&2
fi
exit 1
```
