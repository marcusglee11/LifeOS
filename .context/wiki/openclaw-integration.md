---
source_docs:
  - docs/02_protocols/OpenClaw_COO_Integration_v1.0.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: 310aac1e0eda5cb96842d8a596bbadacbf4935f9
authority: derived
page_class: evergreen
concepts:
  - OpenClaw
  - COO invocation
  - gateway
  - adapter
  - COO Commons
---

## Summary

OpenClaw is the external AI gateway hosting the live COO agent. LifeOS invokes the COO
via the local OpenClaw HTTP gateway. The target architecture (v2.3c) designates COO as
replaceable via stable contracts provided by COO Commons — a substrate-independent shared
services layer holding schemas, validators, policy data, and webhook ingress.

## Key Relationships

- [agent-roles](agent-roles.md) — COO role and autonomy model
- [coo-runtime](coo-runtime.md) — COO runtime and orchestration specs
- [target-architecture](target-architecture.md) — COO as replaceable operational layer; COO Commons design
- Source: `docs/02_protocols/OpenClaw_COO_Integration_v1.0.md`
- Source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md`

## Authority Note

Canonical source: `docs/02_protocols/OpenClaw_COO_Integration_v1.0.md`. That document
wins on any conflict with this page. Implementation detail (adapter code, config files)
is NOT a canonical source.

## Current Truth

**Gateway:** `127.0.0.1:18789` via `openclaw` CLI. Agent slot `main` = live COO.

**Invocation:**
```bash
openclaw agent --agent main --message '<json_str>' --json
# response: result.payloads[0].text
```

**CLI wrappers:** `lifeos coo propose` (backlog → task_proposal.v1), `lifeos coo direct`
(CEO objective → escalation_packet.v1).

**Constraints:** Adapter injects `output_schema` on each call (COO cannot access schemas
directly via gateway). Credentials at `~/.openclaw/.env`. COO output normalizer handles
known gpt model formatting quirks. Verify current version with `openclaw --version`.

**COO Commons (v2.3c):** Co-hosted with substrate in Phase 1. Provides webhook ingestion,
schema validation library (in-process), and phase/policy config via local verified git clone.
COO is fail-closed when Commons is unavailable.

## Open Questions

None.
