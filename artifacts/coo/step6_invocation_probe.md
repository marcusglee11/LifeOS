# Step 6 OpenClaw Invocation Probe

**Date:** 2026-03-08
**Probed by:** Claude Code (sprint team)

---

## Invocation Mechanism

**Method:** Subprocess CLI — `openclaw agent --agent main --message <text> --json`

**Gateway status:** RUNNING at `http://127.0.0.1:18789` (HTTP 200 on health check)

**Agent:** `main` — Identity: ♜ COO (nickname: Cabra)
- Model: `openai-codex/gpt-5.3-codex`
- Workspace: `~/.openclaw/workspace`

---

## Parameters

| Parameter | Value |
|-----------|-------|
| CLI binary | `openclaw` |
| Command | `agent` |
| `--agent` | `main` |
| `--message` | Context JSON serialized as string |
| `--json` | Always set (machine-readable output) |
| `--timeout` | Configurable (default 120s per config; override to 120s for COO propose) |

**Context injection method:** Message body — the entire context dict is serialized to JSON and
passed as the `--message` argument. The COO agent's system prompt (in `~/.openclaw/agents/main/`)
governs how it interprets the message.

**System prompt reference:** The `main` agent's configured identity/system prompt at
`~/.openclaw/agents/main/agent/` is used automatically — no path flag needed.

---

## Output Shape

The `--json` flag produces a JSON envelope:

```json
{
  "runId": "<uuid>",
  "status": "ok",
  "summary": "completed",
  "result": {
    "payloads": [
      {
        "text": "<agent response text>",
        "mediaUrl": null
      }
    ],
    "meta": {
      "durationMs": <int>,
      "agentMeta": {
        "sessionId": "<uuid>",
        "provider": "openai-codex",
        "model": "gpt-5.3-codex",
        "usage": { ... }
      }
    }
  }
}
```

**Response text location:** `result.payloads[0].text`

**Probe verification:**
- Sent: `"Reply: PROBE_OK"`
- Received: `status: ok`, `text: PROBE_OK`
- Round-trip time: ~5 seconds

---

## Error Codes and Failure Modes

| Condition | CLI exit code | `status` field |
|-----------|---------------|----------------|
| Success | 0 | `"ok"` |
| Gateway not running | non-zero | — |
| Timeout | non-zero (SIGTERM) | — |
| Agent error | non-zero | `"error"` (inferred) |

**InvocationError** raised in adapter on any non-zero subprocess exit or timeout.

---

## Dry-Run / Probe Mode

No native dry-run mode. Probe was performed with a trivial message (`"Reply: PROBE_OK"`) to
confirm gateway connectivity and output shape without triggering real COO reasoning.

---

## `cmd_coo_direct()` Wiring Assessment

**FEASIBLE** — no substrate changes beyond `commands.py` + new `invoke.py` adapter required.

The same `openclaw agent --agent main --message <context_json> --json` invocation works for
both `propose` and `direct` modes. The adapter passes `mode` in the context dict so the COO
can select the appropriate action class (`task_proposal.v1` vs `escalation_packet.v1`).

The only additional work is:
1. Building a direct-mode context dict in `cmd_coo_direct()`
2. Parsing the escalation packet from raw output
3. Writing to CEO queue (code already exists in current stub)

**DIRECT_ESCALATION_PARITY: NOT BLOCKED**
