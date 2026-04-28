# OpenClaw Canary Upgrade Operator Runbook
**Date**: 2026-04-27
**Upgrade**: 2026.4.14 → 2026.4.25
**Canonical**: `artifacts/upgrades/openclaw-20260427/operator-runbook.md`

## Prerequisites

| Requirement | Check |
|---|---|
| Shell access to host | `ssh <host>` |
| Running as user `cabra` | `whoami` |
| OpenClaw CLI accessible | `openclaw --version` |
| LifeOS repo cloned | `ls ~/LifeOS/scripts/upgrade/openclaw-canary-upgrade.sh` |
| Systemd user services | `systemctl --user status openclaw-gateway.service` |
| Maintenance window confirmed | No critical dispatch in flight |
| pnpm available (or npm) | `pnpm --version` |

## Exact Invocation

### Dry-run preview (recommended first)
```bash
cd ~/LifeOS
bash scripts/upgrade/openclaw-canary-upgrade.sh --dry-run
```

Review the output. No changes made.

### Full execution
```bash
cd ~/LifeOS
bash scripts/upgrade/openclaw-canary-upgrade.sh
```

The script is self-contained. It:
1. Runs preflight checks (version, paths, services)
2. Captures pre-upgrade status + logs inside an artifact directory
3. Creates a timestamped backup of `~/.openclaw`
4. Runs `openclaw update --yes --tag 2026.4.25`
5. Verifies the new version
6. Restarts services (gateway, bus watcher)
7. Runs automated smoke tests
8. Prints a PASS/FAIL summary with rollback commands

## Expected Outputs

### Artifact locations

| Artifact | Path |
|---|---|
| Pre-upgrade status | `~/LifeOS/artifacts/upgrades/openclaw-20260427/<TIMESTAMP>/pre-upgrade-status.txt` |
| Pre-upgrade logs | `~/LifeOS/artifacts/upgrades/openclaw-20260427/<TIMESTAMP>/pre-upgrade-logs.txt` |
| Upgrade output | `~/LifeOS/artifacts/upgrades/openclaw-20260427/<TIMESTAMP>/upgrade-output.txt` |
| Smoke test results | `~/LifeOS/artifacts/upgrades/openclaw-20260427/<TIMESTAMP>/smoke-test-results.txt` |
| Summary | `~/LifeOS/artifacts/upgrades/openclaw-20260427/<TIMESTAMP>/SUMMARY.md` |
| Backup | `~/openclaw-upgrade-backups/<TIMESTAMP>/dot-openclaw/` |
| Backup (systemd units) | `~/openclaw-upgrade-backups/<TIMESTAMP>/systemd-user/` |

### Smoke tests (automated)

1. **openclaw status** — CLI responds, channels listed
2. **openclaw health** — Gateway reachable, channels healthy
3. **openclaw doctor** — No fatal warnings (non-interactive)
4. **openclaw cron list** — Cron subsystem alive
5. **openclaw memory index** — Memory store accessible
6. **Log error scan** — ≤ 3 error/fatal level lines in last 200 log entries
7. **Channel: telegram** — Telegram health check passes
8. **Agent invocation (quick)** — Quick agent responds via gateway

### Additional operator checks (manual — run after script completes)

```bash
# Confirm version
openclaw --version

# Check all channels deliver
openclaw status --deep

# Verify agent dispatch works
openclaw agent --agent quick -m "test ping"

# Verify cron/heartbeat timing
openclaw cron list
openclaw system heartbeat

# Verify no channel silent failures
openclaw logs --limit 100 --no-color | grep -iE 'error|fail|warn'
```

## Rollback Procedure

If the upgrade causes issues:

### Step 1: Restore config + state
```bash
# Find the latest backup
ls -lt ~/openclaw-upgrade-backups/

# Restore
LATEST_BACKUP=$(ls -dt ~/openclaw-upgrade-backups/*/ | head -1)
rm -rf ~/.openclaw
cp -a "${LATEST_BACKUP}dot-openclaw" ~/.openclaw
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
```

### Step 2: Downgrade package (if runtime rollback needed)
```bash
pnpm install -g openclaw@2026.4.14
systemctl --user restart openclaw-gateway.service
```

### Step 3: Verify rollback
```bash
openclaw --version   # should show 2026.4.14
openclaw health
openclaw status
openclaw doctor
```

### Step 4: Restore bus watcher (if applicable)
```bash
cp ~/openclaw-upgrade-backups/<TIMESTAMP>/systemd-user/* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user restart openclaw-bus-watcher.service
```

## Risks & Assumptions

### Assumptions
- **Single host** — script is designed for this host only (cabra's WSL2 instance)
- **Non-interactive update** — `--yes` flag assumes no prompts needed during upgrade
- **Tag pinning supported** — `--tag 2026.4.25` works with the installed variant (confirmed with `--dry-run`)
- **pnpm is the package manager** — the install is via pnpm, not npm or git
- **Gateway auto-restarts** — `openclaw update` restarts the gateway; script verifies
- **User-level systemd** — services run under `systemctl --user`

### Risks
| Risk | Mitigation |
|---|---|
| Auth/provider regression | Pre/post status captured; rollback defined |
| Model ID drift | Version-pinned upgrade; rollback to exact old version |
| Config schema drift | `openclaw doctor` catches this post-upgrade |
| Plugin incompatibility | Plugin update sync runs as part of update |
| Channel integration regression | Telegram health check in smoke tests |
| Update takes longer than expected | Default timeout per step is 1200s (20 min) |
| Bus watcher compatibility | Service file backed up; tested independently |

## Single-Host Canary Policy

- Run on ONE host first
- Observe for 5–20 minutes after upgrade completes
- Do NOT combine with unrelated config changes
- If promoted: run script on remaining hosts
- If rolled back: follow rollback procedure, then investigate before retrying

## Files

| File | Purpose |
|---|---|
| `scripts/upgrade/openclaw-canary-upgrade.sh` | Executable upgrade script |
| `artifacts/upgrades/openclaw-20260427/operator-runbook.md` | This document |