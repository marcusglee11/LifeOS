# COO Memory Seed — Stateful Content

Read this file at session start to bootstrap project awareness. This is the
flat-markdown companion to `memory_seed.md` (provisioning spec). Both serve
different consumers: this file serves the proxy COO (Claude Code during
burn-in) and any agent needing project context; `memory_seed.md` serves the
real COO (OpenClaw instance with structured memory).

---

## Project History (Key Milestones)

| Date | Milestone | Evidence |
|------|-----------|---------|
| 2026-01-16 | Phase 3 technical deliverables complete | Council ratification pending |
| 2026-01-26 | Trusted Builder Mode v1.1 ratified | Council Ruling |
| 2026-02-03 | Phase 4 (4A0-4D) merged to main | Commit 9f4ee41, 1327 tests |
| 2026-02-14 | E2E Spine Proof complete | run_20260214_053357, Emergency_Declaration_Protocol finalized |
| 2026-02-19 | Checkpoint/Resume E2E Proof | 6 integration tests |
| 2026-02-23 | Council V2 A1-A9 merged | CouncilFSMv2, shadow mode |
| 2026-02-27 | Burn-in Batch 1+2 complete | 40 new tests, 7 findings, 2147 total |
| 2026-02-28 | Worktree-First Build Architecture | start_build.py, close_build.py |
| 2026-03-01 | GitHub Actions Build Loop | CI automation |
| 2026-03-05 | COO Bootstrap campaign launched | Steps 1A-4G built in one day |
| 2026-03-06 | COO Bootstrap 8/9 steps merged | Step 2 merged (51ef1466 + eedb0fa0), Steps 5-6 pending |

## Active Objectives

- **OBJ-BOOTSTRAP**: Stand up operational COO — 8/9 infrastructure steps merged, Step 5 (burn-in) and 6 (live) pending.
- **OBJ-REVENUE**: First external content — LinkedIn posts + B5 Governance Guide. Not started; depends on COO operational.
- **OBJ-TECH-DEBT**: P1 backlog items — Bypass Monitoring, Semantic Guardrails, test_steward_runner fixes. Deferred to COO management.

## Current Campaign State

```
Campaign: COO-BOOTSTRAP
Objective: OBJ-BOOTSTRAP
Status: IN_PROGRESS (Step 5 preparation)

1. [DONE] Step 1A: Structured backlog — merged 23cd2143
2. [DONE] Step 1B: Delegation envelope — merged eb75f2e8
3. [DONE] Step 2: COO Brain — merged 51ef1466 + review fixes eedb0fa0
4. [DONE] Step 3D: Context/parser — merged cf7740f1
5. [DONE] Step 3E: Templates — merged 5a7425b3
6. [DONE] Step 3F: CLI commands — merged 1d6d208c
7. [DONE] Step 4G: State updater — merged 72548d7e
8. [PENDING] Step 5: Burn-in
9. [PENDING] Step 6: Live COO
```

## Agent Performance Patterns

| Provider | Strengths | Failure Modes | Notes |
|----------|-----------|---------------|-------|
| **Codex** | Bounded implementation, fast, good test coverage | Skips worktree isolation instructions; needs cwd passed explicitly | Built Steps 1A, 3E, 4G successfully |
| **Claude Code** | Complex architecture, multi-file reasoning, interactive | Slow on NTFS I/O (WSL); context window pressure on large reads | Built Steps 1B, 3D, 3F, review passes |
| **Gemini** | Analysis, content, risk assessment | Limited code execution capability | Used for council risk review |

Key lessons:
- Worktree isolation is a hard gate, not a soft instruction — pass `cwd=` to agents
- Never block handoffs on timing — use file paths or commit SHAs
- Two agents touching `.gitignore` on different branches causes merge conflicts — sequence or fold changes
- Primary repo stays in detached HEAD during multi-agent work — never write files there

## Architectural Decisions

- **COO invocation**: OpenClaw bridge (`runtime/agents/openclaw_bridge.py`), NOT CLIDispatch. CLIDispatch handles execution agents.
- **Backlog canonical source**: `config/tasks/backlog.yaml` (schema `backlog.v1`). `docs/11_admin/BACKLOG.md` is a derived shadow view.
- **Autonomy model**: 3 levels during burn-in (L0/L3/L4). L1/L2 deferred until Early Trust phase with evidence.
- **Fail-closed principle**: Unknown autonomy category defaults to L4 (escalate). No exceptions.
- **Shadow-first deprecation**: Manual markdown state files auto-regenerated as derived views during burn-in. Physical deletion only after Step 6 verified stable.
- **Git is the shared bus**: Commits, diffs, and files are the only shared memory between agents. No conversation history sharing.

## Delegation Envelope Summary

Source: `config/governance/delegation_envelope.yaml`

- **L0 (autonomous)**: Read operations, memory updates, analysis, status checks
- **L3 (propose and wait)**: Task dispatch, backlog changes, new work, reprioritization
- **L4 (escalate)**: Protected paths, strategy changes, budget above threshold, ambiguous scope, external commitments
- **Default**: L3 (burn-in conservative)
- **Fail-closed**: true
