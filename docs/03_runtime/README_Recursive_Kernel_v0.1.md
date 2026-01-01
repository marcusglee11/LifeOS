# Recursive Kernel v0.1

## Overview
The Recursive Kernel is a self-improvement loop for LifeOS. In v0.1, it is limited to **safe domains** (docs) and provides a scaffold for Planning, Building, Verifying, and Gating.

## How to Run
From the repository root:

```bash
python -m recursive_kernel.runner
```

## Behavior
1. **Plan**: Loads `config/recursive_kernel_config.yaml` and checks `config/backlog.yaml` for `todo` tasks in `safe_domains` (currently `docs`, `tests_doc`).
2. **Build**: Executes the task. Currently supports `rebuild_index` for `docs`, which regenerates `docs/INDEX.md` based on valid markdown files in `docs/`.
3. **Verify**: Runs the configured `test_command` (default: `pytest`).
4. **Gate**: Evaluates the risk of changes.
   - Low risk (docs only, small diff) -> `AUTO_MERGE` (Simulated)
   - High risk -> `HUMAN_REVIEW`
5. **Log**: Writes a JSON report to `logs/recursive_runs/`.

## Logs
Check `logs/recursive_runs/` for execution details. Each run generates a timestamped JSON file.