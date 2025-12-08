
# LifeOS_Recursive_Improvement_Architecture_v0.1

**Version:** v0.1  
**Status:** Draft — for Council and architect review  
**Intended Placement:** `/LifeOS/docs/03_runtime/LifeOS_Recursive_Improvement_Architecture_v0.1.md`  

---

## 1. Purpose & Scope

This document defines the architecture for the **internal recursive self-improvement system** of LifeOS.

Scope:

- How the **COO Runtime** and associated internal frameworks (specs, protocols, prompts, tests) improve themselves over time.
- How to do this while preserving:
  - **Determinism** per runtime version.
  - **Auditability** of all changes.
  - **Governance** via Improvement Proposals (IPs) and the AI Council.

Out of scope:

- External “life” agents (e.g. trading bots, opportunity sniffers) except as missions executed by the runtime.
- Business/product roadmaps.

The goal is to create a **repeatable, governed improvement loop** around a deterministic core, not to make the core itself stochastic.

---

## 2. Design Principles

1. **Determinism per version**  
   - For any given runtime version:  
     `same inputs + same state → same outputs`.  
   - All LLM/tool calls are frozen under a Freeze Protocol and replayable.

2. **Spec- and protocol-first**  
   - Behaviour is defined by explicit specs and protocols (LifeOS Core, COO Runtime spec, StepGate, Council Protocol, DAP, etc.).
   - Code, prompts, and workflows are implementations of those specs.

3. **Governed change only**  
   - No change to specs, runtime code, prompts, or core workflows occurs outside a governed process:
     - Improvement Proposal (IP) → Council review → Fix Plan → tests/replays → promotion.

4. **Full traceability**  
   - Every change is traceable back to:
     - Evidence and telemetry.
     - A specific IP.
     - Council decisions.
     - Test/replay results.
     - Version and commit references.

5. **Replayability**  
   - Past missions can be re-run against new runtime versions to:
     - Validate proposed changes.
     - Detect regressions.

6. **Separation of concerns**  
   - Execution, telemetry, improvement decision-making, and versioning are separated into distinct layers and components.

---

## 3. Layered Architecture Overview

The recursive improvement system is structured into four layers:

1. **Execution Layer (COO Runtime)**
2. **Telemetry & Evidence Layer**
3. **Improvement Layer**
4. **Versioning & Artefact Layer**

Recursive self-improvement emerges from **continuous interaction** between these layers.

### 3.1 Execution Layer

Responsible for **deterministic mission execution**:

- Implements the mission state machine.
- Applies StepGate and Council rules.
- Freezes all non-deterministic model/tool outputs.
- Writes complete execution traces.

### 3.2 Telemetry & Evidence Layer

Responsible for **capturing and structuring evidence**:

- Mission logs and state transitions.
- Metrics and derived aggregations.
- Human and system annotations of problems and friction.

### 3.3 Improvement Layer

Responsible for **figuring out what to change and how**:

- Scans logs and metrics for improvement opportunities.
- Creates and manages IPs.
- Runs Council reviews.
- Generates Fix Plans.
- Orchestrates implementation and validation.

### 3.4 Versioning & Artefact Layer

Responsible for **managing versions and change history**:

- Tracks all versioned artefacts (specs, code, prompts, tests).
- Manages runtime versions and promotion.
- Maintains a change ledger for audit and rollback.

---

## 4. Core Components (by Layer)

### 4.1 Execution Layer Components

#### 4.1.1 Mission Orchestrator (COO Runtime Core)

- Implements the **deterministic mission state machine**.
- Reads the current runtime version (code/spec/prompt set) from the Versioning Layer.
- Executes missions under:
  - StepGate Protocol.
  - Council invocation policies.
  - Tool/model routing policies.
- Ensures that all LLM calls:
  - Are performed in a sandbox.
  - Are frozen (AMU₀ snapshot, Freeze Protocol).
  - Are recorded for replay.

#### 4.1.2 Council Orchestrator (Internal Harness)

- Wraps Council operations as first-class missions.
- Given an input artefact (e.g. an IP, a spec change, a risky decision), runs configured Council roles:
  - Architect, Risk, Alignment, Red-Team, Simplicity, etc.
- Applies the Council Protocol:
  - Role-specific prompts.
  - Reviewer template enforcement.
  - Decision synthesis and gating.
- Produces a deterministic **Council Decision Record** that is written to the Runtime DB.

#### 4.1.3 Tool & Model Router

- Reads model/tool configuration for the current runtime version.
- Routes calls to external LLMs/tools.
- Keeps deterministic boundary by:
  - Freezing outputs.
  - Logging all calls.
  - Ensuring no external network calls occur outside controlled paths.

---

### 4.2 Telemetry & Evidence Layer Components

#### 4.2.1 Mission Logger

- Records for each mission:
  - Mission metadata (type, intent, timestamps).
  - Full state transition history (including rollbacks and divergences).
  - All frozen model outputs and tool results.
  - Council invocations and decisions.
  - Human interventions (overrides, corrections, tags).

- Guarantees that the mission trace is sufficient to:
  - Replay the mission.
  - Diagnose failures and friction.

#### 4.2.2 Metrics & Aggregation Engine

- Derives metrics from mission logs, such as:
  - Mission success/failure rates.
  - Average number of transitions per mission type.
  - Rollbacks/divergences per mission type.
  - Human minutes/annotations per mission.
  - Council escalation rates, council disagreement patterns.

- Stores aggregated metrics in the Runtime DB for use by:
  - The Improvement Scanner.
  - Dashboards and reporting.

#### 4.2.3 Annotation Interface (Human & System)

- Provides a structured way for:
  - You (the user) to tag missions and behaviours (“too much donkey work”, “spec violation”, “confusing output”).
  - System detectors to tag patterns (e.g. “repeated failure in Gate 3 for mission type X”).

- Normalises annotations into a standard format and writes them to the DB as **evidence candidates**.

---

### 4.3 Improvement Layer Components

#### 4.3.1 Improvement Scanner

- Periodically or event-driven scans:
  - Mission logs.
  - Metrics.
  - Annotations.

- Identifies **Improvement Candidates** based on:
  - Recurrent mission failures for specific mission types.
  - High human intervention / friction.
  - Anomalous metric trends.
  - Frequent Council flags of spec violations.

- Groups related evidence into candidate records:
  - Problem class.
  - Severity/impact.
  - Affected mission types.
  - Example missions/logs.

- For each candidate, triggers the IP Manager to create a formal IP.

#### 4.3.2 IP Manager

- Converts candidates (and ad-hoc ideas) into **Improvement Proposals (IPs)** using a defined IP schema:
  - `ip_proposals`
  - `ip_problem_evidence`
  - `ip_root_causes` (optional at MVP)
  - `ip_proposed_changes`
  - `ip_test_plans`
  - `ip_council_reviews`
  - `ip_version_links`
  - `ip_events`
  - `ip_metrics` (expected vs observed, optional at MVP)

- Enforces the IP lifecycle (state machine), e.g.:
  - `DRAFT → UNDER_REVIEW → APPROVED → IN_PROGRESS → AWAITING_TESTS → COMPLETED`  
    with `REJECTED` / `ABANDONED` paths.

- Coordinates with the Council Orchestrator and Test & Replay Engine.

#### 4.3.3 IP–Council Gateway

- Takes an IP and runs a Council review mission:
  - Architect: structural and architectural coherence.
  - Alignment: compliance with LifeOS core principles.
  - Risk: potential new failure modes/regressions.
  - Red-Team: adversarial scenarios.
  - Simplicity/Ops: operational complexity, overengineering.

- Writes Council outputs into `ip_council_reviews`.
- Updates IP status and `decision_outcome` with:
  - Approve / Reject / Revise.
  - Summary rationale.

#### 4.3.4 Fix Plan Generator

- For approved IPs:
  - Generates a **Fix Plan** specifying:
    - Exact artefacts to modify (specs, code, prompts, tests, workflows).
    - Nature of the modification (adding, refactoring, constraining).
    - Associated test plans and replay sets.
  - Writes details into:
    - `ip_proposed_changes`
    - `ip_test_plans`
    - Baseline `ip_metrics` (current performance).

- Produces a deterministic, machine- and human-readable Fix Plan that can be consumed by a builder agent.

#### 4.3.5 Builder Agent Interface (e.g. Antigravity)

- Orchestrates external builder agents according to Fix Plans:
  - Provides artefacts, context, and clear instructions.
  - Receives updated artefacts (specs, code, prompts, tests).
  - Ensures changes are constrained to the planned scope.

- Integrates with the Artefact Registry and Version Manager:
  - Records updated artefact versions.
  - Writes `ip_version_links` (old → new version mapping).

#### 4.3.6 Test & Replay Engine

- Validates candidate runtime versions created by applying Fix Plans.

- Executes:
  - Unit test suites.
  - System tests.
  - Replays of selected historical missions:
    - Using AMU₀ snapshots and frozen inputs/outputs where applicable.
    - Comparing behaviour for determinism and quality.

- Produces:
  - Pass/fail results.
  - Observed metrics (`ip_metrics` with `OBSERVED` phase).

- Feeds results back to:
  - IP Manager (to mark IP `COMPLETED` or flag regression).
  - Council (for optional final review on high-impact changes).

---

### 4.4 Versioning & Artefact Layer Components

#### 4.4.1 Artefact Registry

- Maintains a canonical catalogue of all versioned artefacts:
  - Specs and protocol documents (LifeOS Core, COO Runtime, StepGate, Council, DAP, etc.).
  - Runtime code modules and packages.
  - Prompt libraries (Council roles, mission templates).
  - Test suites and replay sets.

- Each artefact entry includes:
  - Logical identifier and path.
  - Version (vX.Y).
  - Optional commit hash (if Git-backed).
  - Type (SPEC, CODE, PROMPT, TEST, WORKFLOW).

#### 4.4.2 Runtime Version Manager

- Manages **runtime versions**, e.g. `coo-runtime v1.3`:

- For each runtime version, defines:
  - The set of artefact versions composing it.
  - Default model/tool configuration.
  - Applicable policies (e.g. which Council roles to use by default).

- Responsible for:
  - Promoting a candidate runtime version to “current” when tests pass and governance approves.
  - Maintaining previous versions for replay and rollback.

#### 4.4.3 Change Ledger

- Records every significant change event, including:
  - IP IDs.
  - Runtime version promotions and rollbacks.
  - Artefact version changes and their links (`ip_version_links`).
  - Summary of test and replay results.
  - Council decisions and rationales.

- Enables:
  - Full auditability.
  - Reconstruction of the system’s evolution.

---

## 5. Primary Data Stores

1. **Runtime Database (SQLite)**
   - Mission and state tables.
   - Logs and annotations.
   - Metrics and aggregations.
   - IP tables (proposals, evidence, reviews, test plans, metrics, events, version links).
   - Version and configuration metadata.

2. **Artefact Repository**
   - Filesystem, likely Git-backed.
   - Stores content of:
     - Specs and protocol documents.
     - Code.
     - Prompts.
     - Tests and replay fixtures.
   - Linked to Runtime DB via:
     - Artefact Registry.
     - `ip_version_links`.
     - Runtime Version Manager.

3. **Model & Tool Configuration Store**
   - Static configuration files (e.g. YAML/JSON) versioned with the runtime.
   - Describes:
     - Available models and tools.
     - Routing policies and constraints by mission type and risk level.

---

## 6. Key Flows

### 6.1 Normal Mission Execution Flow

1. **Mission creation**
   - Mission Orchestrator reads the current runtime version.
   - Loads relevant policies (StepGate, Council rules, tool/model routing).

2. **Execution**
   - Mission proceeds as a deterministic state machine.
   - Council invoked as needed via Council Orchestrator.
   - All model/tool calls are frozen and logged.

3. **Telemetry capture**
   - Mission Logger records full trace.
   - Metrics Engine updates aggregates.
   - Annotations may be added by user or automated detectors.

4. **Completion**
   - Mission result stored.
   - Execution trace available for replay and analysis.

---

### 6.2 Self-Improvement (IP) Flow

1. **Detection**
   - Improvement Scanner analyses logs, metrics, annotations.
   - Produces Improvement Candidates representing clusters of issues.

2. **IP creation**
   - IP Manager converts candidates into formal IPs:
     - Problem description, evidence, and (optionally) initial root cause hypotheses.
   - IP moves to `UNDER_REVIEW`.

3. **Council review**
   - IP–Council Gateway runs a Council mission on the IP.
   - Council verdicts and comments stored in `ip_council_reviews`.
   - IP status updated: `APPROVED` / `REJECTED` / `REVISE`.

4. **Fix Planning**
   - For approved IPs, Fix Plan Generator:
     - Specifies targeted artefact changes.
     - Defines test plans and replay sets.
     - Captures baseline metrics.

5. **Implementation**
   - Builder Agent Interface:
     - Orchestrates Antigravity or equivalent builder.
     - Applies changes.
     - Updates artefact versions and records them in `ip_version_links`.

6. **Validation**
   - Test & Replay Engine:
     - Executes test suites and replays.
     - Records observed metrics and outcomes.
   - Optionally triggers another Council check for high-impact IPs.

7. **Promotion**
   - Runtime Version Manager:
     - Promotes candidate runtime version to “current” if acceptance criteria are met.
     - Logs promotion in Change Ledger.

8. **Back to execution**
   - New missions now run under the improved runtime version.
   - Telemetry from these missions feeds back into the Improvement Scanner.

---

## 7. Determinism & Governance Invariants

The architecture enforces the following invariants:

1. **Determinism per version**
   - For a fixed runtime version:
     - All missions are deterministic given the same inputs and state.
     - All stochastic external calls are captured as frozen outputs.

2. **No ungoverned self-modification**
   - Any change to:
     - Runtime code.
     - Specs and protocols.
     - Prompt libraries.
     - Core workflows (StepGate, Council)  
     must be:
     - Motivated by an IP.
     - Reviewed by Council.
     - Validated by tests and replays.
     - Recorded in the Change Ledger.

3. **Replayability**
   - Past missions remain re-runnable against:
     - The original runtime version (for audit).
     - New versions (for regression testing).

4. **Traceable evolution**
   - For any runtime version or artefact version, it must be possible to:
     - Identify all IPs that influenced it.
     - Inspect all Council decisions.
     - Review tests and metrics associated with its creation.

---

## 8. Review Prompts & Open Questions

This v0.1 architecture is intended for structured review. Key questions:

1. **Component boundaries**
   - Are any components over-specified or under-specified?

2. **IP lifecycle complexity**
   - Is the lifecycle minimal but sufficient?

3. **Telemetry sufficiency**
   - Are additional metrics or signals needed?

4. **Builder sandboxing**
   - Should builder agents operate in a separate sandbox?

5. **Scaling**
   - Should policies vary by mission type or risk level?

6. **MVP scope**
   - What is the smallest viable subset required to run the first full recursive improvement cycle?

---

**End of document.**
