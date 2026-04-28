---
candidate_id: CAND-SYN-HERMES-0001
source_agent: Hermes
source_packet_type: native_memory_observation_export
source_packet_id: hermes-synthetic-export-0001
generated_utc: "2026-04-28T00:00:00Z"
proposed_action: create
proposed_record_kind: fact
proposed_authority_class: observation
scope: agent
requires_human_review: true
authority_impact: low
personal_inference: false
sensitivity: internal
retention_class: short
classification: agent_memory_candidate
staging_status: candidate_packet
promotion_basis: Hermes native memory is non-canonical; this packet is COO review input only.
sources:
  - source_type: manual_note
    locator: synthetic Hermes native-memory observation fixture
    quoted_evidence: synthetic fixture, not exported real Hermes memory
    captured_utc: "2026-04-28T00:00:00Z"
    content_hash: ""
    commit_sha: ""
summary: Synthetic Hermes-originated candidate packet.
payload:
  title: Synthetic Hermes observation
  record_kind: fact
  scope: agent
  agent: Hermes
---
Synthetic fixture only. Hermes native memory content is not canonical LifeOS memory.
