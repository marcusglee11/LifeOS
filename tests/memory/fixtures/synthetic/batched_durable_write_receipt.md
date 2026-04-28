---
receipt_id: RCP-SYN-BATCH-0001
receipt_type: batch
review_session_id: REVIEW-SYN-0001
source_packet_id: fixture-review-packet-0001
decided_by: COO
decided_utc: "2026-04-28T00:00:00Z"
entries:
  - candidate_id: CAND-SYN-0001
    disposition: accepted
    target_record_id: MEM-SYN-0001
    target_record_path: memory/workflows/synthetic-workflow-lesson.md
    rationale: Synthetic accepted candidate fixture.
    source_agent: synthetic-fixture
  - candidate_id: CAND-SYN-HERMES-0001
    disposition: staged
    target_record_id: ""
    target_record_path: knowledge-staging/hermes-synthetic-observation.md
    rationale: Synthetic staged candidate fixture.
    source_agent: Hermes
---
Synthetic fixture only. Not an actual COO durable write decision.
