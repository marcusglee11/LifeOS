---
candidate_id: CAND-20260428-CODEX-EA-LANE
source_agent: Hermes
source_packet_type: operator_memory_operationalisation
source_packet_id: issue-70-execution-20260428-001
generated_utc: "2026-04-28T08:00:45Z"
proposed_action: create
proposed_record_kind: rule
proposed_authority_class: shared_knowledge
scope: workflow
requires_human_review: true
authority_impact: high
personal_inference: false
sensitivity: internal
retention_class: medium
classification: shared_knowledge_candidate
staging_status: candidate_packet
promotion_basis: Pre-existing LifeOS operating rule with direct impact on EA dispatch routing; retrieving it should prevent accidental Claude/OpenClaw dispatch for COO-managed build work.
sources:
  - source_type: issue
    locator: https://github.com/marcusglee11/LifeOS/issues/69
    quoted_evidence: 'Issue #69 carries label lane:codex whose repository label description is "COO-dispatched EA lane: Codex only"; it is the active operationalization issue for COO-managed work.'
    captured_utc: "2026-04-28T08:00:45Z"
summary: COO-dispatched EA execution for LifeOS build/repo work should use the Codex lane unless Marcus explicitly changes the rule.
payload:
  title: COO EA dispatch uses Codex lane by default
  expected_future_effect: Before dispatching COO-managed LifeOS implementation work, retrieval should route the work to Codex/lane:codex rather than Claude/OpenClaw or a generic agent.
---
Real candidate packet for an action-constraining LifeOS dispatch rule. Not a fixture.
