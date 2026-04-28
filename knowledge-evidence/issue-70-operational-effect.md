# Issue #70 operational effect evidence packet

## Baseline
- Baseline timestamp: 2026-04-28T08:00:45Z
- Base commit: bf04796edb0152150abd0f75be14de44a6269caf
- `python3 tools/memory/validate.py memory`: OK
- `python3 tools/memory/validate.py knowledge-staging`: OK
- `python3 tools/memory/retrieve.py --query "memory operationalisation" --scope project --authority-floor observation --include-sensitive false --json`: `{ "results": [] }`
- Production candidate packets under `knowledge-staging/`: 0
- Durable records under `memory/`: 0
- Durable write receipts under `memory/receipts/`: 0

Counts exclude `.gitkeep`, README/docs-only files, schemas, examples, and `tests/memory/fixtures/synthetic/`.

## Native-memory inspectability note
Hermes/OpenClaw native memory is represented here through already-visible operator/repo evidence, not by a deterministic export of a native-memory database. No native-memory content is imported as durable memory. Uninspectable native-memory sources fail closed.

## Candidate disposition table

| Candidate | Source | Expected future effect | Disposition | Rationale |
|---|---|---|---|---|
| `CAND-20260428-CODEX-EA-LANE` | #69 / lane:codex operating label | Route COO-managed LifeOS build work to Codex | accepted | Action-constraining and immediately testable against #69. |
| `CAND-20260428-NATIVE-MEMORY-NONCANONICAL` | #53 CEO amendment comment | Prevent direct durable writes from Hermes/OpenClaw native memory | staged | High-value but should be promoted after first dispatch record proves the vertical slice. |
| `CAND-20260428-EXTERNAL-COMMS-GATED` | standing operator instruction | Prevent ungated external sends | staged | High-value but private/safety-sensitive; keep staged until reviewed separately. |

## After counts
- Production candidate packets under `knowledge-staging/`: 3
- Durable records under `memory/`: 1
- Durable write receipts under `memory/receipts/`: 1

## Retrieval proof

Retrieval command:

```bash
python3 tools/memory/retrieve.py --query "COO build dispatch Codex" --scope workflow --authority-floor observation --include-sensitive false --json
```

Returned record path: `memory/workflows/coo-ea-dispatch-codex-only.md`
Returned record id: `MEM-20260428-CODEX-EA-LANE`
Returned rank/order: first and only result
Relevant JSON/output excerpt:

```json
{
  "source_path": "memory/workflows/coo-ea-dispatch-codex-only.md",
  "record_id": "MEM-20260428-CODEX-EA-LANE",
  "record_kind": "rule",
  "authority_class": "shared_knowledge",
  "scope": "workflow",
  "write_receipts": ["memory/receipts/rcp-20260428-codex-ea-lane.md"]
}
```

This is a natural-language operational query about COO build dispatch and Codex routing, not a record id, path, or exact-title lookup.

## Downstream usage proof

Downstream URL: https://github.com/marcusglee11/LifeOS/issues/69#issuecomment-4333405725

Expected behaviour without retrieved memory:
- Treat #69 as a generic repo implementation issue and risk routing to the current assistant/Claude/OpenClaw path by habit.

Actual behaviour after retrieval:
- Keep #69 on `lane:codex`; use Codex as the COO-dispatched EA lane for implementation work.

Concrete delta:
- Executor routing decision came from durable memory retrieval, not rediscovery or chat-context memory.

Operational consequence:
- Prevents wrong-lane dispatch for #69 and proves the Phase 1 memory loop can affect a live LifeOS issue.
