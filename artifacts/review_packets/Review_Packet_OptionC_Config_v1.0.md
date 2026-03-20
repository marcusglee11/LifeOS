# Review Packet: Option C Configuration v1.0

**Mission**: Enable "Option C" (OpenAI Plugin) for LifeOS Agents
**Date**: 2026-01-25
**Author**: Antigravity (Builder)
**Mode**: **Standard Stewardship**

## 1. Summary

Enabled and verified "Option C" configuration, allowing LifeOS agents to utilize the user's personal ChatGPT subscription (via `opencode` plugin) instead of API keys. Implemented a "Smart Model Selection" system for the Builder agent to switch between `gpt-5.1-codex-mini` (Fast) and `gpt-5.1-codex-max` (Deep) based on task complexity.

## 2. Changes

| File | Impact |
| :--- | :--- |
| `config/models.yaml` | **MODIFIED** | Configured `steward` (Mini) and `builder` (Dual: Mini/Max). |
| `runtime/agents/models.py` | **MODIFIED** | Added `reasoning_model` field to `AgentConfig` schema. |
| `scripts/opencode_ci_runner.py` | **MODIFIED** | Implemented Smart Selection logic & forced UTF-8 encoding. |
| `docs/01_governance/OptionC_OpenAI.md` | **MODIFIED** | Updated documentation with final architecture. |
| `docs/99_archive/dogfood_v5.md` | **CREATED** | Verification artifact (Steward). |
| `simple_test.txt` | **CREATED** | Verification artifact (Builder Mini). |

## 3. Key Decisions

- **Smart Selection**: To balance speed vs capability, the Builder agent defaults to `mini` (~8s) but switches to `max` (~60s) for "complex" tasks.
- **UTF-8 Enforcement**: Patched the CI runner to handle unicode characters from GPT-5 models, preventing crashes on Windows.
- **Max Availability**: Proven via isolation test (68s latency).

## 4. Verification (Dogfooding)

- **Steward Agent**: SUCCESS (created `docs/99_archive/dogfood_v5.md`).
- **Builder Agent (Mini)**: SUCCESS (created `simple_test.txt` in <10s).
- **Builder Agent (Max)**: SUCCESS (proven in isolation test, verified selection logic in E2E).

## 5. Protocol Checks

- [x] `docs/INDEX.md` updated
- [x] `LifeOS_Strategic_Corpus.md` regenerated
- [x] Flattened files available via Git history
