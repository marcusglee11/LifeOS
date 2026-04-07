#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

# Tier 1: explicit env override (hermetic tests, CI)
# Tier 2: script-relative resolution via BASH_SOURCE[0] (works outside-repo invocations)
# Tier 3: git rev-parse fallback (when invoked from inside the repo)
if [ -n "${LIFEOS_BUILD_REPO:-}" ]; then
    BUILD_REPO="$LIFEOS_BUILD_REPO"
elif _script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null)"; then
    BUILD_REPO="$(cd "$_script_dir/../.." && pwd)"
else
    BUILD_REPO="$(git rev-parse --show-toplevel)"
fi
unset _script_dir
TRAIN_WT="$(dirname "$BUILD_REPO")/LifeOS__wt_coo_training"
TRAIN_BRANCH="coo/training"
OPENCLAW_PROFILE="${OPENCLAW_PROFILE:-}"
OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_STATE_DIR/openclaw.json}"
OPENCLAW_GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
OPENCLAW_BIN="${OPENCLAW_BIN:-}"
OPENCLAW_POLICY_PHASE="${OPENCLAW_POLICY_PHASE:-burnin}"
LIFEOS_DISTILL_ENABLE="${LIFEOS_DISTILL_ENABLE:-0}"
LIFEOS_DISTILL_MODE="${LIFEOS_DISTILL_MODE:-shadow}"

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
  echo "OPENCLAW_POLICY_PHASE=$OPENCLAW_POLICY_PHASE"
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
  export OPENCLAW_POLICY_PHASE
  export LIFEOS_DISTILL_ENABLE
  export LIFEOS_DISTILL_MODE
}

ensure_coo_shim() {
  local shim_path="$HOME/.local/bin/coo"
  local real_path="$HOME/.local/bin/coo.real"
  local wrapper="$BUILD_REPO/runtime/tools/coo_worktree.sh"
  local current_repo_in_shim=""

  mkdir -p "$HOME/.local/bin"

  if [ ! -L "$real_path" ] || [ "$(readlink -f "$real_path" 2>/dev/null || true)" != "$wrapper" ]; then
    ln -sf "$wrapper" "$real_path"
    echo "SHIM_REAL_INSTALLED=$real_path"
  else
    echo "SHIM_REAL_OK=$real_path"
  fi

  if [ -f "$shim_path" ]; then
    current_repo_in_shim="$(
      sed -n 's/^export LIFEOS_BUILD_REPO=\(.*\)$/\1/p' "$shim_path" | head -n 1 | tr -d '"' | tr -d "'"
    )"
  fi

  if [ ! -f "$shim_path" ] || [ "$current_repo_in_shim" != "$BUILD_REPO" ]; then
    python3 - "$shim_path" "$BUILD_REPO" <<'PY'
import json
import stat
import sys
from pathlib import Path

shim = Path(sys.argv[1])
repo = sys.argv[2]
shim.write_text(
    "#!/usr/bin/env bash\n"
    f"export LIFEOS_BUILD_REPO={json.dumps(repo)}\n"
    'exec "$HOME/.local/bin/coo.real" "$@"\n',
    encoding="utf-8",
)
shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
PY
    echo "SHIM_INSTALLED=$shim_path"
  else
    echo "SHIM_OK=$shim_path"
  fi
}

ensure_windows_launchers() {
  local win_dir="$BUILD_REPO/tools/windows"
  local any_found=0
  local cmd_file basename
  if [ ! -d "$win_dir" ]; then
    echo "WINDOWS_LAUNCHERS_DIR_MISSING=$win_dir"
    return 0
  fi
  for cmd_file in "$win_dir"/*.cmd; do
    [ -f "$cmd_file" ] || continue
    any_found=1
    basename="$(basename "$cmd_file")"
    if grep -q "coo " "$cmd_file" 2>/dev/null; then
      echo "WINDOWS_LAUNCHER_OK=$basename"
    else
      echo "WINDOWS_LAUNCHER_WARN=$basename"
    fi
  done
  if [ "$any_found" -eq 0 ]; then
    echo "WINDOWS_LAUNCHERS_NONE_FOUND=true"
  fi
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

distill_enabled() {
  [ "${LIFEOS_DISTILL_ENABLE}" = "1" ]
}

distill_mode_effective() {
  case "${LIFEOS_DISTILL_MODE}" in
    off|shadow|active) printf '%s\n' "${LIFEOS_DISTILL_MODE}" ;;
    *) printf 'shadow\n' ;;
  esac
}

run_openclaw_maybe_distilled() {
  local wrapper_command="$1"
  local traffic_class="$2"
  local template_id="$3"
  local source_path="$4"
  shift 4

  local mode enabled_flag
  mode="$(distill_mode_effective)"
  if distill_enabled; then
    enabled_flag="--enabled"
  else
    enabled_flag=""
  fi

  if ! distill_enabled; then
    run_openclaw "$@"
    return $?
  fi

  local raw_tmp result_tmp
  raw_tmp="$(mktemp)"
  result_tmp="$(mktemp)"
  local raw_rc
  if run_openclaw "$@" >"$raw_tmp" 2>&1; then
    raw_rc=0
  else
    raw_rc=$?
  fi

  if ! python3 runtime/tools/openclaw_distill_lane.py process \
    --payload-file "$raw_tmp" \
    --source-path "$source_path" \
    --source-executable "openclaw" \
    --argv-json "$(python3 - "$@" <<'PY'
import json
import sys
print(json.dumps(["openclaw", *sys.argv[1:]]))
PY
)" \
    --wrapper-command "$wrapper_command" \
    --traffic-class "$traffic_class" \
    --source-command "$*" \
    --template-id "$template_id" \
    --mode "$mode" \
    ${enabled_flag:+$enabled_flag} \
    --state-dir "$OPENCLAW_STATE_DIR" \
    --openclaw-bin "$OPENCLAW_BIN" \
    --openclaw-profile "$OPENCLAW_PROFILE" >"$result_tmp"; then
    redact_sensitive_stream <"$raw_tmp"
    rm -f "$raw_tmp" "$result_tmp"
    return "$raw_rc"
  fi

  if python3 - "$result_tmp" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
text = payload.get("rendered_text") or ""
if payload.get("replacement_allowed") is True and text.strip():
    print(text)
    raise SystemExit(0)
raise SystemExit(1)
PY
  then
    rm -f "$raw_tmp" "$result_tmp"
    return "$raw_rc"
  fi

  redact_sensitive_stream <"$raw_tmp"
  rm -f "$raw_tmp" "$result_tmp"
  return "$raw_rc"
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
expected = str(obj.get("expected_sandbox_posture") or "").strip()
if expected:
    print(f"GATE_EXPECTED_SANDBOX_POSTURE={expected}")
observed = str(obj.get("observed_sandbox_mode") or "").strip()
if observed:
    print(f"GATE_OBSERVED_SANDBOX_MODE={observed}")
session_sandboxed = obj.get("sandbox_session_is_sandboxed")
if isinstance(session_sandboxed, bool):
    print(f"GATE_SANDBOX_SESSION_IS_SANDBOXED={'true' if session_sandboxed else 'false'}")
elevated_enabled = obj.get("sandbox_elevated_enabled")
if isinstance(elevated_enabled, bool):
    print(f"GATE_SANDBOX_ELEVATED_ENABLED={'true' if elevated_enabled else 'false'}")
reasons = obj.get("blocking_reasons") or []
if isinstance(reasons, list) and reasons:
    print("GATE_BLOCKING_REASONS_BEGIN")
    for reason in reasons:
        print(f"- {reason}")
    print("GATE_BLOCKING_REASONS_END")
PY
}

annotate_gate_breakglass_status() {
  local gate_status_path="$1"
  local used="$2"
  local scope="$3"
  local reasons_csv="${4:-}"
  if [ ! -f "$gate_status_path" ]; then
    return 0
  fi
  python3 - <<'PY' "$gate_status_path" "$used" "$scope" "$reasons_csv"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
used = str(sys.argv[2]).strip().lower() == "true"
scope = str(sys.argv[3] or "").strip() or "policy_drift_only"
raw_reasons = str(sys.argv[4] or "")
reasons = [item for item in raw_reasons.split(",") if item]

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    payload = {}

if not isinstance(payload, dict):
    payload = {}

payload["break_glass_used"] = used
payload["break_glass_scope"] = scope
payload["break_glass_bypass_reasons"] = reasons
path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
PY
}

classify_breakglass_gate_reasons() {
  local gate_status_path="$1"
  local catalog_path="${OPENCLAW_GATE_REASON_CATALOG_PATH:-$BUILD_REPO/config/openclaw/gate_reason_catalog.json}"
  python3 - <<'PY' "$gate_status_path" "$catalog_path"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
catalog_path = Path(sys.argv[2])

if not path.exists():
    print("can_bypass=false")
    print("hard_reasons=gate_status_missing")
    print("bypass_reasons=")
    raise SystemExit(0)

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("can_bypass=false")
    print("hard_reasons=gate_status_parse_error")
    print("bypass_reasons=")
    raise SystemExit(0)

reasons = payload.get("blocking_reasons") or []
if not isinstance(reasons, list):
    reasons = []
reasons = [str(r).strip() for r in reasons if str(r).strip()]

if not catalog_path.exists():
    print("can_bypass=false")
    print("hard_reasons=gate_reason_catalog_failed")
    print("bypass_reasons=")
    raise SystemExit(0)

try:
    catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
except Exception:
    print("can_bypass=false")
    print("hard_reasons=gate_reason_catalog_failed")
    print("bypass_reasons=")
    raise SystemExit(0)

catalog = catalog_payload.get("reasons")
if not isinstance(catalog, dict):
    print("can_bypass=false")
    print("hard_reasons=gate_reason_catalog_failed")
    print("bypass_reasons=")
    raise SystemExit(0)

if not reasons:
    print("can_bypass=false")
    print("hard_reasons=startup_failure_without_gate_reasons")
    print("bypass_reasons=")
    raise SystemExit(0)

bypass = []
hard = []
for reason in reasons:
    meta = catalog.get(reason)
    if not isinstance(meta, dict):
        hard.append("gate_reason_unknown")
        continue
    if bool(meta.get("drift_bypassable", False)):
        bypass.append(reason)
    else:
        hard.append(reason)

can_bypass = bool(bypass) and not hard
print(f"can_bypass={'true' if can_bypass else 'false'}")
print("hard_reasons=" + ",".join(sorted(set(hard))))
print("bypass_reasons=" + ",".join(bypass))
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

openclaw_command_uses_training_dir() {
  if [ "$#" -eq 0 ]; then
    return 1
  fi

  case "$1" in
    security|gateway|sandbox)
      return 1
      ;;
    models)
      if [ "${2:-}" = "status" ] || [ "${2:-}" = "list" ] || [ "${2:-}" = "aliases" ]; then
        return 1
      fi
      ;;
    status)
      return 1
      ;;
    channels)
      if [ "${2:-}" = "status" ]; then
        return 1
      fi
      ;;
    memory)
      if [ "${2:-}" = "status" ]; then
        return 1
      fi
      ;;
  esac

  return 0
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
  python3 -c '
import re
import sys

text = sys.stdin.read()
text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
text = re.sub(r"Authorization\s*:\s*Bearer\s+\S+", "Authorization: Bearer [REDACTED]", text, flags=re.I)
text = re.sub(r"\bxapp-[A-Za-z0-9-]{6,}\b", "xapp-[REDACTED]", text)
text = re.sub(r"\bxox[aboprs]-[A-Za-z0-9-]{6,}\b", "xox?-[REDACTED]", text)
text = re.sub(r"\bsk-or-v1[a-zA-Z0-9._-]{6,}\b", "sk-or-v1[REDACTED]", text)
text = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "sk-[REDACTED]", text)
text = re.sub(r"\bsk-ant-[A-Za-z0-9_-]{8,}\b", "sk-ant-[REDACTED]", text)
text = re.sub(r"\bgh[opurs]_[A-Za-z0-9]{12,}\b", "gh*_[REDACTED]", text)
text = re.sub(r"\bAIza[0-9A-Za-z_-]{10,}\b", "AIza[REDACTED]", text)
text = re.sub(r"\bya29\.[0-9A-Za-z._-]{12,}\b", "ya29.[REDACTED]", text)
text = re.sub(r"[A-Za-z0-9+/_=-]{80,}", "[REDACTED_LONG]", text)
sys.stdout.write(text)
'
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

run_startup_probe_bundle() {
  local quiet_mode="${1:-0}"
  local gateway_mode="${2:-normal}"
  local timeout_sec="${COO_STARTUP_TIMEOUT_SEC:-300}"
  local rc

  set +e
  if [ "$quiet_mode" = "1" ]; then
    timeout "$timeout_sec" bash -s -- "$BUILD_REPO" "$gateway_mode" >/dev/null 2>&1 <<'EOF'
set -euo pipefail
repo="$1"
gateway_mode="$2"
start_failed=0
cd "$repo"
if [ "$gateway_mode" = "check-only" ]; then
  if ! runtime/tools/openclaw_gateway_ensure.sh --check-only; then
    start_failed=1
  fi
else
  if ! runtime/tools/openclaw_gateway_ensure.sh; then
    start_failed=1
  fi
fi
export COO_ENFORCEMENT_MODE=mission
if ! runtime/tools/openclaw_models_preflight.sh; then
  start_failed=1
fi
if ! runtime/tools/openclaw_verify_surface.sh; then
  start_failed=1
fi
exit "$start_failed"
EOF
  else
    timeout "$timeout_sec" bash -s -- "$BUILD_REPO" "$gateway_mode" <<'EOF'
set -euo pipefail
repo="$1"
gateway_mode="$2"
start_failed=0
cd "$repo"
if [ "$gateway_mode" = "check-only" ]; then
  if ! runtime/tools/openclaw_gateway_ensure.sh --check-only; then
    start_failed=1
  fi
else
  if ! runtime/tools/openclaw_gateway_ensure.sh; then
    start_failed=1
  fi
fi
export COO_ENFORCEMENT_MODE=mission
if ! runtime/tools/openclaw_models_preflight.sh; then
  start_failed=1
fi
if ! runtime/tools/openclaw_verify_surface.sh; then
  start_failed=1
fi
exit "$start_failed"
EOF
  fi
  rc="$?"
  set -e
  return "$rc"
}

run_safe_remediation_action() {
  local action_id="$1"
  case "$action_id" in
    gateway.ensure)
      (
        cd "$BUILD_REPO"
        runtime/tools/openclaw_gateway_ensure.sh
      )
      ;;
    models.fix)
      (
        cd "$BUILD_REPO"
        python3 runtime/tools/openclaw_model_ladder_fix.py --config "$OPENCLAW_CONFIG_PATH"
      )
      ;;
    *)
      echo "DOCTOR_UNKNOWN_ACTION=$action_id" >&2
      return 1
      ;;
  esac
}

run_doctor() {
  local json_output="$1"
  local apply_safe_fixes="$2"
  local gate_status_path="${OPENCLAW_GATE_STATUS_PATH:-$OPENCLAW_STATE_DIR/runtime/gates/gate_status.json}"
  local catalog_path="${OPENCLAW_GATE_REASON_CATALOG_PATH:-$BUILD_REPO/config/openclaw/gate_reason_catalog.json}"
  local probe_rc=0
  local rc=0
  local fix_actions_file
  local applied_fixes_file="${COO_DOCTOR_APPLIED_FIXES_FILE:-}"
  local own_applied_file=0
  local emit_initial_output=1

  if [ -z "$applied_fixes_file" ]; then
    applied_fixes_file="$(mktemp)"
    own_applied_file=1
  fi
  fix_actions_file="$(mktemp)"
  if [ "$apply_safe_fixes" -eq 1 ] && [ "$json_output" -eq 1 ]; then
    emit_initial_output=0
  fi

  if run_startup_probe_bundle 1 check-only; then
    probe_rc=0
  else
    probe_rc="$?"
  fi

  python3 - "$gate_status_path" "$catalog_path" "$probe_rc" "$json_output" "$fix_actions_file" "$applied_fixes_file" "${COO_STARTUP_TIMEOUT_SEC:-300}" "$emit_initial_output" <<'PY'
import json
import sys
from pathlib import Path

gate_path = Path(sys.argv[1])
catalog_path = Path(sys.argv[2])
probe_rc = int(sys.argv[3])
emit_json = sys.argv[4] == "1"
fix_actions_path = Path(sys.argv[5])
applied_fixes_path = Path(sys.argv[6])
timeout_sec = sys.argv[7]
emit_output = sys.argv[8] == "1"


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


gate = _load_json(gate_path)
catalog = _load_json(catalog_path).get("reasons", {})
if not isinstance(catalog, dict):
    catalog = {}

blocking = gate.get("blocking_reasons") or []
if not isinstance(blocking, list):
    blocking = []
blocking = [str(reason).strip() for reason in blocking if str(reason).strip()]

if probe_rc != 0 and not blocking:
    if probe_rc == 124:
        blocking = ["startup_probe_timed_out"]
    else:
        blocking = ["startup_probe_failed"]

applied = []
if applied_fixes_path.exists():
    applied = [line.strip() for line in applied_fixes_path.read_text(encoding="utf-8").splitlines() if line.strip()]

evidence = {
    "gate_status_path": str(gate_path),
    "verify_out_dir": gate.get("verify_out_dir"),
    "security_audit_file": gate.get("security_audit_file"),
    "security_audit_deep_exit": gate.get("security_audit_deep_exit"),
    "security_audit_fallback_exit": gate.get("security_audit_fallback_exit"),
    "security_audit_mode": gate.get("security_audit_mode"),
}

synthetic = {
    "startup_probe_timed_out": {
        "severity": "hard",
        "remediation": {
            "auto_fixable": False,
            "action_id": None,
            "fix_command": None,
            "manual_hint": f"Startup health checks exceeded {timeout_sec}s. Run coo doctor again after the underlying gateway or verification issue is resolved.",
        },
    },
    "startup_probe_failed": {
        "severity": "hard",
        "remediation": {
            "auto_fixable": False,
            "action_id": None,
            "fix_command": None,
            "manual_hint": "Startup health checks failed before a classified gate result was available. Re-run coo doctor and inspect the latest runtime gate artifacts.",
        },
    },
}

blockers = []
action_lines = []
seen_actions = set()
for reason in blocking:
    meta = catalog.get(reason) or synthetic.get(reason) or {}
    remediation = meta.get("remediation")
    if not isinstance(remediation, dict):
        remediation = {}
    action_id = remediation.get("action_id")
    fix_command = remediation.get("fix_command")
    blocker = {
        "reason": reason,
        "severity": str(meta.get("severity") or "unknown"),
        "auto_fixable": bool(remediation.get("auto_fixable", False)),
        "action_id": action_id if isinstance(action_id, str) and action_id else None,
        "fix_command": fix_command if isinstance(fix_command, str) and fix_command else None,
        "manual_hint": remediation.get("manual_hint") if isinstance(remediation.get("manual_hint"), str) else None,
    }
    blockers.append(blocker)
    if blocker["auto_fixable"] and blocker["action_id"] and blocker["action_id"] not in seen_actions:
      action_lines.append(f"{blocker['action_id']}|{blocker['fix_command'] or blocker['action_id']}")
      seen_actions.add(blocker["action_id"])

fix_actions_path.write_text("\n".join(action_lines) + ("\n" if action_lines else ""), encoding="utf-8")

status = "ok" if not blockers else "blocked"
payload = {
    "status": status,
    "probe_failed": probe_rc != 0,
    "blockers": blockers,
    "fix_commands_available": [item["fix_command"] for item in blockers if item.get("fix_command")],
    "auto_fixes_applied": applied,
    **evidence,
}

if emit_json and emit_output:
    print(json.dumps(payload, indent=2, sort_keys=True))
elif emit_output:
    print(f"DOCTOR_STATUS={status}")
    print(f"GATE_STATUS_PATH={evidence['gate_status_path']}")
    if isinstance(evidence["verify_out_dir"], str) and evidence["verify_out_dir"]:
        print(f"VERIFY_OUT_DIR={evidence['verify_out_dir']}")
    if isinstance(evidence["security_audit_file"], str) and evidence["security_audit_file"]:
        print(f"SECURITY_AUDIT_FILE={evidence['security_audit_file']}")
    if evidence["security_audit_deep_exit"] is not None:
        print(f"SECURITY_AUDIT_DEEP_EXIT={evidence['security_audit_deep_exit']}")
    if evidence["security_audit_fallback_exit"] is not None:
        print(f"SECURITY_AUDIT_FALLBACK_EXIT={evidence['security_audit_fallback_exit']}")
    if isinstance(evidence["security_audit_mode"], str) and evidence["security_audit_mode"]:
        print(f"SECURITY_AUDIT_MODE={evidence['security_audit_mode']}")
    for blocker in blockers:
        print(f"BLOCKER_REASON={blocker['reason']}")
        print(f"BLOCKER_SEVERITY={blocker['severity']}")
        print(f"BLOCKER_AUTO_FIXABLE={'true' if blocker['auto_fixable'] else 'false'}")
        if blocker["fix_command"]:
            print(f"BLOCKER_FIX_COMMAND={blocker['fix_command']}")
        if blocker["manual_hint"]:
            print(f"BLOCKER_MANUAL_HINT={blocker['manual_hint']}")
    for applied_fix in applied:
        print(f"DOCTOR_AUTO_FIX_APPLIED={applied_fix}")
PY

  if [ "$apply_safe_fixes" -eq 1 ]; then
    while IFS='|' read -r action_id fix_command; do
      [ -n "$action_id" ] || continue
      if [ "$json_output" -eq 0 ]; then
        echo "DOCTOR_APPLYING_FIX=${fix_command:-$action_id}"
      fi
      local _fix_ok=0
      if [ "$json_output" -eq 1 ]; then
        if run_safe_remediation_action "$action_id" >/dev/null; then _fix_ok=1; fi
      else
        if run_safe_remediation_action "$action_id"; then _fix_ok=1; fi
      fi
      if [ "$_fix_ok" -eq 1 ]; then
        printf '%s\n' "${fix_command:-$action_id}" >>"$applied_fixes_file"
      elif [ "$json_output" -eq 0 ]; then
        echo "DOCTOR_FIX_FAILED=${fix_command:-$action_id}"
      fi
    done <"$fix_actions_file"
    rm -f "$fix_actions_file"
    if [ "$json_output" -eq 0 ]; then
      echo "DOCTOR_REPROBE_BEGIN"
    fi
    COO_DOCTOR_APPLIED_FIXES_FILE="$applied_fixes_file" run_doctor "$json_output" 0
    rc="$?"
    if [ "$own_applied_file" -eq 1 ]; then
      rm -f "$applied_fixes_file"
    fi
    return "$rc"
  fi

  rm -f "$fix_actions_file"
  if [ "$own_applied_file" -eq 1 ]; then
    rm -f "$applied_fixes_file"
  fi

  if [ "$probe_rc" -eq 0 ] && [ -f "$gate_status_path" ]; then
    python3 - <<'PY' "$gate_status_path"
import json
import sys
from pathlib import Path

try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)

reasons = payload.get("blocking_reasons") or []
raise SystemExit(0 if not reasons else 1)
PY
    return "$?"
  fi
  return 1
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
  runtime/tools/coo_worktree.sh ensure [--json]
  runtime/tools/coo_worktree.sh doctor [--json] [--apply-safe-fixes]
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
  runtime/tools/coo_worktree.sh telegram {run|status}   # @LifeOSCOOBot Telegram adapter

Enforcement modes:
  - Default startup mode is fail-closed for security/model/posture gates.
  - If startup fails, run 'coo doctor' before using break-glass.
  - Use --unsafe-allow-drift for local emergency bypass of policy drift checks only.
EOF
}

cmd="${1:-}"
case "$cmd" in
  -h|--help|help)
    usage
    ;;
  ensure)
    shift || true
    json_output=0
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --json)
          json_output=1
          shift
          ;;
        *)
          echo "ERROR: unknown ensure argument: $1" >&2
          exit 2
          ;;
      esac
    done
    if [ "$json_output" -eq 0 ]; then
      ensure_worktree
      ensure_openclaw_surface
      ensure_coo_shim
      ensure_windows_launchers
      print_header
    else
      ensure_tmp="$(mktemp)"
      (
        ensure_worktree
        ensure_openclaw_surface
        ensure_coo_shim
        ensure_windows_launchers
        print_header
      ) >"$ensure_tmp"
      python3 - "$ensure_tmp" <<'PY'
import json
import sys
from pathlib import Path

payload = {
    "status": "ok",
    "shim": {},
    "shim_real": {},
    "windows_launchers": [],
}

for raw_line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if "=" not in raw_line:
        continue
    key, value = raw_line.split("=", 1)
    if key == "SHIM_INSTALLED":
        payload["shim"] = {"status": "installed", "path": value}
    elif key == "SHIM_OK":
        payload["shim"] = {"status": "ok", "path": value}
    elif key == "SHIM_REAL_INSTALLED":
        payload["shim_real"] = {"status": "installed", "path": value}
    elif key == "SHIM_REAL_OK":
        payload["shim_real"] = {"status": "ok", "path": value}
    elif key in {"WINDOWS_LAUNCHER_OK", "WINDOWS_LAUNCHER_WARN"}:
        payload["windows_launchers"].append(
            {
                "status": "ok" if key.endswith("_OK") else "warn",
                "name": value,
            }
        )
    elif key == "WINDOWS_LAUNCHERS_DIR_MISSING":
        payload["windows_launchers"].append({"status": "missing_dir", "path": value})
    elif key == "WINDOWS_LAUNCHERS_NONE_FOUND":
        payload["windows_launchers"].append({"status": "none_found"})
    elif key == "BUILD_REPO":
        payload["build_repo"] = value
    elif key == "TRAIN_WT":
        payload["train_worktree"] = value
    elif key == "TRAIN_BRANCH":
        payload["train_branch"] = value
    elif key == "OPENCLAW_PROFILE":
        payload["openclaw_profile"] = value
    elif key == "OPENCLAW_STATE_DIR":
        payload["openclaw_state_dir"] = value
    elif key == "OPENCLAW_CONFIG_PATH":
        payload["openclaw_config_path"] = value
    elif key == "OPENCLAW_POLICY_PHASE":
        payload["openclaw_policy_phase"] = value
    elif key == "OPENCLAW_BIN":
        payload["openclaw_bin"] = value

print(json.dumps(payload, indent=2, sort_keys=True))
PY
      rm -f "$ensure_tmp"
    fi
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
    startup_probe_rc=0
    if run_startup_probe_bundle 0 normal; then
      startup_probe_rc=0
    else
      startup_probe_rc="$?"
      start_failed=1
    fi
    gate_status_path="${OPENCLAW_GATE_STATUS_PATH:-$OPENCLAW_STATE_DIR/runtime/gates/gate_status.json}"
    break_glass_scope="policy_drift_only"
    if [ "$start_failed" -ne 0 ] && [ "$unsafe_allow_drift" -ne 1 ]; then
      annotate_gate_breakglass_status "$gate_status_path" "false" "$break_glass_scope" ""
      emit_gate_blocking_summary
      if [ "$startup_probe_rc" -eq 124 ]; then
        echo "ERROR: startup health checks timed out after ${COO_STARTUP_TIMEOUT_SEC:-300}s." >&2
      fi
      echo "ERROR: startup blocked by fail-closed gate policy." >&2
      echo "NEXT: run 'coo doctor' to diagnose and fix, or re-run with --unsafe-allow-drift for emergency local use only." >&2
      exit 1
    fi
    if [ "$start_failed" -ne 0 ] && [ "$unsafe_allow_drift" -eq 1 ]; then
      classify_lines="$(classify_breakglass_gate_reasons "$gate_status_path")"
      can_bypass="$(printf '%s\n' "$classify_lines" | sed -n 's/^can_bypass=//p' | tail -n 1)"
      hard_reasons="$(printf '%s\n' "$classify_lines" | sed -n 's/^hard_reasons=//p' | tail -n 1)"
      bypass_reasons="$(printf '%s\n' "$classify_lines" | sed -n 's/^bypass_reasons=//p' | tail -n 1)"
      if [ "$can_bypass" = "true" ]; then
        annotate_gate_breakglass_status "$gate_status_path" "true" "$break_glass_scope" "$bypass_reasons"
        emit_gate_blocking_summary
        echo "WARNING: --unsafe-allow-drift bypass active for policy drift checks only." >&2
      else
        annotate_gate_breakglass_status "$gate_status_path" "true" "$break_glass_scope" ""
        emit_gate_blocking_summary
        if [ -n "$hard_reasons" ]; then
          echo "ERROR: --unsafe-allow-drift cannot bypass non-policy gate failures: $hard_reasons" >&2
        else
          echo "ERROR: --unsafe-allow-drift cannot classify gate failures safely; refusing bypass." >&2
        fi
        if [ "$startup_probe_rc" -eq 124 ]; then
          echo "ERROR: startup health checks timed out after ${COO_STARTUP_TIMEOUT_SEC:-300}s." >&2
        fi
        echo "ERROR: startup blocked by fail-closed gate policy." >&2
        echo "NEXT: run 'coo doctor' to diagnose and fix." >&2
        exit 1
      fi
    fi
    if [ "$start_failed" -eq 0 ]; then
      annotate_gate_breakglass_status "$gate_status_path" "false" "$break_glass_scope" ""
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
      python3 runtime/tools/openclaw_model_policy_assert.py --config "$OPENCLAW_CONFIG_PATH" --json || true
      echo "MODEL_POLICY_ASSERT_END"
      echo "CONFIG_PAIR_CHECK_BEGIN"
      _instance_profile="${OPENCLAW_INSTANCE_PROFILE_PATH:-config/openclaw/instance_profiles/coo.json}"
      python3 runtime/tools/openclaw_config_pair_check.py \
        --config "$OPENCLAW_CONFIG_PATH" \
        --instance-profile "$_instance_profile" || true
      echo "CONFIG_PAIR_CHECK_END"
      echo "HINT=Run 'openclaw models status --probe' for deeper provider diagnostics."
    )
    ;;
  doctor)
    shift || true
    json_output=0
    apply_safe_fixes=0
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --json)
          json_output=1
          shift
          ;;
        --apply-safe-fixes)
          apply_safe_fixes=1
          shift
          ;;
        *)
          echo "ERROR: unknown doctor argument: $1" >&2
          exit 2
          ;;
      esac
    done
    ensure_openclaw_surface
    if [ "$json_output" -eq 0 ]; then
      print_header
    fi
    run_doctor "$json_output" "$apply_safe_fixes"
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
          policy_tmp="$(mktemp)"
          if ! python3 runtime/tools/openclaw_model_policy_assert.py --config "$OPENCLAW_CONFIG_PATH" --json >"$policy_tmp"; then
            true
          fi
          python3 - "$policy_tmp" <<'PY'
import json
import sys
from pathlib import Path

try:
    result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
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
        expected = ladder.get("required_prefix", [])
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
          rc="$?"
          rm -f "$policy_tmp"
          exit "$rc"
        )
        ;;
      fix)
        ensure_openclaw_surface
        print_header
        (
          cd "$BUILD_REPO"
          python3 runtime/tools/openclaw_model_ladder_fix.py --config "$OPENCLAW_CONFIG_PATH"
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
    if openclaw_command_uses_training_dir "$@"; then
      enter_training_dir
    else
      cd "$BUILD_REPO"
    fi
    if [ "$#" -ge 2 ] && [ "$1" = "models" ] && [ "$2" = "status" ]; then
      run_openclaw_maybe_distilled "coo openclaw -- models status" "repo_scans" "actionable_faults" "" "$@"
    elif [ "$#" -ge 3 ] && [ "$1" = "status" ] && [ "$2" = "--all" ] && [ "$3" = "--usage" ]; then
      run_openclaw_maybe_distilled "coo openclaw -- status --all --usage" "repo_scans" "actionable_faults" "" "$@"
    else
      run_openclaw "$@"
    fi
    ;;
  telegram)
    shift || true
    subcmd="${1:-}"
    case "$subcmd" in
      run|status) ;;
      *)
        echo "Usage: coo telegram {run|status}" >&2
        exit 2
        ;;
    esac
    _tg_env="$HOME/.config/lifeos/telegram.env"
    if [ ! -f "$_tg_env" ]; then
      echo "ERROR: Telegram env file not found: $_tg_env" >&2
      echo "Expected vars: LIFEOS_COO_TELEGRAM_BOT_TOKEN, LIFEOS_COO_TELEGRAM_ALLOW_FROM" >&2
      exit 1
    fi
    # shellcheck source=/dev/null
    set -a
    if ! . "$_tg_env"; then
      echo "ERROR: Failed to source $_tg_env" >&2
      exit 1
    fi
    set +a
    print_header
    cd "$BUILD_REPO"
    # Use the repo venv if available (it has python-telegram-bot installed);
    # fall back to bare python3 for environments without a venv.
    _tg_python="python3"
    if [ -x "$BUILD_REPO/.venv/bin/python3" ]; then
      _tg_python="$BUILD_REPO/.venv/bin/python3"
    fi
    case "$subcmd" in
      run)
        "$_tg_python" -m runtime.cli coo telegram run
        ;;
      status)
        "$_tg_python" -m runtime.cli coo telegram status "${@:2}"
        ;;
    esac
    ;;
  *)
    usage
    exit 2
    ;;
esac
