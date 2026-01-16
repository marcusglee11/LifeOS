| File | Line | Method | Disposition | Rationale |
|---|---|---|---|---|
| `runtime/agents/opencode_client.py` | 343 (approx) | `shutil.rmtree` | GUARDED | Wrapped with `PathGuard.verify_safe_for_destruction`. |
| `scripts/opencode_ci_runner.py` | 288 (approx) | `shutil.rmtree` | GUARDED | Wrapped with `PathGuard.verify_safe_for_destruction`. |
| `runtime/rollback.py` | 111, 160, 171, 181, 187 | `shutil.rmtree` | DEFERRED | Part of trusted `RollbackEngine` (runtime internal). Not OpenCode-local vector. |
| `doc_steward/scripts/port_project_builder.py` | 21 | `shutil.rmtree` | DEFERRED | Legacy stewardship script (not in active OpenCode path). |
| `runtime/migration.py` | 67, 191 | `shutil.rmtree` | DEFERRED | Runtime internal logic. |
| `runtime/safety/halt.py` | 118 | `shutil.rmtree` | DEFERRED | Safety/Halt logic (trusted). |
| `scripts/closure/build_closure_bundle.py` | 226, 365 | `shutil.rmtree` | UNREACHABLE | Only runs in CI/Closure context, not OpenCode agent. |
| `scripts/run_certification_tests.py` | 346 | `shutil.rmtree` | GUARDED_BY_CONTEXT | Test runner cleans its own temp dirs (infrastructure). |
| `runtime/tests/*` | Various | `shutil.rmtree` | SAFE | Test code operating on fixture-created temp dirs. |
| `scripts/smoke_opencode_safety.py` | 54, 61 | `shutil.rmtree` | SAFE | The smoke test itself (verifies the guard). |
