# LifeOS Router & Antigravity Executor Adapter v0.1

**Status**: Spec parked. Not for immediate implementation. Revisit after current Tier-2 hardening and Mission Registry work stabilises.

## 1. Purpose & Scope

Define a Router Layer and Executor Adapter concept for LifeOS.

Provide a future architecture that:
- Makes LifeOS the central thinking + operations hub.
- Allows pluggable executors (Antigravity now, others later).
- Eliminates the user as the "message bus" between planner and executor.

This spec is directional, not an implementation plan. It is meant to be shelved and revisited once the current runtime work is stable.

## 2. Goals

- LifeOS can route:
    - Thoughts, specs, build plans, issues, council packets.
    - To the correct subsystem (runtime, docs, council, executor).
- LifeOS can interact with executors via a stable, executor-agnostic protocol.
- Antigravity can be used as an executor through an adapter, without redesigning higher layers.
- Future executors can replace Antigravity without changing LifeOS’s core logic.

## 3. Non-Goals (for v0.1)

- No requirement to implement:
    - Actual automatic thread/project creation in ChatGPT.
    - Real-time routing automation.
    - A concrete API/CLI to Antigravity.
- No requirement to define full data schemas; only outline core shapes and responsibilities.

## 4. High-Level Architecture

### Layers

**L0 — Router Layer (Routing Engine)**
- Classifies incoming "things" (messages, specs, instructions).
- Decides which LifeOS subsystem should own them:
    - Architecture
    - COO Runtime
    - Council
    - Docs/Index
    - Issues/Backlog
    - Executor (missions)

**L1 — COO Runtime & Orchestration**
- Mission registry, orchestrator, builder, daily loop.
- Fix Packs, Implementation Packets, CRPs, test harnesses.
- Enforces invariants (determinism, anti-failure rules, envelopes).
- Produces Mission Packets that can be executed by an executor.

**L2 — Executor Adapter**
- Presents a stable interface to LifeOS:
    - `run_mission(packet)`
    - `read(path)`
    - `write(path, content)`
    - `run_tests(suite)`
- Hides executor-specific mechanics (Antigravity today, API-based agent tomorrow).

**L3 — Concrete Executors**
- Antigravity v0: manual relay via the user.
- Antigravity v1: scripts + inbox/outbox conventions.
- Executor v2+: direct API/CLI driven agent(s).

## 5. Router Layer — Conceptual Model

The Router is a classification and dispatch engine operating over:

**Inputs**: user messages, AI outputs, specs, review findings.

**Artefact types**:
- Specs (Fix Packs, runtime specs, product docs)
- Build plans / Implementation Plans
- Council Review Packets (CRPs)
- Issues / Risks / Decisions
- Missions to executors
- Notes / ideation / sandbox content

**Core responsibilities**:
- Classify content into lanes, e.g.:
    - Architecture
    - Runtime/Operations
    - Council/Governance
    - Docs/Stewardship
    - Executor/Missions
    - Sandbox/Exploration
- Propose or enforce routing actions, such as:
    - "Create/update spec at path X"
    - "Log issue in Issues Register"
    - "Prepare Mission Packet for executor"
    - "Prepare CRP for Council"
- Maintain indexing hooks, e.g.:
    - Summaries of key decisions.
    - Links to canonical docs.
    - References to issues and Fix Packs.

v0.1 expectation: routing is mostly conceptual and manual (you and ChatGPT agree on lanes); later revisions can automate classification and actions.

## 6. Antigravity as Executor — Adapter Concept

**Problem**: Antigravity is currently a powerful executor with no callable API/CLI from LifeOS. All coordination is mediated by the user.

**Solution**: Define an Executor Adapter layer so LifeOS talks to a stable interface, and Antigravity is just one implementation.

### 6.1. Executor Interface (LifeOS-Facing, conceptual)

At a high level:

```python
Executor.run_mission(mission_packet)
Executor.run_tests(test_suite_descriptor)
Executor.read(path) -> content
Executor.write(path, content)
Executor.apply_fixpack(fp_spec_path)
Executor.report() -> status/artefacts
```

**Mission Packet (conceptual fields)**:
- `id`: stable identifier.
- `type`: e.g. fixpack, build, refactor, doc_stewardship.
- `inputs`: paths to canonical specs/docs in `/LifeOS/docs/...`.
- `constraints`: determinism, no I/O, etc.
- `expected_outputs`: e.g. modified files, new docs, test results.

### 6.2. Antigravity Adapter Phases

**v0 — Manual Relay (current reality)**
- LifeOS (ChatGPT) produces Mission Packets in text.
- User copies packet into Antigravity as a natural language instruction.
- User copies results back into LifeOS context.
- Adapter is conceptual only; no tooling.

**v1 — File-Based Inbox/Outbox (semi-automated)**
- LifeOS writes Mission Packets into a defined directory, e.g.: `/runtime/missions/inbox/`
- Antigravity is instructed to:
    - Read from inbox.
    - Execute missions (modify repo, run tests).
    - Write results to `/runtime/missions/outbox/`.
- User’s role reduces to: "Tell Antigravity to process inbox."

**v2+ — API/CLI-Backed Executor**
- An agent or tool exposes API/CLI commands mapping to `Executor.*` operations.
- A LifeOS controller (outside ChatGPT or via tools) calls the executor directly.
- User is no longer in the loop for normal missions.

**Key invariant**: LifeOS core logic (router + runtime) does not change across v0 → v2; only the adapter implementation changes.

## 7. Risks / Open Questions (for later)

- How to encode mission packets in a way Antigravity can reliably interpret.
- How much of the router’s logic should live in code vs in specs.
- How to avoid overcomplicating the adapter before an actual API exists.
- How to surface mission and executor state back to the user in a clean way (dashboards, logs, etc.).
