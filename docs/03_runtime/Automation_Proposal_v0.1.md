# Automation Proposal v0.1

**Status**: Proposal
**Target**: Reduce "Crank-Turning" to Zero.

## 1. Identified Manual Tasks (The Problem)
The following tasks are currently candidates for human manual labor and must be automated immediately:

1.  **Index Maintenance**: Manually checking if `INDEX_LifeOS.md` matches the actual files in `docs/`.
2.  **Scaffolding**: Creating directories and `__init__.py` files for new components.
3.  **Status Reporting**: Reading multiple `task.md` files to see what is going on.
4.  **Formatting**: Ensuring headers and frontmatter are correct.

## 2. Proposed Automations

### A. Auto-Indexer (`scripts/auto_index.py`)
- **Function**: recursive walk of `docs/`.
- **Output**: Generates a `docs/INDEX_GENERATED.md`.
- **Logic**: Reads the `# Title` from each `.md` file to build a clean link tree.
- **Human Action**: None. (Runs on CI or pre-commit).

### B. Universal Scaffolder (`scripts/new_module.py`)
- **Function**: Creates standard folder structure.
- **Input**: `python scripts/new_module.py --name "my_component"`.
- **Output**: Creates folder, `__init__.py`, `README.md`, `tests/`.
- **Status**: *Partially implemented via `docs/scaffold_lifeos.py`*.

### C. Daily Status Aggregator (`scripts/daily_summary.py`)
- **Function**: Scans all `task.md` files in active workspaces.
- **Output**: Prints a summary to the console:
  ```text
  [Active] Scaffolding: 80%
  [Pending] Anti-Failure: 10%
  ```

## 3. Implementation Roadmap
1.  **Immediate**: Implement `auto_index.py` (High value, low risk).
2.  **Next**: Refine `scaffold_lifeos.py` into `new_module.py`.
3.  **Later**: `daily_summary.py` once we have more active tasks.

## 4. Next Step for Human
- **Approve this proposal**.
- I will then implement `scripts/auto_index.py` immediately.
