# Worktree Evidence — Validator Suite v2.1a P0

## Main Tree (Read-Only Discovery)

Command:
```bash
git rev-parse --show-toplevel && echo '---' && git status --porcelain=v1 && echo '---' && git rev-parse HEAD
```

Output:
```text
/mnt/c/Users/cabra/Projects/LifeOS
---
---
5452fcce3d91aedd68dead9925f449780313fb70
```

## Worktree Creation / Recreation Output

Command executed:
```bash
git -C /mnt/c/Users/cabra/Projects/LifeOS worktree add -b validator-suite-v2.1a-p0 /mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0 2eaade7a65a8c341d2486689b023327bc03bfc55
```

Observed output (key lines):
```text
Deleted branch validator-suite-v2.1a-p0 (was dd2ccea).
Preparing worktree (new branch 'validator-suite-v2.1a-p0')
HEAD is now at 2eaade7 chore(eol): normalize policy tests for clean worktree bootstrap
/mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0
validator-suite-v2.1a-p0
2eaade7a65a8c341d2486689b023327bc03bfc55
```

## Worktree Clean-State Invariant

Pre-implementation check output (captured at setup time):
```text
0
```

Interpretation:
- `git status --porcelain=v1 | wc -l` returned `0` in the new worktree before any implementation edits.

## Worktree Authoritative Status (Post-Implementation)

Command:
```bash
git rev-parse --show-toplevel && git branch --show-current && echo '---' && git status --porcelain=v1 && echo '---' && git diff --name-only
```

Output:
```text
/mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0
validator-suite-v2.1a-p0
---
?? Validation_Surface_Map.md
?? artifacts/validation_samples/
?? runtime/orchestration/orchestrator.py
?? runtime/orchestration/workspace_lock.py
?? runtime/tests/fixtures/validation/
?? runtime/tests/orchestration/test_validation_orchestrator.py
?? runtime/tests/orchestration/test_workspace_lock.py
?? runtime/tests/validation/
?? runtime/validation/
---
```

Untracked/changed paths list:
```text
Validation_Surface_Map.md
artifacts/validation_samples/v2.1a-p0/acceptance_token.json
artifacts/validation_samples/v2.1a-p0/pytest_output.txt
artifacts/validation_samples/v2.1a-p0/validator_report.json
runtime/orchestration/orchestrator.py
runtime/orchestration/workspace_lock.py
runtime/tests/fixtures/validation/acceptance_token_success_fixture.json
runtime/tests/fixtures/validation/validator_report_failure_fixture.json
runtime/tests/orchestration/test_validation_orchestrator.py
runtime/tests/orchestration/test_workspace_lock.py
runtime/tests/validation/test_cleanliness.py
runtime/tests/validation/test_evidence.py
runtime/tests/validation/test_gate_runner_and_acceptor.py
runtime/validation/__init__.py
runtime/validation/acceptor.py
runtime/validation/attempts.py
runtime/validation/cleanliness.py
runtime/validation/codes.py
runtime/validation/core.py
runtime/validation/evidence.py
runtime/validation/gate_runner.py
runtime/validation/reporting.py
```

## Test Command and Output

Command:
```bash
pytest -q runtime/tests/validation/test_evidence.py runtime/tests/validation/test_cleanliness.py runtime/tests/orchestration/test_workspace_lock.py runtime/tests/validation/test_gate_runner_and_acceptor.py runtime/tests/orchestration/test_validation_orchestrator.py
```

Output:
```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 15 items

runtime/tests/validation/test_evidence.py ...                            [ 20%]
runtime/tests/validation/test_cleanliness.py ...                         [ 40%]
runtime/tests/orchestration/test_workspace_lock.py ...                   [ 60%]
runtime/tests/validation/test_gate_runner_and_acceptor.py ...            [ 80%]
runtime/tests/orchestration/test_validation_orchestrator.py ...          [100%]

============================== 15 passed in 2.35s ==============================
```

## Sample Artifacts

- Failure sample: `artifacts/validation_samples/v2.1a-p0/validator_report.json`
- Success sample: `artifacts/validation_samples/v2.1a-p0/acceptance_token.json`
- Test output: `artifacts/validation_samples/v2.1a-p0/pytest_output.txt`
