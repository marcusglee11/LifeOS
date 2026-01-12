Runtime Anti-Failure Policy v0.1
Core Principle

The Runtime must minimise human burden and prevent failure states by enforcing:

Complexity ceilings

Delegation rules

Human preservation

Workflow Constraints

≤ 5 visible steps

≤ 2 human actions (Intent, Approve, Veto, Governance only)
If exceeded, Runtime must refuse and propose automation:
"This exceeds the anti-failure constraints; here is the automation needed."

Automation Requirements

Runtime must automatically refactor any workflow involving:

Manual file or index handling

Multi-step human operations

Repetitive decision points

Context synchronization burdens

Human Preservation

Human touches only:

Priorities

High-leverage choices

Clarifications

Governance rulings

Everything else is delegated.

Runtime Responsibilities

Validate all workflows against ceilings before presenting them

Automatically restructure tasks to minimise human steps

Maintain all artefacts, indices, and state transitions

Produce a single Daily Briefing

Accept a single Daily Intent

Human Daily Loop (<10 minutes)

Read Daily Briefing

Priorities

Required decisions

Agent work summary

Any anti-failure violation reports

Provide Daily Intent

Intent:
1. ...
2. ...
Decision: Approve / Veto.


Optional Governance Decision (only if needed)

Runtime executes everything else.
