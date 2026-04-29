# Issue #81 Hermes Gateway Proof Slice

Scope: evidence only. No architecture semantics added. No Gateway/MCP tools added.

Branch: `spike/hermes-gateway-proof`
Base HEAD: `f3a5fbbde5d4289669896c3cc48abf60c0ed92d5`
Fixture: `artifacts/hermes_gateway_proof/issue_81_hermes_native_memory_sample.md`
Audit report: `artifacts/hermes_gateway_proof/issue_81_hermes_gateway_audit_report.json`
Session id: `sess-issue-81-hermes-gateway-proof`

## Proof Command

```bash
python3 tools/memory/hermes_native_audit.py --snapshot artifacts/hermes_gateway_proof/issue_81_hermes_native_memory_sample.md --report artifacts/hermes_gateway_proof/issue_81_hermes_gateway_audit_report.json --session-id sess-issue-81-hermes-gateway-proof --agent Hermes --scope workflow --iso-timestamp 2026-04-29T00:00:00Z --retrieval-limit 2
```

Result: exit `0`, stdout empty.

## Gateway Calls Observed

Gateway session log path created during proof:
`knowledge-staging/_sessions/sess-issue-81-hermes-gateway-proof.jsonl`

```jsonl
{"agent_claim": null, "candidate_id": null, "candidate_path": null, "findings": [], "query_or_summary": "[candidate_handoff] class=shared_knowledge kind=lesson scope=workflow Gateway v0.1 keeps Hermes native memory non-canonical; candidate evidence requires human review before durable promotion.", "result_ok": true, "session_id": "sess-issue-81-hermes-gateway-proof", "timestamp_utc": "2026-04-29T10:14:26Z", "tool": "memory.retrieve", "transport_identity": "hermes-native-audit"}
{"agent_claim": "Hermes", "candidate_id": "CAND-a94a0692e6ba2b11", "candidate_path": "knowledge-staging/cand-20260429-hermes-a94a0692e6ba2b11.md", "findings": [], "query_or_summary": "Hermes native memory candidate: [candidate_handoff] class=shared_knowledge kind=lesson scope=workflow Gateway v0.1 keeps Hermes native memory non-canonical; candidate evidence r...", "result_ok": true, "session_id": "sess-issue-81-hermes-gateway-proof", "timestamp_utc": "2026-04-29T10:14:26Z", "tool": "memory.capture_candidate", "transport_identity": "hermes-native-audit"}
{"agent_claim": null, "candidate_id": null, "candidate_path": null, "findings": [], "query_or_summary": "[pointer_only] See memory/workflows/coo-ea-dispatch-codex-only.md for related LifeOS context; do not copy native detail into durable memory.", "result_ok": true, "session_id": "sess-issue-81-hermes-gateway-proof", "timestamp_utc": "2026-04-29T10:14:27Z", "tool": "memory.retrieve", "transport_identity": "hermes-native-audit"}
{"agent_claim": null, "candidate_id": null, "candidate_path": null, "findings": [], "query_or_summary": "[archive_observation] stale native-memory note about retired direct candidate emission; operator may archive after review.", "result_ok": true, "session_id": "sess-issue-81-hermes-gateway-proof", "timestamp_utc": "2026-04-29T10:14:27Z", "tool": "memory.retrieve", "transport_identity": "hermes-native-audit"}
```

Retrieval proof: all retrieval context calls use Gateway tool `memory.retrieve` with transport identity `hermes-native-audit`.

Candidate proof: candidate-worthy evidence uses Gateway tool `memory.capture_candidate`. No direct Hermes/#80-style candidate emission observed.

## Candidate Evidence Created

Candidate path created during proof:
`knowledge-staging/cand-20260429-hermes-a94a0692e6ba2b11.md`

Candidate header excerpt:

```yaml
candidate_id: CAND-a94a0692e6ba2b11
source_agent: Hermes
source_packet_type: memory_gateway_capture
source_packet_id: gateway-CAND-a94a0692e6ba2b11
generated_utc: '2026-04-29T00:00:00Z'
proposed_action: create
proposed_record_kind: lesson
proposed_authority_class: shared_knowledge
scope: workflow
requires_human_review: true
classification: shared_knowledge_candidate
staging_status: candidate_packet
promotion_basis: Hermes native memory is non-canonical; this handoff is review input through LifeOS Memory Gateway only.
sources:
- source_type: manual_note
  locator: artifacts/hermes_gateway_proof/issue_81_hermes_native_memory_sample.md:3
```

Candidate stayed under `knowledge-staging/` during the proof run. No durable memory acceptance, write receipt, or promotion happened. Gateway-created candidate/session files were transient proof outputs and were removed before handoff so final repo changes stay limited to this proof artifact, committed audit report, and fixture.

## Audit Report Receipts

```json
{
  "compaction": {
    "mutated_native_files": false,
    "recommendation_only": true
  },
  "gateway_boundary": {
    "capture_tool": "memory.capture_candidate",
    "compaction_mutates_native": false,
    "direct_candidate_emission": false,
    "durable_memory_write": false,
    "retrieval_tool": "memory.retrieve"
  },
  "summary": {
    "candidate_handoff_attempted": 1,
    "candidate_handoff_succeeded": 1,
    "entries": 3
  }
}
```

Entry dispositions:

- `HNA-0001`: `candidate_handoff`; retrieval tool `memory.retrieve`; handoff tool `memory.capture_candidate`; candidate path `knowledge-staging/cand-20260429-hermes-a94a0692e6ba2b11.md`.
- `HNA-0002`: `pointer_only`; retrieval tool `memory.retrieve`; handoff not attempted.
- `HNA-0003`: `archive_observation`; retrieval tool `memory.retrieve`; handoff not attempted.

Compaction/classification output is recommendation-only. It did not mutate Hermes native memory, `MEMORY.md`, `USER.md`, or LifeOS durable `memory/`.

## Durable Memory Non-Mutation Proof

```bash
git diff --name-status -- memory
```

Output: empty. Exit `0`.

```bash
git status --short -- memory
```

Output: empty. Exit `0`.

```bash
git status --short -- MEMORY.md USER.md
```

Output: empty. Exit `0`.

## Required Validation

```bash
git diff --check
```

Output: empty. Exit `0`.

Environment note: this WSL runtime has `python3`; `python` is not installed.

```bash
python3 tools/memory/validate.py knowledge-staging --json
```

Output:

```json
{
  "findings": [],
  "ok": true
}
```

Exit `0`.

```bash
python3 -m pytest tests/memory/test_hermes_native_audit.py tests/memory/test_memory_gateway_mcp.py tests/memory/test_memory_phase1.py -q --tb=short
```

Output summary:

```text
34 passed in 1.42s
```

Exit `0`.

Repo baseline command required by local agent instructions:

```bash
pytest runtime/tests -q
```

Post-review output summary:

```text
=========== 3237 passed, 6 skipped, 7 warnings in 256.03s (0:04:16) ============
```

Exit `0`.

## GitHub Issue State

Read-only command:

```bash
gh issue view 81 --repo marcusglee11/LifeOS --json number,state,title,url
```

Output:

```json
{"number":81,"state":"OPEN","title":"AA revise: LifeOS memory MCP gateway v0.1","url":"https://github.com/marcusglee11/LifeOS/issues/81"}
```

No GitHub issue close, commit, push, merge, candidate promotion, cron creation, durable memory mutation, or real Hermes native-memory mutation was performed. Issue #81 remains open.

PR closure semantics: use `Refs #81`, not `Closes #81`, unless a separate AA/COO closure review explicitly approves closing the architecture gate.
