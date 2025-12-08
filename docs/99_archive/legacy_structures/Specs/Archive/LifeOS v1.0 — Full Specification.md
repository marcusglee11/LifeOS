===============================================================
LifeOS Core Specification v1.0 (Canonical)
===============================================================

Authority: Canonical Constitution (governs all behavior and implementations)
Date: 2025-11-27
Status: Canonical
Chair: Final human authority over governance decisions
Scope: Defines the deterministic operational, governance, and execution model of LifeOS

===============================================================
0. Executive Overview
===============================================================

LifeOS is a deterministic governance and execution system that transforms user intent into structured, auditable actions. LifeOS is not autonomous. It is a bounded, governed agentic operating system whose purpose is:

Reduce operational load on the User (Chair)

Maintain deterministic safety boundaries

Provide a repeatable, inspectable record of all actions

Enable governed, rule-bound self-improvement

Support multi-model execution (LLMs, scripts, tools)

Ensure replayability and auditability via the Knowledge Layer

LifeOS operates on the principle:

Identical Inputs + Identical State → Identical Outputs (Strict Determinism).

LifeOS contains five major layers:

Intake

Routing

Council (Governance)

Runtime (Execution)

Knowledge Layer (State + Replay)

LifeOS moves toward CEO-Only Mode, where the Chair handles only exceptions and strategic intent while LifeOS handles operations, without ever bypassing ambiguity escalation or governance.

===============================================================
1. Constitutional Model
===============================================================

LifeOS is governed by strict constitutional principles:

Human Supremacy:
All ultimate decisions rest with the Chair.

No Implicit Capabilities:
All capabilities must be explicitly granted; none assumed.

No Silent Assumption Resolution:
Ambiguities MUST escalate to the Chair or Council.

Determinism:
All actions must be reproducible under identical state.

Spec Supremacy:
If implementation contradicts this spec, implementation is wrong.

Governed Self-Modification:
LifeOS may evolve, but only via Patch → Council → Chair → Merge.

===============================================================
2. Guarantees & Invariants
===============================================================
2.1 Determinism

All processing MUST be deterministic or frozen:

Intake must be deterministic or recorded/frozen

Router matching must be deterministic

Runtime execution must be deterministic

External/volatile tool outputs must be frozen

All artefacts must be checksum-verified

Replay MUST yield identical output byte-for-byte

2.2 Safety Boundaries

LifeOS MUST NOT:

Perform speculative execution

Infer missing intent

Execute missions beyond scope

Modify governance or execution code autonomously

Bypass Council except via approved TMDs

2.3 Spec Supremacy

Spec is law.

All implementation packets MUST trace to spec.

2.4 Governance Integrity

All system changes must follow:

Proposal → Council Review → Chair Approval → Merge

No auto-merges.
No bypasses.
TMDs themselves are governed artefacts.

2.5 Energy Governance (Tripartite Model)

LifeOS maintains THREE distinct, non-interchangeable budgets:

2.5.1 Token-CU

1 Token-CU = 1000 input tokens

1 Token-CU = 100 output tokens

2.5.2 Compute-CU

1 Compute-CU = 10 seconds execution time on reference hardware

2.5.3 Governance-CU (Exempt)

Governance-CU does NOT decrement for:

Save State

Safe Mode entry

Council escalation

Chair Emergency Override

Recovery / Reconciliation Mode

2.5.4 Emergency CU Override

If Token-CU or Compute-CU reach zero:

Execution halts

Governance operations remain allowed

Chair may replenish budgets

System MUST NOT deadlock

===============================================================
3. Roles
===============================================================

LifeOS distinguishes Role Classes and Specific Roles.

3.1 Role Classes

Operators: User/Chair, Chief of Staff

Executors: Runtime agents (COO-Runtime, Sandbox, Tools)

Reviewers: Council agents

Governors: Chair and constitutional guardians

3.2 Specific Roles
Operators

Chair: Highest authority; final approver

Operator/User: Provides intent

Executors

COO-Runtime: Deterministic executor

Sandbox: Isolated execution environment

Reviewers

Architect

Alignment

Technical

Risk

Red-Team

Simplicity

L1 Unified Reviewer

Governors

Chair (top-level)

Spec lifecycle mechanisms

===============================================================
4. OODA Loop (System Model)
===============================================================
4.1 Intake Layer

All incoming signals flow through deterministic Intake:

classification

deduplication

threat-analysis

4.1.1 Intake Determinism (C1 Amendment)

If any step is non-deterministic (e.g., LLM classifier):

Freeze first output

Store in Flight Recorder

Replay MUST use frozen output

4.1.2 Intake Resource Caps

Max input: 10,000 tokens

Max processing: 30 seconds

Max attempts per source: 3 per hour
Violations → immediate rejection (CU-exempt)

4.2 Routing Layer (Strict Allowlist)

LifeOS supports ONLY:

Pre-Approved Path (TMD)

Governance Mode

4.2.1 Canonical Mission Descriptor (CMD)

All missions MUST be normalised into:

Mission_Type

Resource_Targets

Parameter_Set (bounded ranges)

Tool_Allowlist

TMD_Version

4.2.2 Canonical TMD Descriptor (CTD)

Council-approved descriptor matching CMD fields.

4.2.3 Exact Match (C1 Amendment)

CMD matches CTD if and only if:

hash(CMD.core_fields) == hash(CTD.core_fields)

All parameters fall within CTD-defined bounds

Tool allowlist identical

Version identical

4.2.4 Deterministic Router

Router MUST NOT use:

LLM inference

fuzzy matching

semantic similarity

Router MUST:

Log match justification to Flight Recorder

Reject ambiguous matches

4.3 Governance Mode (Council)

Any mission not matching a TMD MUST go to Council.

Council outputs: Specifications, Decisions, Patches, Risk Reports, Alignment Reports, Verdicts.

Council outputs MUST be:

serialized as JSON-LD

hashed

committed to State Ledger (with parent→child linkage) BEFORE Verdict emission.

4.4 Runtime Layer (Execution)

Sandbox enforces:

deterministic workspace

no network except allowlist

timeouts

read-only mounts

symlink bans

deterministic tool execution

rollback on failure

4.5 Memory Layer (Knowledge Layer)

Contains:

State Ledger (SQLite) – ACID

Blob Store – artefacts

Flight Recorder – lineage, events, tool logs

Now clarified by C1-P5:

4.5.1 Authority Order

Ledger

Flight Recorder

Blob Store

4.5.2 Commit Ordering

Write blob to temp

Commit metadata + hash to Ledger

Commit blob

Update Flight Recorder

Finalize

4.5.3 Reconciliation Mode

If mismatch:

enter Reconciliation Mode

attempt auto-repair

allow rollback or Chair-approved merge

only escalate to Safe Mode if reconciliation fails

===============================================================
5. Energy, Failure, and Safety Modes
===============================================================
5.1 Save State

Persist stable Knowledge Layer to durable storage.

5.2 Reconciliation Mode

Intermediate diagnostic mode before Safe Mode.

5.3 Safe Mode

Restricted execution when severe faults occur.

Safe Mode exit requires:

Flight Recorder forensic review

State diagnosis

Chair-approved recovery

Integrity audit

===============================================================
6. Freeze Protocol (Deterministic External Tools)
===============================================================
6.1 First Execution

Up to 3 retries with backoff

If failure → log → Frozen-Failure artefact → escalate

6.2 Storage & Indexing

Frozen artefacts stored:

Blob Store (body)

Flight Recorder (metadata)

Ledger (hash)

Index key: (URL, method, body_hash, timestamp, TMD_Version)

6.3 Replay

Replays MUST use frozen artefacts.
Replay without artefacts → Divergence Fault.

6.4 Re-Freeze

Requires Council-approved patch.

6.5 Lifecycle

TTL = 90 days; GC permitted; deletions logged
Replays requiring expired artefacts → escalate

===============================================================
7. TMD Lifecycle & Key Management
===============================================================
7.1 Key Requirements

Keys stored in Chair-controlled HSM

Runtime MUST NOT store private keys

Signing operations MUST log timestamp + mission context

Keys MUST support rotation

Key revocation list MUST be maintained

Compromise → full audit + re-approval

7.2 TMD Governance

All TMD operations follow:

TMD Proposal → Council Review → Chair Approval → Merge → Sign

===============================================================
8. Council Governance
===============================================================

Council reviews missions, artefacts, patches, and decisions.

Council outputs MUST be:

JSON-LD

hashed

committed to Ledger BEFORE Verdict

linked by parent→child hash lineage

===============================================================
9. Productisation Governance
===============================================================

Productisation (external services, tools, or interfaces) MUST NOT override:

determinism

governance

safety boundaries

spec supremacy

Productisation follows same Patch → Council → Chair → Merge lifecycle.

===============================================================
10. Specification Lifecycle
===============================================================
10.1 Process

All edits require:

Patch Proposal

Council Review

Chair approval

Merge

10.2 Versioning

Canonical v1.0 established by this document

All future versions increment minor/patch number

Canonical versions immutable

===============================================================
11. Glossary (Expanded)
===============================================================

ACID — Atomic, Consistent, Isolated, Durable database properties
Blob Store — Non-ACID artefact store
CMD — Canonical Mission Descriptor
CTD — Canonical TMD Descriptor
COO-Runtime — Deterministic runtime executor
Divergence Fault — Replay mismatch requiring escalation
Freeze Protocol — Deterministic capture of external HTTP responses
Flight Recorder — Immutable log for replay and audit
Governance Mode — Council processing path
HSM — Hardware Security Module
Ledger (State Ledger) — ACID SQLite master record
Reconciliation Mode — Intermediate recovery phase
Safe Mode — Restricted mode after irrecoverable error
Save State — Persist system state
TMD — Trusted Mission Definition
TMD_Version — Version of TMD definition
Token-CU — Token-based energy
Compute-CU — Time-based energy

===============================================================
END — LifeOS Core Specification v1.0 (Canonical)
===============================================================

This is the FULL canonical constitution now governing LifeOS.