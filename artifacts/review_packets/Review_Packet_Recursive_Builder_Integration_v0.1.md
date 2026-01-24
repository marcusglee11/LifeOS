# Review Packet: Recursive Builder Integration (Phase 4 P1)

**Mode**: Standard Implementation  
**Date**: 2026-01-23  
**Run ID**: P4P1-RBI

---

## Scope Envelope

**Allowed Paths**:

- `recursive_kernel/` — Parser and runner changes
- `recursive_kernel/tests/` — New test files

**Forbidden Paths**: None modified outside scope

---

## Summary

Wired `recursive_kernel/runner.py` to dispatch `AutonomousBuildCycleMission` from backlog items with deterministic, fail-closed behavior.

---

## Issue Catalogue

| ID | Priority | Description | Status |
|----|----------|-------------|--------|
| P0.2 | P0 | Backlog parser with SHA256 item_key | DONE |
| P0.3 | P0 | Atomic mutation helper | DONE |
| P0.4 | P0 | Runner autonomous mode | DONE |
| P0.5 | P0 | Evidence contract | DONE |
| P1.1 | P1 | Test coverage | DONE |

---

## Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `--autonomous --dry-run` selects item deterministically | PASS | CLI output below |
| Dry-run produces zero side effects | PASS | 3/3 tests pass |
| Blocks on malformed P0/P1 items | PASS | `test_blocks_on_malformed_backlog` |
| Blocks on git dirty (non-dry-run) | PASS | `test_blocks_on_git_dirty` |
| Backlog mutation is atomic | PASS | `test_marks_item_done_atomically` |
| All tests pass | PASS | 28/28 |

---

## Closure Evidence Checklist

| Category | Requirement | Verified |
|----------|-------------|----------|
| **Provenance** | Code changes | 4 files |
| **Artifacts** | Test files | 2 new test files |
| **Repro** | Test command | `pytest recursive_kernel/tests/ -v` |
| **Outcome** | Terminal proof | 28 passed in 0.70s |

---

## Non-Goals

- Multi-item batch processing (default is 1, max 3)
- AutonomousBuildCycleMission internals unchanged
- No new governance frameworks

---

## Changes

| File | Change Type |
|------|-------------|
| `recursive_kernel/backlog_parser.py` | NEW |
| `recursive_kernel/runner.py` | MODIFIED |
| `recursive_kernel/tests/__init__.py` | NEW |
| `recursive_kernel/tests/test_backlog_parser.py` | NEW |
| `recursive_kernel/tests/test_runner_integration.py` | NEW |

---

## Example Backlog Line Format

**Canonical Grammar**:

```markdown
- [ ] **Title** — DoD: Description — Owner: antigravity — Context: Optional
```

**Example**:

```markdown
### P0 (Critical)

- [ ] **Finalize CSO_Role_Constitution v1.0** — DoD: Markers removed; CEO approved — Owner: antigravity — Context: Phase 3 closure
```

---

## Test Output (Verbatim)

```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-8.3.4
collected 28 items

recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_parses_valid_p0_item PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_parses_why_now_as_dod PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_ignores_headers_and_blank_lines PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_done_item_status PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_inprogress_status PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_fails_closed_on_missing_required_fields PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_fails_closed_on_missing_owner PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_item_without_priority_section_gets_p3 PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_stable_item_key_generation PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_different_content_different_key PASSED
recursive_kernel/tests/test_backlog_parser.py::TestBacklogParser::test_file_not_found_raises PASSED
recursive_kernel/tests/test_backlog_parser.py::TestSelectEligibleItem::test_selects_first_p0_over_p1 PASSED
recursive_kernel/tests/test_backlog_parser.py::TestSelectEligibleItem::test_selects_file_order_within_priority PASSED
recursive_kernel/tests/test_backlog_parser.py::TestSelectEligibleItem::test_skips_done_items PASSED
recursive_kernel/tests/test_backlog_parser.py::TestSelectEligibleItem::test_returns_none_when_no_eligible PASSED
recursive_kernel/tests/test_backlog_parser.py::TestMarkItemDone::test_marks_item_done_atomically PASSED
recursive_kernel/tests/test_backlog_parser.py::TestMarkItemDone::test_preserves_other_lines PASSED
recursive_kernel/tests/test_backlog_parser.py::TestMarkItemDone::test_fails_on_file_changed PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerDryRun::test_dry_run_no_dispatch PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerDryRun::test_dry_run_no_backlog_mutation PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerDryRun::test_dry_run_no_artifact_creation PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerSelection::test_selects_p0_over_p1 PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerSelection::test_returns_zero_when_no_eligible PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerOutcomes::test_escalation_emits_artifact PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerOutcomes::test_waiver_emits_artifact PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerOutcomes::test_success_marks_item_done PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerFailClosed::test_blocks_on_malformed_backlog PASSED
recursive_kernel/tests/test_runner_integration.py::TestAutonomousRunnerFailClosed::test_blocks_on_git_dirty PASSED

============================= 28 passed in 0.70s ==============================
```

---

## Dry-Run Output (Verbatim)

```
Recursive Kernel Runner v0.2 (Autonomous Mode)
Run ID: 4f925398
Dry Run: True

WARNING: Repository has uncommitted changes (ignored in dry-run)
Baseline commit: 178b9b52d152480b541850bf310a6e3bade98d46
Parsed 17 total items from backlog

=== Selected Item ===
  Key: 32a5b3e37af2513d
  Priority: P0
  Title: Finalize CSO_Role_Constitution v1.0 (Remove Waiver W1)
  DoD: Markers removed; CEO approved; W1 waiver removed
  Owner: antigravity
  Line: 9

DRY RUN: Would dispatch mission with payload:
{
  "item_key": "32a5b3e37af2513d",
  "priority": "P0",
  "title": "Finalize CSO_Role_Constitution v1.0 (Remove Waiver W1)",
  "dod": "Markers removed; CEO approved; W1 waiver removed",
  "owner": "antigravity",
  "context": "Phase 3 closure ratified with W1 waiver; removal required"
}

DRY RUN complete. No side effects performed.
```
