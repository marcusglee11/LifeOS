# Phase 4A0: Loop Spine (A1 Chain Controller)

**Version:** 1.0
**Status:** Planning
**Date:** 2026-02-02
**Priority:** P0 (Critical Path)

---

## 1. Overview

### 1.1 Why 4A0 Exists

**Verified Reality Correction:** The autonomous loop controller (chain-grade A1 sequencer with checkpoint seam) does not exist. The current `autonomous_build_cycle.py` is a mission implementation, not a resumable chain controller with proper checkpoint semantics.

Before CEO approval queue (4A) or backlog selection (4B) can be meaningful, the system needs a canonical sequencer that:
- Runs a deterministic chain: hydrate → policy → sequence steps → checkpoint → resume
- Can pause at checkpoint and persist state
- Can resume deterministically from checkpoint
- Emits stable artefacts (terminal packet, ledger records)
- Fails closed on dirty repo or policy violation

### 1.2 What This Phase Delivers

| Deliverable | Description |
|-------------|-------------|
| A1 Controller Module | `runtime/orchestration/loop/spine.py` |
| Minimal State Machine | States: INIT, RUNNING, CHECKPOINT, RESUMED, TERMINAL |
| Ledger Integration | Checkpoint state written to ledger |
| Checkpoint Seam | Pause contract - saves state, emits checkpoint packet |
| Resume Contract | Load checkpoint, validate policy hash, continue |
| Terminal Packet | Success/blocked/checkpoint outcome with deterministic format |

### 1.3 What This Phase Does NOT Include

- CEO queue backend (Phase 4A)
- Backlog selection (Phase 4B)
- Envelope expansion (Phase 4C/4D)
- Full autonomy (Phase 4E)
- New policies or governance documents

---

## 2. Orchestration Surface Clarification

**Canonical Sequencer Architecture:**

```
┌─────────────────────────────────────────────────┐
│            Loop Spine (A1 Controller)           │
│  - Canonical chain sequencer                    │
│  - Checkpoint/resume contract                   │
│  - Terminal packet emission                     │
└─────────────────┬───────────────────────────────┘
                  │ delegates to
                  ▼
┌─────────────────────────────────────────────────┐
│         Tier-2 Orchestrator (engine.py)         │
│  - Workflow execution (max 5 steps)             │
│  - Step-level state management                  │
│  - Mission dispatch                             │
└─────────────────┬───────────────────────────────┘
                  │ uses
                  ▼
┌─────────────────────────────────────────────────┐
│           Run Controller (run_controller.py)    │
│  - Kill switch check                            │
│  - Run lock management                          │
│  - Repo clean check                             │
└─────────────────────────────────────────────────┘
```

**Avoid "Two Engines" Drift:** Loop Spine is the sequencer; Orchestrator is the workflow executor; run_controller is lifecycle safety. They are layered, not competing.

---

## 3. TDD Acceptance Criteria

```gherkin
Feature: A1 Loop Spine (Chain Controller)
  As the autonomous build loop
  I want a canonical sequencer with checkpoint semantics
  So that I can pause, persist state, and resume deterministically

  Background:
    Given the LifeOS repository is clean
    And the ledger is initialized

  Scenario: Single chain execution to terminal
    Given a task spec is provided
    When the loop spine runs the chain
    Then it executes: hydrate → policy → design → build → review → steward
    And it emits a terminal packet with outcome PASS or BLOCKED
    And the ledger contains a complete attempt record
    And the terminal packet has deterministic field ordering

  Scenario: Checkpoint pauses execution
    Given a chain is running
    When a checkpoint trigger fires (e.g., ESCALATION_REQUESTED)
    Then execution pauses immediately
    And checkpoint state is persisted to ledger
    And a checkpoint packet is emitted to artifacts/
    And the process exits with code 0 (clean pause)

  Scenario: Resume from checkpoint deterministically
    Given a checkpoint exists from a previous run
    And the checkpoint has not been resolved
    When the loop spine is invoked with --resume
    Then it loads the checkpoint state
    And it validates the policy hash matches
    And it continues from the checkpoint step
    And it does NOT re-execute completed steps

  Scenario: Resume fails if policy changed
    Given a checkpoint exists with policy_hash "abc123"
    And the current policy_hash is "def456"
    When the loop spine attempts to resume
    Then it fails with POLICY_CHANGED_MID_RUN
    And it emits a terminal packet with BLOCKED outcome
    And the checkpoint is preserved (not deleted)

  Scenario: Dirty repo fails closed
    Given the repository has uncommitted changes
    When the loop spine is invoked
    Then it fails immediately with REPO_DIRTY
    And no steps are executed
    And no artefacts are emitted (fail-closed)

  Scenario: Checkpoint resolved triggers resume
    Given a checkpoint is pending CEO resolution
    And the CEO has marked it resolved (approved/rejected)
    When the loop spine checks for resolution
    Then it reads the resolution from the checkpoint seam
    And it resumes (if approved) or terminates (if rejected)
```

---

## 4. Atomic Tasklist

### T4A0-01: Define Spine State Machine

**File:** `runtime/orchestration/loop/spine.py`

- [ ] **T4A0-01a:** Define `SpineState` enum
- [ ] **T4A0-01b:** Define `CheckpointPacket` dataclass
- [ ] **T4A0-01c:** Define `TerminalPacket` dataclass

### T4A0-02: Implement LoopSpine Class

- [ ] **T4A0-02a:** Create `LoopSpine` class skeleton
- [ ] **T4A0-02b:** Implement `run(task_spec, resume_from)` method
- [ ] **T4A0-02c:** Implement `_checkpoint(trigger, step_index)` method
- [ ] **T4A0-02d:** Implement `_resume(checkpoint_id)` method
- [ ] **T4A0-02e:** Implement `_emit_terminal(outcome, reason)` method

### T4A0-03: Implement Checkpoint Seam

- [ ] **T4A0-03a:** Define checkpoint file format
- [ ] **T4A0-03b:** Implement `_save_checkpoint(packet)` method
- [ ] **T4A0-03c:** Implement `_load_checkpoint(checkpoint_id)` method
- [ ] **T4A0-03d:** Implement `_check_resolution(checkpoint)` method

### T4A0-04: Write Unit Tests

**File:** `runtime/tests/test_loop_spine.py`

- [ ] **T4A0-04a:** Test: single chain to terminal
- [ ] **T4A0-04b:** Test: checkpoint pauses execution
- [ ] **T4A0-04c:** Test: resume from checkpoint
- [ ] **T4A0-04d:** Test: resume fails on policy change
- [ ] **T4A0-04e:** Test: dirty repo fails closed
- [ ] **T4A0-04f:** Test: checkpoint resolution triggers resume

### T4A0-05: Artefact Output Contract

The spine emits these artefacts with stable, deterministic formatting:

| Artefact | Path | Format |
|----------|------|--------|
| Terminal Packet | `artifacts/terminal/TP_<run_id>.yaml` | YAML, sorted keys |
| Checkpoint Packet | `artifacts/checkpoints/CP_<run_id>_<step>.yaml` | YAML, sorted keys |
| Ledger Record | `artifacts/loop_state/attempt_ledger.jsonl` | JSONL, one record per line |
| Step Summary | `artifacts/steps/<run_id>_<step>.json` | JSON, sorted keys |

---

## 5. DoD (Definition of Done)

1. [ ] Single command runs one chain: `coo spine run <task_spec>` (task_spec is JSON file or inline JSON)
2. [ ] Can pause at checkpoint: checkpoint file emitted, process exits with code 2
3. [ ] Can resume deterministically: `coo spine resume <checkpoint_id>`
4. [ ] Emits stable artefacts: terminal packet, ledger records, step summaries
5. [ ] Fail-closed on dirty repo: no execution, no artefacts
6. [ ] All 6 TDD scenarios pass

---

## 6. Verification Checklist

- [ ] `pytest runtime/tests/test_loop_spine.py -v` - All tests pass
- [ ] `coo spine run '{"task":"test"}'` - Executes chain and emits artefacts
- [ ] `coo spine run task_spec.json` on dirty repo - Fails closed with no artefacts
- [ ] Checkpoint created on ESCALATION_REQUESTED trigger
- [ ] Resume from checkpoint works with matching policy
- [ ] Resume fails with policy hash mismatch (emits BLOCKED terminal)
- [ ] `coo spine --help` and `coo spine run --help` display correct usage

---

**END OF PHASE 4A0 PLAN**
