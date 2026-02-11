# Review Packet: Smoke Test Isolation (Hardened)

**Mission Name**: Smoke Test Isolation & Egg-info Remediation
**Version**: v1.1
**Date**: 2026-02-11
**Author**: Antigravity Agent

## Scope Envelope

- **Allowed Paths**: `.gitignore`, `scripts/`, `runtime/tests/`
- **Forbidden Paths**: Governance specs, foundational protocols.
- **Authority**: Builder/Implementer role.

## Summary

Isolated "as-installed" smoke tests by utilizing `git worktree` and fresh virtual environments, preventing pollution of the main repository and ensuring compatibility with `DIRTY_REPO_PRE` enforcement. Hardened script logic with strict error handling (`run_cmd_ok`) and robust relative-to-absolute path resolution for deterministic acceptance proofs.

## Issue Catalogue

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| P0 | High | `DIRTY_REPO_PRE` blocks smoke tests due to `egg-info` in index. | Untracked `egg-info` and implemented isolation. |
| P1 | Med | Packaging artifacts and session logs pollute `git status`. | Updated `.gitignore` with root-anchored rules. |
| P1 | Med | Windows `pip.exe` cannot upgrade itself directly. | Switched to `python -m pip` for upgrades. |

## Acceptance Criteria

| Criterion | Status | Evidence Pointer |
|-----------|--------|------------------|
| Untracked egg-info | PASS | `git ls-files | grep egg-info` (empty) |
| Hardened .gitignore | PASS | Verify .gitignore entries |
| Isolated Smoke Success | PASS | `pytest runtime/tests/test_isolated_smoke_test.py` (PASS) |
| Repo Cleanliness | PASS | `git status --porcelain=v1` (empty) |
| Path Resolution | PASS | Proof paths resolved correctly in worktree |

## Closure Evidence Checklist

| Category | Requirement | Verified |
|----------|-------------|----------|
| **Provenance** | Code commit hash + message | [d63bf92] test(smoke): harden isolated worktree smoke (strict rc + path resolution + clean repo assert) |
| | Docs commit hash + message | N/A |
| | Changed file list (paths) | .gitignore, runtime/tests/test_isolated_smoke_test.py, scripts/isolated_smoke_test.py, (5 deleted egg-info files) |
| **Artifacts** | `Review_Packet_Smoke_Test_Isolation_v1.1.md` | [artifacts/review_packets/Review_Packet_Smoke_Test_Isolation_v1.0.md] (Updated) |
| **Repro** | Test command(s) exact cmdline | `pytest -v runtime/tests/test_isolated_smoke_test.py` |
| **Outcome** | Terminal outcome proof | PASS |

## Appendix: Flattened Code (Hardened)

### runtime/tests/test_isolated_smoke_test.py

```python
import subprocess
import sys
from pathlib import Path

def test_isolated_smoke_test_preserves_cleanliness():
    repo_root = Path(__file__).parents[2]
    script_path = repo_root / "scripts" / "isolated_smoke_test.py"
    res = subprocess.run([sys.executable, str(script_path)], cwd=repo_root, capture_output=True, text=True)
    assert res.returncode == 0, f"Isolated smoke test failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
    status_res = subprocess.run(["git", "status", "--porcelain=v1"], cwd=repo_root, capture_output=True, text=True)
    assert status_res.stdout.strip() == "", f"Repo is dirty:\n{status_res.stdout}"
```
