# ARCH_LifeOS_Operating_Model_v0.4

**Version:** 0.4  
**Date:** 2026-01-03  
**Status:** Active  
**Author:** GL (with AI collaboration)

---

> [!IMPORTANT]
> **Non-Canonical Artifact**
> This document describes a conceptual, WIP target operating model. It is **not** canonical and is **not** part of the formal LifeOS authority chain. Future governance decisions cannot cite this document as binding authority.

---

## 1. Purpose and Scope

### 1.1. What is LifeOS?

LifeOS is a governance-first personal operating system designed to extend one person's operational capacity through AI. The goal is to convert high-level intent into auditable, autonomous action—reducing the manual effort required to coordinate between AI tools, manage routine tasks, and maintain complex systems.

LifeOS is not a product for distribution. It is infrastructure for a single operator (GL) to expand his effective reach across work, finances, and life administration.

### 1.2. What This Document Covers

This document defines the operating model for LifeOS build automation: how AI agents receive instructions, execute work, and commit results without continuous human intervention.

It does not cover:
- The full LifeOS technical architecture (see: Technical Architecture v1.2)
- Governance specifications for council review (see: F3, F4, F7 specs)
- Life domain applications (health, finance, productivity agents)

### 1.3. Current State

| Dimension | Status |
|-----------|--------|
| Codebase | Functional Python implementation with 316 passing tests across Tier-1 and Tier-2 components |
| Documentation | Extensive governance specs, some ahead of implementation |
| Autonomous execution | **Validated as of 2026-01-03** — see §2 |
| Daily operation | Manual orchestration between AI collaborators |

The core challenge: GL currently acts as the "waterboy" shuttling context between ChatGPT (thinking partner), Claude (execution partner), and specialized agents. Every action requires human initiation. The goal is to invert this—humans define intent, agents execute autonomously, humans review async.

---

## 2. Validated Foundation

On 2026-01-03, the following capability was verified:

**An AI agent (OpenCode) can run headless via CI, execute a task, create files, and commit to a git repository without human intervention during execution.**

### 2.1. Proof of Concept Results

| Element | Evidence |
|---------|----------|
| Trigger | `scripts/opencode_ci_runner.py` |
| Agent | OpenCode server at `http://127.0.0.1:4096` |
| Session | `ses_47c563db0ffeG8ZRFXgNddZI4o` |
| Output | File `ci_proof.txt` created with content "Verified" |
| Commit | `51ef5dba` — "CI: OpenCode verification commit" |
| Author | `OpenCode Robot <robot@lifeos.local>` |

Execution log confirmed: server ready → session created → prompt sent → agent responded → file verified → commit verified → **CI INTEGRATION TEST PASSED**.

### 2.2. What This Proves

1. **Headless execution works.** The agent does not require an interactive terminal or human presence.
2. **Git integration works.** The agent can commit changes with proper attribution.
3. **The architecture is viable.** The stack described in §4 is not speculative—it has been demonstrated.

### 2.3. What Remains Unproven

1. **Multi-step workflows.** The proof shows a single task; chained tasks with checkpoints are untested.
2. **Test suite integration.** The agent committed a file but did not run the existing 316 tests.
3. **Failure recovery.** Behavior on error, timeout, or invalid output is undefined.
4. **Substantive work.** Creating a proof file is trivial; modifying production code is not.

---

## 3. Architectural Principles

### 3.1. Complexity is Debt

Every component added is a component that can break, requires maintenance, and delays shipping. The architecture must be as simple as possible while achieving autonomy—and no simpler.

**Decision heuristic:** If a component cannot be justified in one sentence tied to a concrete, current problem, it is excluded.

### 3.2. Earn Your Infrastructure

Infrastructure is added reactively, not speculatively.

| Signal | Response |
|--------|----------|
| "We might need X" | Do not build X |
| "X broke twice this week" | Now build X |
| "X is a bottleneck blocking progress" | Now optimize X |

### 3.3. Governance Follows Capability

LifeOS has extensive governance documentation (council review processes, structured packet formats, approval workflows). This governance framework is currently ahead of execution capability.

**Constraint:** New governance documentation is paused until autonomous execution reaches Rung 2 (see §5). Govern what exists, not what might exist.

### 3.4. Auditability by Default

All agent actions must produce artifacts that can be reviewed after the fact. Git commits, CI logs, and test results form the audit trail. No "trust me, I did it" claims.

---

## 4. Technical Architecture

### 4.1. System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         OPERATOR                             │
│                    (GL — async oversight)                    │
│                                                              │
│   Defines tasks • Reviews PRs • Approves merges • Exceptions │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ intent / review
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR                           │
│                   (OpenCode via CI Runner)                   │
│                                                              │
│   Receives prompts • Executes via tools • Commits results    │
│   API endpoint: http://127.0.0.1:4096                        │
│   Trigger: scripts/opencode_ci_runner.py                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ file I/O / git / shell
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         RUNTIME                              │
│              (Git Repository + GitHub Actions)               │
│                                                              │
│   Source of truth • CI/CD pipeline • Test execution          │
│   Test suite: 316 tests (Tier-1 + Tier-2)                    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ persists
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                          STATE                               │
│                (Filesystem + Git History)                    │
│                                                              │
│   All state is files • All changes are commits • Auditable   │
└─────────────────────────────────────────────────────────────┘
```

### 4.2. Component Specifications

#### 4.2.1. Orchestrator: OpenCode

OpenCode is an AI coding agent with API access, enabling headless (non-interactive) operation.

| Property | Value |
|----------|-------|
| Server endpoint | `http://127.0.0.1:4096` |
| Trigger mechanism | `scripts/opencode_ci_runner.py` |
| Capabilities | File read/write, shell commands, git operations |
| Commit identity | `OpenCode Robot <robot@lifeos.local>` |

**Why OpenCode (not Antigravity):** The previous build agent (Antigravity) lacked API access, requiring interactive terminal sessions. This blocked autonomous operation. OpenCode's API enables the CI runner pattern demonstrated in §2.

**Migration status:** OpenCode is now primary for autonomous tasks. Antigravity remains available for interactive sessions during transition.

#### 4.2.2. Runtime: Git + GitHub Actions

| Function | Implementation |
|----------|----------------|
| Source of truth | Git repository (GitHub-hosted) |
| CI trigger | Push to branch, scheduled cron, or manual dispatch |
| Test execution | `pytest` running 316 existing tests |
| Deployment | Merge to main after PR approval |

**Workflow pattern:**
1. CI runner triggers OpenCode with task prompt
2. OpenCode executes, commits to feature branch
3. GitHub Action runs test suite
4. If tests pass: PR opened for review
5. GL reviews async, approves or requests changes
6. Merge to main on approval

#### 4.2.3. State: Filesystem as Database

LifeOS does not use a separate database. All state is stored as files in the repository.

- **Configuration:** YAML/JSON files in `/config`
- **Documentation:** Markdown in `/docs`
- **Code:** Python in `/src`
- **Audit trail:** Git commit history

This eliminates sync problems between code and data, ensures all changes are versioned, and makes the system trivially portable.

### 4.3. Explicitly Excluded Components

The following are intentionally not part of the current architecture. Each has a defined trigger condition for future inclusion.

| Component | Rationale for Exclusion | Trigger to Reconsider |
|-----------|------------------------|----------------------|
| **Kubernetes** | Container orchestration overhead exceeds value for single-agent workloads | Multiple long-running agents competing for compute resources |
| **Vector database / RAG** | No retrieval bottleneck observed; context window sufficient | Agent consistently fails due to context limits on large codebases |
| **Policy-as-Code (OPA)** | Test assertions + PR review provide sufficient safety gates | Automated decisions with financial or safety impact must bypass human review |
| **Terraform / IaC** | No cloud infrastructure to manage; runs on local/single VM | Deployment to multiple cloud resources required |
| **Multi-agent federation** | Single-agent capability unproven; coordination adds complexity | One agent is bottlenecked and task is cleanly separable |
| **Internal Developer Platform** | Single user, single path; IDP solves team divergence problems | Never (wrong tool for single-operator system) |

---

## 5. The Autonomy Ladder

Progress is measured by capability level, not architectural sophistication. Each rung represents increased agent autonomy and decreased human involvement in routine execution.

### Rung 0: Manual Orchestration
**Status:** Current baseline (pre-2026-01-03)

Human initiates every action. AI tools are reactive—they respond to prompts but do not act independently. GL manually shuttles context between Claude, ChatGPT, and other agents.

**Human role:** Initiator, executor, coordinator
**Agent role:** Responder

### Rung 1: Triggered Autonomy
**Status:** Validated (2026-01-03)

Agent executes a defined task when triggered by CI, cron, or command. Human reviews output asynchronously. The agent cannot initiate work, but can complete work without supervision during execution.

**Human role:** Trigger, async reviewer
**Agent role:** Executor

**Demonstrated capability:** OpenCode created file and committed via CI runner.

**Next target task:** Documentation hygiene—lint markdown, update timestamps, flag broken links. Low stakes, high repetition, clear success criteria.

### Rung 2: Supervised Chains
**Status:** Not yet attempted

Agent executes multi-step workflows with human approval at defined checkpoints. For example: receive spec → implement → run tests → open PR → await review → merge on approval.

**Human role:** Checkpoint approver, exception handler
**Agent role:** Workflow executor

**Target task:** Build cycle for small features—agent receives a specification, implements it, validates with tests, and submits for review.

**Governance integration:** Council review process (F3 spec) applies to significant changes at this rung.

### Rung 3: Delegated Domains
**Status:** Future

Agent owns a domain end-to-end within defined constraints. Human intervenes by exception, not by routine. Agent handles the normal case autonomously.

**Human role:** Exception handler, constraint setter
**Agent role:** Domain owner

**Target domains:** Repository maintenance (dependency updates, test coverage, doc sync), routine administrative tasks.

### Rung 4: Autonomous Initiative
**Status:** Future

Agent identifies tasks worth doing, proposes them, and executes approved proposals. Human defines goals and constraints; agent determines actions.

**Human role:** Goal setter, proposal approver
**Agent role:** Initiator, planner, executor

This rung emerges from patterns discovered at Rung 3. Premature to specify further.

---

## 6. Implementation Plan

### Phase 1: Validate the Loop (Weeks 1-2)
**Objective:** Demonstrate end-to-end autonomous execution with test verification.

| Action | Status | Exit Criterion |
|--------|--------|----------------|
| Validate OpenCode CI connectivity | ✓ Complete | Server responds, session created |
| Execute trivial task (create file) | ✓ Complete | File exists, commit verified |
| Integrate test suite execution | Pending | CI runs `pytest`, results logged |
| Execute substantive task (doc hygiene) | Pending | Meaningful changes, tests pass |
| Schedule overnight run | Pending | GL wakes to committed, passing changes |

**Phase 1 exit criteria:** Scheduled job runs without human intervention; GL reviews results next morning.

### Phase 2: Raise the Stakes (Weeks 3-4)
**Objective:** Autonomous execution of multi-file, testable changes with PR workflow.

| Action | Exit Criterion |
|--------|----------------|
| Extend to multi-file modifications | Agent modifies 2+ files in single task |
| Implement PR workflow | Agent commits to branch, opens PR |
| Add notification on completion/failure | GL receives alert (email, webhook, etc.) |
| Document observed failure modes | Failure catalog with mitigations |

**Phase 2 exit criteria:** Agent submits PR with working code; GL reviews and merges.

### Phase 3: Supervised Chains (Weeks 5-8)
**Objective:** Multi-step workflows with checkpoint approval.

| Action | Exit Criterion |
|--------|----------------|
| Define 2-3 step workflow | Spec exists with clear handoff points |
| Implement checkpoint notifications | GL notified at each checkpoint |
| Add rollback capability | Failed step reverts cleanly |
| Extract reusable prompt templates | Documented patterns for common tasks |

**Phase 3 exit criteria:** Agent completes chained workflow from single initial trigger; Rung 2 achieved.

### Phase 4: Expand Scope (Month 3+)
**Objective:** Multiple autonomous domains operating in parallel.

| Action | Exit Criterion |
|--------|----------------|
| Identify second domain | Based on Phase 1-3 learnings |
| Apply proven patterns | Reuse templates and workflows |
| Evaluate multi-agent need | Documented decision with rationale |
| Add infrastructure only if earned | Per §4.3 trigger conditions |

**Phase 4 exit criteria:** 2+ domains operating autonomously; GL in async oversight role for routine operations.

---

## 7. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Agent produces broken code** | High | Medium | Test suite gates all merges; PR review for non-trivial changes; rollback capability |
| **API costs exceed budget** | Medium | Medium | Hard quota on API keys; alert at 50% monthly threshold; fallback to smaller models |
| **Agent hallucinates task completion** | Medium | High | Require artifact proof (commit, file, log); verification step in CI runner |
| **Scope creep into enterprise architecture** | High | High | This document; explicit exclusion triggers in §4.3; 3-month hold on excluded components |
| **Operator over-engineers instead of shipping** | High | High | Phase 1 has 2-week timebox; ship or retrospective |
| **Single point of failure (OpenCode)** | Medium | High | Antigravity remains available as fallback; architecture is agent-agnostic |
| **Security: agent with commit access** | Medium | High | Commits to branches only; merge requires human approval; audit via git history |

---

## 8. Governance Integration

This operating model exists within the broader LifeOS governance framework. It does not replace governance—it provides the execution capability that governance oversees.

### 8.1. Relationship to Existing Specs

| Spec | Relevance to This Document |
|------|---------------------------|
| **F3 (Council Review)** | Applies to significant changes at Rung 2+; agent-submitted PRs for substantial features require council review |
| **F4 (Inter-Agent Communication)** | Structured packet format used if/when multi-agent coordination is added |
| **F7 (Audit Requirements)** | Git history + CI logs satisfy audit trail requirements |

### 8.2. Governance Pause

Per principle §3.3, new governance documentation is paused until Rung 2 is achieved. Current specs are sufficient to govern the execution capability being built. Additional governance would be premature.

### 8.3. Audit Trail

All agent actions produce auditable artifacts:

| Action | Audit Artifact |
|--------|---------------|
| File creation/modification | Git diff in commit |
| Task execution | CI runner logs |
| Test results | GitHub Actions output |
| Approval decisions | PR review comments |
| Merge | Git merge commit with approver |

No separate audit log is required; git history is the audit log.

---

## 9. Success and Failure Criteria

### This Document Succeeds If:

1. Phase 1 completes within 2 weeks of validation date (by 2026-01-17)
2. GL spends less time on orchestration, more time on substantive decisions
3. Excluded components (§4.3) remain excluded for at least 3 months
4. Autonomy ladder rungs are climbed sequentially, not skipped
5. The architecture remains simple enough to explain in 5 minutes

### This Document Fails If:

1. It spawns child architecture documents before Phase 2 completes
2. Components are added speculatively ("just in case")
3. GL is still manually orchestrating routine tasks after 30 days
4. The test suite is bypassed or ignored
5. No autonomous work ships in January 2026

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **Agent** | An AI system capable of executing tasks via API (e.g., OpenCode, Claude, ChatGPT) |
| **Antigravity** | Previous build agent; lacks API access; being replaced by OpenCode |
| **CI Runner** | Script that triggers agent execution in headless mode (`scripts/opencode_ci_runner.py`) |
| **Council Review** | Governance process where multiple AI roles review significant changes (per F3 spec) |
| **GL** | The operator; single user of LifeOS |
| **Governance** | Framework of specs and processes ensuring safe, auditable agent operation |
| **Headless** | Execution without interactive terminal; agent runs via API only |
| **OpenCode** | Current build agent; has API access enabling autonomous operation |
| **Rung** | A level on the Autonomy Ladder representing agent capability |
| **Waterboy** | Manual orchestration pattern where human shuttles context between AI tools |

---

## Appendix A: OpenCode CI Runner Reference

**Location:** `scripts/opencode_ci_runner.py`

**Function:** Starts OpenCode server, creates session, sends task prompt, verifies output, commits result.

**Invocation:**
```bash
python scripts/opencode_ci_runner.py --task "description of task"
```

**Server endpoint:** `http://127.0.0.1:4096`

**Session management:** Runner creates new session per invocation; sessions are not persistent.

**Commit identity:**
```
Author: OpenCode Robot <robot@lifeos.local>
```

---

## Appendix B: Migration from Antigravity

### B.1. Background

Antigravity served as the initial build agent and document steward for LifeOS. It has extensive context on the codebase and governance specs but lacks API access—requiring interactive terminal sessions that block autonomous operation.

### B.2. Migration Approach

| Phase | Action | Status |
|-------|--------|--------|
| 1 | Validate OpenCode CI capability | ✓ Complete |
| 2 | OpenCode assumes doc steward role | Pending |
| 3 | Parallel operation during transition | Pending |
| 4 | Antigravity deprecated for autonomous tasks | Future |

### B.3. Contingency

If OpenCode proves insufficient for complex tasks, Antigravity remains available for interactive sessions. The architecture is agent-agnostic—the CI runner pattern can wrap any agent with API access.

---

## Appendix C: Document History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | — | Initial concept (not documented) |
| 0.2 | 2026-01 | Enterprise architecture proposal (Kubernetes, SLSA, federated agents) — rejected as overcapitalized |
| 0.3 | 2026-01-03 | Minimal viable architecture — validated but incomplete |
| 0.4 | 2026-01-03 | Comprehensive operating model incorporating CI validation proof |

---

*End of document.*
