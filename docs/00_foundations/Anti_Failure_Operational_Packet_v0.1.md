LifeOS — Anti-Failure Operational Packet v0.1

Format: Markdown with embedded YAML sections for machine parsing.
Purpose: Ensure LifeOS does not collapse due to human fragility, cognitive load, or operational bottlenecking during construction or operation.

This packet is complete, deterministic, and ready for future agent ingestion, RAG indexing, or conversion into a file artefact when you say so.

LifeOS — Anti-Failure Operational Packet v0.1

Status: Draft for immediate operational use
Placement (recommended): /LifeOS/docs/00_foundations/Anti_Failure_Operational_Packet_v0.1.md
Owning Agent: Antigravity (Builder) + Document Steward + COO Runtime

1. Purpose

To prevent LifeOS from failing during its creation or operation due to:

Excessive cognitive load on the human founder

Operational friction and crank-turning

Complexity drift

Fragmented context

System reliance on the human as fallback

Construction-phase architectures that violate LifeOS principles

This packet defines the spec, mechanisms, and activation plan required to stabilise the system and ensure LifeOS builds itself — not by placing more burden on the human, but by shifting that burden to agents.

1. Core Principle: Human Preservation

LifeOS shall treat the human as:

A rare, high-value resource

A fragile node with variable availability

A poor executor but excellent intent-setter

A non-scalable dependency

A last-resort override, not a worker

Agents MUST execute all tasks that can reasonably be automated.

Human involvement must be restricted to:

Providing intent

Approving or vetoing

Governance judgments

Prioritisation decisions

Clarifying ambiguity

Any task that falls to the human outside these categories represents a system design failure.

1. Spec (Conceptual Requirements)
3.1 Requirements for LifeOS Stability

LifeOS must guarantee the following:

Minimal Operable Core remains simple and stable

Delegation-first architecture (agent execution is the default)

Automation of all crank-turning

Friction-based veto for any new process

Idle-Resilient Mode during low human energy

Self-maintenance routines to prevent decay

Complexity ceilings for subsystems

Recursion control to prevent runaway design

Operational continuity even when the human disengages

3.2 Failure Conditions (must be prevented)

LifeOS is failing if:

The human is performing routine execution steps

Artefact creation/update depends on human copying/pasting

The human is manually indexing, renaming, structuring files

New architecture layers appear without friction evaluation

Multiple active projects dilute context stability

Agents do not enforce minimal substrate invariants

Human energy cycles cause operational collapse

1. Mechanisms

The following YAML describes concrete mechanisms that agents (Antigravity, Steward, Runtime) must implement or enforce.

mechanisms:
  minimal_substrate:
    - intent_capture: "Single entry point for human intent."
    - deterministic_execution: "Runtime executes tasks; agents handle all steps."
    - artefact_stewardship: "Document Steward owns file creation, updates, indexing."
    - state_awareness: "Agents manage and recall canonical state, not the human."
    - recursion_control: "No recursive loops added until substrate is stable."
    - human_preservation: "Human participation limited to intent, approval, governance."

  delegation_rules:
    - "If a machine can perform a task, the machine must perform it."
    - "Human must not interact with file systems except for approval or review."
    - "Agents must rewrite or restructure workflows to reduce human steps."

  complexity_controls:
    - max_steps_per_workflow: 5
    - max_human_actions_per_packet: 2
    - lateral_project_limit: 3
    - governance_required_for_complexity_increase: true

  idle_resilience:
    - fallback_mode_trigger: "Human inactivity > 48 hours OR explicit request."
    - fallback_features:
        - "Simplify active workflows."
        - "Pause non-essential projects."
        - "Surface only essential summaries."
        - "Maintain index integrity."
        - "Preserve state for rehydration."

  self_maintenance:
    daily:
      - "Check for drift across artefacts."
      - "Surface a 3-line summary of current system state."
    weekly:
      - "Propose simplifications."
      - "Prune deprecated files pending approval."
    monthly:
      - "Re-run substrate validation."

1. Git Safety Invariant (The "Anti-Deletion" Rule)

To prevent data loss during branch switching or recovery:

1. **NEVER** use `git stash --include-untracked` (or `-u`) unless you are 100% certain you will pop the stash on the *exact same branch* immediately.
2. **NEVER** implicitly trust Git to manage untracked/ignored files during a checkout.
3. **MANDATORY PROTOCOL** for switching contexts with untracked files:
    * **Identify**: Run `git status` to list untracked files.
    * **Isolate**:
        * Option A: Commit them to a temporary safety branch (e.g., `backup/safety_<timestamp>`).
        * Option B: Move them physically outside the repository (e.g., `../temp_safety/`).
    * **Verify**: Ensure the working directory is clean via `git clean -nfd` (dry run) before switching.
4. **RECOVERY**: If a switch fails or hangs on deletion prompts, **ABORT** and answer 'n' to all deletion requests.

5. Activation Plan (Actions → Measures → Outcomes)

These are defined for agents first, human second.
You should only approve or veto — nothing else.

actions:
  agent_actions:
    - "Antigravity generates a single canonical builder prompt incorporating the Human Preservation Principle."
    - "Document Steward collapses current artefact tree into a minimal, stable hierarchy."
    - "Runtime produces a minimal daily operational loop for the human requiring < 10 minutes."
    - "Antigravity identifies 3 recurring crank-turn tasks and drafts automation workflows."
    - "Document Steward establishes the canonical index as a machine-owned artefact (no human edits)."
    - "Runtime implements a friction-warning check for workflows exceeding the complexity threshold."

  human_actions:
    - "Approve or reject the minimal daily operational loop."
    - "Approve or reject the 3 tasks selected for automation."

measures:

* name: manual_file_ops_per_day
    target: "zero or trending toward zero"
* name: human_copy_paste_events
    target: "significant reduction over 14 days"
* name: substrate_stability
    target: "no new primitives introduced"
* name: daily_loop_completion
    target: ">= 5 of 7 days for initial cycle"

outcomes:

* "The human performs dramatically fewer routine steps."
* "LifeOS becomes stable with a smaller operable core."
* "Agents own execution, maintenance, and file management."
* "Friction begins trending downward instead of upward."
* "The build phase becomes survivable and scalable."

1. Ownership and Enforcement

Antigravity enforces build-time principles

Document Steward enforces artefact and index invariants

Runtime enforces operational and complexity limits

Human approves or redirects only

1. Completion Criteria for v0.1

This packet is considered “active” when:

Minimal substrate is in place

Daily summary loop exists and is approved

First three crank-turn tasks are automated

File operations → delegated

Index management → delegated

Human steps → reduced

Substrate remains stable for 14 days

END OF PACKET
