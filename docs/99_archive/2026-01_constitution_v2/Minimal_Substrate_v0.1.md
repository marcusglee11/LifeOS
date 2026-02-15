# LifeOS — Minimal Substrate v0.1

**Status**: Active
**Parent**: Anti-Failure Operational Packet v0.1
**Purpose**: Define the immutable core invariants required to prevent operational collapse.

## 1. Definition
The **Minimal Substrate** is the smallest possible set of mechanisms required to keep LifeOS valid, deterministic, and improvable without human operational labor.

If any of these invariants are violated, the system is considered "Unstable" and must halt expansion until stabilized.

## 2. Core Invariants

### 2.1 Intent Capture (The Only Human Input)
- **Invariant**: The human must have a single, low-friction channel to inject intent.
- **Mechanism**: A "Task" or "Mission" boundary (chat or file).
- **Prohibited**: Scattering intent across emails, disparate notes, or mental state.

### 2.2 Deterministic Execution (Agent Owned)
- **Invariant**: Once intent is set, execution must be deterministic and agent-driven.
- **Mechanism**: The Runtime Engine (or equivalent script) executes the workflow.
- **Prohibited**: "Human loops" where the human must manually move files or trigger steps mid-flow.

### 2.3 Artefact Stewardship (System Owned)
- **Invariant**: The location, naming, and indexing of files are managed by the system (Document Steward).
- **Mechanism**: `doc_steward` scripts validate and fix structure.
- **Prohibited**: Human manually renaming files or reorganizing folders to "clean up".

### 2.4 State Awareness
- **Invariant**: System state is recorded in files, not human memory.
- **Mechanism**: Logs, status files, and indexes.
- **Prohibited**: "I remember where I left off" (Implicit state).

## 3. Stabilization Protocol
If the substrate is unstable (e.g., human is doing manual work):
1. **Freeze**: Stop new features.
2. **Delegate**: Write a script to handle the manual step.
3. **Verify**: Ensure the script runs without human intervention.
4. **Resume**: Only after the invariant is restored.

