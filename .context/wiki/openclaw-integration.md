---
source_docs:
  - docs/02_protocols/OpenClaw_COO_Integration_v1.0.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: c7df98632ed6dfee99daaada103cd613dc630501
authority: derived
page_class: evergreen
concepts:
  - OpenClaw
  - COO invocation
  - gateway
  - adapter
---

## Summary

OpenClaw is the external AI gateway hosting the live COO agent. LifeOS invokes the COO
via the local OpenClaw HTTP gateway. The target architecture (v2.3c) designates COO as
replaceable via stable contracts provided by COO Commons.

## Key Relationships

- [agent-roles](agent-roles.md) — COO role and autonomy model
- [coo-runtime](coo-runtime.md) — COO runtime and orchestration specs
- [target-architecture](target-architecture.md) — COO as replaceable operational layer
- Source: `docs/02_protocols/OpenClaw_COO_Integration_v1.0.md`
- Source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md`

## Authority Note

Canonical source: `docs/02_protocols/OpenClaw_COO_Integration_v1.0.md`. That document
wins on any conflict with this page. Implementation details (adapter code, config files)
are not canonical sources.

## Current Truth

**Gateway:** `127.0.0.1:18789` via `openclaw` CLI. Agent slot `main` = live COO.

**Invocation:**
```bash
openclaw agent --agent main --message '<json_str>' --json
# response: result.payloads[0].text
```

**CLI wrappers:** `lifeos coo propose` (backlog → task_proposal.v1), `lifeos coo direct`
(CEO objective → escalation_packet.v1 → CEO queue).

**Constraints:**
- Adapter injects `output_schema` on each call (COO cannot access schemas via gateway directly).
- Output normalizer handles gpt model formatting quirks (unindented sub-keys).
- Credentials: `~/.openclaw/.env` (refresh token if expired).
- Current version: see `LIFEOS_STATE.md` or run `openclaw --version`.

## Open Questions

None.
