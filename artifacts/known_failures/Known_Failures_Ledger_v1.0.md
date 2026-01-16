# Known Failures Ledger v1.0

**Status**: Canonical (SOURCE OF TRUTH for regression gate)  
**Generated**: 2026-01-09T03:02:07Z  
**Ref**: `416e23cb216a88ed4eeee267b1d027b8193bac24`

## Purpose

This ledger documents known failing tests in the LifeOS repository. It serves as the authoritative source for the "no new failures" gate enforced by `scripts/check_known_failures_gate.py`.

**Gate Semantics**:

- ✅ **PASS**: If `HEAD_failures ⊆ ledger_entries` (all failures are known)
- ❌ **FAIL**: If `HEAD_failures ⊄ ledger_entries` (new unknown failures detected)

## Known Failures (24 total)

### Runtime Tests (1)

| NodeID | Reason | Owner | Removal Criteria |
| :----- | :----- | :---- | :--------------- |
| `runtime/tests/test_cold_start_marker.py::test_cold_start_engine_init_time` | Cold start timing threshold exceeded in test environment | runtime | Optimize engine init or adjust timing threshold |

### Governance Tests (1)

| NodeID | Reason | Owner | Removal Criteria |
| :----- | :----- | :---- | :--------------- |
| `runtime/tests/test_opencode_governance/test_phase1_contract.py::test_t5_canonical_evidence_capture` | Runner failed with code 2 - governance contract test needs update | governance | Update test to match current governance runner implementation |

### Documentation Tests (1)

| NodeID | Reason | Owner | Removal Criteria |
| :----- | :----- | :---- | :--------------- |
| `tests_doc/test_links.py::test_link_integrity` | Broken internal links found in documentation | doc_steward | Fix all broken internal documentation links |

### Recursive Steward Runner Tests (21)

All failures below are caused by `steward_runner.py` missing from test worktree setup.

**Removal Criteria**: Fix test worktree setup to include `scripts/steward_runner.py`

| NodeID |
| :----- |
| `tests_recursive/test_steward_runner.py::TestAT01MissingRunId::test_missing_run_id_fails` |
| `tests_recursive/test_steward_runner.py::TestAT06NoChangeNoCommit::test_no_change_exits_success` |
| `tests_recursive/test_steward_runner.py::TestAT07ChangeWithinAllowedPathsCommits::test_allowed_change_commits` |
| `tests_recursive/test_steward_runner.py::TestAT09DryRunNeverCommits::test_dry_run_skips_commit` |
| `tests_recursive/test_steward_runner.py::TestAT10LogDeterminism::test_logs_are_deterministic` |
| `tests_recursive/test_steward_runner.py::TestAT11TestScopeEnforcement::test_tests_argv_includes_paths` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[../docs/-path_traversal]` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[//server/share/-absolute_path_unc]` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[/absolute/path/-absolute_path_unix0]` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[/absolute/path/-absolute_path_unix1]` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[C:/temp/-absolute_path_windows]` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[C:\\temp\\-absolute_path_windows]` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[docs%2Ffolder-url_encoded_chars]` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[docs/*.md-glob_pattern]` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[docs/../other/-path_traversal]` |
| `tests_recursive/test_steward_runner.py::TestAT13FailClosedUnsafePaths::test_unsafe_path_fails[docs/?.md-glob_pattern]` |
| `tests_recursive/test_steward_runner.py::TestAT14DirtyDuringRun::test_dirty_during_run_rejected` |
| `tests_recursive/test_steward_runner.py::TestAT15LogFieldSorting::test_log_lists_are_sorted` |
| `tests_recursive/test_steward_runner.py::TestAT16DefaultDryRun::test_no_flags_is_dry_run` |
| `tests_recursive/test_steward_runner.py::TestAT17CommitFlagEnables::test_commit_flag_enables` |
| `tests_recursive/test_steward_runner.py::TestAT18ExplicitDryRun::test_explicit_dry_run` |

---

## Maintenance

**Editing this ledger is governance-controlled**. Changes must:

1. Be justified with clear rationale
2. Update both JSON and Markdown versions in sync
3. Maintain deterministic ordering (sorted by nodeid)
4. Include ref/ticket when adding entries

**Source of Truth**: `artifacts/known_failures/known_failures_ledger_v1.0.json`
