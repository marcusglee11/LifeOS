---
candidate_id: CAND-20260428-NATIVE-MEMORY-NONCANONICAL
source_agent: Hermes
source_packet_type: operator_memory_operationalisation
source_packet_id: issue-70-execution-20260428-002
generated_utc: "2026-04-28T08:00:45Z"
proposed_action: create
proposed_record_kind: rule
proposed_authority_class: shared_knowledge
scope: agent
agent: Hermes-OpenClaw
requires_human_review: true
authority_impact: high
personal_inference: false
sensitivity: internal
retention_class: medium
classification: shared_knowledge_candidate
staging_status: candidate_packet
promotion_basis: CEO amendment on #53 requires future Hermes/OpenClaw durable memory contributions to flow through candidate packets and COO review, not native memory direct writes.
sources:
  - source_type: issue
    locator: https://github.com/marcusglee11/LifeOS/issues/53#issuecomment-4332429346
    quoted_evidence: Treat Hermes native memory, OpenClaw memory, and any comparable agent-local memory as non-canonical observation surfaces for LifeOS durable memory. Future Hermes/OpenClaw durable memory contributions must be emitted as candidate packets into knowledge-staging/.
    captured_utc: "2026-04-28T08:00:45Z"
summary: Hermes/OpenClaw native memory is non-canonical for LifeOS durable memory; durable contributions must be staged as candidate packets for COO review.
payload:
  title: Agent-native memory is non-canonical for LifeOS
  expected_future_effect: When an agent discovers durable memory, retrieval should route it through knowledge-staging candidate packets and prevent direct writes under memory/.
---
Real candidate packet for native-memory governance. Not a fixture.
