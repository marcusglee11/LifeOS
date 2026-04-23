---
source_docs:
  - runtime/orchestration/coo/invoke.py
  - config/coo/prompt_canonical.md
  - config/agent_roles/coo.md
last_updated: bf4d9ecd
concepts:
  - OpenClaw
  - COO invocation
  - gateway
  - gpt-5.3-codex
  - adapter
---

# OpenClaw Integration

## Summary

OpenClaw is the external AI gateway running the live COO (model: gpt-5.3-codex).
It exposes a local HTTP gateway at `127.0.0.1:18789`. LifeOS invokes it via the
`openclaw` CLI; the runtime adapter in `invoke.py` normalizes responses and
injects the output schema that the COO needs (it cannot access LifeOS schemas
directly through the gateway).

## Key Relationships

- **[agent-roles](agent-roles.md)** — COO is the agent running inside OpenClaw.
- **[coo-runtime](coo-runtime.md)** — the COO runtime calls invoke.py to dispatch to OpenClaw.
- **Adapter**: `runtime/orchestration/coo/invoke.py`
- **Commands**: `runtime/orchestration/coo/commands.py`
- **Schema reference**: `artifacts/coo/schemas.md`
- **Canonical prompt**: `config/coo/prompt_canonical.md`

## Invocation Pattern

```bash
openclaw agent --agent main --message '<json_str>' --json
```

Response: `result.payloads[0].text`

Agent `main` = COO (gpt-5.3-codex). Gateway must be running before invocation.

## CLI Commands

```bash
lifeos coo propose   # COO reviews backlog → task_proposal.v1 YAML
lifeos coo direct    # CEO objective → escalation_packet.v1 → queued to CEO
```

## Known Quirks

- gpt-5.3-codex produces proposals with unindented sub-keys → normalizer in `invoke.py` handles this.
- Must inject `output_schema` with concrete YAML example in context — COO cannot access `schemas.md` directly via gateway invocation.
- Gateway token was revoked once (2026-03-25); refresh via `~/.openclaw/.env`. OpenClaw version: `2026.3.23-2`.

## Current State

Operational since 2026-03-08. Last upgrade: 2026.3.2 → 2026.3.23-2 (npm, 2026-03-25).
Promotion-run tx `b0a9937e` recorded on main. Telegram bot reconnected with fresh token same date.

## Open Questions

None currently flagged.
