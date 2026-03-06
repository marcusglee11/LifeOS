# COO Dispatch Memory Seed (Provisioning Spec)

This file is provisioning guidance for the existing 4-layer COO memory architecture.
It is not a runtime memory source.

## 1) Structured Entries (`coo-memory.py write`)

Run from:
`/home/cabra/.openclaw/workspace/COO/memory/`

Example seed commands:

```bash
python3 coo-memory.py write \
  --type fact \
  --namespace lifeos/dispatch \
  --domain orchestration \
  --ttl_class stable \
  --confidence 0.99 \
  --source_kind file \
  --source_ref runtime/orchestration/dispatch/order.py \
  --excerpt "ExecutionOrder schema contract" \
  --subject "ExecutionOrder contract" \
  --content "COO emits execution_order.v1 artifacts consumed by DispatchEngine from artifacts/dispatch/inbox." \
  --tags "dispatch,execution_order,contract"

python3 coo-memory.py write \
  --type fact \
  --namespace lifeos/governance \
  --domain autonomy \
  --ttl_class stable \
  --confidence 0.99 \
  --source_kind file \
  --source_ref docs/01_governance/COO_Operating_Contract_v1.0.md \
  --excerpt "Burn-in autonomy model" \
  --subject "Burn-in defaults" \
  --content "During burn-in, actions default to L3 unless explicitly L0; unknown actions fail closed to L4 escalation." \
  --tags "governance,autonomy,burn-in"

python3 coo-memory.py write \
  --type fact \
  --namespace lifeos/providers \
  --domain routing \
  --ttl_class active \
  --confidence 0.95 \
  --source_kind file \
  --source_ref runtime/agents/cli_dispatch.py \
  --excerpt "CLIProvider enum" \
  --subject "Provider set" \
  --content "Supported CLI providers are codex, gemini, and claude_code; COO may emit auto as advisory routing metadata." \
  --tags "providers,routing,dispatch"

python3 coo-memory.py write \
  --type fact \
  --namespace lifeos/escalation \
  --domain queue \
  --ttl_class stable \
  --confidence 0.99 \
  --source_kind file \
  --source_ref runtime/orchestration/ceo_queue.py \
  --excerpt "EscalationType enum values" \
  --subject "CEO escalation types" \
  --content "Escalation types: governance_surface_touch, budget_escalation, protected_path_modification, ambiguous_task, policy_violation." \
  --tags "escalation,ceo_queue,governance"
```

## 2) Root `MEMORY.md` Additions (High-Signal Only)

Add only concise directives that must be always loaded:

- COO does not write product code; COO proposes tasks and emits dispatch artifacts.
- Burn-in autonomy: L0/L3/L4 only; unknown category => L4.
- ExecutionOrder schema authority is `runtime/orchestration/dispatch/order.py`.
- Governance/advisory references are read from source docs, not duplicated in prompt memory.

## 3) QMD / Retrieval Notes

Index for retrieval:

- `docs/01_governance/COO_Operating_Contract_v1.0.md`
- `docs/01_governance/CSO_Role_Constitution_v1.0.md`
- `docs/01_governance/COO_Expectations_Log_v1.0.md`
- `runtime/orchestration/dispatch/order.py`
- `runtime/orchestration/ceo_queue.py`
- `runtime/agents/cli_dispatch.py`
- `config/tasks/backlog.yaml`

Bridge rule:
- Structured memory under `workspace/COO/memory/structured/` is authoritative but not auto-indexed by general workspace recall.
- Mirror only high-signal directives into root `MEMORY.md` for immediate recall.

## 4) Validation Checklist

- Validate each structured write against:
  `/home/cabra/.openclaw/workspace/COO/memory/structured/memory.schema.json`
- Verify `coo-memory.py query --namespace lifeos/dispatch` returns seeded entries.
- Keep root MEMORY additions under strict high-signal scope.
