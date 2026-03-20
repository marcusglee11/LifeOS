# Review Packet: Task2 Config Hygiene v1.0

## Mission
Execute Task 2 from `artifacts/plans/2026-02-21-repo-hygiene-sprint.md`:
- Align pytest version constraint with installed pytest 9.0.2
- Remove stale ignore for `tests_recursive/test_e2e_smoke_timeout.py`
- Keep ignore rationale comments accurate

## Files Changed
- `requirements.txt`
- `pyproject.toml`

## Implementation Summary
1. Updated dependency metadata date in `requirements.txt` to `2026-02-21`.
2. Updated pytest constraint in `requirements.txt` from `<9.0` to `<10.0`.
3. Removed stale ignore entry for `tests_recursive/test_e2e_smoke_timeout.py` from `pyproject.toml`.
4. Updated remaining ignore comments in `pyproject.toml` to reflect current rationale.

## Validation Evidence
### Targeted Task 2 checks
- Command: `pytest runtime/tests/test_config_hygiene.py -v`
- Result: `2 passed`

- Command: `pytest tests_recursive/test_e2e_smoke_timeout.py -v`
- Result: `6 passed`

### Regression sweep (as requested by plan)
- Command: `pytest runtime/tests -q`
- Result: `3 failed, 1689 passed, 8 skipped`
- Failures observed:
  - `runtime/tests/test_coo_worktree_marker_receipt.py::test_coo_e2e_marker_receipt_projects_canonical_capsule`
  - `runtime/tests/test_opencode_stage1_5_live.py::TestZenModelComparison::test_model_responds[opencode/kimi-k2.5-free]`
  - `runtime/tests/test_opencode_stage1_5_live.py::TestZenModelComparison::test_model_responds[opencode/glm-5-free]`
- Notes:
  - Failure signatures are runtime/environment related (`EACCES` to user home lock/log files and network/model endpoint availability), not caused by Task 2 config edits.

## Diff Summary
- `requirements.txt`
  - `# Generated: 2026-01-19` -> `# Generated: 2026-02-21`
  - `pytest>=7.0,<9.0` -> `pytest>=7.0,<10.0`
- `pyproject.toml`
  - Removed `--ignore=tests_recursive/test_e2e_smoke_timeout.py`
  - Updated stale ignore rationale comments for remaining ignored suites

## Appendix A: Flattened Code (Full)

### `requirements.txt`
```text
# LifeOS Dependencies
# Generated: 2026-02-21

# Core
pyyaml>=6.0,<7.0
httpx>=0.27.0,<1.0
requests>=2.31.0,<3.0
jsonschema>=4.21.0,<5.0

# Testing (minimal for CI)
pytest>=7.0,<10.0

# Typing
types-PyYAML>=6.0,<7.0

# Note: Run `pip install -r requirements.txt` to install
# For development: `pip install -r requirements-dev.txt`
# Run `pip-audit` periodically to check for vulnerabilities
```

### `pyproject.toml`
```toml
# Project Metadata

[project]
name = "lifeos"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
lifeos = "runtime.cli:main"
coo = "runtime.cli:main"

[tool.setuptools]
packages = ["runtime", "recursive_kernel", "doc_steward", "opencode_governance", "project_builder"]

[tool.pytest.ini_options]
# Merged configuration from pytest.ini and doc_steward/scripts/pyproject.toml
minversion = "6.0"
testpaths = [
    "runtime/tests",
    "tests_doc",
    "tests_recursive"
]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
pythonpath = [
    ".",
    "project_builder",
    "runtime"
]

# Addopts: verbose mode with ignored paths for excluded tests
# Each exclusion documented with evidence (verified 2026-02-08):
addopts = [
    "-v",
    # Archived legacy tests from pre-Phase 3 rewrite — not maintained
    "--ignore=runtime/tests/archive_legacy_r6x",
    # 25/27 failing — WSL git worktree ops too slow for CI (W0-T05)
    "--ignore=tests_recursive/test_steward_runner.py",
    # 1/5 failing — test_hardlink_defense triggers SecurityViolation on WSL
    "--ignore=runtime/tests/test_sandbox_remediation.py",
    # 1/1 failing — non-deterministic approval demo
    "--ignore=runtime/tests/test_demo_approval_determinism.py",
]

# Filter warnings
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::pytest.PytestDeprecationWarning"
]

# Custom markers
markers = [
    "cold_start: marks tests that measure or test cold start (first-run) performance and initialization"
]
```
