# ARCH_LifeOS_Operating_Model_v0.3: The Shipping Edition

**Version:** 0.3  
**Status:** Architecture Proposal  
**Strategic Focus:** Minimal viable autonomy, then iterate.

---

## 1. Executive Summary

**The Problem:** LifeOS has extensive governance documentation, 316 passing tests, and zero autonomous operation. The operator (GL) remains the waterboy shuttling context between AI collaborators.

**The Goal:** One agent doing one thing end-to-end without human intervention. Then two things. Then patterns emerge.

**The Pivot from v0.2:** v0.2 proposed enterprise-grade infrastructure (Kubernetes, SLSA L3, Federated Agents, FinOps governance) for a single-user system. This is architectural overcapitalization. v0.3 proposes the minimum viable stack that achieves autonomy, with complexity added only when earned by actual bottlenecks.

**Success Metric:** GL wakes up to completed work he didn't manually orchestrate.

---

## 2. Architectural Principles

### 2.1. Complexity is Debt

Every component added is a component that can break, requires maintenance, and delays shipping. The architecture should be as simple as possible while achieving autonomy—and no simpler.

**Heuristic:** If you can't explain why a component is necessary in one sentence tied to a concrete problem, remove it.

### 2.2. Earn Your Infrastructure

| Trigger | Response |
|---------|----------|
| "We might need X" | Don't build X |
| "X broke twice this week" | Now build X |
| "X is a bottleneck" | Now optimize X |

### 2.3. One Path, Not Golden Paths

"Golden Paths" and Internal Developer Platforms serve teams with divergent needs. LifeOS has one user. There is one path: the one that works.

### 2.4. Governance Follows Capability

The existing governance framework is ahead of execution capability. New governance documentation is blocked until execution catches up. Govern what exists, not what might exist.

---

## 3. Technical Architecture

### 3.1. The Stack

```
┌─────────────────────────────────────────────────┐
│                    OPERATOR                      │
│              (GL - async oversight)              │
└─────────────────────┬───────────────────────────┘
                      │ reviews / approves
                      ▼
┌─────────────────────────────────────────────────┐
│                 ORCHESTRATOR                     │
│         (Single agent with API access)           │
│    Currently: OpenCode migrating from Antigravity│
└─────────────────────┬───────────────────────────┘
                      │ executes
                      ▼
┌─────────────────────────────────────────────────┐
│                   RUNTIME                        │
│     Git repo + GitHub Actions + test suite       │
└─────────────────────┬───────────────────────────┘
                      │ persists
                      ▼
┌─────────────────────────────────────────────────┐
│                    STATE                         │
│   Filesystem (repo) + lightweight DB if needed   │
└─────────────────────────────────────────────────┘
```

**That's it.** No Kubernetes. No Knative. No Terraform modules. No OPA policy engine. No vector database. No GraphRAG.

### 3.2. Component Specifications

**Orchestrator (OpenCode)**
- Has API access (the capability Antigravity lacked)
- Receives task via structured prompt or queue
- Executes using standard tools (file I/O, git, shell)
- Commits results to repo
- Signals completion

**Runtime (GitHub Actions)**
- Triggered by commits or schedule
- Runs test suite (316 existing tests)
- Deploys/executes approved changes
- Posts results to notification channel

**State (Git Repository)**
- Single source of truth
- All changes via commits (auditable by default)
- No separate "Life Database" to sync

**Governance (Embedded, Not Layered)**
- Approval gates are GitHub PR reviews, not OPA policies
- Cost limits are API key quotas, not FinOps dashboards
- Safety constraints are test assertions, not policy-as-code

### 3.3. What's Explicitly Excluded (For Now)

| Component | Why Excluded | Trigger to Add |
|-----------|--------------|----------------|
| Kubernetes | Orchestration overhead exceeds value at n=1 agents | Multiple long-running agents competing for resources |
| Vector DB / RAG | No retrieval bottleneck yet | Agent struggles with context window limits |
| Policy-as-Code (OPA) | Test assertions + PR review sufficient | Automated decisions with financial/safety impact bypass human review |
| IDP (Backstage) | One user, one path | Never (this is a team tool) |
| Terraform/IaC | No infrastructure to manage | Cloud resources beyond single VM |
| Multi-agent federation | Coordination overhead without proven single-agent success | One agent is bottlenecked and task is cleanly separable |

---

## 4. The Autonomy Ladder

Progress is measured by climbing rungs, not by architectural sophistication.

### Rung 0: Manual Orchestration (Current State)
GL shuttles context between Claude, ChatGPT, and specialized agents. Every action requires human initiation.

### Rung 1: Triggered Autonomy
Agent executes a defined task when triggered (cron, webhook, or GL command). Human reviews output async.

**First target:** Doc steward hygiene—lint, format, update timestamps, flag inconsistencies. Low stakes, high repetition, clear success criteria.

### Rung 2: Supervised Chains
Agent executes multi-step workflows. Human approves at checkpoints (e.g., PR review before merge).

**Target:** Build cycle—receive instruction, implement, test, submit PR, await approval, merge.

### Rung 3: Delegated Domains
Agent owns a domain end-to-end within defined constraints. Human intervenes by exception.

**Target:** Repository maintenance—dependency updates, test coverage gaps, documentation sync.

### Rung 4: Autonomous Initiative
Agent identifies tasks, proposes them, and executes approved proposals without GL defining the work.

**Target:** TBD—this emerges from Rung 3 patterns.

---

## 5. Implementation Plan

### Phase 1: Prove the Loop (Week 1-2)

**Objective:** One autonomous execution, any task, any stakes.

**Actions:**
1. Validate OpenCode API connectivity
2. Define single task with clear input/output (doc hygiene recommended)
3. Write GitHub Action that: triggers agent → agent executes → commits result → runs tests
4. Execute manually once. Then schedule.

**Exit Criteria:** Scheduled job runs overnight, GL wakes to committed changes that pass tests.

### Phase 2: Raise the Stakes (Week 3-4)

**Objective:** Autonomous execution of substantive work.

**Actions:**
1. Extend to multi-file changes
2. Add PR workflow (agent commits to branch, opens PR, awaits review)
3. Implement notification on completion/failure
4. Document failure modes encountered

**Exit Criteria:** Agent submits PR with working code change. GL reviews and merges.

### Phase 3: Chain Tasks (Week 5-8)

**Objective:** Multi-step workflows with checkpoints.

**Actions:**
1. Define 2-3 step workflow (e.g., receive spec → implement → test → PR)
2. Implement checkpoint notifications
3. Add rollback capability on failure
4. Begin extracting patterns into reusable prompts/templates

**Exit Criteria:** Agent completes chained workflow with single initial trigger.

### Phase 4: Expand Scope (Month 3+)

**Objective:** Second and third autonomous domains.

**Actions:**
1. Identify next domain based on Phase 1-3 learnings
2. Apply proven patterns
3. Evaluate whether multi-agent coordination is now justified
4. Add infrastructure only if concrete bottleneck demands it

**Exit Criteria:** Multiple domains operating autonomously with GL in async oversight role.

---

## 6. Risk Register

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Agent produces broken code | High | Test suite gates all merges. PR review for non-trivial changes. |
| API costs spike | Medium | Hard quota on API keys. Alert at 50% monthly budget. |
| Agent hallucinates task completion | Medium | Require artifact (commit, file, log) as proof of execution. |
| Scope creep into enterprise architecture | High | This document. Refer to §3.3 exclusion triggers. |
| GL over-engineers instead of shipping | High | Phase 1 has 2-week timebox. Ship or retro. |

---

## 7. What This Document Is Not

**Not a platform strategy.** There is no platform. There is a repo and an agent.

**Not a team topology.** There is no team. There is GL and his AI collaborators.

**Not a long-term architecture.** This is the minimum structure to achieve autonomy. Architecture evolves from working systems, not from documents.

**Not comprehensive.** It deliberately excludes most of what a "complete" operating model would contain. Completeness is not the goal. Shipping is.

---

## 8. Success Criteria for This Document

This document succeeds if:

1. Phase 1 completes within 2 weeks
2. GL spends less time on infrastructure and more time on substantive work
3. The excluded components (§3.3) remain excluded for at least 3 months
4. Autonomy ladder rungs are climbed, not skipped

This document fails if:

1. It spawns child documents before Phase 1 ships
2. Components are added "just in case"
3. GL is still the waterboy in 30 days

---

## Appendix A: Migration Notes (Antigravity → OpenCode)

Current state: Antigravity is build agent but lacks API access for autonomous operation.

Migration approach:
1. OpenCode assumes doc steward role first (low-risk validation)
2. Parallel operation during transition
3. Antigravity deprecated once OpenCode proves equivalent capability
4. COO orchestrator layer added only if multi-agent coordination becomes necessary

---

## Appendix B: Governance Integration

Existing governance specs (F3, F4, F7, etc.) remain authoritative. This operating model does not replace governance—it provides execution capability for governance to govern.

Integration points:
- Council review process applies to significant changes (Rung 2+)
- Structured packet format used for agent ↔ agent communication when multi-agent is justified
- Audit trail is git history (commit log, PR discussion, CI results)

New governance documentation is paused until Rung 2 is achieved. Govern what runs, not what might run.
