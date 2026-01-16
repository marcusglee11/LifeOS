# Review Packet: Config Consolidation v1.0

**Mission Name**: Config Consolidation
**Date**: 2026-01-09
**Author**: Antigravity Agent
**Status**: COMPLETED

## Summary

Established `runtime/agents/models.py` as the single source of truth for model/provider defaults throughout the codebase. This eliminates the scattered hardcoded strings that caused the Grok/OpenRouter vs Zen/Minimax mismatch.

## Key Changes

### Phase 1: Canonical Constants Added

Added to `runtime/agents/models.py`:

```python
DEFAULT_MODEL = "minimax-m2.1-free"
DEFAULT_PROVIDER = "zen_anthropic"
DEFAULT_ENDPOINT = "https://opencode.ai/zen/v1/messages"
DEFAULT_API_KEY_ENV = "ZEN_STEWARD_KEY"
API_KEY_FALLBACK_CHAIN = ["ZEN_STEWARD_KEY", "ZEN_API_KEY", ...]
```

Plus helper functions:

- `validate_config()` - Fail-fast check for API key availability
- `get_api_key()` - Get first available key from fallback chain

### Phase 2: Scripts Updated

| File | Change |
|------|--------|
| `scripts/opencode_ci_runner.py` | Import `DEFAULT_MODEL`, use in argparse |
| `runtime/agents/opencode_client.py` | Import `DEFAULT_MODEL`, `API_KEY_FALLBACK_CHAIN` |
| `scripts/verify_opencode_connectivity.py` | Use `validate_config()` and `DEFAULT_MODEL` |
| `scripts/opencode_performance_tests.py` | Import `DEFAULT_MODEL` |

### Phase 3: Tests Updated

| File | Change |
|------|--------|
| `runtime/tests/test_opencode_client.py` | Import and assert against `DEFAULT_MODEL` |
| `tests/test_agent_api.py` | Import `DEFAULT_MODEL` |
| `tests/test_agent_logging.py` | Import `DEFAULT_MODEL` |
| `tests/test_agent_fixtures.py` | Import `DEFAULT_MODEL` |

## Acceptance Criteria

| Criteria | Status |
|----------|--------|
| No hardcoded `grok-4.1-fast` in Python files | PASS |
| All affected tests pass | PASS (65/65) |
| Connectivity verification uses correct model | PASS (`ZEN:MiniMax-M2.1`) |

## How to Change Models Going Forward

1. Edit `config/models.yaml` (canonical config file)
2. Update `DEFAULT_MODEL` in `runtime/agents/models.py`
3. Run `pytest` to verify no breakage

## Files Modified

- `runtime/agents/models.py`
- `scripts/opencode_ci_runner.py`
- `runtime/agents/opencode_client.py`
- `scripts/verify_opencode_connectivity.py`
- `scripts/opencode_performance_tests.py`
- `runtime/tests/test_opencode_client.py`
- `tests/test_agent_api.py`
- `tests/test_agent_logging.py`
- `tests/test_agent_fixtures.py`
