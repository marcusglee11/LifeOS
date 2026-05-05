# Cabra Readiness Smoke Report

**Issue:** #108  
**Timestamp:** 2026-05-04T13:24:36Z  
**Branch:** fix/codex-only-ea-dispatch  
**HEAD:** 7729cde490307aa8fd72b949e5d96fec199de712  
**EA:** claude-sonnet-4-6 (Claude Code)

---

## Summary

| Gate | Result | Notes |
|------|--------|-------|
| OpenClaw binary present | **PASS** | `/home/cabra/.local/bin/openclaw` 2026.4.27 (cbc2ba0) |
| OpenClaw gateway reachable | **PASS** | ws://127.0.0.1:18789 · 130ms · running (pid 87737) |
| OpenClaw update pending | **WARN** | 2026.5.3-1 available; current 2026.4.27. Not applying (not approved). |
| Memory backend enabled | **PASS** | plugin memory-core · enabled |
| LifeOS orientation: backlog.yaml | **PASS** | 30 tasks loaded (15 pending, 15 completed) |
| LifeOS orientation: LIFEOS_STATE.md | **PASS** | Accessible, content read |
| LifeOS orientation: delegation_envelope.yaml | **PASS** | schema=delegation_envelope.v1, trust_tier=burn-in |
| LifeOS orientation: dispatch inbox | **PASS** | Accessible; 0 pending orders |
| Active COO registry | **PASS** | openclaw, status=active |
| GitHub auth/bus | **PASS** | marcusglee11 logged in, scopes: gist/read:org/repo |
| GitHub issue #108 readable | **PASS** | state=open, title verified |
| Python runtime | **PASS** | 3.12.3 |
| pytest collection | **PASS** | 3216 tests collected |
| Import: runtime.orchestration.coo.backlog | **PASS** | |
| Import: runtime.orchestration.coo.auto_dispatch | **PASS** | |
| Import: runtime.orchestration.coo.invoke | **PASS** | |
| Import: runtime.gateway.deterministic_call | **PASS** | |
| Import: runtime.config.flags | **PASS** | |
| Import: runtime.config.loader | **PASS** | |
| Auto-dispatch predicates | **PASS** | T-003 eligible, T-009/T-010 ineligible (risk=med) — expected |
| Codex-only dispatch tests | **PASS** | 3/3 passed (test_codex_only_dispatch_policy.py) |
| Auto-dispatch test suite | **PASS** | 29/29 passed (orchestration/coo/test_auto_dispatch.py) |
| Protected artefacts config | **PASS** | config/governance/protected_artefacts.json loaded |
| Policy posture | **PASS** | mode=PRIMARY, allow_posture_loosen=false |
| ZEN_*_KEY env vars present | **FAIL** | No ZEN_BUILDER_KEY, ZEN_STEWARD_KEY, etc. in shell env. Zen API calls would fail at runtime. |
| Provider health file | **FAIL** | artifacts/health/provider_state.json not found — gateway health tracking not initialized |
| Cron inventory | **WARN** | .claude/settings.json crons=[]. No active scheduled tasks. Nightly queue file present (3 tasks) but not triggered. |
| Messaging test | **SKIP** | Not approved — dry-run/readback only. Telegram model config present. |
| OpenClaw restart/update | **SKIP** | Not approved |
| Node service (systemd) | **WARN** | systemd not installed for Node service |

---

## Repeatable Smoke Procedure

Run this from any fresh Cabra/OpenClaw session in the repo root. No network calls, no mutations.

```bash
#!/usr/bin/env bash
# Cabra Readiness Smoke — Issue #108
# Run from: /mnt/c/Users/cabra/Projects/LifeOS
# Requires: Python 3.12+, openclaw in PATH, gh CLI authenticated

set -euo pipefail
REPO_ROOT="/mnt/c/Users/cabra/Projects/LifeOS"
cd "$REPO_ROOT"

echo "=== [1] OpenClaw version ==="
openclaw --version

echo "=== [2] OpenClaw gateway status ==="
openclaw status | grep -E "Gateway|Memory|Agents|Update"

echo "=== [3] Orientation sources ==="
test -f config/tasks/backlog.yaml && echo "PASS: backlog.yaml" || echo "FAIL: backlog.yaml"
test -f docs/11_admin/LIFEOS_STATE.md && echo "PASS: LIFEOS_STATE.md" || echo "FAIL: LIFEOS_STATE.md"
test -f config/governance/delegation_envelope.yaml && echo "PASS: delegation_envelope.yaml" || echo "FAIL: delegation_envelope.yaml"
test -d artifacts/dispatch/inbox && echo "PASS: dispatch inbox dir" || echo "FAIL: dispatch inbox"

echo "=== [4] Active COO ==="
python3 -c "
import yaml
with open('config/governance/active_coo.yaml') as f:
    c = yaml.safe_load(f)
assert c['status'] == 'active' and c['active_coo_id'] == 'openclaw', f'FAIL: {c}'
print('PASS: active_coo =', c['active_coo_id'])
"

echo "=== [5] Delegation envelope ==="
python3 -c "
import yaml
with open('config/governance/delegation_envelope.yaml') as f:
    e = yaml.safe_load(f)
assert e['schema_version'] == 'delegation_envelope.v1', f'FAIL: {e}'
print('PASS: schema =', e['schema_version'], '| trust_tier =', e['trust_tier'])
"

echo "=== [6] Backlog load ==="
python3 -c "
import sys; sys.path.insert(0, '.')
from runtime.orchestration.coo.backlog import load_backlog
from pathlib import Path
tasks = load_backlog(Path('config/tasks/backlog.yaml'))
print(f'PASS: {len(tasks)} tasks loaded')
"

echo "=== [7] GitHub auth ==="
gh auth status --hostname github.com | grep -E "Logged in|Active account"

echo "=== [8] Codex-only dispatch policy tests ==="
python3 -m pytest runtime/tests/test_codex_only_dispatch_policy.py -q --no-header

echo "=== [9] Auto-dispatch tests ==="
python3 -m pytest runtime/tests/orchestration/coo/test_auto_dispatch.py -q --no-header

echo "=== [10] Provider health file check ==="
test -f artifacts/health/provider_state.json \
  && echo "PASS: provider_state.json exists" \
  || echo "WARN: artifacts/health/provider_state.json missing — gateway health not initialized"

echo "=== [11] ZEN key env check ==="
for key in ZEN_BUILDER_KEY ZEN_STEWARD_KEY ZEN_DESIGNER_KEY ZEN_BUILD_CYCLE_KEY ZEN_REVIEWER_KEY; do
  test -n "${!key:-}" && echo "PASS: $key set" || echo "WARN: $key not set"
done

echo "=== SMOKE COMPLETE ==="
```

---

## Pass / Fail / Warn Table (Summary)

| Category | PASS | FAIL | WARN | SKIP |
|----------|------|------|------|------|
| OpenClaw runtime | 2 | 0 | 1 | 0 |
| Orientation sources | 4 | 0 | 0 | 0 |
| Gateway | 1 | 1 | 0 | 0 |
| Memory | 1 | 0 | 0 | 0 |
| GitHub bus | 2 | 0 | 0 | 0 |
| Python/tests | 12 | 0 | 0 | 0 |
| API keys | 0 | 1 | 0 | 0 |
| Cron | 0 | 0 | 1 | 0 |
| Node service | 0 | 0 | 1 | 0 |
| Messaging | 0 | 0 | 0 | 1 |
| Mutations | 0 | 0 | 0 | 3 |
| **TOTALS** | **22** | **2** | **3** | **4** |

**Readiness verdict:** CONDITIONAL PASS — core orientation, runtime, tests, and gateway all pass. Two FAILs (ZEN keys missing, provider health file absent) block Zen API dispatch but not read-only COO session operation. Three WARNs are advisory.
