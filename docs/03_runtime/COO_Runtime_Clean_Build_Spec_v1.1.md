COO Runtime — V1.1 CLEAN BUILD
Project Starter Pack (Paste & Use)
0. PROJECT PURPOSE

This project houses a clean, unpolluted, V1.1-aligned implementation environment for the COO Runtime and its user-facing demos, without legacy threads or stale context.

It intentionally excludes:

old demos

old debugging cycles

old user tests

superseded fix packs

legacy council discussions

old StepGate explorations

Everything here is current, alive, and aligned with:

COO Runtime v1.1

Stage B User Surface

DEMO_FILE_V1 (deterministic baseline demo)

DEMO_APPROVAL_V1 (upcoming hybrid-agent demo)

Council Protocol v1.0

StepGate Protocol

Intent Routing Rule

Alignment Layer v1.4

This is your V2 working environment.

1. PROJECT THREAD STRUCTURE (Only Four Threads)

Your project should contain only the following:

THREAD 1 — Runtime Core (Active)

Purpose:
All architectural, deterministic-execution, orchestrator, mission, and logging work.

Includes:

Runtime Spec v1.0

Implementation Packet v1.0

COO Runtime v1.1 behavioural invariants

DB, mission graph, orchestrator logic

Logging format

Execution pipeline refinement

Determinism properties

Flight recorder

AMU₀ interactions (if needed)

Thread starter message to paste:

COO Runtime V1.1 — Runtime Core (Clean Thread)

This thread holds the runtime architecture, orchestrator logic, mission execution model, and all deterministic behaviour for COO Runtime V1.1. No demos, no governance, no council reviews here. Pure runtime mechanics only.

State: Clean boot.
Artifacts to import: Runtime Spec v1.0, Implementation Packet v1.0.

Begin by confirming: “Runtime core initialisation — go”.

THREAD 2 — User Surface & Demos (Active)

Purpose:
Everything user-facing: CLI, receipts, introspection, demos, UX.

Includes:

DEMO_FILE_V1 (approved baseline demo)

DEMO_APPROVAL_V1 (new hybrid-agent deterministic demo)

CLI receipt format

Mission/Logs presentation

UX & user test loops (StepGate)

Thread starter message to paste:

COO Runtime V1.1 — User Surface & Demos (Clean Thread)

This thread handles all user-facing behaviour: CLI, receipts, UX, and demos. The current canonical demo is DEMO_FILE_V1. We will be designing and implementing DEMO_APPROVAL_V1 here.

State: Clean boot, V1.1-aligned.
Artifacts to import: Stage B User Surface Spec, DEMO_FILE_V1 Implementation Packet, DEMO_APPROVAL_V1 Thread Starter.

Begin by saying: “Gate 1 — go”.

THREAD 3 — Governance Layer (Active)

Purpose:
Council, StepGate, Intent Routing, and governance invariants.

Includes:

Council Protocol v1.0

Council Invocation Rule

Intent Routing Rule

StepGate Protocol

Role boundaries

Deterministic review processes

Governance invariants and escalation

Thread starter message to paste:

LifeOS Governance Layer — Council, StepGate, Routing (Clean Thread)

This thread encapsulates all governance scaffolding: Council Protocol v1.0, StepGate, Intent Routing Rule, Council Invocation Rule, and role-boundary logic. No runtime build work here — governance/spec logic only.

State: Clean boot.
Artifacts to import: Council Protocol v1.0, Intent Routing Rule, StepGate Protocol.

Begin by saying: “Governance sync — begin”.

THREAD 4 — Productisation (Dormant)

Purpose:
Long-term positioning, roadmap, niche selection, demos-as-product, onboarding design.

Includes:

Strategic roadmap V1 → V2 → V3

niche exploration

DevRel plan

packaging (pip, docker, oss split)

landing page and onboarding flows

business model hypotheses

Thread starter message to paste:

COO Runtime — Productisation & Roadmap (Clean Thread)

This thread holds the long-term product direction: positioning, roadmap, target personas, onboarding, pricing, packaging. Not active unless explicitly invoked.

State: Dormant but preserved.

Begin by saying: “Resume product track”.

2. ARTEFACTS TO CARRY INTO THE NEW PROJECT

Only the live, correct, unpolluted artefacts should be imported:

Runtime

COO Runtime Spec v1.0

Implementation Packet v1.0

Stage B User Surface Spec

DEMO_FILE_V1 Implementation Packet

Governance

Council Protocol v1.0

Council Invocation Rule

Intent Routing Rule

StepGate Protocol

Alignment Layer v1.4

Demos

DEMO_FILE_V1 receipt+timeline model

DEMO_APPROVAL_V1 Thread Starter (from previous message)

Testing / UX

Minimal Product Test principles (structure, determinism tests)

State

Nothing else.

3. ARTEFACTS TO NOT BRING OVER

Leave behind entirely:

Old / Obsolete

LLM summariser demo

Top_p debugging and fix cycles

Early Phase 14 threads

All summariser user tests

Any council tied to summariser

Attempts at old CLI surfaces

Context-heavy / Confusing

R6.4 / R6.5 extended dialogues

Multi-model council experiments

Strategy digressions not tied to roadmap

Early architectural brainstorms

Meta-conversations about your career

Exploratory “life philosophy” digressions

Past emotional or reflective side-conversations

These pollute the working state.

4. MIGRATION CHECKLIST (Simple, Clear)
Step 1 — Create new project

Name:
“COO Runtime — V1.1 Clean Build”

Step 2 — Create the four threads

Paste the exact starter messages.

Step 3 — Import artefacts

Manually paste in:

Runtime Spec v1.0

Implementation Packet v1.0

Stage B User Surface Spec

DEMO_FILE_V1 packet

Governance protocols

DEMO_APPROVAL_V1 Thread Starter

Step 4 — Archive old project

Do NOT delete — just cease using it.

Step 5 — Start the new work

Enter the User Surface & Demos thread, say:
“Gate 1 — go”
and we design DEMO_APPROVAL_V1 cleanly.

5. Clean Kickoff Sequence (recommended)

Create new project

Open Runtime Core thread → “Runtime core initialisation — go”

Open Governance Layer thread → “Governance sync — begin”

Open User Surface & Demos thread → “Gate 1 — go”

Open Productisation thread LAST and keep dormant

This sets up the environment for the next month of development.