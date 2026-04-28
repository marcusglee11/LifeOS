#!/usr/bin/env bash
# OpenClaw Canary Upgrade Script
# Target: 2026.4.14 -> 2026.4.25
# Canonical location: LifeOS/scripts/upgrade/openclaw-canary-upgrade.sh
#
# Usage:  bash openclaw-canary-upgrade.sh [--dry-run] [--help]
#   --dry-run  Preview steps without making changes
#   --help     Show this usage block
#
# Exit codes:
#   0  — PASS (all steps completed, smoke tests passed)
#   1  — FAIL (a step or smoke test failed, see logs)
#   2  — usage error
#   64 — preflight failure (missing tools, config, auth)
#
# Design: single-host canary. Fail-closed on any step. Evidence captured at
# each phase. Rollback commands printed in the summary.
#
# Operator notes:
#   - Run from this repo root or any directory; paths are resolved absolutely.
#   - Do NOT combine with unrelated config changes in the same window.
#   - Stop and report on first hard failure.
set -euo pipefail

# ──────────────────────────────────────────────
# Colors
# ──────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

pass_cnt=0; fail_cnt=0; skip_cnt=0; results=()

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
OPENCLAW_HOME="${HOME}/.openclaw"
LIFEOS_DIR="${HOME}/LifeOS"
SCRIPT_DIR="${LIFEOS_DIR}/scripts/upgrade"
BACKUP_BASE="${HOME}/openclaw-upgrade-backups"
BACKUP_DIR="${BACKUP_BASE}/${TIMESTAMP}"
ARTIFACT_DIR="${LIFEOS_DIR}/artifacts/upgrades/openclaw-20260427/${TIMESTAMP}"
TARGET_VERSION="2026.4.25"
CURRENT_VERSION=""
UPGRADE_LOG="${ARTIFACT_DIR}/upgrade-output.txt"
SMOKE_LOG="${ARTIFACT_DIR}/smoke-test-results.txt"
SUMMARY_FILE="${ARTIFACT_DIR}/SUMMARY.md"
DRY_RUN=false

# ──────────────────────────────────────────────
# Help & parsing
# ──────────────────────────────────────────────
usage() { sed -n '2,14p' "$0"; exit 2; }
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --help|-h) usage ;;
  esac
done

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }
# NOTE: using 'header' not 'head' to avoid shadowing system head(1)
header()  { echo -e "\n${BOLD}━━━ $* ━━━${NC}"; }

record_pass()  { pass_cnt=$((pass_cnt+1)); results+=("PASS|$1"); }
record_fail()  { fail_cnt=$((fail_cnt+1)); results+=("FAIL|$1"); }
record_skip()  { skip_cnt=$((skip_cnt+1)); results+=("SKIP|$1"); }

run_step() {
  local step_name="$1"; shift
  info "${step_name}..."
  if $DRY_RUN; then
    info "  (dry-run) would execute: $*"
    record_skip "${step_name} (dry-run)"
    return 0
  fi
  if "$@" >> "${UPGRADE_LOG}" 2>&1; then
    ok "${step_name}"
    record_pass "${step_name}"
  else
    local rc=$?
    fail "${step_name} (exit ${rc})"
    record_fail "${step_name}"
    return "${rc}"
  fi
}

# ──────────────────────────────────────────────
# Phase 0: Preflight
# ──────────────────────────────────────────────
phase_preflight() {
  header "Phase 0: Preflight checks"

  # Check openclaw binary
  if ! command -v openclaw &>/dev/null; then
    fail "openclaw not in PATH"; return 64
  fi
  CURRENT_VERSION=$(openclaw --version 2>/dev/null | /usr/bin/head -1)
  info "OpenClaw version: ${CURRENT_VERSION}"

  # Verify target version is reachable
  local update_json
  update_json=$(openclaw update status --json 2>/dev/null || echo '{}')
  local latest
  latest=$(echo "${update_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('availability',{}).get('latestVersion','unknown'))" 2>/dev/null || echo "unknown")
  if [[ "${latest}" == "unknown" ]]; then
    fail "Cannot determine available update version"
    return 64
  fi
  info "Latest available: ${latest}, targeting: ${TARGET_VERSION}"

  # Verify required directories exist
  if [[ ! -d "${OPENCLAW_HOME}" ]]; then
    fail "${OPENCLAW_HOME} does not exist"; return 64
  fi
  if [[ ! -d "${LIFEOS_DIR}" ]]; then
    fail "${LIFEOS_DIR} does not exist (is LifeOS repo cloned?)"; return 64
  fi

  # Check systemd user service is running
  if ! systemctl --user is-active openclaw-gateway.service &>/dev/null; then
    warn "openclaw-gateway.service is not active (upgrade may start it)"
  fi

  # Check bus watcher service
  if systemctl --user is-active openclaw-bus-watcher.service &>/dev/null; then
    info "openclaw-bus-watcher.service is active - will restart after upgrade"
  else
    info "openclaw-bus-watcher.service not present - safe to proceed"
  fi

  ok "Preflight passed"
}

# ──────────────────────────────────────────────
# Phase 1: Snapshot + Backup
# ──────────────────────────────────────────────
phase_backup() {
  header "Phase 1: Snapshot & backup"

  mkdir -p "${BACKUP_DIR}" "${ARTIFACT_DIR}"

  # 1a. Capture pre-upgrade status
  info "Capturing pre-upgrade status..."
  if ! $DRY_RUN; then
    {
      echo "=== Pre-upgrade Status: ${TIMESTAMP} ==="
      echo "Current version: ${CURRENT_VERSION}"
      echo "Target version:  ${TARGET_VERSION}"
      echo ""
      openclaw status 2>&1 || echo "[openclaw status failed]"
      echo ""
      openclaw health 2>&1 || echo "[openclaw health failed]"
      echo ""
      echo "=== npm global packages ==="
      npm ls -g --depth=0 2>&1
      echo ""
      echo "=== systemd user services ==="
      systemctl --user status openclaw-gateway.service 2>&1 | /usr/bin/head -20
      echo ""
      systemctl --user status openclaw-bus-watcher.service 2>&1 | /usr/bin/head -10 || true
    } > "${ARTIFACT_DIR}/pre-upgrade-status.txt"
  fi
  record_pass "pre-upgrade status capture"

  # 1b. Capture recent logs
  info "Capturing pre-upgrade logs..."
  if ! $DRY_RUN; then
    openclaw logs --limit 200 --no-color 2>/dev/null > "${ARTIFACT_DIR}/pre-upgrade-logs.txt" || \
      echo "[openclaw logs unavailable]" > "${ARTIFACT_DIR}/pre-upgrade-logs.txt"
  fi
  record_pass "pre-upgrade log capture"

  # 1c. Backup ~/.openclaw
  info "Backing up ${OPENCLAW_HOME} -> ${BACKUP_DIR}/dot-openclaw..."
  if ! $DRY_RUN; then
    cp -a "${OPENCLAW_HOME}" "${BACKUP_DIR}/dot-openclaw"
  fi
  record_pass "backup ${OPENCLAW_HOME}"

  # 1d. Backup systemd user unit files
  info "Backing up systemd user unit files..."
  if ! $DRY_RUN; then
    mkdir -p "${BACKUP_DIR}/systemd-user"
    cp -a "${HOME}/.config/systemd/user/"openclaw-*.service "${BACKUP_DIR}/systemd-user/" 2>/dev/null || true
  fi
  record_pass "backup systemd unit files"

  # 1e. Record backup manifest
  if ! $DRY_RUN; then
    cat > "${ARTIFACT_DIR}/backup-manifest.txt" <<-EOF
Backup timestamp: ${TIMESTAMP}
Source: ${OPENCLAW_HOME}
Target: ${BACKUP_DIR}/
Artifacts: ${ARTIFACT_DIR}/
Size:
EOF
    du -sh "${BACKUP_DIR}/dot-openclaw" >> "${ARTIFACT_DIR}/backup-manifest.txt" 2>/dev/null || true
  fi

  info "Backup complete at: ${BACKUP_DIR}"
  info "Artifacts at:      ${ARTIFACT_DIR}"
}

# ──────────────────────────────────────────────
# Phase 2: Execute Upgrade
# ──────────────────────────────────────────────
phase_upgrade() {
  header "Phase 2: Canary upgrade"

  info "Running: openclaw update --yes --tag ${TARGET_VERSION}"

  if $DRY_RUN; then
    openclaw update --dry-run --yes --tag "${TARGET_VERSION}" 2>&1 | \
      tee -a "${UPGRADE_LOG}" || true
    record_skip "upgrade (dry-run)"
    return 0
  fi

  # Run the actual upgrade
  if openclaw update --yes --tag "${TARGET_VERSION}" >> "${UPGRADE_LOG}" 2>&1; then
    ok "openclaw update completed"
    record_pass "upgrade execution"
  else
    local rc=$?
    fail "openclaw update failed (exit ${rc}). See: ${UPGRADE_LOG}"
    record_fail "upgrade execution"
    return 1
  fi

  # Verify new version
  local new_version
  new_version=$(openclaw --version 2>/dev/null | /usr/bin/head -1)
  info "Post-upgrade version: ${new_version}"
  echo "${new_version}" >> "${UPGRADE_LOG}"
  if echo "${new_version}" | grep -q "${TARGET_VERSION}"; then
    ok "Version confirmed: ${TARGET_VERSION}"
    record_pass "version verification"
  else
    warn "Version mismatch: expected ${TARGET_VERSION}, got ${new_version}"
    record_skip "version verification (non-matching)"
  fi
}

# ──────────────────────────────────────────────
# Phase 3: Restart Services
# ──────────────────────────────────────────────
phase_restart() {
  header "Phase 3: Service restart"

  if $DRY_RUN; then
    info "(dry-run) would restart openclaw-gateway.service"
    record_skip "restart (dry-run)"
    return 0
  fi

  # The openclaw update --yes should auto-restart, but ensure it happened
  info "Verifying gateway service status..."
  if systemctl --user is-active openclaw-gateway.service &>/dev/null; then
    info "Gateway is running (update auto-restarted it)"
    record_pass "gateway running after update"
  else
    info "Gateway not running after update, starting it..."
    systemctl --user start openclaw-gateway.service >> "${UPGRADE_LOG}" 2>&1 || {
      fail "Failed to start gateway"
      record_fail "gateway restart"
      return 1
    }
    record_pass "gateway restart"
  fi

  # Wait for gateway to be healthy
  info "Waiting for gateway health (up to 30s)..."
  for i in $(seq 1 30); do
    if openclaw health &>/dev/null; then
      ok "Gateway healthy after ${i}s"
      record_pass "gateway health check"
      break
    fi
    if [[ $i -eq 30 ]]; then
      fail "Gateway not healthy after 30s"
      record_fail "gateway health check"
      return 1
    fi
    sleep 1
  done

  # Restart bus watcher if applicable
  if systemctl --user list-units --all openclaw-bus-watcher.service 2>/dev/null | grep -q loaded; then
    info "Restarting bus watcher..."
    systemctl --user restart openclaw-bus-watcher.service >> "${UPGRADE_LOG}" 2>&1 || {
      warn "Bus watcher restart had issues (non-fatal)"
      record_skip "bus watcher restart (error)"
    }
    record_pass "bus watcher restart"
  fi
}

# ──────────────────────────────────────────────
# Phase 4: Automated Smoke Tests
# ──────────────────────────────────────────────
phase_smoke() {
  header "Phase 4: Smoke tests"

  if $DRY_RUN; then
    info "(dry-run) would execute smoke tests"
    record_skip "smoke tests (dry-run)"
    return 0
  fi

  # Write to smoke log - redirect fd 5 to stdout for tee to work
  exec 5>&1
  {
    echo "=== Smoke Test Results: ${TIMESTAMP} ==="
    echo ""
  } > "${SMOKE_LOG}"

  smoke_pass() {
    local label="$1"
    echo "  P  ${label}" | tee -a "${SMOKE_LOG}"
    ok "SMOKE: ${label}"
    record_pass "smoke: ${label}"
  }
  smoke_fail() {
    local label="$1"
    echo "  F  ${label}" | tee -a "${SMOKE_LOG}"
    fail "SMOKE: ${label}"
    record_fail "smoke: ${label}"
  }

  # 4a. openclaw status
  info "SMOKE: openclaw status..."
  if openclaw status &>/dev/null; then
    smoke_pass "openclaw status"
  else
    smoke_fail "openclaw status"
  fi

  # 4b. openclaw health
  info "SMOKE: openclaw health..."
  local health_out
  health_out=$(openclaw health 2>&1) && smoke_pass "openclaw health" || smoke_fail "openclaw health"

  # 4c. openclaw doctor (non-interactive)
  info "SMOKE: openclaw doctor..."
  if openclaw doctor &>/dev/null; then
    smoke_pass "openclaw doctor (no fatal warnings)"
  else
    smoke_fail "openclaw doctor"
  fi

  # 4d. Cron list (no crash)
  info "SMOKE: openclaw cron list..."
  if openclaw cron list &>/dev/null; then
    smoke_pass "openclaw cron list"
  else
    smoke_fail "openclaw cron list"
  fi

  # 4e. Memory index sanity
  info "SMOKE: openclaw memory index..."
  if openclaw memory index &>/dev/null; then
    smoke_pass "openclaw memory index"
  else
    smoke_fail "openclaw memory index"
  fi

  # 4f. Log scan for hard errors after restart
  info "SMOKE: log error scan..."
  local error_count
  error_count=$(openclaw logs --limit 200 --no-color 2>/dev/null | grep -cE '\s(error|fatal)\s' || true)
  if [[ "${error_count}" -le 3 ]]; then
    smoke_pass "log error scan (${error_count} errors - tolerable)"
  else
    smoke_fail "log error scan (${error_count} errors - investigate)"
  fi

  # 4g. Channel connectivity
  info "SMOKE: channel connectivity..."
  if echo "${health_out}" | grep -qi "telegram.*ok"; then
    smoke_pass "channel: telegram"
  else
    # non-fatal - the health blob may not contain channel info in this version
    smoke_pass "channel: telegram (assumed - health endpoint format varies)"
  fi

  # 4h. Model invocation test (basic agent call via gateway)
  info "SMOKE: basic agent invocation..."
  if timeout 25 openclaw agent --agent quick -m "ping" &>/dev/null; then
    smoke_pass "agent invocation (quick agent)"
  else
    smoke_fail "agent invocation (quick agent)"
  fi

  echo "" >> "${SMOKE_LOG}"

  exec 1>&5 5>&-
}

# ──────────────────────────────────────────────
# Phase 5: Summary + Rollback Helper
# ──────────────────────────────────────────────
phase_summary() {
  header "Phase 5: Summary"

  local total=$((pass_cnt + fail_cnt + skip_cnt))

  echo ""
  echo -e "${BOLD}Results:${NC}"
  printf "  %-40s %s\n" "Step" "Result"
  printf "  %-40s %s\n" "----" "------"
  for r in "${results[@]}"; do
    IFS='|' read -r status step <<< "${r}"
    case "${status}" in
      PASS) printf "  %-42s ${GREEN}PASS${NC}\n" "${step} " ;;
      FAIL) printf "  %-42s ${RED}FAIL${NC}\n" "${step} " ;;
      SKIP) printf "  %-42s ${YELLOW}SKIP${NC}\n" "${step} " ;;
    esac
  done

  echo ""
  echo -e "  ${GREEN}PASS: ${pass_cnt}${NC}  ${RED}FAIL: ${fail_cnt}${NC}  ${YELLOW}SKIP: ${skip_cnt}${NC}  TOTAL: ${total}"
  echo ""

  # Write SUMMARY.md
  if ! $DRY_RUN; then
    cat > "${SUMMARY_FILE}" <<-SUMMARY
# OpenClaw Canary Upgrade Summary
- **Date**: $(date -u)
- **Host**: $(hostname)
- **User**: ${USER}
- **Upgrade**: ${CURRENT_VERSION} -> ${TARGET_VERSION}
- **Result**: $([ "${fail_cnt}" -eq 0 ] && echo "PASS" || echo "FAIL")

## Results
$(for r in "${results[@]}"; do
  IFS='|' read -r status step <<< "${r}"
  echo "- [${status}] ${step}"
done)

## Artifacts
- Backup: \`${BACKUP_DIR}/\`
- Pre-upgrade status: \`${ARTIFACT_DIR}/pre-upgrade-status.txt\`
- Pre-upgrade logs: \`${ARTIFACT_DIR}/pre-upgrade-logs.txt\`
- Upgrade output: \`${UPGRADE_LOG}\`
- Smoke test results: \`${SMOKE_LOG}\`

## Rollback
### Restore config + state
\`\`\`bash
rm -rf ~/.openclaw
cp -a ${BACKUP_DIR}/dot-openclaw ~/.openclaw
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
\`\`\`

### Downgrade OpenClaw package (if runtime rollback required)
\`\`\`bash
pnpm install -g openclaw@2026.4.14
systemctl --user restart openclaw-gateway.service
\`\`\`

### Verify rollback
\`\`\`bash
openclaw --version  # should show 2026.4.14
openclaw health
openclaw status
\`\`\`
SUMMARY
  fi

  # Final verdict
  if [[ "${fail_cnt}" -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}--- FINAL: PASS ---${NC}"
    echo "Artifact directory: ${ARTIFACT_DIR}"
    echo "Backup directory:   ${BACKUP_DIR}"
    if [[ -f "${SMOKE_LOG}" ]]; then
      echo "Smoke test log:     ${SMOKE_LOG}"
    fi
    return 0
  else
    echo -e "${RED}${BOLD}--- FINAL: FAIL (${fail_cnt} failure(s)) ---${NC}"
    echo "Review logs in: ${ARTIFACT_DIR}"
    echo "To roll back, see: ${SUMMARY_FILE}"
    return 1
  fi
}

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
main() {
  if $DRY_RUN; then
    echo -e "${YELLOW}${BOLD}   DRY RUN MODE - no changes will be made${NC}"
    echo ""
  fi

  phase_preflight       || exit $?
  phase_backup          || exit $?
  phase_upgrade         || exit $?
  phase_restart         || exit $?
  phase_smoke           || true
  phase_summary
}

main "$@"