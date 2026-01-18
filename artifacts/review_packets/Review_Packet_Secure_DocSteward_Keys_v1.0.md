# Review Packet — Secure DocSteward Keys v1.0

## Summary
This mission successfully implemented a hardened, isolated usage tracking mechanism for the OpenCode Doc Steward. By leveraging an ephemeral OpenCode server with an isolated configuration directory and explicit environment variable overrides, we ensured that the Doc Steward exclusively uses the designated `STEWARD_OPENROUTER_KEY` and the `x-ai/grok-4.1-fast` model, preventing unintended fallback or credential leakage.

## Issue Catalogue
| ID | Issue | Severity | Status |
|----|-------|----------|--------|
| I-01 | OpenCode fallback to OpenAI despite OpenRouter config | High | Resolved |
| I-02 | API Key leakage in logs/git | High | Resolved |
| I-03 | Model routing ambiguity in OpenCode | Medium | Resolved |
| I-04 | Isolated config directory path resolution on Windows | Medium | Resolved |

## Proposed Resolutions
- **Isolation**: Implement an ephemeral server per mission with its own temp config/data directories.
- **Credential Forced**: Directly set `OPENROUTER_API_KEY` and invalidate `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`.
- **Model Force**: Explicitly specify the model in the ephemeral server's `opencode.json`.

## Implementation Guidance
The `scripts/opencode_ci_runner.py` is the canonical entry point. It now handles the creation and cleanup of the temporary environment. Any future modifications to the steward's provider settings should be applied here.

## Acceptance Criteria
- [x] Doc Steward uses `x-ai/grok-4.1-fast` exclusively.
- [x] Usage is reported to OpenRouter under the unique `STEWARD_OPENROUTER_KEY`.
- [x] No OpenAI/Anthropic fallback occurs.
- [x] Temporary config/data directories are cleaned up after mission completion.
- [x] Security sweep confirms no keys committed to the repository.

## Non-Goals
- Modifying the global `~/.config/opencode/` settings (this mission focused on the Steward's isolation).
- Implementing a permanent project-level OpenRouter proxy.

## Appendix — Flattened Artefacts

### File: [scripts/opencode_ci_runner.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_ci_runner.py)
```python
# (Contents of scripts/opencode_ci_runner.py included in the actual commit)
```

### File: [opencode.json](file:///c:/Users/cabra/Projects/LifeOS/opencode.json)
```json
{
  "instructions": [
    "AGENTS.md",
    "docs/11_admin/LIFEOS_STATE.md"
  ],
  "model": "x-ai/grok-4.1-fast",
  "$schema": "https://opencode.ai/config.json"
}
```
