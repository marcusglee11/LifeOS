# Diagnostic Report: Zen API Connectivity (Updated)

**Date:** 2026-01-09
**Status:** ENDPOINT FORMAT MISMATCH

## Findings

### Working Test

```bash
curl -X POST "https://opencode.ai/zen/v1/chat/completions" \
  -H "Authorization: Bearer sk-6xIR..." \
  -d '{"model":"glm-4.7-free",...}'
```

**Result:** HTTP 200 ✅ — Response received!

### The Problem

| Component | Format Used |
|-----------|-------------|
| Zen Endpoint | **OpenAI** (`/chat/completions`) |
| `claude-code` CLI | **Anthropic** (`/v1/messages`) |

These formats are **incompatible**. The `claude-code` CLI cannot use an OpenAI-style endpoint directly.

## Options

### Option 1: Use Anthropic Directly

If you have Anthropic API credits, use the standard key and endpoint.

### Option 2: Use an OpenAI-Compatible Agent

Replace `claude-code-mcp` with an OpenAI-compatible tool (e.g., `aider`, `continue.dev`, OpenCode).

### Option 3: Proxy/Adapter

Use a tool like `litellm` to translate Anthropic requests to OpenAI format.

## Recommendation

For this spike, **Option 1** (direct Anthropic key) is the fastest path to validating role capabilities. The Zen endpoint can be integrated later with an OpenAI-compatible agent layer.
