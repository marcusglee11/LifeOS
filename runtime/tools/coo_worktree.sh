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

resolve_dashboard_url() {
  local fallback_url output parsed token
  fallback_url="http://127.0.0.1:${OPENCLAW_GATEWAY_PORT}/"
  output="$(run_openclaw dashboard --no-open 2>/dev/null || true)"
  parsed="$(printf '%s\n' "$output" | sed -n 's/.*Dashboard URL: \(http[^[:space:]]*\).*/\1/p' | tail -n 1)"
  if [ -n "$parsed" ]; then
    printf '%s\n' "$parsed"
    return 0
  fi
  token="$(resolve_gateway_token_from_config)"
  if [ -n "$token" ]; then
    printf '%s#token=%s\n' "$fallback_url" "$token"
    return 0
  fi
  echo "WARN: gateway token not found; opening unauthenticated dashboard URL." >&2
  printf '%s\n' "$fallback_url"
  return 0
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
  - Interactive mode (tui, app, diag, start, models, openclaw): Fail-soft on ladder issues
  - Mission mode (e2e, job, run-job): Fail-closed on ladder issues
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
      export COO_ENFORCEMENT_MODE=interactive
      runtime/tools/openclaw_gateway_ensure.sh
      runtime/tools/openclaw_models_preflight.sh
    )
    dashboard_url="$(resolve_dashboard_url)"
    echo "DASHBOARD_URL=$dashboard_url"
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
    app_url="$(resolve_dashboard_url)"
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
