# Archive: 2026-02-14 Consolidation

## Archive Policy (Immutable)

Archived files are historical snapshots and **MUST NOT be edited**.

**Only allowed modifications inside `archive/`:**
- Typo fixes in the archive README itself
- Mechanical path corrections if repo structure changes (rare)

## Disposition Table

| File | Reason archived | Superseded by | Last-known date | Notes (do not resurrect) |
|------|----------------|---------------|-----------------|--------------------------|
| `ARCHITECTURE_DIAGRAMS.md` | Stale architectural reference | Current runtime architecture in codebase | 2026-01-28 | References unbuilt Council Agent; outdated design |
| `Autonomy Project Baseline.md` | Obsolete autonomy report | E2E Spine Proof (2026-02-14) | 2026-02-02 | Superseded by validated E2E spine proof |
| `Indexing_Test_v0.1.md` | Test artifact | N/A (test artifact) | 2026-01-28 | One-time test file; no ongoing relevance |
| `LifeOS Autonomous Build Loop System - Status Report 20260202.md` | Obsolete autonomy report | E2E Spine Proof (2026-02-14) | 2026-02-02 | Superseded by validated E2E spine proof |
| `PROJECT_ADMIN_SUMMARY.md` | Stale project snapshot | `LIFEOS_STATE.md` (auto-updated) | 2026-01-28 | Duplicate of canonical auto-updated STATE |
| `PROJECT_DEPENDENCY_GRAPH.md` | Stale project snapshot | `LIFEOS_STATE.md` + `BACKLOG.md` | 2026-01-28 | Duplicate of canonical auto-updated STATE/BACKLOG |
| `PROJECT_GANTT_CHART.md` | Stale project snapshot | `LIFEOS_STATE.md` + `BACKLOG.md` | 2026-01-28 | Duplicate of canonical auto-updated STATE/BACKLOG |
| `PROJECT_MASTER_TASK_LIST.md` | Stale project snapshot | `BACKLOG.md` (auto-updated) | 2026-01-28 | Duplicate of canonical auto-updated BACKLOG |
| `PROJECT_STATUS_v1.0.md` | Stale project snapshot | `LIFEOS_STATE.md` (auto-updated) | 2026-01-28 | Duplicate of canonical auto-updated STATE |
| `PROJECT_TASKS_v1.0.jsonl` | Stale project snapshot | `BACKLOG.md` (auto-updated) | 2026-01-28 | Duplicate of canonical auto-updated BACKLOG |
| `Roadmap Fully Autonomous Build Loop20260202.md` | Obsolete autonomy report | E2E Spine Proof (2026-02-14) | 2026-02-02 | Superseded by validated E2E spine proof |

## Context

This consolidation was performed as part of the `docs/11_admin` Consolidation, Alignment & Automation initiative (2026-02-14). The admin directory was reduced from 22 files to a canonical allowlist, with historical documents archived for reference only.

**Authority:** `docs/11_admin/LIFEOS_STATE.md` and `docs/11_admin/BACKLOG.md` are the canonical, auto-updated sources of truth for project state and backlog. These archived files represent point-in-time snapshots that are no longer maintained.
