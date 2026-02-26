# GitHub Actions Feasibility Report for LifeOS Build Loop

**Generated:** 2026-02-26
**Scope:** Investigation of 7 existing workflows for build loop integration
**Repository:** Public, owner type User, visibility public
**Branch:** build/multi-provider-dispatch (investigation only, no code changes)

---

## 1. Current Workflow Inventory

| # | Workflow File | Display Name | Trigger(s) | Runner(s) | Jobs | Estimated Runtime |
|---|---|---|---|---|---|---|
| 1 | `ci.yml` | LifeOS CI | push (main, develop), pull_request | ubuntu-latest | `test` (matrix 3.11/3.12), `lint`, `docs`, `validate` | ~90s (observed 01:14:53 to 01:16:23 = 90s wall clock) |
| 2 | `opencode_ci.yml` | OpenCode CI Integration | workflow_dispatch only | ubuntu-latest | `validate-agent-commit` | Unknown (manual only, requires OPENROUTER_API_KEY) |
| 3 | `phase1_autonomy_nightly.yml` | Phase 1 Autonomy - Nightly Doc Hygiene | cron `0 20 * * *` (8 PM UTC daily), workflow_dispatch | ubuntu-latest | `doc-hygiene-autonomous` | Failing immediately (0s wall clock since 2026-02-19) |
| 4 | `recursive_kernel_nightly.yml` | Nightly Full Test Suite | cron `0 3 * * *` (3 AM UTC daily), workflow_dispatch | ubuntu-latest | `full-test`, `coverage-report` | ~90s (observed ~80-90s) -- **failing consistently** |
| 5 | `branch_housekeeping_delete_merged_validator_suite.yml` | Branch Housekeeping Delete Merged Validator Suite | cron `19 3 * * *` (3:19 AM UTC daily), workflow_dispatch | ubuntu-latest | `delete-merged-validator-suite` | ~11s (observed) |
| 6 | `tool_invoke_hardening.yml` | Tool Invoke Hardening CI | push (paths: runtime/tools/**, governance, tests), pull_request (same paths), workflow_dispatch | ubuntu-latest + windows-latest | `test-linux`, `test-windows` | ~60s (observed) |
| 7 | `validate-governance-index.yml` | Validate Governance Index | pull_request (paths: docs/01_governance/**, tools/validate_governance_index.py, self) | ubuntu-latest | `validate` | <30s (lightweight, no pip install of full deps) |

### Health Status Summary

- **Healthy (green):** ci.yml, branch_housekeeping, tool_invoke_hardening, validate-governance-index
- **Consistently failing:** recursive_kernel_nightly.yml (8+ consecutive failures, runs 68-72 all red)
- **Broken/stalled:** phase1_autonomy_nightly.yml (instant failure since 2026-02-19, likely disabled/errored at workflow level)
- **Untested in CI:** opencode_ci.yml (manual-only, depends on external API key)

---

## 2. Missing Secrets/Tokens Needed for Build Loop

### Currently Referenced Secrets

| Secret | Used By | Purpose | Status |
|---|---|---|---|
| `GITHUB_TOKEN` | opencode_ci.yml (checkout) | Standard token for repo operations | Auto-provided by Actions |
| `OPENROUTER_API_KEY` | opencode_ci.yml | OpenRouter API access for agent model calls | **Must be manually configured** |

### Secrets Required for Build Loop Integration

| Secret | Needed For | Priority |
|---|---|---|
| `OPENROUTER_API_KEY` | Any workflow that invokes LLM models (build loop agent calls) | **P0 -- required** |
| `ANTHROPIC_API_KEY` | If build loop uses Claude directly (not via OpenRouter) | P1 -- depends on dispatch architecture |
| PAT with `contents:write` | Phase 1 Autonomy auto-commit (currently uses GITHUB_TOKEN which cannot trigger further workflows) | P1 -- see Section 7 |

### Current Secret Configuration

The repository secrets list returned empty. Either no secrets are configured, or the querying token lacks admin-level `secrets:read` permission. **Action needed:** verify via GitHub Settings > Secrets and Variables > Actions.

---

## 3. Actions Minutes/Billing Assessment

### Billing Context

- **Repository visibility:** Public
- **Owner type:** User (personal account)
- **Key fact:** GitHub Actions is **free and unlimited** for public repositories on all plan tiers

### Current Consumption Estimate (per month)

| Workflow | Trigger Frequency | Est. Minutes/Run | Monthly Runs | Monthly Minutes |
|---|---|---|---|---|
| ci.yml | ~10-20 pushes/PRs per week | 3 min (2 matrix + lint + docs + validate) | ~60-80 | ~180-240 |
| recursive_kernel_nightly | Daily | 2 min (2 jobs) | 30 | ~60 |
| branch_housekeeping | Daily | <1 min | 30 | ~15 |
| phase1_autonomy_nightly | Daily (broken) | <1 min (instant fail) | 30 | ~5 |
| tool_invoke_hardening | Path-triggered (~5/week) | 2 min (linux + windows) | ~20 | ~40 |
| validate-governance-index | PR-triggered (~2/week) | <1 min | ~8 | ~4 |
| opencode_ci | Manual only | 2 min | ~2 | ~4 |
| **Total** | | | **~180-200** | **~310-370** |

### Build Loop Addition Impact

A build loop workflow would add:
- If **nightly:** +2-5 min/day = ~60-150 min/month
- If **per-push on main:** +2-5 min per merge = ~40-100 min/month
- If **agent-driven with LLM calls:** runtime depends on model response latency, could be 5-15 min/run

**Assessment:** No billing concern. Public repos get unlimited free minutes on ubuntu-latest. The windows-latest runner in tool_invoke_hardening is also free for public repos. No cost blockers exist.

---

## 4. Runtime Dependencies

### Python Versions

| Workflow | Python Version(s) |
|---|---|
| ci.yml (test job) | 3.11, 3.12 (matrix) |
| ci.yml (docs, validate) | 3.11 |
| opencode_ci.yml | 3.11 |
| phase1_autonomy_nightly.yml | 3.11 |
| recursive_kernel_nightly.yml | 3.11 |
| tool_invoke_hardening.yml | 3.11 |
| validate-governance-index.yml | 3.11 |

**Observation:** All workflows standardize on 3.11. Only ci.yml also tests 3.12. Build loop should target 3.11 as the primary runtime.

### pip Dependencies

| Dependency Set | Installed By | Contents |
|---|---|---|
| `requirements.txt` | Most workflows | pyyaml, httpx, requests, jsonschema, pytest, types-PyYAML |
| `requirements-dev.txt` | ci.yml, recursive_kernel, tool_invoke | Adds pytest-asyncio, pytest-cov on top of requirements.txt |
| `pyyaml` alone | ci.yml validate job | Minimal install for governance validator |

### System Packages (apt)

| Package | Used By | Purpose |
|---|---|---|
| `ripgrep` | ci.yml (test + docs jobs) | Policy constant enforcement grep, doc validation |
| `markdownlint-cli` (npm) | ci.yml (test job), phase1_autonomy_nightly | Markdown linting |

### Node.js

| Version | Used By | Purpose |
|---|---|---|
| Node 20 | ci.yml (lint job) | Biome linter |
| Node 20 | opencode_ci.yml | opencode-ai npm package |
| Implicit (actions/github-script) | branch_housekeeping, phase1_autonomy | GitHub Script action (bundled) |

### Build Loop Implications

A build loop workflow would need:
- Python 3.11
- `requirements-dev.txt` (includes pytest for validation steps)
- `ripgrep` (if running policy assertions)
- Possibly `markdownlint-cli` (if doc hygiene is part of loop)
- **No exotic dependencies** -- everything is standard Ubuntu apt/pip/npm

---

## 5. Cron Schedule Blockers

### Current Cron Schedule Map (UTC)

| Time (UTC) | Workflow | What It Does |
|---|---|---|
| 20:00 | phase1_autonomy_nightly | Doc hygiene + auto-commit + issue creation |
| 03:00 | recursive_kernel_nightly | Full test suite + coverage |
| 03:19 | branch_housekeeping | Delete merged validator-suite branches |

### Conflicts and Blockers

1. **03:00 and 03:19 overlap window:** The nightly test suite (03:00) and branch housekeeping (03:19) run within 19 minutes of each other. If the nightly suite takes longer than 19 minutes, both could be active simultaneously. Currently not a problem (nightly finishes in ~90s), but a build loop scheduled near this window would increase contention.

2. **Phase 1 Autonomy at 20:00 UTC pushes to main:** This workflow commits and pushes directly to main, which would trigger ci.yml. If a build loop also pushes to main, there is a potential for race conditions on main HEAD. **This is the most significant cron blocker for build loop integration.**

3. **GitHub cron jitter:** GitHub Actions cron triggers can be delayed up to 15 minutes during high-load periods. Scheduling a build loop "after" another workflow based on cron time alone is unreliable.

4. **No concurrency guards:** None of the 7 workflows use GitHub's `concurrency` key (confirmed by grep). Multiple instances of the same workflow can run simultaneously. This is a gap that must be addressed before adding a build loop.

### Recommendations

- Schedule build loop outside the 03:00-03:30 and 19:45-20:15 UTC windows
- Add `concurrency` groups to prevent overlapping runs (see Section 6)
- Consider converting phase1_autonomy from cron to workflow_call triggered after build loop completes

---

## 6. Concurrency Group Needs

### Current State

**No concurrency configuration exists in any workflow.** This was confirmed by grep across all 7 workflow files.

### Risk Assessment

| Scenario | Risk | Impact |
|---|---|---|
| Two ci.yml runs on rapid pushes | Low -- test-only, no writes | Wasted minutes, confusing status checks |
| Two phase1_autonomy runs | **High** -- both commit/push to main | Race condition, force-push conflicts, diverged HEAD |
| Build loop + phase1_autonomy | **Critical** -- both modify main | Merge conflicts, corrupted state, duplicate commits |
| Build loop + nightly tests | Low -- nightly is read-only | No conflict, but confusing if both report different states |

### Recommended Concurrency Groups

```yaml
# For ci.yml -- cancel previous on same branch
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

# For phase1_autonomy_nightly -- single instance only
concurrency:
  group: nightly-doc-hygiene
  cancel-in-progress: false

# For build loop -- exclusive lock, never cancel
concurrency:
  group: build-loop
  cancel-in-progress: false

# For any workflow that writes to main
concurrency:
  group: main-writer
  cancel-in-progress: false
```

### Run-Lock vs Actions Concurrency

The LifeOS build loop currently uses a local run-lock mechanism (file-based locking in the spine). In GitHub Actions, this translates to:

- **Actions `concurrency` key:** Native, reliable, zero-config. Queues or cancels runs. **Recommended for all CI workflows.**
- **File-based run-lock:** Would require persisting lock state to an artifact or branch. Fragile in a stateless CI environment. **Not recommended for Actions.**
- **Hybrid approach:** Use Actions concurrency for workflow-level exclusion; use the existing run-lock within a single workflow run for intra-step coordination. This is the pragmatic path.

---

## 7. Permissions Model

### Current Permissions Usage

| Workflow | Explicit Permissions | Token Used | Writes To |
|---|---|---|---|
| ci.yml | None declared (defaults) | Implicit GITHUB_TOKEN | Nothing (read-only) |
| opencode_ci.yml | `contents: write` | `secrets.GITHUB_TOKEN` | Local commit only (no push) |
| phase1_autonomy_nightly.yml | `contents: write`, `issues: write` | Implicit GITHUB_TOKEN | Pushes to main, creates issues |
| recursive_kernel_nightly.yml | None declared | Implicit GITHUB_TOKEN | Nothing (read-only) |
| branch_housekeeping | `contents: write` | Implicit GITHUB_TOKEN | Deletes branches via API |
| tool_invoke_hardening.yml | None declared | Implicit GITHUB_TOKEN | Nothing (read-only) |
| validate-governance-index.yml | None declared | Implicit GITHUB_TOKEN | Nothing (read-only) |

### PAT vs GitHub App vs GITHUB_TOKEN Analysis

| Option | Pros | Cons | Fit for Build Loop |
|---|---|---|---|
| **GITHUB_TOKEN** (default) | Zero config, auto-scoped, auto-rotated | Cannot trigger other workflows (pushes from GITHUB_TOKEN do not fire `on: push`), limited to repo scope | **Insufficient** if build loop push needs to trigger ci.yml |
| **Personal Access Token (PAT)** | Pushes trigger workflows, simple to set up | Tied to personal account, broad scope, manual rotation, security risk if leaked | **Acceptable for solo project**, not ideal long-term |
| **GitHub App** | Fine-grained permissions, pushes trigger workflows, auto-rotation, not tied to personal account | More complex setup (create App, install, manage), overkill for single-user repo | **Best practice** but likely over-engineered for current scale |

### Key Issue: GITHUB_TOKEN Workflow Trigger Limitation

Phase 1 Autonomy pushes to main using GITHUB_TOKEN. These pushes **do not** trigger ci.yml. This means automated doc hygiene commits bypass CI validation entirely. A build loop that pushes code changes faces the same gap.

**Recommendation:** Use a fine-grained PAT stored as a repository secret for any workflow that pushes to main and needs downstream CI to fire. For a single-user public repo, this is the pragmatic choice. Migrate to a GitHub App if/when the project adds collaborators.

---

## 8. Secret Management Approach

### Current State

No secrets appear to be configured in the repository (the API query returned empty). The `opencode_ci.yml` workflow references `OPENROUTER_API_KEY` but this secret likely does not exist, meaning that workflow would fail if triggered.

### Required Secrets for Build Loop

| Secret Name | Purpose | Sensitivity | Rotation Cadence |
|---|---|---|---|
| `OPENROUTER_API_KEY` | LLM model calls via OpenRouter | High (billing) | Quarterly or on suspected leak |
| `LIFEOS_PAT` | Push-to-main with workflow trigger capability | High (repo write) | 90 days (GitHub fine-grained PAT max is 1 year) |
| `ANTHROPIC_API_KEY` | Direct Claude API calls (if bypassing OpenRouter) | High (billing) | Quarterly |

### Recommended Approach

1. **Use GitHub repository secrets** (not environment secrets) for simplicity. Environment-level secrets add complexity without benefit for a single-branch deployment model.

2. **Create a fine-grained PAT** with minimum permissions:
   - `contents: write` (push code)
   - `actions: write` (trigger workflows, optional)
   - `issues: write` (if build loop creates issues)
   - Scope to this repository only

3. **Do not store secrets in code, config files, or `.env` files.** The `.gitignore` should exclude `.env*` patterns.

4. **Audit access periodically.** For a public repo, leaked secrets are the primary risk vector. Enable GitHub's secret scanning (free for public repos).

5. **Use `environment` protection rules** if the build loop will perform destructive actions (deploy, force-push). This adds a manual approval gate without requiring a GitHub App.

---

## 9. Artifact Retention Policy

### Current State

**No workflows currently upload artifacts.** None of the 7 workflows use `actions/upload-artifact`. Test results, coverage reports, and hygiene reports are generated but only exist in the workflow log output.

### What the Build Loop Would Generate

| Artifact Type | Size Estimate | Retention Need | Suggested Policy |
|---|---|---|---|
| Test results (pytest XML/JSON) | <1 MB | 7-30 days | Upload, 30-day retention |
| Coverage report (HTML/XML) | 1-5 MB | 7 days | Upload, 7-day retention |
| Build loop terminal packets (YAML) | <100 KB | 90 days | Upload, 90-day retention (governance evidence) |
| Build loop ledger entries | <50 KB | 90 days | Commit to repo (already the pattern) |
| Doc hygiene reports | <100 KB | 7 days | Upload, 7-day retention |
| Morning report (issue body) | N/A | Permanent (GitHub issue) | Already handled via issues |

### Recommendations

1. **Add `actions/upload-artifact@v4` to existing test workflows** for test result persistence:
   ```yaml
   - uses: actions/upload-artifact@v4
     if: always()
     with:
       name: test-results-${{ matrix.python-version }}
       path: test-results/
       retention-days: 30
   ```

2. **Set default retention at the repository level** via Settings > Actions > General > Artifact and log retention. Recommended: 30 days (balances storage with auditability).

3. **For governance evidence artifacts** (terminal packets, ledger entries), continue committing to the repo rather than relying on artifact retention. Artifacts are ephemeral; git commits are permanent. This aligns with the existing "git is the shared bus" principle.

4. **GitHub's default artifact retention is 90 days** for public repos. Reducing to 30 days for non-governance artifacts saves storage and reduces noise.

---

## 10. Recommendations and Blockers

### Blockers (Must Fix Before Build Loop)

| ID | Blocker | Severity | Details |
|---|---|---|---|
| **B1** | No concurrency guards on any workflow | **Critical** | A build loop that writes to main without concurrency protection risks race conditions with phase1_autonomy_nightly and other write workflows. Add `concurrency` groups before deployment. |
| **B2** | GITHUB_TOKEN cannot trigger downstream workflows | **High** | If the build loop pushes code, ci.yml will not run on that push. A PAT or GitHub App token is required for the push step. |
| **B3** | Nightly test suite (recursive_kernel_nightly) is persistently red | **High** | 8+ consecutive failures. The build loop cannot rely on nightly as a health signal until this is fixed. Investigate and resolve the root cause. |
| **B4** | Phase 1 Autonomy is broken | **Medium** | Instant failures since 2026-02-19 (0-second runs). This workflow pushes to main -- a broken workflow that partially executes could leave main in a bad state. Disable or fix before adding build loop. |
| **B5** | No secrets configured | **High** | Build loop requires at minimum an LLM API key (OPENROUTER_API_KEY or ANTHROPIC_API_KEY). Must be configured in repository settings. |

### Recommendations (Priority Order)

| Priority | Recommendation | Effort | Impact |
|---|---|---|---|
| **P0** | Add `concurrency` groups to all 7 workflows (see Section 6 templates) | 30 min | Prevents race conditions, prerequisite for build loop |
| **P0** | Configure required secrets (OPENROUTER_API_KEY, LIFEOS_PAT) | 15 min | Unblocks build loop and fixes opencode_ci.yml |
| **P0** | Fix or disable recursive_kernel_nightly.yml | 1-2 hours | Restores nightly health signal |
| **P1** | Fix or disable phase1_autonomy_nightly.yml | 1 hour | Eliminates broken nightly that could interfere with main |
| **P1** | Create build loop workflow with `workflow_dispatch` + cron trigger | 2-4 hours | Core deliverable |
| **P1** | Add artifact upload to test workflows | 30 min | Test result persistence for debugging |
| **P2** | Set repository-level artifact retention to 30 days | 5 min | Storage hygiene |
| **P2** | Add branch protection rule requiring ci.yml to pass | 15 min | Prevents broken code from reaching main |
| **P2** | Consider matrix-testing Python 3.13 in ci.yml | 15 min | Forward compatibility |
| **P3** | Migrate from PAT to GitHub App for write operations | 2-4 hours | Better security posture, not urgent for solo project |

### Proposed Build Loop Workflow Architecture

```
Trigger: cron (daily, off-peak) + workflow_dispatch

concurrency:
  group: build-loop
  cancel-in-progress: false

Steps:
  1. Checkout (with PAT for push capability)
  2. Install deps (requirements-dev.txt + ripgrep + markdownlint-cli)
  3. Pre-flight: pytest runtime/tests -q (fail-fast if red)
  4. Execute build loop spine (python -m runtime.engine ...)
  5. Post-flight: pytest runtime/tests -q (verify no regressions)
  6. Commit + push results (if any changes)
  7. Upload artifacts (terminal packets, test results)
  8. Create summary issue (optional, like phase1_autonomy pattern)
```

### Schedule Recommendation

```
Build loop:      02:00 UTC  (before nightly tests)
Nightly tests:   03:00 UTC  (validates build loop output)
Branch cleanup:  03:19 UTC  (unchanged)
Doc hygiene:     20:00 UTC  (keep separate from build, or convert to post-build-loop trigger)
```

This staggers all write operations with adequate buffer time and keeps the nightly test suite as an independent validation of whatever the build loop produced.

---

## Appendix: Raw Data

### Recent Workflow Run Log (from API query, 2026-02-20 to 2026-02-25)

```
2026-02-25 05:06 Branch Housekeeping    success  (11s)
2026-02-25 04:59 Nightly Full Test      failure  (92s)
2026-02-24 05:04 Branch Housekeeping    success  (14s)
2026-02-24 04:58 Nightly Full Test      failure  (83s)
2026-02-23 05:11 Branch Housekeeping    success  (13s)
2026-02-23 05:05 Nightly Full Test      failure  (92s)
2026-02-22 05:00 Branch Housekeeping    success  (12s)
2026-02-22 04:55 Nightly Full Test      failure  (79s)
2026-02-21 04:48 Branch Housekeeping    success  (13s)
2026-02-21 04:42 Nightly Full Test      failure  (88s)
2026-02-21 01:14 LifeOS CI              success  (90s)
2026-02-21 01:14 Phase 1 Autonomy       failure  (0s -- instant)
2026-02-21 00:03 LifeOS CI              success  (90s)
2026-02-21 00:03 Tool Invoke Hardening  success  (40s)
2026-02-20 23:58 Tool Invoke Hardening  success  (61s)
```

### Dependency Footprint

```
Core: pyyaml, httpx, requests, jsonschema, pytest, types-PyYAML
Dev:  pytest-asyncio, pytest-cov
System: ripgrep (apt), markdownlint-cli (npm), Node 20, Python 3.11
```
