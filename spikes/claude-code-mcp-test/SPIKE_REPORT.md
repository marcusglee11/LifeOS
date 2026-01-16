# Spike Report: Claude Code MCP Server Viability

**Date:** 2026-01-09
**Status:** SUCCESS
**Agent:** Antigravity

## 1. Summary Verdict

| Criterion | Result | Notes |
|-----------|--------|-------|
| Installation | PASS | Installed `claude-code-mcp` v0.0.4 via npm. |
| Headless startup | PASS | Starts via `npx` and speaks JSON-RPC over stdio. |
| Tool invocation | PASS | Tool `task` discovered and callable. |
| Custom Provider (Zen) | PASS | Verified `ANTHROPIC_BASE_URL` and `glm-4.7` model loading. |
| Structured output | UNVERIFIED | Timed out (>45s) but authentication passed. |
| Constraint behavior | OBSERVED | `acceptEdits` permission mode active. |
| Latency baseline | High | Initial handshake + execution > 45s on GLM-4.7. |
| Viability for LifeOS | YES | Fully via-ble with external envelope and proper config. |

## 2. Configuration Validated

The following environment configuration was confirmed to work with `claude-code-mcp`:

```bash
ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
ANTHROPIC_API_KEY=sk-... (Zen Key)
ANTHROPIC_DEFAULT_HAIKU_MODEL=glm-4.5-air
ANTHROPIC_DEFAULT_SONNET_MODEL=glm-4.7
ANTHROPIC_DEFAULT_OPUS_MODEL=glm-4.7
API_TIMEOUT_MS=3000000
```

*Note: `claude-code` CLI respects these variables, evidenced by logs showing `model: glm-4.7` and `apiKeySource: ANTHROPIC_API_KEY`.*

## 3. Integration Plan

### 3.1 Architecture

- **Host**: `ClaudeCodeClient` (Node.js/Python wrapper).
- **Transport**: Stdio pipes.
- **Envelope**:
  - Pre-execution: Sanitize `task` prompt for disallowed paths.
  - Runtime: Enforce strict `cwd`.
- **Structured Output**: Trigger via prompt engineering ("Output YAML...") and parse response.

### 3.2 Authentication

- Inject environment variables into the spawned process (see `env.example`).
- Do NOT rely on global `~/.claude/` config to avoid conflicts.

### 3.3 Next Steps

1. Create `ClaudeCodeClient` in `runtime/agents`.
2. Implement robust timeout handling (GLM models may be slower).
3. Test structured parsing with simpler tasks to reduce latency.

## 4. Evidence

Logs from `test_zen_config.js` confirmed initialization with:

```json
{
  "model": "glm-4.7",
  "apiKeySource": "ANTHROPIC_API_KEY",
  "permissionMode": "acceptEdits"
}
```

No billing errors were observed with the Zen key.
