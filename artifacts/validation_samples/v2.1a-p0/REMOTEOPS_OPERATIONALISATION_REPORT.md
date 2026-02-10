# REMOTEOPS_OPERATIONALISATION_REPORT

## What changed

- `.github/workflows/branch_housekeeping_delete_merged_validator_suite.yml` (new)
- `runtime/orchestration/remote_ops.py` (new)
- `runtime/tests/orchestration/test_remote_ops.py` (new)
- `artifacts/validation_samples/v2.1a-p0/remote_ops_pytest_output.txt` (new)

## Change list command output

### Command

```bash
git diff --name-only -- .github/workflows/branch_housekeeping_delete_merged_validator_suite.yml runtime/orchestration/remote_ops.py runtime/tests/orchestration/test_remote_ops.py artifacts/validation_samples/v2.1a-p0/remote_ops_pytest_output.txt && git ls-files --others --exclude-standard -- .github/workflows/branch_housekeeping_delete_merged_validator_suite.yml runtime/orchestration/remote_ops.py runtime/tests/orchestration/test_remote_ops.py artifacts/validation_samples/v2.1a-p0/remote_ops_pytest_output.txt
```

### Output

```text
.github/workflows/branch_housekeeping_delete_merged_validator_suite.yml
artifacts/validation_samples/v2.1a-p0/remote_ops_pytest_output.txt
runtime/orchestration/remote_ops.py
runtime/tests/orchestration/test_remote_ops.py
```

## Server-side cleanup guarantee

Branch deletion is now guaranteed by GitHub Actions instead of workstation network conditions.
The workflow checks merged status against a deterministic base branch and deletes merged `validator-suite-*` refs using the GitHub API (`deleteRef`).
404 (already gone) and 403/protected/denied outcomes are non-fatal and logged as skip/success semantics.

Manual trigger: GitHub Actions workflow **"Branch Housekeeping Delete Merged Validator Suite"** via `workflow_dispatch`.

## Local DNS deferral semantics

`runtime/orchestration/remote_ops.py` adds trusted housekeeping semantics:

- DNS/name-resolution failures (`Could not resolve hostname`, `name resolution`) => `DEFERRED`, non-blocking, backoff schedule (5m, 15m, 45m, then 24h cap).
- Non-DNS failures => `DEFERRED` for attempts 1-3, `TERMINAL` at attempt >=4 with `needs_escalation=true`, still non-blocking for housekeeping.
- Artifacts are written atomically under ignore-proofed run roots:
  - `artifacts/validation_runs/<run_id>/<attempt_id>/remote_ops_queue.jsonl`
  - `artifacts/validation_runs/<run_id>/<attempt_id>/remote_ops_report.json`
- Manual fallback path is deterministic: `artifacts/validation_runs/manual/manual/...`

## Existing runtime delete-call search (P0.R3)

### Command

```bash
rg -n "git push origin --delete|deleteRef\(|ls-remote --heads origin" runtime scripts .github 2>/dev/null || true
```

### Output

```text
scripts/git_workflow.py:264:    print(f"   git push origin --delete {current}")
scripts/git_workflow.py:365:        print(f"   3. Delete sync branch: git push origin --delete {sync_branch}")
.github/workflows/branch_housekeeping_delete_merged_validator_suite.yml:96:                await github.rest.git.deleteRef({ owner, repo, ref: `heads/${candidate}` });
runtime/orchestration/remote_ops.py:231:        error_text = f"git push origin --delete timed out after {timeout_seconds}s"
```

Interpretation: no existing orchestrator/runner remote-branch delete path required rerouting; matches plan assumption.

## Workflow file (exact content)

Path: `.github/workflows/branch_housekeeping_delete_merged_validator_suite.yml`

```yaml
name: Branch Housekeeping Delete Merged Validator Suite

on:
  schedule:
    - cron: "19 3 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  delete-merged-validator-suite:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout full history
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Fetch remote branch refs
        run: git fetch --prune --no-tags origin "+refs/heads/*:refs/remotes/origin/*"

      - name: Resolve housekeeping base branch
        id: resolve_base
        uses: actions/github-script@v7
        with:
          script: |
            const preferred = "build/eol-clean-invariant";
            const owner = context.repo.owner;
            const repo = context.repo.repo;

            try {
              await github.rest.repos.getBranch({ owner, repo, branch: preferred });
              core.setOutput("base_branch", preferred);
              core.info(`Using preferred base branch: ${preferred}`);
            } catch (error) {
              if (error.status === 404) {
                const fallback = context.payload.repository.default_branch;
                core.setOutput("base_branch", fallback);
                core.info(`Preferred base missing; using default branch: ${fallback}`);
              } else {
                throw error;
              }
            }

      - name: Delete merged validator-suite branches
        uses: actions/github-script@v7
        env:
          BASE_BRANCH: ${{ steps.resolve_base.outputs.base_branch }}
        with:
          script: |
            const { execFileSync } = require("node:child_process");

            const owner = context.repo.owner;
            const repo = context.repo.repo;
            const base = process.env.BASE_BRANCH;

            const runGit = (args) => {
              return execFileSync("git", args, { encoding: "utf8" }).trim();
            };

            const refsText = runGit(["for-each-ref", "--format=%(refname:strip=3)", "refs/remotes/origin"]);
            const candidates = refsText
              .split("\n")
              .map((line) => line.trim())
              .filter((line) => line.length > 0)
              .filter((line) => line.startsWith("validator-suite-"))
              .sort((a, b) => a.localeCompare(b));

            core.info(`Base branch: ${base}`);
            core.info(`Candidates (${candidates.length}): ${candidates.join(", ") || "<none>"}`);

            const rows = [];
            for (const candidate of candidates) {
              let merged = false;
              try {
                runGit(["merge-base", "--is-ancestor", `origin/${candidate}`, `origin/${base}`]);
                merged = true;
              } catch (error) {
                if (error.status === 1) {
                  merged = false;
                } else {
                  const detail = String(error.stderr || error.message || "merge-base failed").trim();
                  rows.push({ branch: candidate, merged: "unknown", action: "skipped_check_error", detail });
                  core.warning(`Skip ${candidate}: merge-base check error: ${detail}`);
                  continue;
                }
              }

              if (!merged) {
                rows.push({ branch: candidate, merged: "no", action: "skipped_not_merged", detail: "not ancestor of base" });
                continue;
              }

              try {
                await github.rest.git.deleteRef({ owner, repo, ref: `heads/${candidate}` });
                rows.push({ branch: candidate, merged: "yes", action: "deleted", detail: "deleted via deleteRef" });
              } catch (error) {
                if (error.status === 404) {
                  rows.push({ branch: candidate, merged: "yes", action: "already_deleted", detail: "branch vanished before delete" });
                } else if (error.status === 403) {
                  rows.push({ branch: candidate, merged: "yes", action: "skipped_protected_or_denied", detail: "permission denied or branch protected" });
                } else {
                  const detail = String(error.message || "deleteRef failed").trim();
                  rows.push({ branch: candidate, merged: "yes", action: "skipped_delete_error", detail });
                  core.warning(`Skip ${candidate}: deleteRef error: ${detail}`);
                }
              }
            }

            const summary = [
              "## Validator Suite Branch Housekeeping",
              `Base branch: ${base}`,
              "",
              "| Branch | Merged | Action | Detail |",
              "|---|---|---|---|",
              ...rows.map((row) => `| ${row.branch} | ${row.merged} | ${row.action} | ${row.detail} |`),
            ];

            if (rows.length === 0) {
              summary.push("No validator-suite branches found.");
            }

            await core.summary.addRaw(summary.join("\n")).write();
```

## RemoteOps key functions with line ranges

- `runtime/orchestration/remote_ops.py:76` (`attempt_root_for_remote_ops`) and `runtime/orchestration/remote_ops.py:81` / `runtime/orchestration/remote_ops.py:85` (queue/report paths)
- `runtime/orchestration/remote_ops.py:96` (`_backoff_delta_for_attempt`) and `runtime/orchestration/remote_ops.py:106` (`_looks_like_dns_failure`)
- `runtime/orchestration/remote_ops.py:132` (`_write_queue_atomic`)
- `runtime/orchestration/remote_ops.py:155` (`write_remote_ops_report`)
- `runtime/orchestration/remote_ops.py:182` (`try_delete_remote_branch`)

### Snippet

```text
76-86: path roots and manual/default placement under artifacts/validation_runs/<run_id>/<attempt_id>/
96-103: deterministic backoff 5m/15m/45m/24h-cap
132-147: atomic JSONL queue write with temp file + os.replace
155-179: deterministic report payload with retention_days=30 via write_json_atomic
182-299: housekeeping execution, DNS deferral, non-DNS retry/terminal policy, non-blocking result
```

## Test execution evidence

### Command

```bash
pytest -q runtime/tests/orchestration/test_remote_ops.py runtime/tests/orchestration/test_validation_orchestrator.py runtime/tests/orchestration/test_workspace_lock.py runtime/tests/validation/test_cleanliness.py runtime/tests/validation/test_gate_runner_and_acceptor.py runtime/tests/validation/test_evidence.py | tee artifacts/validation_samples/v2.1a-p0/remote_ops_pytest_output.txt
```

### Output (also saved at `artifacts/validation_samples/v2.1a-p0/remote_ops_pytest_output.txt`)

```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /mnt/c/Users/cabra/Projects/LifeOS
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 23 items

runtime/tests/orchestration/test_remote_ops.py ....                      [ 17%]
runtime/tests/orchestration/test_validation_orchestrator.py .....        [ 39%]
runtime/tests/orchestration/test_workspace_lock.py ...                   [ 52%]
runtime/tests/validation/test_cleanliness.py ....                        [ 69%]
runtime/tests/validation/test_gate_runner_and_acceptor.py ....           [ 86%]
runtime/tests/validation/test_evidence.py ...                            [100%]

============================== 23 passed in 4.16s ==============================
```
