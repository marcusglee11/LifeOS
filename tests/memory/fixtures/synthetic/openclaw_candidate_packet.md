---
candidate_id: CAND-SYN-OPENCLAW-0001
source_agent: OpenClaw
source_packet_type: workorder_distillation
source_packet_id: openclaw-synthetic-distillation-0001
generated_utc: "2026-04-28T00:00:00Z"
proposed_action: create
proposed_record_kind: pattern
proposed_authority_class: agent_memory
scope: agent
requires_human_review: true
authority_impact: low
personal_inference: false
sensitivity: internal
retention_class: medium
classification: agent_memory_candidate
staging_status: candidate_packet
promotion_basis: OpenClaw may propose memory only through candidate packet transport.
sources:
  - source_type: workorder
    locator: synthetic OpenClaw workorder fixture
    quoted_evidence: synthetic fixture, not real OpenClaw durable memory
    captured_utc: "2026-04-28T00:00:00Z"
    content_hash: ""
    commit_sha: ""
summary: Synthetic OpenClaw-originated candidate packet.
payload:
  title: Synthetic OpenClaw agent pattern
  record_kind: pattern
  scope: agent
  agent: OpenClaw
---
Synthetic fixture only. OpenClaw durable memory writes remain prohibited.
