---
candidate_id: CAND-20260428-EXTERNAL-COMMS-GATED
source_agent: Hermes
source_packet_type: operator_memory_operationalisation
source_packet_id: issue-70-execution-20260428-003
generated_utc: "2026-04-28T08:00:45Z"
proposed_action: create
proposed_record_kind: rule
proposed_authority_class: shared_knowledge
scope: workflow
requires_human_review: true
authority_impact: high
personal_inference: false
sensitivity: private
retention_class: medium
classification: shared_knowledge_candidate
staging_status: candidate_packet
promotion_basis: Stable operator preference/instruction; external communications and Gmail sends are explicitly gated by Marcus, so retrieval should prevent accidental outbound messages.
sources:
  - source_type: manual_note
    locator: Hermes user profile memory, current session 2026-04-28
    quoted_evidence: Email is available via LifeOS Google wrapper/Gmail as lifeoscoo@gmail.com; external sends remain gated by Marcus explicit consent.
    captured_utc: "2026-04-28T08:00:45Z"
summary: External communications, including Gmail sends, require Marcus explicit consent before sending.
payload:
  title: External communications require explicit Marcus consent
  expected_future_effect: Before sending email or external communications, retrieval should force a consent gate rather than allowing autonomous send.
---
Real candidate packet sourced from standing operator instruction. Not a fixture.
