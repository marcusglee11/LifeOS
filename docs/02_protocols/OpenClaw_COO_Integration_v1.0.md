# OpenClaw COO Integration v1.0

**Status:** Active  
**Applies To:** COO invocation via OpenClaw gateway

---

## Overview

OpenClaw is the external AI gateway hosting the live COO agent. LifeOS invokes the COO
by sending structured JSON messages to the local OpenClaw HTTP gateway.

## Gateway

- **URL:** `127.0.0.1:18789`
- **Protocol:** HTTP/JSON via `openclaw` CLI
- **Agent slot:** `main` = live COO

## Invocation Pattern

```bash
openclaw agent --agent main --message '<json_str>' --json
```

Response: `result.payloads[0].text` contains COO output.

## CLI Wrappers

| Command | Purpose |
| ------- | ------- |
| `lifeos coo propose` | Reads backlog → emits `task_proposal.v1` YAML |
| `lifeos coo direct` | CEO objective → `escalation_packet.v1` → CEO queue |

## Known Constraints

- COO cannot access LifeOS schemas directly via gateway; the adapter
  (`runtime/orchestration/coo/invoke.py`) injects `output_schema` with each call.
- Gateway credentials stored at `~/.openclaw/.env` (token; refresh if expired).
- COO output normalizer handles known gpt model formatting quirks (unindented sub-keys).

## Current Version

OpenClaw version as last recorded in LIFEOS_STATE.md. Verify with `openclaw --version`.
