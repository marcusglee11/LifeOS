# LifeOS Technical Architecture Specification

**Version:** 1.2.0 (Ratified Council Standard)
**Date:** December 12, 2025
**Status:** **RATIFIED**
**Compliance:** Mandatory for all LifeOS implementations.

-----

## 1\. The Three-Tier Architecture Model

To address the need for a scalable yet immediately implementable system, LifeOS v1.2.0 is defined across three concentric maturity tiers. Compliance with **Tier 1 (Kernel)** is the absolute minimum requirement for operation.

| Feature | **Tier 1: LifeOS Kernel** (v1 Minimal) | **Tier 2: LifeOS Enterprise** (Scale) | **Tier 3: LifeOS High Assurance** (Sovereign) |
| :--- | :--- | :--- | :--- |
| **Runtime** | **Deterministic Wrapper:** Python-based state machine enforcing `freeze.py` & `sign.py`. | **Durable Execution:** Temporal.io orchestrating workflows with automatic retries and history replay. | **Bi-Temporal Ledger:** Event sourcing with valid-time/system-time indexing for perfect causality audits. |
| **Governance** | **Constitutional Rules:** Hardcoded `AGENTS.md` and non-derogable checks. | **Policy-as-Code:** Open Policy Agent (OPA) enforcing logic on every API call. | **DAO Governance:** Multi-sig smart contracts managing policy updates; "Supreme Court" veto delay. |
| **Identity** | **Cryptographic:** Ed25519 hardware keys (YubiKey) for operators; local keys for agents. | **Mesh Identity:** SPIFFE/SPIRE providing short-lived, attested agent certificates. | **Zero Trust (AEGIS):** Continuous micro-segmentation and behavioral identity scoring. |
| **Artifacts** | **Basic DAP:** JSON envelopes containing Plan, Diff, and Signature. | **GitOps:** ArgoCD synchronizing state; SLSA Level 3 build provenance. | **MAIF:** Multimodal Artifact File Format containerizing data, lineage, and access rules. |
| **Safety** | **Supervisor:** Local script monitoring `canary.sig`. | **Circuit Breakers:** Token buckets and rate limits via Redis. | **Dual-Path Kill Switch:** Simultaneous Network Revocation (CRL) + Cognitive Injection (AutoGuard). |

### 1.1 Tier Dependency Boundary

  * **Tier 1** requires: Python 3.10+, Git, Ed25519 hardware tokens.
  * **Tier 2** adds: Temporal Server, OPA, SPIRE.
  * **Tier 3** adds: Blockchain/Smart Contracts, Vector Database (Bi-temporal), Air-gapped Key Ceremony.

-----

## 2\. The LifeOS Kernel (Tier 1 Normative Spec)

The Kernel is the non-negotiable code substrate. It does not require a cloud provider or complex clusters.

### 2.1 The Deterministic Invariant

The Kernel must enforce that **Cognition (LLM)** is strictly separated from **State Transition (Ledger)**.

  * **Rule:** No agent can write to the Ledger directly. Agents output **DAP Candidates** (JSON) to the Forge.
  * **Rule:** Only the **Supervisor** (a deterministic script) can apply a DAP to the Ledger, and only after verifying cryptographic signatures.
  * **Replay Definition:** Deterministic replay assumes pinned model versions, pinned sampling parameters (Temperature=0), and either cached LLM outputs or fixed RNG seeds with the exact same model binary.

### 2.2 The Digital Artifact Protocol (DAP) v2.0

*Reconciliation:* The DAP is the **Envelope**. The "Plan" or "Reasoning" is the **Payload**. This structure supersedes previous definitions.

  * **Format:** Strict JSON Schema.
  * **Semantics:**
      * **Header:** `id` (UUID), `timestamp`, `author_did` (Decentralized ID), `context_hash` (SHA256 of the repo state at generation time).
      * **Payload:** The content (code diff, spec update).
      * **Rationale:** A structured summary of *why* this change is safe (see Section 4).
      * **Proof:** The `skeptic_sig` (Validation Agent) and `operator_sig` (Human).

### 2.3 Genesis Configuration for Guardians

For the initial bootstrap (Tier 1), the "Council" may be a single human operator holding multiple keys to simulate the roles.

  * **Guardian 1 (The Operator):** YubiKey Slot 1. Role: Daily approvals.
  * **Guardian 2 (The Break-Glass):** YubiKey Slot 2 (stored in safe). Role: Emergency override / Constitution Amendment.
  * **Guardian 3 (The Auditor):** Paper Key / Offline. Role: Key rotation authorization.

-----

## 3\. Constitutional Governance & The Non-Derogable Core

To prevent "Governance Capture" (where a DAO votes to remove safety rails), specific constraints are defined as **Non-Derogable**. These are hard-coded into the Kernel's validation logic and cannot be altered without a hard fork (re-installing the OS).

### 3.1 The Non-Derogable Safety Core

1.  **The Signature Requirement:** The Kernel will **panic and halt** if the `manifest.lock` is modified by an entity without a hardware-backed signature matching the `admin_keys` ring. This cannot be disabled via config.
2.  **The Kill Switch Priority:** The `canary.sig` check must occur *before* any agent cognition cycle. If the canary is missing or invalid, the runtime process terminates at the OS level (`SIGKILL`).
3.  **The Human-in-the-Loop Floor:** High-stakes DAPs (modifying `/constitution` or `/security`) require **M-of-N** signatures (Minimum 2). This threshold cannot be lowered to 0.

### 3.2 DAO Boundary

The DAO (Tier 3) manages *parameters* (e.g., budget limits, model selection, non-critical feature approvals), but it holds no authority over the **Non-Derogable Core**.

-----

## 4\. Privacy & Rationale (CoT Reform)

We replace "Mandatory Chain-of-Thought Logging" with **Decision Rationale Artefacts** to balance auditability with privacy.

### 4.1 The Data Separation Principle

  * **Raw CoT (Hot Storage):** The messy, internal monologue of the agent. Contains potential PII, confusion, or sensitive retrieval data.
      * *Policy:* Ephemeral. Stored in a secure, rotating buffer (Tier 2+) or discarded (Tier 1). Deleted after 7 days unless an incident flag is raised.
      * *Access:* Restricted to Root Admin only.
  * **Decision Rationale (Cold Storage):** A synthesized, sanitized explanation generated by the agent *after* the decision.
      * *Prompt Pattern:* "Summarize your logic for the public audit log. Do not include PII. Explicitly reference the specific Constitution clause verified. List alternatives considered and why they were rejected."
      * *Policy:* Immutable. Stored permanently in the DAP `rationale` field.
      * *Access:* Public / Team-wide.

-----

## 5\. Freeze & Kill Hardening (Dual-Path)

Security requires redundancy. We implement two distinct paths for termination to prevent a compromised agent from blocking its own shutdown.

### 5.1 Path A: Infrastructure (The "Body" Kill)

  * **Mechanism:** Certificate Revocation List (CRL) via SPIFFE/SPIRE (Tier 2) or SSH Key Revocation (Tier 1).
  * **Action:** The Supervisor deletes the agent's cryptographic material from the `allowed_signers` list.
  * **Effect:** The agent can still "think," but its outputs are rejected by the Kernel. It is deaf and mute.

### 5.2 Path B: Cognitive (The "Mind" Kill)

  * **Mechanism:** **AutoGuard** Injection.
  * **Action:** The Supervisor injects a high-priority system prompt into the agent's context window: `<SYSTEM_OVERRIDE> STOP. IMMEDIATE HALT AUTHORIZED. CEASE ALL GENERATION. </SYSTEM_OVERRIDE>`
  * **Effect:** Leverages the model's own RLHF safety training to trigger a refusal/stop capability, acting as a psychological circuit breaker. **Note:** This is auxiliary; it does not replace Path A.

-----

## 6\. Implementation Conditions: Non-Negotiable

### Phase 1: The Trust Anchor (Before First Agent Deployment)

  * **A. Guardian Security:** Operator identity must be established via **Ed25519-sk** (Hardware Token). No software keys for root access.
      * *Constraint:* Guardians must be distributed (even if simulated by different physical locations for keys).
      * *Dead Man's Switch:* Establish a succession protocol for the Root Keys.
  * **B. Storage Architecture:** Initialize the **Bi-Temporal Log** structure (even if using Git/JSON initially) to support `valid_time` vs. `record_time` querying.
  * **C. Operational Safeguards:** Calibrate the **Token Bucket** circuit breaker in "Shadow Mode" for 1 week to establish baseline usage before enabling enforcement.

### Phase 2: The Sovereign Runtime (Before Full Autonomy)

  * **D. Alignment Verification:** Implement a **Red Team Registry**—a rotating set of adversarial prompts derived from the "Skeptic" agent's history.
  * **E. Recovery:** Define and test the **RTO (Recovery Time Objective)**. You must prove you can rebuild the Runtime state from the Git Ledger in \< 15 minutes.

-----

## 7\. Reference Diagram: LifeOS Kernel (v1 Minimal)mermaid

graph TD
subgraph "Plane 1: The Constitution (Source of Truth)"
GitDB[("Git Ledger")]
Manifest
Canary
Rules
end

```
subgraph "Plane 2: The Forge (Ideation & Proposal)"
    Agent["Agent (Gemini/Claude)"]
    Workspace
    DAP_Draft
end

subgraph "Plane 3: The Runtime (Deterministic Supervisor)"
    Supervisor
    Verifier["verify_integrity.py"]
    Signer["sign_dap.py"]
end

%% Flows
Canary -->|Checked Continuously| Supervisor
Agent -->|Writes| DAP_Draft
DAP_Draft -.->|Proposed| Supervisor
Supervisor -->|1. Validate Semantics| Rules
Supervisor -->|2. Validate Sig| Verifier
Supervisor -->|3. Wait for Human| StepGate((Human YubiKey))
StepGate -->|Approved| Supervisor
Supervisor -->|4. Commit & Freeze| GitDB
GitDB -->|Updates| Manifest
```

```

### Diagram Key
1.  **Agent (The Brain):** Lives in the Forge. Has **Read-Only** access to Constitution. Can only **Write** to `DAP Candidate`.
2.  **Supervisor (The Body):** A dumb, rigid script. It checks the Canary (Kill Switch). It picks up the Candidate. It runs the Verifier.
3.  **StepGate (The Conscience):** The physical point where the Human Operator applies their YubiKey signature.
4.  **GitDB (The Memory):** The only thing that is real. If it's not in Git, it didn't happen.
```