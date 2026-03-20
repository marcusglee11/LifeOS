# Review_Packet_COO_Webchat_Gateway_Token_URL_Fix_v1.0

## Mission
Eliminate COO webchat disconnect `1008 unauthorized: gateway token missing` by ensuring COO app launch uses an authenticated dashboard URL that includes the gateway token.

## Scope
- Updated dashboard URL resolution in COO launcher.
- No docs updated.
- No governance/foundation files touched.

## Changed Files
- `runtime/tools/coo_worktree.sh`

## Implementation Summary
1. Added `resolve_gateway_token_from_config()` to read `gateway.auth.token` from `OPENCLAW_CONFIG_PATH` using Python JSON parsing.
2. Updated `resolve_dashboard_url()` flow:
- first try `openclaw dashboard --no-open` and parse `Dashboard URL:`.
- if unavailable, derive authenticated URL as `http://127.0.0.1:${OPENCLAW_GATEWAY_PORT}/#token=<token>` from config.
- if token is unavailable, warn and fall back to unauthenticated URL.
3. `start` and `app` command paths continue using `resolve_dashboard_url()` and therefore now get tokenized URL in fallback mode.

## Verification
- `bash -n runtime/tools/coo_worktree.sh` passed.
- Confirmed token exists at configured path via JSON read (`gateway_token_present=True`).
- In this restricted execution environment, `openclaw dashboard --no-open` and `openclaw_gateway_ensure.sh` are blocked by interface-enumeration confinement (`uv_interface_addresses ...`), so full end-to-end browser launch was not runnable here.

## Operational Use
- Launch webchat with `coo app` (or `bash runtime/tools/coo_worktree.sh app`).
- If required, inspect startup output for `APP_OPENED=...#token=...` or `DASHBOARD_URL=...#token=...`.

## Appendix A: Flattened Changed Code

### `runtime/tools/coo_worktree.sh`
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
  s="$(git -C "$BUILD_REPO" status --porcelain)"
  d="$(git -C "$BUILD_REPO" diff --name-only --diff-filter=U)"
  [ -z "$s" ] && [ -z "$d" ]
}

training_repo_clean() {
  local s d
  s="$(git -C "$TRAIN_WT" status --porcelain)"
  d="$(git -C "$TRAIN_WT" diff --name-only --diff-filter=U)"
  [ -z "$s" ] && [ -z "$d" ]
}

redact_sensitive_stream() {
  sed \
    -e 's/\("botToken"[[:space:]]*:[[:space:]]*"\)[^"]*"/\1[REDACTED]"/g' \
    -e 's/\("token"[[:space:]]*:[[:space:]]*"\)[^"]*"/\1[REDACTED]"/g' \
    -e 's/\("gatewayToken"[[:space:]]*:[[:space:]]*"\)[^"]*"/\1[REDACTED]"/g' \
    -e 's/\("apiKey"[[:space:]]*:[[:space:]]*"\)[^"]*"/\1[REDACTED]"/g' \
    -e 's/\("authorization"[[:space:]]*:[[:space:]]*"\)[^"]*"/\1[REDACTED]"/g' \
    -e 's/\(x-api-key:[[:space:]]*\)[^[:space:]]\+/\1[REDACTED]/Ig' \
    -e 's/\(Authorization:[[:space:]]*Bearer[[:space:]]\)[^[:space:]]\+/\1[REDACTED]/Ig'
}

run_or_warn() {
  local label="$1"
  shift
  if "$@"; then
    return 0
  fi
  local code=$?
  echo "WARN: $label failed (exit $code)" >&2
  return 0
}

run_startup_diagnostics() {
  local diag_root ts out
  diag_root="$OPENCLAW_STATE_DIR/runtime/diagnostics"
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  out="$diag_root/${ts}"
  mkdir -p "$out"

  run_or_warn "gateway health snapshot" run_openclaw health --json >"$out/health.json"
  run_or_warn "gateway status snapshot" run_openclaw status --all --json >"$out/status_all.json"
  run_or_warn "models status snapshot" run_openclaw models status --json >"$out/models_status.json"
  run_or_warn "channels status snapshot" run_openclaw channels status --json >"$out/channels_status.json"
  run_or_warn "memory status snapshot" run_openclaw memory status --json >"$out/memory_status.json"

  echo "DIAG_DIR=$out"
}

usage() {
  cat <<'EOF'
Usage: runtime/tools/coo_worktree.sh <command> [args]

Commands:
  start           Ensure gateway + model preflight from BUILD_REPO
  tui [-- ...]    Start COO TUI in training worktree (auto-starts services)
  app             Start gateway+preflight then open dashboard URL
  stop            Stop local gateway process
  diag            Run runtime diagnostics and print key status
  rebuild         Hard reset training worktree to BUILD_REPO/HEAD
  merge-main      Fast-forward/merge TRAIN_BRANCH -> BUILD_REPO/current branch (requires clean trees)
  close [args...] Run closure gate from BUILD_REPO with any extra args
  train [args...] Run coo autonomous mission in training worktree
  coo [args...]   Alias for train
  status          Show BUILD_REPO/TRAIN_WT status and HEADs

Env:
  OPENCLAW_STATE_DIR   Override OpenClaw state dir (default: ~/.openclaw)
  OPENCLAW_CONFIG_PATH Override OpenClaw config path (default: $OPENCLAW_STATE_DIR/openclaw.json)
  OPENCLAW_GATEWAY_PORT Override gateway port (default: 18789)
  OPENCLAW_PROFILE     Optional OpenClaw profile name (maps to --profile)

Notes:
  - BUILD_REPO is the current repository where this script is executed.
  - TRAIN_WT is a sibling worktree at ../LifeOS__wt_coo_training on branch coo/training.
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
        echo "WARN: models status returned non-zero" >&2
      fi
      rm -f "$status_tmp"
      echo "MODELS_STATUS_END"
      run_startup_diagnostics
    )
    ;;
  rebuild)
    shift || true
    ensure_worktree
    if ! build_repo_clean; then
      echo "ERROR: BUILD_REPO has uncommitted changes. Commit/stash before rebuild." >&2
      exit 3
    fi
    echo "Rebuilding $TRAIN_WT from $BUILD_REPO/HEAD"
    git -C "$BUILD_REPO" worktree remove --force "$TRAIN_WT"
    git -C "$BUILD_REPO" worktree add -B "$TRAIN_BRANCH" "$TRAIN_WT" HEAD
    git -C "$TRAIN_WT" reset --hard HEAD
    git -C "$TRAIN_WT" clean -fdx
    ;;
  merge-main)
    shift || true
    ensure_worktree
    if ! build_repo_clean; then
      echo "ERROR: BUILD_REPO is dirty. Commit/stash first." >&2
      exit 4
    fi
    if ! training_repo_clean; then
      echo "ERROR: TRAIN_WT is dirty. Commit/stash first." >&2
      exit 5
    fi
    current_branch="$(git -C "$BUILD_REPO" rev-parse --abbrev-ref HEAD)"
    echo "Merging $TRAIN_BRANCH into $current_branch"
    git -C "$BUILD_REPO" fetch --all --prune
    git -C "$BUILD_REPO" merge --ff-only "$TRAIN_BRANCH" || git -C "$BUILD_REPO" merge --no-ff "$TRAIN_BRANCH"
    ;;
  close)
    shift || true
    ensure_openclaw_surface
    print_header
    (
      cd "$BUILD_REPO"
      python3 runtime/tools/closure_gate.py --repo-root . "$@"
    )
    ;;
  train|coo)
    shift || true
    ensure_openclaw_surface
    print_header
    "$0" start
    enter_training_dir
    run_openclaw agent coo --session main "$@"
    ;;
  status)
    shift || true
    ensure_worktree
    ensure_openclaw_surface
    print_header
    echo "BUILD_BRANCH=$(git -C "$BUILD_REPO" rev-parse --abbrev-ref HEAD)"
    echo "BUILD_HEAD=$(git -C "$BUILD_REPO" rev-parse --short HEAD)"
    echo "TRAIN_BRANCH_CUR=$(git -C "$TRAIN_WT" rev-parse --abbrev-ref HEAD)"
    echo "TRAIN_HEAD=$(git -C "$TRAIN_WT" rev-parse --short HEAD)"
    echo "BUILD_DIRTY=$(if build_repo_clean; then echo no; else echo yes; fi)"
    echo "TRAIN_DIRTY=$(if training_repo_clean; then echo no; else echo yes; fi)"
    ;;
  *)
    usage
    exit 2
    ;;
esac
```
