# Review_Packet_COO_UX_Single_Command_v1.1

## Mission
Implement UX Hardening v2 with single-entrypoint COO commands:
- `coo start`
- `coo tui`
- `coo app`
- `coo stop`
- `coo diag`

## Branch Context
- branch: build/ux-coo-single-command
- base_head_before_commit: 5812c96

## Embedded Model Policy (Verbatim)
A) Execution-tier (cheap/default) ladder — used by “main” and “quick”
1) openai-codex/gpt-5.3-codex  (tier: low)
2) google-gemini-cli/gemini-3-flash-preview (Copilot subscription)
3) openrouter/pony-alpha
4) zen/opencode/<Kimi K2.5 Free identifier>   (ONLY if already discoverable in config or models list; do not invent)

B) Thinking-tier ladder — used by “think”
1) openai-codex/gpt-5.3-codex  (tier: extra_high)
2) github-copilot/claude-opus-4.6
3) openrouter/deepseek-v3.2
4) zen/opencode/<Kimi K2.5 Free identifier>   (same discovery rule)

C) Guardrails
- No Haiku-tier or small-model fallbacks on any agent surface that can receive untrusted messages.
- If any rung is missing/unavailable, allow a degraded ladder ONLY if at least one working model exists per agent.
- Preflight must clearly report which rung(s) are failing (auth / provider down / model missing), without leaking secrets.

## What Changed
1. Added deterministic `openclaw` binary resolution in `runtime/tools/coo_worktree.sh`.
2. Added new COO UX command dispatcher entries: `start`, `tui`, `app`, `stop`, `diag`.
3. Added WSL-safe gateway ensure script with tmux-first and nohup fallback startup:
   - `runtime/tools/openclaw_gateway_ensure.sh`
4. Added local gateway stop script for tmux and nohup pidfile:
   - `runtime/tools/openclaw_gateway_stop_local.sh`
5. Added machine-checkable model policy assertion script:
   - `runtime/tools/openclaw_model_policy_assert.py`
6. Added auth-aware model preflight script:
   - `runtime/tools/openclaw_models_preflight.sh`
7. Added policy assertion unit tests:
   - `runtime/tests/test_openclaw_model_policy_assert.py`
8. Added Windows launchers:
   - `tools/windows/COO_TUI.cmd`
   - `tools/windows/COO_APP.cmd`
   - `tools/windows/COO_STOP.cmd`
   - `tools/windows/README.md`

## Preflight Logic: “TUI Ready”
`coo start` now:
1. Ensures OpenClaw binary is resolvable.
2. Runs gateway ensure (`openclaw_gateway_ensure.sh`).
3. Runs model/auth preflight (`openclaw_models_preflight.sh`).
4. Prints dashboard URL only on success.

`openclaw_models_preflight.sh` passes only when:
- gateway is reachable,
- model policy assertion is valid,
- at least one working model exists per agent (`main`, `quick`, `think`),
- top-rung auth is present per agent.

## Failure Modes and NEXT Commands
- `policy_violated`: fix `~/.openclaw/openclaw.json` ladder ordering/fallbacks.
- `top_rung_auth_missing`: run one or more:
  - `openclaw onboard`
  - `openclaw models auth login --provider openai-codex`
  - `openclaw models auth login --provider github-copilot`
  - `openclaw models auth login --provider google-gemini-cli`
  - `openclaw models auth login --provider openrouter`
- `gateway_unreachable` with confinement signature:
  - `uv_interface_addresses returned Unknown system error 1`
  - NEXT: run outside restricted sandbox / host context that permits interface enumeration.

## Evidence
- evidence_dir: `artifacts/evidence/openclaw/ux/20260212T113326Z`
- key files:
  - `repo_state_before.txt`
  - `openclaw_version.txt`
  - `acceptance_coo_diag.txt`
  - `acceptance_coo_start.txt`
  - `acceptance_coo_tui.txt`
  - `acceptance_coo_stop.txt`
  - `acceptance_windows_sim_start.txt`
  - `acceptance_windows_sim_diag.txt`
  - `pytest_model_policy_assert.txt`
  - `git_diff_name_only.txt`
  - `git_status_after.txt`

## Acceptance Summary (This Host)
- `coo diag`: rc=0
- `coo start`: rc=1 (fail-closed due known confinement signature)
- `coo tui -- --help`: rc=1 (inherits `coo start` fail-closed)
- `coo stop`: rc=0
- `bash -lic ... coo start`: rc=1 (same confinement)
- `bash -lic ... coo diag`: rc=0

This repository-side implementation is complete. Startup remains fail-closed in this constrained runtime when gateway cannot enumerate interfaces.

## Operator Quickstart
1. `coo tui`
2. `coo app`
3. `coo stop`

## Appendix A — Flattened Code (All Changed Files)

### FILE: runtime/tools/coo_worktree.sh
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
text = re.sub(r'\bxoxb-[A-Za-z0-9-]{6,}\b', 'xoxb-[REDACTED]', text)
text = re.sub(r'\bsk-or-v1[a-zA-Z0-9._-]{6,}\b', 'sk-or-v1[REDACTED]', text)
text = re.sub(r'\bsk-[A-Za-z0-9_-]{8,}\b', 'sk-[REDACTED]', text)
text = re.sub(r'\bAIza[0-9A-Za-z_-]{10,}\b', 'AIza[REDACTED]', text)
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
  runtime/tools/coo_worktree.sh start
  runtime/tools/coo_worktree.sh tui [-- <tui-args...>]
  runtime/tools/coo_worktree.sh app
  runtime/tools/coo_worktree.sh stop
  runtime/tools/coo_worktree.sh diag
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
    ensure_openclaw_surface
    print_header
    (
      cd "$BUILD_REPO"
      runtime/tools/openclaw_gateway_ensure.sh
      runtime/tools/openclaw_models_preflight.sh
    )
    echo "DASHBOARD_URL=http://127.0.0.1:${OPENCLAW_GATEWAY_PORT}/"
    ;;
  tui)
    shift || true
    if [ "${1:-}" = "--" ]; then
      shift || true
    fi
    "$0" start
    ensure_openclaw_surface
    print_header
    enter_training_dir
    run_openclaw tui --deliver --session main "$@"
    ;;
  app)
    shift || true
    "$0" start
    ensure_openclaw_surface
    print_header
    app_url="http://127.0.0.1:${OPENCLAW_GATEWAY_PORT}/"
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

### FILE: runtime/tools/openclaw_gateway_ensure.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CFG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
CHECK_ONLY=0
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
RECEIPT_DIR="$STATE_DIR/runtime"
RECEIPT_PATH="$RECEIPT_DIR/gateway_last_start.json"
PIDFILE="$RECEIPT_DIR/openclaw-gateway.pid"
NOHUP_LOG="$RECEIPT_DIR/openclaw-gateway.nohup.log"
KNOWN_UV_IFADDR='uv_interface_addresses returned Unknown system error 1'

usage() {
  cat <<'USAGE'
Usage:
  runtime/tools/openclaw_gateway_ensure.sh [--check-only]
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
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

if [ -z "$OPENCLAW_BIN" ] || [ ! -x "$OPENCLAW_BIN" ]; then
  echo "ERROR: OPENCLAW_BIN is not executable. Resolve OpenClaw binary first." >&2
  exit 127
fi

if ! mkdir -p "$RECEIPT_DIR" 2>/dev/null; then
  RECEIPT_DIR="/tmp/openclaw-runtime"
  mkdir -p "$RECEIPT_DIR"
  RECEIPT_PATH="$RECEIPT_DIR/gateway_last_start.json"
  PIDFILE="$RECEIPT_DIR/openclaw-gateway.pid"
  NOHUP_LOG="$RECEIPT_DIR/openclaw-gateway.nohup.log"
fi

port_reachable() {
  python3 - <<'PY' "$PORT"
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
s.settimeout(0.75)
try:
    s.connect(("127.0.0.1", port))
except Exception:
    print("false")
    raise SystemExit(1)
print("true")
PY
}

run_probe() {
  local out rc_file rc
  out="$(mktemp)"
  rc_file="${out}.rc"
  (
    set +e
    timeout 10s "$OPENCLAW_BIN" gateway --port "$PORT" probe --json >"$out" 2>&1
    echo "$?" >"$rc_file"
  )
  rc="$(sed -n '1p' "$rc_file" | tr -d '[:space:]')"
  rm -f "$rc_file"
  if [ "$rc" -eq 0 ]; then
    rm -f "$out"
    return 0
  fi
  if rg -q "$KNOWN_UV_IFADDR" "$out"; then
    rm -f "$out"
    return 2
  fi
  rm -f "$out"
  return 1
}

write_receipt() {
  local started_via="$1"
  local reachable="$2"
  python3 - <<'PY' "$RECEIPT_PATH" "$TS_UTC" "$PORT" "$OPENCLAW_BIN" "$CFG_PATH" "$started_via" "$reachable"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "ts_utc": sys.argv[2],
    "port": int(sys.argv[3]),
    "openclaw_bin": sys.argv[4],
    "openclaw_config_path": sys.argv[5],
    "started_via": sys.argv[6],
    "reachable": sys.argv[7].lower() == "true",
}
path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")
PY
}

reachable=false
if run_probe; then
  reachable=true
elif port_reachable >/dev/null 2>&1; then
  reachable=true
fi

if [ "$reachable" = true ]; then
  write_receipt "already_up" "true"
  echo "GATEWAY_STATUS=already_up PORT=$PORT"
  exit 0
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  write_receipt "check_only_unreachable" "false"
  echo "GATEWAY_STATUS=unreachable PORT=$PORT"
  exit 1
fi

started_via="none"

if [ -n "${XDG_RUNTIME_DIR:-}" ] && command -v systemctl >/dev/null 2>&1; then
  set +e
  timeout 20s "$OPENCLAW_BIN" gateway --port "$PORT" start >/dev/null 2>&1
  rc_start=$?
  set -e
  if [ "$rc_start" -eq 0 ]; then
    started_via="systemd_user_best_effort"
  fi
fi

if [ "$started_via" = "none" ]; then
  if command -v tmux >/dev/null 2>&1; then
    if tmux has-session -t openclaw-gateway >/dev/null 2>&1; then
      started_via="tmux_existing"
    else
      set +e
      tmux new-session -d -s openclaw-gateway \
        "OPENCLAW_STATE_DIR='$STATE_DIR' OPENCLAW_CONFIG_PATH='$CFG_PATH' OPENCLAW_GATEWAY_PORT='$PORT' '$OPENCLAW_BIN' gateway run --port '$PORT' --verbose" >/dev/null 2>&1
      rc_tmux_new=$?
      set -e
      if [ "$rc_tmux_new" -eq 0 ]; then
        started_via="tmux_started"
      fi
    fi
  fi
fi

if [ "$started_via" = "none" ]; then
  set +e
  nohup env OPENCLAW_STATE_DIR="$STATE_DIR" OPENCLAW_CONFIG_PATH="$CFG_PATH" OPENCLAW_GATEWAY_PORT="$PORT" \
    "$OPENCLAW_BIN" gateway run --port "$PORT" --verbose >"$NOHUP_LOG" 2>&1 &
  pid=$!
  rc_nohup=$?
  set -e
  if [ "$rc_nohup" -eq 0 ] && [ -n "${pid:-}" ]; then
    printf '%s\n' "$pid" >"$PIDFILE"
    started_via="nohup_started"
  else
    echo "ERROR: unable to start gateway via tmux or nohup." >&2
    write_receipt "start_failed" "false"
    exit 1
  fi
fi

for _ in $(seq 1 20); do
  set +e
  run_probe
  probe_rc=$?
  set -e
  if [ "$probe_rc" -eq 0 ]; then
    write_receipt "$started_via" "true"
    echo "GATEWAY_STATUS=up PORT=$PORT STARTED_VIA=$started_via"
    exit 0
  fi
  if [ "$probe_rc" -eq 2 ] && [ -f "$NOHUP_LOG" ] && rg -q "$KNOWN_UV_IFADDR" "$NOHUP_LOG"; then
    write_receipt "$started_via" "false"
    echo "ERROR: gateway start blocked by environment confinement ($KNOWN_UV_IFADDR)." >&2
    echo "NEXT: run outside restricted sandbox or use a host context where interface enumeration is permitted." >&2
    exit 1
  fi
  if port_reachable >/dev/null 2>&1; then
    write_receipt "$started_via" "true"
    echo "GATEWAY_STATUS=up PORT=$PORT STARTED_VIA=$started_via"
    exit 0
  fi
  sleep 1
done

write_receipt "$started_via" "false"
echo "ERROR: gateway still unreachable after startup attempt (started_via=$started_via port=$PORT)." >&2
exit 1
```

### FILE: runtime/tools/openclaw_gateway_stop_local.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
RUNTIME_DIR="$STATE_DIR/runtime"
PIDFILE="$RUNTIME_DIR/openclaw-gateway.pid"

if ! mkdir -p "$RUNTIME_DIR" 2>/dev/null; then
  RUNTIME_DIR="/tmp/openclaw-runtime"
  mkdir -p "$RUNTIME_DIR"
  PIDFILE="$RUNTIME_DIR/openclaw-gateway.pid"
fi

stopped=false

if command -v tmux >/dev/null 2>&1; then
  if tmux has-session -t openclaw-gateway >/dev/null 2>&1; then
    tmux kill-session -t openclaw-gateway >/dev/null 2>&1 || true
    stopped=true
  fi
fi

if [ -f "$PIDFILE" ]; then
  pid="$(sed -n '1p' "$PIDFILE" | tr -d '[:space:]')"
  if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    stopped=true
  fi
  rm -f "$PIDFILE"
fi

if [ "$stopped" = true ]; then
  echo "GATEWAY_STOP=local_process_stopped"
else
  echo "GATEWAY_STOP=no_local_gateway_process"
fi
```

### FILE: runtime/tools/openclaw_model_policy_assert.py
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

EXECUTION_BASE = [
    "openai-codex/gpt-5.3-codex",
    "google-gemini-cli/gemini-3-flash-preview",
    "openrouter/pony-alpha",
]
THINKING_BASE = [
    "openai-codex/gpt-5.3-codex",
    "github-copilot/claude-opus-4.6",
    "openrouter/deepseek-v3.2",
]
DISALLOWED_FALLBACK_RE = re.compile(r"(haiku|small)", re.IGNORECASE)
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$", re.IGNORECASE)
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
        # Expected table order: Model Input Ctx Local Auth Tags
        # Use token positions from the end to tolerate variable spacing.
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
    candidates = []
    for mid in list(cfg_ids) + list(list_ids):
        low = mid.lower()
        if "kimi" in low and ("opencode/" in low or low.startswith("zen/opencode/")):
            candidates.append(mid)
    if not candidates:
        return None
    # Prefer explicit zen/opencode namespace when present.
    zen_first = [c for c in candidates if c.lower().startswith("zen/opencode/")]
    if zen_first:
        return sorted(set(zen_first))[0]
    return sorted(set(candidates))[0]


def _probe_kimi_via_provider_lists() -> List[str]:
    discovered: List[str] = []
    for provider in ("zen", "opencode"):
        rc, out = _safe_run([OPENCLAW_BIN, "models", "list", "--all", "--provider", provider], timeout_s=20)
        if rc != 0:
            continue
        for mid in _parse_models_list_text(out).keys():
            discovered.append(mid)
    return sorted(set(discovered))


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
        ladder = []
        if isinstance(primary, str):
            ladder.append(primary)
        if isinstance(fallbacks, list):
            ladder.extend([str(x) for x in fallbacks if isinstance(x, str)])
        return ladder
    return []


def _ordered_subsequence(actual: Sequence[str], expected: Sequence[str]) -> bool:
    idx = 0
    for model in actual:
        try:
            pos = expected.index(model, idx)
        except ValueError:
            return False
        idx = pos + 1
    return True


def _provider_of(model_id: str) -> str:
    return model_id.split("/", 1)[0].strip().lower() if "/" in model_id else "unknown"


def assert_policy(cfg: Dict[str, Any], models_status: Dict[str, Dict[str, Any]], kimi_id: Optional[str]) -> Dict[str, Any]:
    execution_expected = list(EXECUTION_BASE)
    thinking_expected = list(THINKING_BASE)
    unresolved_optional_rungs: List[str] = []
    if kimi_id:
        execution_expected.append(kimi_id)
        thinking_expected.append(kimi_id)
    else:
        unresolved_optional_rungs.extend(
            [
                "execution:zen/opencode/<Kimi K2.5 Free identifier>",
                "thinking:zen/opencode/<Kimi K2.5 Free identifier>",
            ]
        )

    violations: List[str] = []
    ladders: Dict[str, Any] = {}

    def validate(agent_id: str, expected: List[str]) -> None:
        actual = _agent_ladder(cfg, agent_id)
        if not actual:
            violations.append(f"{agent_id}: ladder missing")
            ladders[agent_id] = {
                "actual": [],
                "expected": expected,
                "working_models": [],
                "working_count": 0,
                "top_rung_auth_missing": True,
            }
            return

        if actual[0] != expected[0]:
            violations.append(f"{agent_id}: primary must be {expected[0]}, got {actual[0]}")
        if not _ordered_subsequence(actual, expected):
            violations.append(f"{agent_id}: ladder order mismatch with policy")

        for fb in actual[1:]:
            if DISALLOWED_FALLBACK_RE.search(fb):
                violations.append(f"{agent_id}: disallowed fallback model id: {fb}")

        for model in actual:
            if model not in expected:
                violations.append(f"{agent_id}: model not in policy ladder: {model}")

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
            "expected": expected,
            "working_models": working_models,
            "working_count": working_count,
            "top_rung_auth_missing": top_rung_auth_missing,
            "top_rung_working": top_working,
        }

    validate("main", execution_expected)
    validate("quick", execution_expected)
    validate("think", thinking_expected)

    # Enforce extra_high when represented explicitly.
    think_agent = None
    for item in ((cfg.get("agents") or {}).get("list") or []):
        if isinstance(item, dict) and str(item.get("id") or "") == "think":
            think_agent = item
            break
    if isinstance(think_agent, dict):
        think_level = think_agent.get("thinking") if "thinking" in think_agent else think_agent.get("thinkingDefault")
        if think_level is not None and str(think_level).lower() not in {"extra_high", "extra-high", "very_high"}:
            violations.append(f"think: thinking tier should be extra_high when configured, got {think_level}")

    providers = sorted(
        {
            _provider_of(m)
            for m in execution_expected + thinking_expected
            if isinstance(m, str) and "/" in m
        }
    )
    auth_missing_providers = sorted(
        {
            _provider_of((ladders.get(aid) or {}).get("actual", [None])[0] or "")
            for aid in ("main", "quick", "think")
            if (ladders.get(aid) or {}).get("top_rung_auth_missing") is True
        }
    )

    return {
        "policy_ok": len(violations) == 0,
        "execution_ladder_expected": execution_expected,
        "thinking_ladder_expected": thinking_expected,
        "unresolved_optional_rungs": unresolved_optional_rungs,
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

    cfg_path = Path(args.config).expanduser()
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
    if not kimi_id:
        kimi_id = _discover_kimi_id(cfg_ids, _probe_kimi_via_provider_lists())

    result = assert_policy(cfg, models_status, kimi_id)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(f"policy_ok={'true' if result['policy_ok'] else 'false'} violations={len(result['violations'])}")
    return 0 if result["policy_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

### FILE: runtime/tools/openclaw_models_preflight.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_MODELS_PREFLIGHT_OUT_DIR:-$STATE_DIR/runtime/models_preflight/$TS_UTC}"
LIST_TIMEOUT_SEC="${OPENCLAW_MODELS_LIST_TIMEOUT_SEC:-20}"
PROBE_TIMEOUT_SEC="${OPENCLAW_MODELS_PROBE_TIMEOUT_SEC:-70}"

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
timeout "$PROBE_TIMEOUT_SEC" "$OPENCLAW_BIN" models status --probe > "$probe_raw" 2>&1
rc_probe=$?
set -e

python3 - <<'PY' "$probe_raw" "$probe_sanitized"
import re,sys
inp=open(sys.argv[1],encoding='utf-8',errors='replace').read()
text=inp
text=re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}','[REDACTED_EMAIL]',text)
text=re.sub(r'Authorization\s*:\s*Bearer\s+\S+','Authorization: Bearer [REDACTED]',text,flags=re.I)
text=re.sub(r'\bxapp-[A-Za-z0-9-]{6,}\b','xapp-[REDACTED]',text)
text=re.sub(r'\bxoxb-[A-Za-z0-9-]{6,}\b','xoxb-[REDACTED]',text)
text=re.sub(r'\bsk-[A-Za-z0-9_-]{8,}\b','sk-[REDACTED]',text)
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
  pass=false
  reason="top_rung_auth_missing"
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
  echo "rc_policy=$rc_policy"
  echo "models_list_out=$models_list_out"
  echo "models_probe_sanitized=$probe_sanitized"
  echo "policy_json=$policy_json"
} > "$summary_out"

if [ "$pass" = true ]; then
  echo "PASS models_preflight=true reason=ok summary=$summary_out"
  exit 0
fi

echo "FAIL models_preflight=false reason=$reason summary=$summary_out" >&2
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
elif [ "$reason" = "top_rung_auth_missing" ]; then
  echo "NEXT: openclaw onboard" >&2
  IFS=',' read -r -a provs <<< "$providers_referenced"
  for provider in "${provs[@]}"; do
    case "$provider" in
      openai-codex|github-copilot|google-gemini-cli|openrouter|opencode|zen)
        echo "NEXT: openclaw models auth login --provider $provider" >&2
        ;;
    esac
  done
elif [ "$reason" = "no_working_model_for_agent" ]; then
  echo "NEXT: Verify provider auth and model availability; ensure at least one working model per agent." >&2
fi
exit 1

```

### FILE: runtime/tests/test_openclaw_model_policy_assert.py
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
                            "google-gemini-cli/gemini-3-flash-preview",
                            "openrouter/pony-alpha",
                        ],
                    },
                },
                {
                    "id": "quick",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "google-gemini-cli/gemini-3-flash-preview",
                        ],
                    },
                },
                {
                    "id": "think",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "github-copilot/claude-opus-4.6",
                            "openrouter/deepseek-v3.2",
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
google-gemini-cli/gemini-3-flash-preview   text+image 1024k    no    yes   configured
github-copilot/claude-opus-4.6             text+image 125k     no    yes   configured
openrouter/deepseek-v3.2                   text+image 200k     no    no    configured
openrouter/pony-alpha                      text+image 200k     no    yes   configured
opencode/kimi-k2.5-free                    text+image 256k     no    yes   configured
"""


def test_policy_assert_passes_for_valid_ordered_ladders():
    cfg = _cfg()
    status = _parse_models_list_text(_models_list_text())
    kimi = _discover_kimi_id([], list(status.keys()))
    result = assert_policy(cfg, status, kimi)
    assert result["policy_ok"] is True
    assert result["ladders"]["main"]["working_count"] >= 1
    assert result["ladders"]["quick"]["working_count"] >= 1
    assert result["ladders"]["think"]["working_count"] >= 1


def test_policy_assert_fails_on_wrong_order():
    cfg = _cfg()
    cfg["agents"]["list"][0]["model"]["fallbacks"] = [
        "openrouter/pony-alpha",
        "google-gemini-cli/gemini-3-flash-preview",
    ]
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, "opencode/kimi-k2.5-free")
    assert result["policy_ok"] is False
    assert any("order mismatch" in v for v in result["violations"])


def test_policy_assert_fails_on_disallowed_small_or_haiku():
    cfg = _cfg()
    cfg["agents"]["list"][1]["model"]["fallbacks"] = ["anthropic/claude-3-haiku-20240307"]
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

```

### FILE: tools/windows/COO_TUI.cmd
```bat
@echo off
setlocal
wsl.exe -d Ubuntu -e bash -lic "cd /mnt/c/Users/cabra/Projects/LifeOS && coo tui"
endlocal

```

### FILE: tools/windows/COO_APP.cmd
```bat
@echo off
setlocal
wsl.exe -d Ubuntu -e bash -lic "cd /mnt/c/Users/cabra/Projects/LifeOS && coo app"
endlocal

```

### FILE: tools/windows/COO_STOP.cmd
```bat
@echo off
setlocal
wsl.exe -d Ubuntu -e bash -lic "cd /mnt/c/Users/cabra/Projects/LifeOS && coo stop"
endlocal

```

### FILE: tools/windows/README.md
```markdown
# COO Windows Launchers

These launchers provide pin-friendly Windows entrypoints for the COO UX.

Files:

- `COO_TUI.cmd`: launch `coo tui` inside WSL Ubuntu.
- `COO_APP.cmd`: launch `coo app` inside WSL Ubuntu.
- `COO_STOP.cmd`: launch `coo stop` inside WSL Ubuntu.

Pin instructions:

1. Navigate to `tools/windows/` in File Explorer.
2. Right-click a `.cmd` file and create a shortcut.
3. Pin the shortcut to Start or Taskbar.

Security notes:

- Launchers never include tokens or secrets.
- Slack tokens/signing secrets must be supplied as environment variables at runtime only.

```

### FILE: runtime/tools/coo_worktree.sh
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
text = re.sub(r'\bxoxb-[A-Za-z0-9-]{6,}\b', 'xoxb-[REDACTED]', text)
text = re.sub(r'\bsk-or-v1[a-zA-Z0-9._-]{6,}\b', 'sk-or-v1[REDACTED]', text)
text = re.sub(r'\bsk-[A-Za-z0-9_-]{8,}\b', 'sk-[REDACTED]', text)
text = re.sub(r'\bAIza[0-9A-Za-z_-]{10,}\b', 'AIza[REDACTED]', text)
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
  runtime/tools/coo_worktree.sh start
  runtime/tools/coo_worktree.sh tui [-- <tui-args...>]
  runtime/tools/coo_worktree.sh app
  runtime/tools/coo_worktree.sh stop
  runtime/tools/coo_worktree.sh diag
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
    ensure_openclaw_surface
    print_header
    (
      cd "$BUILD_REPO"
      runtime/tools/openclaw_gateway_ensure.sh
      runtime/tools/openclaw_models_preflight.sh
    )
    echo "DASHBOARD_URL=http://127.0.0.1:${OPENCLAW_GATEWAY_PORT}/"
    ;;
  tui)
    shift || true
    if [ "${1:-}" = "--" ]; then
      shift || true
    fi
    "$0" start
    ensure_openclaw_surface
    print_header
    enter_training_dir
    run_openclaw tui --deliver --session main "$@"
    ;;
  app)
    shift || true
    "$0" start
    ensure_openclaw_surface
    print_header
    app_url="http://127.0.0.1:${OPENCLAW_GATEWAY_PORT}/"
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

### FILE: runtime/tools/openclaw_gateway_ensure.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CFG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
CHECK_ONLY=0
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
RECEIPT_DIR="$STATE_DIR/runtime"
RECEIPT_PATH="$RECEIPT_DIR/gateway_last_start.json"
PIDFILE="$RECEIPT_DIR/openclaw-gateway.pid"
NOHUP_LOG="$RECEIPT_DIR/openclaw-gateway.nohup.log"
KNOWN_UV_IFADDR='uv_interface_addresses returned Unknown system error 1'

usage() {
  cat <<'USAGE'
Usage:
  runtime/tools/openclaw_gateway_ensure.sh [--check-only]
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
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

if [ -z "$OPENCLAW_BIN" ] || [ ! -x "$OPENCLAW_BIN" ]; then
  echo "ERROR: OPENCLAW_BIN is not executable. Resolve OpenClaw binary first." >&2
  exit 127
fi

if ! mkdir -p "$RECEIPT_DIR" 2>/dev/null; then
  RECEIPT_DIR="/tmp/openclaw-runtime"
  mkdir -p "$RECEIPT_DIR"
  RECEIPT_PATH="$RECEIPT_DIR/gateway_last_start.json"
  PIDFILE="$RECEIPT_DIR/openclaw-gateway.pid"
  NOHUP_LOG="$RECEIPT_DIR/openclaw-gateway.nohup.log"
fi

port_reachable() {
  python3 - <<'PY' "$PORT"
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
s.settimeout(0.75)
try:
    s.connect(("127.0.0.1", port))
except Exception:
    print("false")
    raise SystemExit(1)
print("true")
PY
}

run_probe() {
  local out rc_file rc
  out="$(mktemp)"
  rc_file="${out}.rc"
  (
    set +e
    timeout 10s "$OPENCLAW_BIN" gateway --port "$PORT" probe --json >"$out" 2>&1
    echo "$?" >"$rc_file"
  )
  rc="$(sed -n '1p' "$rc_file" | tr -d '[:space:]')"
  rm -f "$rc_file"
  if [ "$rc" -eq 0 ]; then
    rm -f "$out"
    return 0
  fi
  if rg -q "$KNOWN_UV_IFADDR" "$out"; then
    rm -f "$out"
    return 2
  fi
  rm -f "$out"
  return 1
}

write_receipt() {
  local started_via="$1"
  local reachable="$2"
  python3 - <<'PY' "$RECEIPT_PATH" "$TS_UTC" "$PORT" "$OPENCLAW_BIN" "$CFG_PATH" "$started_via" "$reachable"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "ts_utc": sys.argv[2],
    "port": int(sys.argv[3]),
    "openclaw_bin": sys.argv[4],
    "openclaw_config_path": sys.argv[5],
    "started_via": sys.argv[6],
    "reachable": sys.argv[7].lower() == "true",
}
path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")
PY
}

reachable=false
if run_probe; then
  reachable=true
elif port_reachable >/dev/null 2>&1; then
  reachable=true
fi

if [ "$reachable" = true ]; then
  write_receipt "already_up" "true"
  echo "GATEWAY_STATUS=already_up PORT=$PORT"
  exit 0
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  write_receipt "check_only_unreachable" "false"
  echo "GATEWAY_STATUS=unreachable PORT=$PORT"
  exit 1
fi

started_via="none"

if [ -n "${XDG_RUNTIME_DIR:-}" ] && command -v systemctl >/dev/null 2>&1; then
  set +e
  timeout 20s "$OPENCLAW_BIN" gateway --port "$PORT" start >/dev/null 2>&1
  rc_start=$?
  set -e
  if [ "$rc_start" -eq 0 ]; then
    started_via="systemd_user_best_effort"
  fi
fi

if [ "$started_via" = "none" ]; then
  if command -v tmux >/dev/null 2>&1; then
    if tmux has-session -t openclaw-gateway >/dev/null 2>&1; then
      started_via="tmux_existing"
    else
      set +e
      tmux new-session -d -s openclaw-gateway \
        "OPENCLAW_STATE_DIR='$STATE_DIR' OPENCLAW_CONFIG_PATH='$CFG_PATH' OPENCLAW_GATEWAY_PORT='$PORT' '$OPENCLAW_BIN' gateway run --port '$PORT' --verbose" >/dev/null 2>&1
      rc_tmux_new=$?
      set -e
      if [ "$rc_tmux_new" -eq 0 ]; then
        started_via="tmux_started"
      fi
    fi
  fi
fi

if [ "$started_via" = "none" ]; then
  set +e
  nohup env OPENCLAW_STATE_DIR="$STATE_DIR" OPENCLAW_CONFIG_PATH="$CFG_PATH" OPENCLAW_GATEWAY_PORT="$PORT" \
    "$OPENCLAW_BIN" gateway run --port "$PORT" --verbose >"$NOHUP_LOG" 2>&1 &
  pid=$!
  rc_nohup=$?
  set -e
  if [ "$rc_nohup" -eq 0 ] && [ -n "${pid:-}" ]; then
    printf '%s\n' "$pid" >"$PIDFILE"
    started_via="nohup_started"
  else
    echo "ERROR: unable to start gateway via tmux or nohup." >&2
    write_receipt "start_failed" "false"
    exit 1
  fi
fi

for _ in $(seq 1 20); do
  set +e
  run_probe
  probe_rc=$?
  set -e
  if [ "$probe_rc" -eq 0 ]; then
    write_receipt "$started_via" "true"
    echo "GATEWAY_STATUS=up PORT=$PORT STARTED_VIA=$started_via"
    exit 0
  fi
  if [ "$probe_rc" -eq 2 ] && [ -f "$NOHUP_LOG" ] && rg -q "$KNOWN_UV_IFADDR" "$NOHUP_LOG"; then
    write_receipt "$started_via" "false"
    echo "ERROR: gateway start blocked by environment confinement ($KNOWN_UV_IFADDR)." >&2
    echo "NEXT: run outside restricted sandbox or use a host context where interface enumeration is permitted." >&2
    exit 1
  fi
  if port_reachable >/dev/null 2>&1; then
    write_receipt "$started_via" "true"
    echo "GATEWAY_STATUS=up PORT=$PORT STARTED_VIA=$started_via"
    exit 0
  fi
  sleep 1
done

write_receipt "$started_via" "false"
echo "ERROR: gateway still unreachable after startup attempt (started_via=$started_via port=$PORT)." >&2
exit 1
```

### FILE: runtime/tools/openclaw_gateway_stop_local.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
RUNTIME_DIR="$STATE_DIR/runtime"
PIDFILE="$RUNTIME_DIR/openclaw-gateway.pid"

if ! mkdir -p "$RUNTIME_DIR" 2>/dev/null; then
  RUNTIME_DIR="/tmp/openclaw-runtime"
  mkdir -p "$RUNTIME_DIR"
  PIDFILE="$RUNTIME_DIR/openclaw-gateway.pid"
fi

stopped=false

if command -v tmux >/dev/null 2>&1; then
  if tmux has-session -t openclaw-gateway >/dev/null 2>&1; then
    tmux kill-session -t openclaw-gateway >/dev/null 2>&1 || true
    stopped=true
  fi
fi

if [ -f "$PIDFILE" ]; then
  pid="$(sed -n '1p' "$PIDFILE" | tr -d '[:space:]')"
  if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    stopped=true
  fi
  rm -f "$PIDFILE"
fi

if [ "$stopped" = true ]; then
  echo "GATEWAY_STOP=local_process_stopped"
else
  echo "GATEWAY_STOP=no_local_gateway_process"
fi
```

### FILE: runtime/tools/openclaw_model_policy_assert.py
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

EXECUTION_BASE = [
    "openai-codex/gpt-5.3-codex",
    "google-gemini-cli/gemini-3-flash-preview",
    "openrouter/pony-alpha",
]
THINKING_BASE = [
    "openai-codex/gpt-5.3-codex",
    "github-copilot/claude-opus-4.6",
    "openrouter/deepseek-v3.2",
]
DISALLOWED_FALLBACK_RE = re.compile(r"(haiku|small)", re.IGNORECASE)
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$", re.IGNORECASE)
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
        # Expected table order: Model Input Ctx Local Auth Tags
        # Use token positions from the end to tolerate variable spacing.
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
    candidates = []
    for mid in list(cfg_ids) + list(list_ids):
        low = mid.lower()
        if "kimi" in low and ("opencode/" in low or low.startswith("zen/opencode/")):
            candidates.append(mid)
    if not candidates:
        return None
    # Prefer explicit zen/opencode namespace when present.
    zen_first = [c for c in candidates if c.lower().startswith("zen/opencode/")]
    if zen_first:
        return sorted(set(zen_first))[0]
    return sorted(set(candidates))[0]


def _probe_kimi_via_provider_lists() -> List[str]:
    discovered: List[str] = []
    for provider in ("zen", "opencode"):
        rc, out = _safe_run([OPENCLAW_BIN, "models", "list", "--all", "--provider", provider], timeout_s=20)
        if rc != 0:
            continue
        for mid in _parse_models_list_text(out).keys():
            discovered.append(mid)
    return sorted(set(discovered))


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
        ladder = []
        if isinstance(primary, str):
            ladder.append(primary)
        if isinstance(fallbacks, list):
            ladder.extend([str(x) for x in fallbacks if isinstance(x, str)])
        return ladder
    return []


def _ordered_subsequence(actual: Sequence[str], expected: Sequence[str]) -> bool:
    idx = 0
    for model in actual:
        try:
            pos = expected.index(model, idx)
        except ValueError:
            return False
        idx = pos + 1
    return True


def _provider_of(model_id: str) -> str:
    return model_id.split("/", 1)[0].strip().lower() if "/" in model_id else "unknown"


def assert_policy(cfg: Dict[str, Any], models_status: Dict[str, Dict[str, Any]], kimi_id: Optional[str]) -> Dict[str, Any]:
    execution_expected = list(EXECUTION_BASE)
    thinking_expected = list(THINKING_BASE)
    unresolved_optional_rungs: List[str] = []
    if kimi_id:
        execution_expected.append(kimi_id)
        thinking_expected.append(kimi_id)
    else:
        unresolved_optional_rungs.extend(
            [
                "execution:zen/opencode/<Kimi K2.5 Free identifier>",
                "thinking:zen/opencode/<Kimi K2.5 Free identifier>",
            ]
        )

    violations: List[str] = []
    ladders: Dict[str, Any] = {}

    def validate(agent_id: str, expected: List[str]) -> None:
        actual = _agent_ladder(cfg, agent_id)
        if not actual:
            violations.append(f"{agent_id}: ladder missing")
            ladders[agent_id] = {
                "actual": [],
                "expected": expected,
                "working_models": [],
                "working_count": 0,
                "top_rung_auth_missing": True,
            }
            return

        if actual[0] != expected[0]:
            violations.append(f"{agent_id}: primary must be {expected[0]}, got {actual[0]}")
        if not _ordered_subsequence(actual, expected):
            violations.append(f"{agent_id}: ladder order mismatch with policy")

        for fb in actual[1:]:
            if DISALLOWED_FALLBACK_RE.search(fb):
                violations.append(f"{agent_id}: disallowed fallback model id: {fb}")

        for model in actual:
            if model not in expected:
                violations.append(f"{agent_id}: model not in policy ladder: {model}")

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
            "expected": expected,
            "working_models": working_models,
            "working_count": working_count,
            "top_rung_auth_missing": top_rung_auth_missing,
            "top_rung_working": top_working,
        }

    validate("main", execution_expected)
    validate("quick", execution_expected)
    validate("think", thinking_expected)

    # Enforce extra_high when represented explicitly.
    think_agent = None
    for item in ((cfg.get("agents") or {}).get("list") or []):
        if isinstance(item, dict) and str(item.get("id") or "") == "think":
            think_agent = item
            break
    if isinstance(think_agent, dict):
        think_level = think_agent.get("thinking") if "thinking" in think_agent else think_agent.get("thinkingDefault")
        if think_level is not None and str(think_level).lower() not in {"extra_high", "extra-high", "very_high"}:
            violations.append(f"think: thinking tier should be extra_high when configured, got {think_level}")

    providers = sorted(
        {
            _provider_of(m)
            for m in execution_expected + thinking_expected
            if isinstance(m, str) and "/" in m
        }
    )
    auth_missing_providers = sorted(
        {
            _provider_of((ladders.get(aid) or {}).get("actual", [None])[0] or "")
            for aid in ("main", "quick", "think")
            if (ladders.get(aid) or {}).get("top_rung_auth_missing") is True
        }
    )

    return {
        "policy_ok": len(violations) == 0,
        "execution_ladder_expected": execution_expected,
        "thinking_ladder_expected": thinking_expected,
        "unresolved_optional_rungs": unresolved_optional_rungs,
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

    cfg_path = Path(args.config).expanduser()
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
    if not kimi_id:
        kimi_id = _discover_kimi_id(cfg_ids, _probe_kimi_via_provider_lists())

    result = assert_policy(cfg, models_status, kimi_id)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(f"policy_ok={'true' if result['policy_ok'] else 'false'} violations={len(result['violations'])}")
    return 0 if result["policy_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

### FILE: runtime/tools/openclaw_models_preflight.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_MODELS_PREFLIGHT_OUT_DIR:-$STATE_DIR/runtime/models_preflight/$TS_UTC}"
LIST_TIMEOUT_SEC="${OPENCLAW_MODELS_LIST_TIMEOUT_SEC:-20}"
PROBE_TIMEOUT_SEC="${OPENCLAW_MODELS_PROBE_TIMEOUT_SEC:-70}"

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
timeout "$PROBE_TIMEOUT_SEC" "$OPENCLAW_BIN" models status --probe > "$probe_raw" 2>&1
rc_probe=$?
set -e

python3 - <<'PY' "$probe_raw" "$probe_sanitized"
import re,sys
inp=open(sys.argv[1],encoding='utf-8',errors='replace').read()
text=inp
text=re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}','[REDACTED_EMAIL]',text)
text=re.sub(r'Authorization\s*:\s*Bearer\s+\S+','Authorization: Bearer [REDACTED]',text,flags=re.I)
text=re.sub(r'\bxapp-[A-Za-z0-9-]{6,}\b','xapp-[REDACTED]',text)
text=re.sub(r'\bxoxb-[A-Za-z0-9-]{6,}\b','xoxb-[REDACTED]',text)
text=re.sub(r'\bsk-[A-Za-z0-9_-]{8,}\b','sk-[REDACTED]',text)
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
  pass=false
  reason="top_rung_auth_missing"
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
  echo "rc_policy=$rc_policy"
  echo "models_list_out=$models_list_out"
  echo "models_probe_sanitized=$probe_sanitized"
  echo "policy_json=$policy_json"
} > "$summary_out"

if [ "$pass" = true ]; then
  echo "PASS models_preflight=true reason=ok summary=$summary_out"
  exit 0
fi

echo "FAIL models_preflight=false reason=$reason summary=$summary_out" >&2
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
elif [ "$reason" = "top_rung_auth_missing" ]; then
  echo "NEXT: openclaw onboard" >&2
  IFS=',' read -r -a provs <<< "$providers_referenced"
  for provider in "${provs[@]}"; do
    case "$provider" in
      openai-codex|github-copilot|google-gemini-cli|openrouter|opencode|zen)
        echo "NEXT: openclaw models auth login --provider $provider" >&2
        ;;
    esac
  done
elif [ "$reason" = "no_working_model_for_agent" ]; then
  echo "NEXT: Verify provider auth and model availability; ensure at least one working model per agent." >&2
fi
exit 1

```

### FILE: runtime/tests/test_openclaw_model_policy_assert.py
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
                            "google-gemini-cli/gemini-3-flash-preview",
                            "openrouter/pony-alpha",
                        ],
                    },
                },
                {
                    "id": "quick",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "google-gemini-cli/gemini-3-flash-preview",
                        ],
                    },
                },
                {
                    "id": "think",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "github-copilot/claude-opus-4.6",
                            "openrouter/deepseek-v3.2",
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
google-gemini-cli/gemini-3-flash-preview   text+image 1024k    no    yes   configured
github-copilot/claude-opus-4.6             text+image 125k     no    yes   configured
openrouter/deepseek-v3.2                   text+image 200k     no    no    configured
openrouter/pony-alpha                      text+image 200k     no    yes   configured
opencode/kimi-k2.5-free                    text+image 256k     no    yes   configured
"""


def test_policy_assert_passes_for_valid_ordered_ladders():
    cfg = _cfg()
    status = _parse_models_list_text(_models_list_text())
    kimi = _discover_kimi_id([], list(status.keys()))
    result = assert_policy(cfg, status, kimi)
    assert result["policy_ok"] is True
    assert result["ladders"]["main"]["working_count"] >= 1
    assert result["ladders"]["quick"]["working_count"] >= 1
    assert result["ladders"]["think"]["working_count"] >= 1


def test_policy_assert_fails_on_wrong_order():
    cfg = _cfg()
    cfg["agents"]["list"][0]["model"]["fallbacks"] = [
        "openrouter/pony-alpha",
        "google-gemini-cli/gemini-3-flash-preview",
    ]
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, "opencode/kimi-k2.5-free")
    assert result["policy_ok"] is False
    assert any("order mismatch" in v for v in result["violations"])


def test_policy_assert_fails_on_disallowed_small_or_haiku():
    cfg = _cfg()
    cfg["agents"]["list"][1]["model"]["fallbacks"] = ["anthropic/claude-3-haiku-20240307"]
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

```

### FILE: tools/windows/COO_TUI.cmd
```bat
@echo off
setlocal
wsl.exe -d Ubuntu -e bash -lic "cd /mnt/c/Users/cabra/Projects/LifeOS && coo tui"
endlocal

```

### FILE: tools/windows/COO_APP.cmd
```bat
@echo off
setlocal
wsl.exe -d Ubuntu -e bash -lic "cd /mnt/c/Users/cabra/Projects/LifeOS && coo app"
endlocal

```

### FILE: tools/windows/COO_STOP.cmd
```bat
@echo off
setlocal
wsl.exe -d Ubuntu -e bash -lic "cd /mnt/c/Users/cabra/Projects/LifeOS && coo stop"
endlocal

```

### FILE: tools/windows/README.md
```markdown
# COO Windows Launchers

These launchers provide pin-friendly Windows entrypoints for the COO UX.

Files:

- `COO_TUI.cmd`: launch `coo tui` inside WSL Ubuntu.
- `COO_APP.cmd`: launch `coo app` inside WSL Ubuntu.
- `COO_STOP.cmd`: launch `coo stop` inside WSL Ubuntu.

Pin instructions:

1. Navigate to `tools/windows/` in File Explorer.
2. Right-click a `.cmd` file and create a shortcut.
3. Pin the shortcut to Start or Taskbar.

Security notes:

- Launchers never include tokens or secrets.
- Slack tokens/signing secrets must be supplied as environment variables at runtime only.

```
