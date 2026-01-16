# Disposition Table: Destructive Operations Audit

| File | Line | Method | Disposition | Rationale |
|---|---|---|---|---|
| **OpenCode-Local Vectors (Guarded)** |||||
| `runtime/agents/opencode_client.py` | 347 | `shutil.rmtree` | GUARDED | Wrapped with `PathGuard.verify_safe_for_destruction` in `_cleanup_config`. |
| `scripts/opencode_ci_runner.py` | 288 | `shutil.rmtree` | GUARDED | Wrapped with `PathGuard.verify_safe_for_destruction` in `cleanup_isolated_config`. |
| `scripts/opencode_ci_runner.py` | 406, 423, 435 | `git reset --hard` | REMOVED | Commented out unsafe reset calls; replaced with logged blocks. |
| **Governance/Orchestration Layer** |||||
| `runtime/orchestration/operations.py` | 43 | `git clean -fd` (whitelist) | DECLARATIVE_ONLY | Whitelist used for compensation validation, not execution. No active execution pathway found in codebase. |
| **Runtime Internal (Deferred)** |||||
| `runtime/rollback.py` | 111, 160, 171, 181, 187 | `shutil.rmtree` | DEFERRED | Part of trusted `RollbackEngine` (runtime internal). Not OpenCode-local vector. |
| `runtime/migration.py` | 67, 191 | `shutil.rmtree` | DEFERRED | Runtime internal logic. |
| `runtime/safety/halt.py` | 118 | `shutil.rmtree` | DEFERRED | Safety/Halt logic (trusted). |
| **Infrastructure/Testing** |||||
| `doc_steward/scripts/port_project_builder.py` | 21 | `shutil.rmtree` | DEFERRED | Legacy stewardship script (not in active OpenCode path). |
| `scripts/closure/build_closure_bundle.py` | 226, 365 | `shutil.rmtree` | UNREACHABLE | Only runs in CI/Closure context, not OpenCode agent. |
| `scripts/run_certification_tests.py` | 346 | `shutil.rmtree` | GUARDED_BY_CONTEXT | Test runner cleans its own temp dirs (infrastructure). |
| `runtime/tests/*` | Various | `shutil.rmtree` | SAFE | Test code operating on fixture-created temp dirs. |
| `scripts/smoke_opencode_safety.py` | 54, 61 | `shutil.rmtree` | SAFE | The smoke test itself (verifies the guard). |

## Summary

- **Guarded:** 2 OpenCode-local `shutil.rmtree` calls + 3 `git reset --hard` removals
- **Declarative Only:** 1 `git clean -fd` whitelist entry (no execution)
- **Deferred:** 9 runtime internal operations (trusted context)
- **Safe:** Test/infrastructure code (controlled environment)
