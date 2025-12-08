# LifeOS v1 Hybrid Technical Architecture  
Version: v0.1-DRAFT  
Status: Draft — non-canonical until Governance Council approval  
Basis: Council Hybrid Architecture Ruling on Q1 + Fix Plan v1.0 (G1–P5), DAP v2.0, Runtime v1 direction, StepGate constraints  
File: LifeOS_v1_Hybrid_Tech_Architecture_v0.1-DRAFT.md

---

## 1. Context & Scope

### 1.1 Purpose of This Document

This document defines the **LifeOS v1 Hybrid Technical Architecture** that operationalises the Council ruling:

- Deterministic core + Git-based canonical memory + LLMs at the edge.
- Constitutional governance, freeze protocol, and explicit capability/sandbox model.
- Strong auditability, reproducibility, and UX simplicity.
- A directory and infrastructure pattern that is usable by both humans and autonomous agents (“directory as context”).

It is a **non-canonical architectural draft** that:

- Translates the ruling + Fix Plan into a concrete module and dataflow design.
- Provides a reference for Runtime, Governance, and Productisation projects.
- Serves as an input for a future Governance Council review to become a v1.x canonical spec.

### 1.2 In-Scope

- Overall LifeOS v1 system architecture.
- Deterministic runtime core and its state model.
- Git-backed canonical state spine and artefact lifecycle.
- LLM integration boundary (edge) and artefact-based interaction model.
- Freeze, replay, and rollback semantics at an architectural level (not full formal spec).
- Governance hooks: constitutional layer, capability model, policy injection, kill switches.
- Observability, logging, and auditability hooks.
- UX abstraction: CLI-first, config (YAML) layer, basic user mental model.
- **Agent-centric infrastructure patterns**:
  - Directory layout as externalised memory for agents.
  - Canonicalisation and adversarial validation infrastructure (e.g. `freeze` and `debate` tools).

### 1.3 Out-of-Scope

- Fully detailed API definitions or schemas for each module.
- Formal cryptographic primitives (algorithms, key lengths, concrete key management).
- Fully detailed Governance Council procedures and role prompts.
- v2 distributed/clustered deployments (only forward-compatibility considerations).
- Implementation-specific choices beyond indicative examples (e.g. exact languages, frameworks).

### 1.4 References

This architecture assumes and references, but does not restate:

- Council Hybrid Architecture Ruling on Q1 + Fix Plan v1.0 (G1–P5).
- LifeOS — Core Specification (constitutional and programme framing).
- DAP v2.0 — Deterministic Artefact Protocol.
- StepGate Protocol — communication and gating between CEO and agents.
- Runtime v1 direction (deterministic Python + SQLite-based runner, local Git repo).
- Governance Council and AI Council specifications (for rulings, CRPs, and charters).
- Emerging **.agent / guidance** patterns for agent-centric repositories.

---

## 2. Requirements Envelope

### 2.1 Musts (Hard Constraints)

Derived from the Council Fix Plan (G1–P5) and existing specs:

1. **Hybrid Architecture Commitment**
   - Deterministic execution core; all side-effects originate in deterministic components.
   - Git-backed canonical state spine for artefacts and configuration.
   - LLMs operate strictly at the edge, producing artefacts that deterministic components interpret.

2. **Constitution & Governance (G1–G3)**
   - Constitutional rules and arbitration logic must be represented in a signed, immutable structure.
   - Any change to constitutional rules, core policies, or model baselines requires:
     - Multi-party human approval.
     - An auditable record (proposal → review → decision).
   - Meta-governance process must be defined for altering governance processes themselves.

3. **Deterministic Core & State (D1–D6)**
   - **Freeze protocol** must have a formal spec (total ordering, conflicts, atomicity, concurrency behaviour).
   - All canonical state transitions must be:
     - Logged and tied to cryptographic hashes (commits and, where used, lock-manifests).
     - Reconstructable from Git plus deterministic re-execution.
   - Deterministic behaviour must be testable via automated suites (replay and invariants).

4. **LLM Boundary & Behaviour (L1–L4)**
   - All LLM interactions:
     - Go through a dedicated LLM Gateway.
     - Are expressed as structured calls with explicit schemas (inputs, outputs, error channels).
   - LLM outputs must be cached as artefacts; deterministic replay uses cached outputs, not fresh calls.
   - LLMs must not directly execute code or perform side-effects; they only emit artefacts.
   - A capability/sandbox model must restrict access to filesystem, network, external APIs.

5. **Validation, Observability, and Provenance (V1–V4, O1–O3)**
   - Schema + invariant validation for all critical artefacts and state transitions.
   - Tests and schemas must be treated as high-integrity artefacts (immutable once frozen).
   - Audit logs must capture:
     - Who/what initiated actions.
     - How state changed (input→output, before/after hashes).
     - LLM prompts, responses, and model versions.

6. **Product & UX Constraints (P1–P5)**
   - CLI-first, with a small set of commands and a primary YAML (or similar) config file.
   - “Small first success” must be achievable by a solo user with minimal setup.
   - Internal complexity must be hidden behind simple abstractions; expert controls are opt-in.
   - Architecture must allow future productisation (e.g. SaaS, on-prem), without rewrite.

7. **Git as Canonical Spine**
   - Git (or an equivalent append-only, content-addressable store) is the canonical memory for:
     - Artefacts.
     - Configuration.
     - Freeze snapshots and tags.
   - No mutable state outside Git and local runtime DBs is considered canonical.

8. **Deterministic Guidance for Agents**
   - Project guidance and constitutional prompts for agents must:
     - Live at stable, well-known paths (e.g. `guidance/AGENTS.md`, `.agent/`).
     - Be machine-ingestable and version-controlled.
   - Application of guidance (e.g. adversarial validation, freeze) must follow deterministic, repeatable workflows.

### 2.2 Shoulds (Strong Preferences)

- Use commodity, inspectable components (e.g. Git CLI, SQLite, local filesystem, Docker containers).
- Keep runtime deployment as simple as possible (single-machine, single-repo v1).
- Make it easy to integrate external tools (IDEs, editors, additional test runners).
- Prefer textual, diffable artefacts over opaque binaries.
- Provide explicit hooks for future multi-project / multi-tenant scenarios.
- Encourage **directory-as-context** patterns to simplify agent retrieval of relevant knowledge.

### 2.3 Open Choices (Design Freedom)

- Internal factoring of planes into modules (e.g. whether Freeze Engine is standalone or part of Runtime Orchestrator).
- Exact naming, layout, and granularity of internal services vs libraries.
- Concrete cryptographic primitives and key management systems (within the constraints above).
- Exact layout of the Git repo (branches/tags strategy, directory structures) beyond high-level requirements.
- Choice of orchestration mechanism (simple process runner vs more advanced job queue) for v1, as long as determinism is maintained.

---

## 3. Architecture Overview

### 3.1 High-Level System View

LifeOS v1 consists of:

1. **Deterministic Runtime Core**  
   - Executes missions and tasks according to a declarative configuration and mission plan.
   - Uses a local state database (e.g. SQLite) and local filesystem workspace.
   - Orchestrates freeze operations, tests, replays, and artefact lifecycle.

2. **Git-Based Canonical State Spine**  
   - Stores canonical artefacts, configuration, and frozen test suites.
   - Captures freeze snapshots and tags for replay and rollback.
   - Provides the ground truth for council reviews and audits.

3. **LLM Edge Layer (LLM Gateway)**  
   - Mediates all calls to external LLMs.
   - Enforces schemas, capability limits, and logging for prompts/responses.
   - Converts stochastic outputs into structured artefacts persisted into Git.

4. **Governance & Constitution Plane**  
   - Encodes constitutional rules and policies as signed artefacts.
   - Provides read-only policy injection into the runtime for v1.
   - Serves as the interface to Governance Council, which approves canonical changes.

5. **Agent-Centric Infrastructure Layer**  
   - Defines a repeatable **repository scaffold** (e.g. `.agent/`, `guidance/`, `specs/`) to externalise memory, plans, and tools for agents.
   - Provides canonicalisation and adversarial validation tools to keep specs aligned with guidance.

6. **Observability & UX**  
   - CLI surfacing missions and operations.
   - Logging and telemetry for each run.
   - Minimal but sufficient views for users to inspect mission state, artefacts, and history.

### 3.2 Major Subsystems

- **Runtime Orchestrator**
- **Task/Job Engine**
- **Freeze & Replay Engine**
- **Artefact Store & Workspace Manager**
- **Git Integration & Snapshot Manager**
- **LLM Gateway & Artefact Cache**
- **Governance Interface Layer**
- **Policy Engine**
- **Canonicalisation Subsystem (Freeze Tool + Lock Manifest)**
- **Adversarial Validation Subsystem (Debate Tool)**
- **Agent Guidance & Context Store (`guidance/`, `.agent/` etc.)**
- **Observability & Telemetry Service**
- **CLI & Configuration Layer**

### 3.3 Planes / Layers

Conceptual planes and their mapping:

- **Constitution / Governance Plane**
  - Governance Interface Layer.
  - Policy Engine (read-only for v1).
  - Adversarial Validation Subsystem (logical home, even if implemented via LLM Edge).

- **Forge / Runtime Plane**
  - Runtime Orchestrator, Task Engine, Freeze & Replay Engine.

- **Ledger / State Plane**
  - Artefact Store, Git Integration, Snapshot Manager.
  - Canonicalisation Subsystem (lock manifest generation and verification).

- **LLM Edge Plane**
  - LLM Gateway, Prompt/Response Templates, Artefact Cache.
  - Execution surface for the Adversarial Validation Subsystem.

- **UX / Product Plane**
  - CLI, YAML Config Layer, optional UI adapters.
  - Make-like or workflow entrypoints (e.g. `init`, `freeze`, `verify`, `debate`) as a thin UX over the infra.

- **Agent Context Plane (cross-cutting)**
  - `guidance/` and `.agent/` directories.
  - Stores guidance, memory, and plans in predictable locations for agents.

---

## 4. Modules & Planes

### 4.1 Module Inventory

| Module                          | Plane                          | Responsibility                                                        | Trust Level              |
|---------------------------------|--------------------------------|------------------------------------------------------------------------|--------------------------|
| Governance Interface            | Constitution/Governance        | Load constitutional rules, policies, model baselines                   | High (read-only in v1)  |
| Policy Engine                   | Constitution/Governance        | Evaluate policies, expose constraints to runtime                       | High                     |
| Adversarial Validation Subsystem| Governance + LLM Edge          | Run adversarial reviews of specs/artefacts against guidance            | Medium (uses LLMs, gated)|
| Runtime Orchestrator            | Forge/Runtime                  | Coordinate mission runs, steps, freeze points                          | High                     |
| Task/Job Engine                 | Forge/Runtime                  | Execute deterministic tasks, manage subprocesses                       | High                     |
| Freeze & Replay Engine          | Forge/Runtime + Ledger         | Implement freeze protocol, replay and rollback operations              | High                     |
| Artefact Store                  | Ledger/State                   | Manage artefact lifecycle in workspace                                 | High                     |
| Snapshot Manager                | Ledger/State                   | Capture and tag snapshots, prepare Git commits                         | High                     |
| Git Integration Layer           | Ledger/State                   | Commit, tag, and fetch canonical artefacts and configs                 | High                     |
| Canonicalisation Subsystem      | Ledger/State                   | Generate and verify lock manifests over frozen artefacts               | High                     |
| LLM Gateway                     | LLM Edge                       | Mediate LLM calls, enforce schema and capability model                 | Medium (stochastic IO)   |
| LLM Artefact Cache              | LLM Edge / Ledger              | Persist and retrieve LLM outputs for replay                            | High                     |
| Agent Guidance & Context Store  | Agent Context / Governance     | Hold `AGENTS.md`, templates, memory, and plans for agents              | High (read-mostly)       |
| Observability Service           | Cross-plane                    | Logging, metrics, correlation IDs                                      | High                     |
| CLI Frontend                    | UX/Product                     | User commands, mission invocation, inspection                          | Medium                   |
| Config Loader                   | UX/Product + Ledger            | Load and validate configs (YAML) from Git workspace                    | High                     |
| Workspace Manager               | Forge/Runtime + Ledger         | Prepare per-mission working directories, clean up                      | High                     |

### 4.2 Governance / Constitution Plane

- **Governance Interface**
  - Reads canonical constitutional artefacts from Git.
  - Exposes them to runtime as read-only views (e.g. config objects).
  - Ensures only signed and verified artefacts are accepted.

- **Policy Engine**
  - Evaluates:
    - Which operations require governance approval.
    - Which LLM models are permitted.
    - Constraints on freeze, rollback, and external integrations.
  - Provides a query interface to runtime (“Is operation X permitted under policy Y?”).

- **Adversarial Validation Subsystem**
  - Consumes:
    - Project guidance (e.g. `guidance/AGENTS.md`).
    - Draft specs or artefacts (e.g. under `specs/drafts/`).
  - Uses LLM Gateway to run deterministic, adversarial reviews (temperature=0, structured output).
  - Produces:
    - Machine-parsable critique artefacts (e.g. JSON logs).
    - PASS/FAIL decisions for use in CI or local workflows.
  - Acts as a mandatory gate (by policy) before specs advance from Draft → Frozen.

### 4.3 Runtime / Execution Plane

- **Runtime Orchestrator**
  - Parses mission definitions (from CLI and config).
  - Plans run steps, including LLM invocation steps and freeze points.
  - Interacts with Task Engine, Freeze Engine, Artefact Store.

- **Task/Job Engine**
  - Runs deterministic tasks (scripts, tests, build steps).
  - Captures execution metadata (start/end, exit codes, logs).
  - Integrates with Workspace Manager for local paths.

- **Freeze & Replay Engine**
  - Provides operations: `freeze`, `replay`, `rollback`, `compare`.
  - Coordinates snapshot capture with Snapshot Manager and Git Integration.
  - Ensures freeze semantics (no further mutation of frozen artefacts).

### 4.4 Artefact & State Plane

- **Artefact Store**
  - Manages artefacts in the local workspace:
    - Draft, Proposed, Frozen, Canonical (mirroring Git state).
  - Applies DAP v2.0 rules to artefact creation and naming.
  - May mirror repo layout patterns such as:
    - `specs/drafts/`, `specs/frozen/`, `specs/templates/`.

- **Snapshot Manager**
  - Builds snapshot records that:
    - Capture config, artefacts, test results, and LLM outputs.
    - Are ready to be committed as atomic units.

- **Git Integration Layer**
  - Implements canonical operations:
    - Commit, tag, branch for freeze snapshots.
  - Ensures consistency between workspace and repo.
  - Prevents non-protocol direct pushes (e.g. by enforcing patterns in CLI usage).

- **Canonicalisation Subsystem**
  - Generates a **lock manifest** (e.g. `manifest.lock`) mapping frozen file paths to cryptographic hashes.
  - Supports a `freeze` mode:
    - Hashes all files under the frozen spec directory.
    - Writes a sorted, deterministic manifest.
  - Supports a `verify` mode:
    - Recomputes hashes and compares with the lock manifest.
    - Flags added/removed/changed files to detect drift or tampering.

### 4.5 LLM Edge Plane

- **LLM Gateway**
  - Accepts high-level requests from Runtime Orchestrator (“Generate test plan for X”, “Summarise logs”).
  - Encodes them as structured prompts with:
    - Explicit schemas for expected responses.
    - Model version and configuration.
  - Logs all prompts/responses with correlation IDs and commit hashes.

- **LLM Artefact Cache**
  - Stores LLM responses as artefacts (e.g. JSON, Markdown).
  - Indexes them by request ID, model, and input hash.
  - Ensures deterministic replay uses cached responses.

- **Adversarial Validation Execution**
  - Runs the Validator persona via the LLM Gateway.
  - Uses deterministic sampling (temperature=0) and provider fallbacks where appropriate.
  - Emits structured JSON suitable for machine-gated CI.

### 4.6 UX / Product Plane

- **CLI Frontend**
  - Provides commands such as:
    - `lifeos init`, `lifeos run`, `lifeos freeze`, `lifeos replay`, `lifeos status`.
    - For infra-centric repos, may also expose `freeze`, `verify`, `debate` entrypoints as convenience wrappers.
  - Maps user intent to mission definitions and runtime operations.

- **Config Loader**
  - Loads `lifeos.yaml` (or equivalent) from the repo.
  - Validates against configuration schema.
  - Resolves environment-specific overrides in a deterministic way.

- **Workspace Manager**
  - Prepares a temporary workspace per mission (directories, symlinks).
  - Ensures clean environments and handles clean-up after runs.

- **Agent Context Patterns**
  - Optionally enforces conventions such as:
    - `.agent/memory`, `.agent/plans`, `.agent/tools` for machine-centric state.
    - `guidance/AGENTS.md`, `guidance/ARCHITECTURE.md`, `guidance/STYLES.md` as constitutional documents.

---

## 5. Dataflows & Interfaces

### 5.1 End-to-End Flow: Typical Mission

1. **Intent Capture**
   - User runs `lifeos run <mission>` with optional flags.
   - CLI reads configuration from Git-tracked files.

2. **Mission Planning**
   - Runtime Orchestrator:
     - Validates mission definition.
     - Optionally calls LLM Gateway to refine steps (LLM outputs stored as artefacts).

3. **Execution**
   - Task Engine executes steps deterministically:
     - Uses workspace with defined inputs.
     - Logs actions and results via Observability.

4. **Validation & Freeze**
   - Runtime Orchestrator invokes tests.
   - On success, calls Freeze & Replay Engine to:
     - Capture snapshot via Snapshot Manager.
     - Create freeze artefacts (reports, manifests).
     - Commit and tag via Git Integration.
   - Canonicalisation Subsystem:
     - Generates or updates the lock manifest over frozen specs/state.
     - Optionally runs a `verify` step to ensure clean state before and/or after freeze.

5. **Governance Handoff (Optional)**
   - Freeze snapshot and artefacts become candidates for Governance review.
   - Governance Interface exposes them as read-only inputs for council.
   - Adversarial Validation Subsystem may be invoked on key specs prior to council.

6. **Replay / Comparison**
   - Later runs use `lifeos replay`:
     - Rebuild environment.
     - Use cached LLM artefacts.
     - Compare results with previous snapshots.

### 5.2 Artefact Lifecycle

Stages:

1. **Draft**
   - Created during active missions or ideation, editable.
   - May live under repo paths such as `specs/drafts/`.

2. **Proposed**
   - Candidate outputs for freeze; subject to validation/tests and adversarial review.

3. **Adversarially-Reviewed**
   - Has passed Adversarial Validation Subsystem (status PASS, score threshold).
   - Critique logs stored (e.g. `logs/debates/`), forming part of the audit trail.

4. **Frozen**
   - Passed tests; freeze snapshot captured.
   - Included in canonicalisation lock manifest.
   - Immutable in workspace and Git (enforced by policy/tools).

5. **Canonical**
   - Approved by Governance Council (if applicable).
   - Marked/tagged as “official” baseline.

6. **Archived**
   - Retired artefacts; preserved for audit, not active.

Transitions are handled by Runtime Orchestrator + Freeze Engine + Adversarial Validation Subsystem, with Git Integration and Canonicalisation enforcing immutability for Frozen/Canonical artefacts.

### 5.3 Interfaces Between Key Modules

- **Runtime Orchestrator ↔ Task Engine**
  - API: submit tasks, receive results.
  - Data: step definitions, execution metadata.

- **Runtime Orchestrator ↔ Freeze & Replay Engine**
  - API: `freeze(snapshot_spec)`, `replay(snapshot_id)`, `rollback(snapshot_id)`.
  - Data: snapshot manifests, run IDs, commit hashes.

- **Freeze & Replay Engine ↔ Snapshot Manager**
  - API: `create_snapshot(run_context)`, `load_snapshot(id)`.
  - Data: snapshot bundles (config, artefacts, test results, LLM outputs).

- **Snapshot Manager ↔ Git Integration**
  - API: `commit(snapshot_bundle)`, `tag(snapshot_id)`.
  - Data: tree of files and metadata, commit messages.

- **Git Integration ↔ Canonicalisation Subsystem**
  - The Canonicalisation Subsystem operates over the frozen spec/state directory:
    - Uses the filesystem view anchored to Git working tree.
    - Writes/read `manifest.lock` as a versioned artefact.

- **Runtime / Artefact Store ↔ LLM Gateway**
  - API: `request_llm(task_type, input_payload, schema_ref)`.
  - Data: structured request/response; references to artefact IDs.

- **Adversarial Validation Subsystem ↔ LLM Gateway**
  - Sends deterministic prompt chains composed of:
    - Guidance content (e.g. `AGENTS.md`).
    - Spec content.
  - Receives structured JSON critiques.

- **Governance Interface ↔ Runtime**
  - API: `is_allowed(operation, context)`, `get_policies()`, `get_constitution_version()`.
  - Data: policy and constitution objects derived from signed artefacts.

### 5.4 External Integrations

- **Local Git CLI**
  - Used by Git Integration Layer.

- **Filesystem**
  - Workspace directories, artefact storage.

- **LLM Providers**
  - Accessed only via LLM Gateway with strict schemas and logging.
  - May be abstracted via libraries (e.g. provider-agnostic clients) without changing architectural role.

- **Optional: Container Runtime**
  - If used, Task Engine may launch containers for isolation, but this is a design choice, not a hard requirement.

---

## 6. Determinism & Replay

### 6.1 Determinism Model

- Deterministic behaviour is defined as:
  - Given the same:
    - Mission definition,
    - Configuration and environment,
    - Set of artefacts (including cached LLM outputs),
  - The runtime must produce identical outputs (artefacts, logs, exit states).

- Non-deterministic elements (LLMs, wall-clock time, randomness) must:
  - Be converted into artefacts with explicit identifiers.
  - Be captured as part of snapshots for replay.

- **Guidance determinism**:
  - The effect of project guidance on agents must be reproducible:
    - Same `AGENTS.md` + same spec input → same adversarial critique (within practical limits).
    - Enforced via temperature=0.0, constrained output formats, and clear schemas.

### 6.2 Replay Semantics

- `lifeos replay <snapshot_id>`:
  - Reconstructs the environment and inputs dictated by the snapshot.
  - Uses cached LLM artefacts referenced by the snapshot.
  - Re-runs deterministic steps and produces a new run report.
  - Compares key invariants (artefact hashes, test outcomes) to original snapshot.

- Replays are logged and can be compared across environments (e.g. dev vs CI).

### 6.3 Freeze Protocol Integration

- Freeze protocol defines:
  - Points at which state can be frozen.
  - Constraints:
    - No pending mutable tasks.
    - All tests and validations passed.
  - Required outputs:
    - Snapshot manifest.
    - Artefact registry.
    - Commit and tag operations.
    - Updated lock manifest (if using canonicalisation subsystem).

- Freeze Engine ensures:
  - Single total order per repo for freeze events.
  - Concurrency control (e.g. lock file or Git branch strategy) to avoid conflicting freezes.

- Canonicalisation Subsystem:
  - Provides **file integrity monitoring** over frozen specs.
  - Allows infra or CI to assert: “Working tree matches frozen manifest” before running sensitive operations.

### 6.4 Rollback & Recovery

- Rollback operations:
  - `rollback(snapshot_id)`:
    - Restores workspace to that snapshot’s state.
    - Optionally creates a new snapshot describing the rollback action itself.
  - Governance policies may:
    - Require approvals for rollback beyond certain scopes.
    - Forbid rollback of specific canonical snapshots without council review.

- Lock manifest and Git history together provide:
  - Ability to detect tampering (lock mismatch, history rewrite).
  - Basis for recovery to last known-good freeze.

---

## 7. Security, Governance & Observability Hooks

### 7.1 Threat Model Summary

Primary threats:

- LLM prompt injection and artefact poisoning.
- Git history tampering (force-push, rebase, history rewrite).
- Unauthorised modifications to constitutional or policy artefacts.
- Runtime misconfiguration or policy bypass.
- Silent failures of logging and observability.
- Agent-level drift due to inconsistent or missing guidance.

### 7.2 Security Anchors

- **Constitutional Artefacts**
  - Signed and verified before use.
  - Stored in a dedicated directory under Git with stricter review rules.

- **Git History**
  - Freeze commits tagged and never rewritten.
  - Recommended: server-side or repo-level protections against history rewrites for critical branches.

- **Canonicalisation Lock Manifest**
  - Serves as an additional anchor over frozen specs.
  - Verifying the manifest can detect out-of-band changes or corruption.

- **Configuration**
  - Config artefacts validated against schemas before use.
  - High-risk config changes can be flagged for governance review.

- **LLM Gateway**
  - Whitelisted models and endpoints only.
  - Tokens and credentials managed outside runtime config (e.g. environment variables).

- **Guidance Files (e.g. `AGENTS.md`)**
  - Treated as high-integrity artefacts, with change history subject to governance scrutiny.
  - Deterministically located for all agents.

### 7.3 Governance Hooks

- Governance Interface:
  - Injects:
    - Allowed operations.
    - Allowed model versions.
    - Thresholds for approvals (e.g. “freezes beyond level X require council review”).

- Enforcement Points:
  - Before:
    - Freeze operations.
    - Rollbacks of canonical snapshots.
    - Model baseline upgrades.
    - Acceptance of new guidance or architectural axioms.
  - Runtime Orchestrator must consult Policy Engine and fail closed on denial.

- Adversarial Validation:
  - Enforced by policy and workflow:
    - Specs of certain classes cannot move to Frozen without a successful adversarial pass.
    - CI can call the Adversarial Validation Subsystem and gate merges on its status.

### 7.4 Observability & Auditability

- Logging requirements:
  - Every mission, task, freeze, replay, rollback must be logged.
  - Logs must include:
    - Correlation IDs.
    - Commit hashes.
    - Snapshot IDs.
    - LLM model versions and prompt/response hashes (and text, where allowed).
    - Adversarial validation results (status, score, main critique points).

- Telemetry:
  - Health checks for:
    - Runtime.
    - Git operations.
    - LLM gateway connectivity.
    - Canonicalisation and verification operations.

- Audit Trails:
  - For each canonical artefact:
    - Where it came from (run ID, snapshot ID, commit).
    - Which adversarial validation was performed, if any.
    - Who/what requested the operation.

---

## 8. UX & Product Considerations

### 8.1 User Profiles & Primary Flows

Primary v1 user:

- Solo or small-team technical user.
- Comfortable with Git and CLI.
- Wants deterministic, auditable execution and LLM assistance.
- Increasingly, wants to delegate more work to autonomous agents operating within the repo.

Key flows:

- Initialise a project (`lifeos init` or equivalent infra bootstrap).
- Configure missions and policies.
- Run missions with LLM assistance.
- Freeze, replay, and inspect history.
- Prepare artefacts for council review.
- For architecture/infra repos: run `freeze`, `verify`, and `debate` workflows as part of a spec lifecycle.

### 8.2 CLI and Configuration Surface

- Example commands:
  - `lifeos init`
  - `lifeos run <mission>`
  - `lifeos freeze`
  - `lifeos replay <snapshot_id>`
  - `lifeos status`
  - `lifeos diff <snapshot_a> <snapshot_b>`
- For infra repos, additional Make or CLI targets:
  - `init` (bootstraps directory structure: `specs/`, `guidance/`, `.agent/`, `logs/`, etc.).
  - `freeze` (calls Canonicalisation Subsystem).
  - `verify` (checks for drift against lock manifest).
  - `debate` (invokes Adversarial Validation Subsystem on a given spec).

- Primary config:
  - `lifeos.yaml`:
    - Missions.
    - Runtime options.
    - Paths for artefacts and tests.
    - Governance integration level (where allowed by policy).

- Design principles:
  - Favour sensible defaults over many flags.
  - Provide `--dry-run` and `--explain` modes to show what will happen.

### 8.3 Onboarding & Learnability

- “Happy path”:
  - Minimal steps from `lifeos init` to first `lifeos run` and `lifeos freeze`.
  - For infra repos, minimal steps to:
    - Initialise directory structure.
    - Author first spec from templates.
    - Run `debate` and `freeze`.

- Documentation hooks:
  - Commands that generate annotated example configs and templates.
  - CLI guidance that references `guidance/` and `specs/templates/` as starting points.

### 8.4 Productisation Hooks

- Architectural features supporting future productisation:
  - Clear separation of:
    - CLI layer.
    - Core runtime.
    - LLM gateway.
    - Infra tooling (canonicalisation, adversarial validation).
  - Observability interfaces that can be wired to external monitoring (e.g. SaaS).
  - Policy and governance hooks that can be integrated with external identity systems later.
  - Standardised repo scaffolds that enable LifeOS-based tools to attach to arbitrary projects.

---

## 9. Skeptic Findings & Local Mitigations

### 9.1 Critical Risks

1. **Prompt Injection & Artefact Poisoning**
   - LLM gateway may generate plausible but malicious artefacts.
   - Artefacts, once frozen, could propagate bad assumptions.

2. **Git History Manipulation**
   - A user with direct Git access could rewrite history, bypassing freeze semantics.

3. **Policy Bypass via Configuration**
   - Users could alter configs to weaken safeguards if config is not treated as high-integrity.

4. **Complexity Creep**
   - Even with a simple CLI, underlying architecture may overwhelm users if surfaced poorly.

5. **LLM Dependency Risk**
   - Over-reliance on LLM outputs for planning and testing could obscure deterministic guarantees.

6. **Guidance Drift**
   - If `AGENTS.md` and related guidance files are edited casually, agent behaviour can drift, undermining determinism and governance.

### 9.2 Mitigation Strategies

- Prompt Injection:
  - Apply schema validation and invariant checks on all LLM artefacts.
  - Require human review for high-risk LLM-generated artefacts before freeze.

- Git History:
  - Encourage protected branches and server-side hooks in recommended deployment.
  - Detect divergence from expected commit graph in runtime (fail closed if freeze tags or lock manifests are altered improperly).

- Policy Bypass:
  - Treat critical config as artefacts with their own freeze lifecycle.
  - Require governance approvals for changes to high-risk sections (e.g. model policy).

- Complexity:
  - Keep CLI surface minimal, and hide advanced options under explicit “expert mode”.
  - Provide opinionated defaults and templates.
  - Encourage standardised repo layouts to reduce cognitive load.

- LLM Dependency:
  - Encourage deterministic fallbacks and tests.
  - Make LLM-assisted steps explicit and clearly marked in logs and artefacts.
  - Adversarial Validation Subsystem itself should be treated as a tool, not an oracle; its outputs are subject to governance review.

- Guidance Drift:
  - Version-control guidance and treat changes as governance events.
  - Require adversarial review and human sign-off on major changes to `AGENTS.md` and architectural axioms.

### 9.3 Trade-offs and Non-Goals

- Not aiming for:
  - Multi-tenant, multi-user SaaS-grade environment in v1.
  - Perfect tamper-proofing without any external infrastructure.
- Accepting:
  - Some reliance on user discipline and Git hygiene in local environments.
  - Incremental hardening via Governance and Runtime v1.x iterations.
  - Pragmatic use of LLM provider abstractions and fallbacks, as long as boundary rules are respected.

---

## 10. Open Questions & Governance Decisions Needed

### 10.1 Open Design Questions

- Exact granularity of modules (library vs service boundaries).
- Specific Git workflows to recommend (branch naming, tag schemes).
- Concrete conventions for directory layout under `/LifeOS/docs` vs per-project repos, including:
  - Whether `.agent/`, `guidance/`, `specs/` should be universal across LifeOS repos.
- Containerisation strategy (mandatory vs optional).
- Whether to adopt a workflow engine (e.g. durable orchestration) for long-running or human-in-the-loop debates v1 vs v2.

### 10.2 Governance Decisions Requested

- Approval of:
  - The high-level plane/module boundaries outlined here.
  - The chosen role of Git as canonical spine vs any alternative stores.
  - The LLM gateway as the only permitted pathway for LLM calls in v1.
  - Use of a Canonicalisation Subsystem and lock manifest as part of the freeze protocol.

- Decisions on:
  - Required governance level for:
    - Freeze operations.
    - Rollbacks.
    - Model baseline upgrades.
    - Changes to guidance and architectural axioms.

### 10.3 Evolution Path

- Expected early evolutions:
  - v1.1: hardened Freeze Protocol spec and tests; lock-manifest semantics formalised across repos.
  - v1.2: richer observability and external monitoring hooks; standardised `.agent/` and `guidance/` patterns.
  - v2.0: distributed deployments, remote Git, multi-user governance integration; possible migration of freeze/debate flows into a durable workflow engine.

This document is intended as a candidate architecture to be:

1. Compared with alternative architectures (e.g. Gemini’s draft).
2. Synthesised into a consolidated hybrid architecture.
3. Submitted to the Governance Council as a CRP input for canonicalisation.
