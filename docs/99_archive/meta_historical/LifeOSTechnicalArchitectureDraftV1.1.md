LifeOS Technical Architecture Specification

Version: 1.1.0 (Council-Conditioned Draft) Status: PROPOSED Date: 2025-12-09 Compliance: Incorporates Council Fix Plan v1.1.

    Conformance Note: A system may only claim "LifeOS v1 Architecture-Conformant" once all Normative sections (Constitution, DAP, Freeze Protocol, IAM) are implemented. Sections labeled "Informative" (Horizons, vendor choices) are flexible.

1. Architectural Philosophy: The Kernel Invariant

LifeOS is a Recursively Self-Improving (RSI) Operating System designed to manage entropy through strict separation of stochastic intelligence and deterministic execution.
1.1 The Determinism Invariant

LifeOS resolves the conflict between probabilistic LLMs and deterministic systems via a strict invariant:

    Cognition is Stochastic: Agents are expected to be noisy.

    Orchestration is Deterministic: The runtime never relies on an LLM for control flow during execution.

    The Replay Rule: Given the same Git commit, manifest.lock, DAP set, and cached LLM artifacts, all workflows must replay to the same observable result without re-querying the model.

2. System Topology: The Three Planes
Plane 1: The Constitution (Normative)

    Role: The immutable Source of Truth.

    Components: AGENTS.md (Directive), manifest.lock (Merkle Root), decisions.lock (StepGate History).

    Access Rule: Agents have Read-Only access. Only the Freeze Workflow (triggered by StepGate) can write here.

Plane 2: The Forge (Informative)

    Role: The high-entropy workspace for ideation and drafting.

    Components: Google Antigravity, Cursor, local scratchpads.

    Output: Agents here produce DAP Candidates (JSON). They never commit code directly to the Ledger.

Plane 3: The Ledger (Normative)

    Role: The durable execution environment.

    Components: Temporal.io (Orchestrator), Git (Storage).

    Access Rule: The Runtime executes DAPs only after they pass the StepGate.

2.4 Capability & Identity Model (v1 Skeleton)

    Identities: Distinct cryptographic identities (Service Accounts) must exist for:

        agent-architect: Proposes changes.

        agent-skeptic: Critiques changes.

        human-governor: Signs amendments.

        runtime-privileged: The only identity allowed to push to main.

3. The Digital Artifact Protocol (DAP)

All systemic changes must be encapsulated in a DAP.
3.1 DAP Types

    spec_update: Changes to documentation.

    code_patch: Changes to implementation.

    governance_change: Updates to voting thresholds or role assignments.

    constitution_amendment: Critical. Changes to core axioms. Requires M-of-N Multi-Sig.

3.2 Context & Hashing

To ensure replayability, every DAP includes a context_hash: $$ \text{context_hash} = \text{SHA256}(\text{prompt} |

| \text{git_commit_sha} | | \text{manifest_lock_hash}) $$

    Purpose: Ensures a DAP generated for System v1.0 cannot be accidentally applied to System v1.1.

3.3 Semantic Constraints

    Path Whitelisting: DAPs may only touch files within /src or /docs. Access to /.github or root configs requires a governance_change type.

    Invariant Checks: The DAP validation block must list passed invariants (e.g., ["no_external_network_calls", "test_coverage_maintained"]).

4. The Core Workflow: The Constitutional Loop
4.1 Freeze Protocol Semantics

    Lock: Acquire a pessimistic lock on the target path.

    Verify: Re-calculate hashes of all files in the DAP payload.

    Update: Write files to disk; update manifest.lock.

    Atomic Commit: Push to Git. If the push fails (race condition), the entire transaction rolls back.

4.2 The Debate (Temporal)

    Deterministic Replay: The debate is a Temporal Workflow. LLM calls are Activities. Their results are cached in the Temporal Event History. Replaying the workflow uses the cache, ensuring the "Debate" doesn't change outcome when viewed later.

4.3 The StepGate (Multi-Human Consensus)

    Mechanism: A "Signal" sent to the Temporal Workflow.

    Requirement:

        Standard DAP: 1 Human Signature (Hardware Token preferred).

        Constitutional Amendment: Quorum (e.g., 2-of-3) Human Signatures.

    Audit: The signature payload includes {dap_id, signer_id, timestamp, decision}.

4.4 Rate Limiting & Escalation

    Velocity Limit: Max 5 DAPs frozen per hour to prevent "Agent Swarm" attacks.

    Escalation: DAPs touching /security or /auth automatically trigger "High Risk" mode, requiring additional signatures.

5. Implementation Roadmap
Horizon 1: The Iron Prototype (Now - Month 1)

    Scope: Single-tenant, local execution.

    Stack: Python scripts + Local Git + Self-Hosted Temporal (Docker).

    Goal: Establish the directory structure and manual freeze.py workflow.

Horizon 2: The Constitutional Cloud (Month 2 - 6)

    Scope: Cloud-hosted, automated CI/CD gating.

    Stack: Temporal Cloud, Vertex AI (for Agent Identity).

    Goal: Automate the Debate loop.

Horizon 3: Operational Excellence (Month 6+)

    Scope: High-availability, Disaster Recovery.

    Focus: Adversarial Red-Teaming of the Constitution itself.

6. Security & Safety Protocols (Normative)
6.1 Cryptographic Integrity

    Algorithm: Ed25519 for signatures; SHA-256 for artifact hashing.

    Key Storage: Human keys on hardware tokens (YubiKey). Runtime keys in Secret Manager (accessed only by Temporal Workers).

6.2 manifest.lock Enforcement

    Rule: The manifest.lock is the only source of truth for file integrity.

    Check: Every Runtime operation begins by verifying SHA256(fs) == manifest.lock. Mismatch = Immediate Halt.

6.3 Kill Switch (Signed Canary)

    Mechanism: A CANARY.signed file in the repo root.

    Logic: Workers check for the presence and valid signature of the Canary before every activity.

    Trigger: Deleting the file or invalidating the signature causes an immediate hard-stop of all workers.

6.4 Rollback Protocol

    Forward-Only: We never git reset on the remote.

    Revert DAP: To rollback, we generate a revert_dap that applies the inverse diff. This preserves the audit trail of the mistake and the correction.

7. Open Decisions (Parameterisation)

    DeepEval Threshold: Default: 0.85. High-Risk: 0.95.

    Model Agnosticism: The architecture does not hardcode "Gemini". The Architect role is an interface. We will rotate models (Claude/Gemini/DeepSeek) to prevent vendor-specific bias/lock-in.
