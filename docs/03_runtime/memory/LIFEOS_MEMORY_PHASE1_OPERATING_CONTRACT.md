# LifeOS Memory Phase 1 Operating Contract

Authority: `docs/03_runtime/memory/LIFEOS_MEMORY_KNOWLEDGE_ARCHITECTURE_v0.5.md`.

## Contract

- Phase 1 memory is repo-backed, deterministic, and manually governed.
- Automatic durable writes are not implemented.
- Vector indexes, embeddings, automatic canon promotion, and non-COO durable writes are out of scope.
- COO means Boss/Marcus acting through explicit manual review and repo merge.
- Hermes, OpenClaw, EAs, and advisory agents emit candidate packets into
  `knowledge-staging/`.
- Durable memory records under `memory/` require `writer: COO`, non-empty
  sources, and receipt references when derived from candidates.
- Synthetic fixtures live under `tests/memory/fixtures/synthetic/` and are not durable memory history.

## Path Map

- `schemas/memory/`: JSON Schemas for records, packets, receipts, conflicts, and supersession edges.
- `knowledge-staging/`: candidate packets, distillations, promotion candidates, conflict candidates, and review digests.
- `memory/`: durable memory records only after COO review.
- `memory/receipts/`: single or batched durable write receipts.
- `knowledge-evidence/`: extracted evidence only when embedded evidence is too large or reused.
- `tools/memory/validate.py`: fail-closed validator.
- `tools/memory/new_record.py`: interactive shell generator.
- `tools/memory/retrieve.py`: deterministic filesystem retrieval.
- `tests/memory/`: focused memory tests and synthetic fixtures.

## Candidate Packet Transport

1. Agent or workorder emits candidate packet.
2. Candidate packet is committed to a branch in `knowledge-staging/`.
3. PR is opened for COO review.
4. COO accepts, rejects, stages, or merges candidate.
5. Every disposition emits a single receipt or batched receipt entry.
6. Accepted durable records move to `memory/` with `writer: COO` and `write_receipts`.

Raw issue comments, PR comments, chats, and native-memory observations are
ingress only. They must be converted to candidate packets before durable
disposition.

## Hermes/OpenClaw Native Memory Posture

Hermes and OpenClaw native memory surfaces are non-canonical observation
surfaces. They must not become LifeOS durable memory, shared knowledge, or canon
by direct write.

Future Hermes/OpenClaw durable-memory contributions must be candidate packets
into `knowledge-staging/`.

Existing native-memory contents, when accessible, get one disposition:

- candidate packet for COO review
- archived non-canonical observation
- discard with no durable import

Inspection/export guidance:

1. Prefer deterministic export commands or UI exports that produce stable text or JSON.
2. Preserve source surface, export timestamp, and hash in candidate packet sources.
3. If export cannot be reproduced deterministically, fail closed and record limitation in PR notes.
4. Do not infer missing history or fabricate durable memory provenance.

Observed Hermes memory-pressure complaint: outside repo-controlled scope for
native product memory. This Phase 1 implementation reduces repo-side risk by
replacing direct durable-write behavior with candidate-packet transport, but
does not change Hermes native memory capacity.

## Hermes Native-Memory Adoption Runbook

References:

- [#80 closure](https://github.com/marcusglee11/LifeOS/issues/80)
- [#81 Gateway/control issue](https://github.com/marcusglee11/LifeOS/issues/81)
- [PR #84](https://github.com/marcusglee11/LifeOS/pull/84)
- [Post-merge proof](https://github.com/marcusglee11/LifeOS/issues/80#issuecomment-4341510317)

### Boundary

This runbook is documentation-only operator guidance for the already-merged Hermes native-memory
audit/classification bridge from PR #84.
It does not create new Gateway tools, MCP tools, transport modes, lifecycle states, promotion APIs,
durable-memory write paths, native-memory mutation paths, cron/scheduled execution, vector search,
reranking, or auto-promotion.
The #81 Gateway/control issue remains the sole authority for Gateway candidate-emission/control
semantics.
Hermes must not directly emit #80-style candidate packets, write durable memory, mutate native
memory, promote memory, or bypass the Gateway.

### Permitted Use

Hermes may run the native-memory audit/classification bridge only to classify, inspect, and prepare
operator-reviewable evidence.
Gateway `memory.retrieve` may be used only through the Gateway when an operator or approved workflow
needs existing memory context.
Gateway `memory.capture_candidate` may be used only through the Gateway to prepare candidate evidence
for later review. It is not a durable write, not a promotion, and not acceptance into memory.

### Operator Flow

Run the native-memory audit/classification bridge when an operator has a deterministic Hermes
native-memory snapshot/export, or explicit entry text, and needs classification before review:

```bash
python3 tools/memory/hermes_native_audit.py \
  --snapshot <path-to-hermes-memory-export> \
  --report artifacts/hermes-native-audit.json \
  --session-id <operator-session-id>
```

Use `--entry <text>` for a single operator-supplied observation. Use `--no-capture-candidates` for
classification-only review. Use `--no-retrieve-context` when Gateway retrieval is not needed or not
approved for the workflow.

Use Gateway `memory.retrieve` only when existing LifeOS memory context is needed to decide whether
Hermes native-memory evidence is duplicate, stale, conflicting, already captured, or review-worthy.
The bridge may request this context through the Gateway; operators must not treat retrieval output as
promotion approval.

Use Gateway `memory.capture_candidate` only when the audit result identifies candidate evidence worth
later review. Candidate capture must preserve source surface, source locator, timestamp, content hash,
redaction status, proposed authority class, and rationale. `memory.capture_candidate` emits candidate
evidence only; it does not write durable memory, mutate native memory, accept memory, or promote memory.

Treat compaction output as recommendation-only. The bridge may label entries as `keep_native`,
`pointer_only`, `archive_observation`, `candidate_handoff`, or `discard`, but those labels do not
authorize deletion, native-memory mutation, durable-memory writes, or promotion. Operator review and
the #81 Gateway/control issue remain authoritative.

### Stop Rule

Stop immediately and escalate back to design review if the runbook needs any of the following:

- new Gateway or MCP tools
- new authority or lifecycle semantics
- direct Hermes candidate emission
- durable memory writes
- native-memory mutation
- promotion or auto-promotion
- vector search, reranking, or ranking policy
- remote transport
- cron or scheduled execution
- Phase 2/3 behaviour

## Tool Usage

Validator:

```bash
python tools/memory/validate.py <path-or-dir>
```

Generator:

```bash
python tools/memory/new_record.py
```

Retrieval:

```bash
python tools/memory/retrieve.py --query <text> --scope <scope> --authority-floor <class> --include-sensitive false
```

## Receipt Expectations

- Accepted candidate: receipt points to durable target record.
- Rejected candidate: receipt records rationale, target may be empty.
- Staged candidate: receipt records staging path and rationale.
- Merged candidate: receipt records target record or merged destination.
- Batch receipts must include one entry per candidate.

## Fail-Closed Rules

Validator rejects missing required fields, invalid enums, empty sources,
non-COO durable records, state records missing state metadata, active non-canon
records missing `review_after`, candidate-derived durable records missing
`write_receipts`, agent-scoped path mismatches, repo evidence without
commit-stable provenance, and direct non-COO durable writes under `memory/`.
