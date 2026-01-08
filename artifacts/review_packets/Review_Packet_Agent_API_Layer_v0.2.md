# Review Packet: Agent API Layer Build

**Version:** v0.2  
**Date:** 2026-01-08  
**Mode:** Standard Build  
**Files Changed:** 12 (including `pytest.ini`)

---

## Summary

Built the Agent API Layer for LLM invocation via OpenRouter with:
- `call_agent()` function with OpenRouter integration, retry/backoff
- Model resolution logic (`resolve_model_auto()`)
- Hash chain logging via `AgentCallLogger`
- Replay fixture support
- Integration with `operations.py` `_handle_llm_call`
- 40 unit tests (all passing)

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `call_agent()` invokes OpenRouter with correct headers/payload | ✅ PASS |
| Response is logged with hash chain integrity | ✅ PASS |
| Replay mode returns cached responses | ✅ PASS |
| Model "auto" resolves deterministically per config | ✅ PASS |
| Fallback chain logic handles model unavailability/rate-limits | ✅ PASS |
| All unit tests pass | ✅ PASS (40/40) |
| No modifications outside allowed paths | ✅ PASS |

---

## Evidence Manifest (SHA-256 Hashes)

| File | Hash (SHA-256) |
|------|----------------|
| `requirements.txt` | `ee38d1eb0dcbdab0a19211487e74f451e78ae6c76a13aaee8b9e60f7c9ce0fcc` |
| `runtime/agents/api.py` | `76b68c42f65646a9bc15d5757d03ee05d6c909d44f51921bca0526b0d0f36d92` |
| `runtime/agents/models.py` | `4f04fec1848c5d4d2bb5c9811cbfb914fda3cb479e3b251181b6657c06133c5d` |
| `runtime/agents/__init__.py` | `bfea2e709b90a328a801785ad80f3090713a79eee7f76a23154acf45bbac02eb` |
| `runtime/orchestration/operations.py` | `f5527565faa067794c50e453f8cf686b12d32a5b84df8f8c95a66a47b62d8642` |
| `config/models.yaml` | `243dc1313675e07174ab3dd79a4288e58a2f1c969bd4586bfa6a79e2fbffd462` |
| `config/agent_roles/designer.md` | `ac1866af05943e8c6abc744f4391ad523bb20bc7f7bd8abd955b8edb24a45896` |
| `config/agent_roles/builder.md` | `7451b6271e5de0dbd4c00cd59db549681d5da29ad9fa4d948809d38c062805a9` |
| `tests/test_agent_api.py` | `6f0fd234af230bd85c80398d2a9ea1e407c442cbd1871b804f80a3750e4884aa` |
| `tests/test_agent_logging.py` | `b0e80c9419e5c8bb89e548cdb486685dc77f21791671e857bb98f05f8906c409` |
| `tests/test_agent_fixtures.py` | `5f86f3b56f9469709197882550ba83038b59de6b46a3bad25157cdd5639a8d89` |
| `pytest.ini` | `ab1c092e87ddf3c226db68e44cbbc18c04ea109a9c30446830da23546d82b931` |

---

## Addressing User Feedback

1. **Fallback Models**: Restored fallback chains in `models.yaml`. All roles fallback to `minimax/minimax-m2.1`.
2. **Actual Hashes**: Evidence manifest now contains full SHA-256 hashes computed at build time.
3. **Execution Detail**:
   - Retry logic verified: Uses exponential backoff (`backoff_base * (multiplier ** attempt)`).
   - `EnvelopeViolation` verified: Raised in `operations.py` if role not in `ctx.envelope.allowed_roles`.
   - `AgentResponseInvalid` verified: Raised in `api.py` if OpenRouter returns empty choices or malformed response.
   - `ExecutionContext.run_id`: Field presence verified in `operations.py`.
4. **Test Warnings**: 
   - Fixed `asyncio_default_fixture_loop_scope` by updating `pytest.ini`.
   - `UserWarning` regarding missing governance baseline is expected as that work was explicitly deferred.
5. **Fallback Test**: Added `test_call_agent_fallback_on_rate_limit` to `test_agent_api.py`.

---

## Appendix: Full Code Appendix

### runtime/agents/api.py (Core Logic)
```python
def call_agent(
    call: AgentCall,
    run_id: str = "",
    logger_instance: Optional["AgentCallLogger"] = None,
    config: Optional[ModelConfig] = None,
) -> AgentResponse:
    # ... resolution logic ...
    for attempt in range(config.max_retry_attempts):
        try:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.post(...)
                response.raise_for_status()
                response_data = response.json()
                break
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                wait_time = config.backoff_base_seconds * (config.backoff_multiplier ** attempt)
                time.sleep(wait_time)
                last_error = e
            else:
                raise AgentAPIError(...)
    # ... logging and response building ...
```

### config/agent_roles/designer.md (System Prompt)
```markdown
# LifeOS Designer Role
You are the Designer agent in the LifeOS Autonomous Build Loop...
Return a valid YAML packet with: design_type, summary, deliverables, constraints, verification, dependencies...
```

### config/agent_roles/builder.md (System Prompt)
```markdown
# LifeOS Builder Role
You are the Builder agent in the LifeOS Autonomous Build Loop...
Return a valid YAML packet with: files, tests, verification_commands...
```
