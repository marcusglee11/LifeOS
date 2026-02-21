# OpenCode CLI Config — Build Summary
**Branch:** `build/opencode-cli-config-20260219`
**Date:** 2026-02-20
**Goal:** Configure OpenCode to be the best possible code constructor for LifeOS; establish whether the autonomous build loop is production-ready.

---

## What We Tested

| Stage | What | Result |
|-------|------|--------|
| Stage 1 | Config loading, model resolution, fallback chains | All unit tests pass |
| Stage 1.5 | Live comparison: glm-5-free vs kimi-k2.5-free | glm-5 better for YAML output; kimi better for agentic tasks |
| Stage 2 | Fallback packet extraction + traceback logging | 6 unit tests pass |
| Stage 3 (pre-fix) | Full spine with free models | BLOCKED (527s) — reviewer returned prose, not YAML |
| Stage 3 (post-fix) | Full spine with paid models (claude-sonnet-4-5) | **PASS (61.1s)** — autonomous commit `f7daab46` |

---

## Infrastructure Bugs Found and Fixed

All bugs meant that `call_agent()` could never produce a commit — the loop was architecturally broken before this sprint.

### Bug 1: Builder could not write files to disk
**Root cause:** `call_agent()` is a chat completion API. The LLM generates text but cannot write files. The build mission called `call_agent()` and then ran `git diff --name-only` — which always returned empty, so no artifacts were detected, and the review defaulted to `needs_revision`.

**Fix:** Added `_apply_build_packet()` to `build.py`. After `call_agent()` returns, parse the `files[]` array from the LLM packet and write each file to disk. Changed artifact detection from `git diff --name-only` (misses new files) to `git status --porcelain` (detects both modified and new files).

### Bug 2: Steward interface mismatch
**Root cause:** `steward._route_to_opencode()` passed `--task-file <path>` to `opencode_ci_runner.py`, but the runner only accepts `--task <json_string>`. The task_data schema was also wrong.

**Fix:** Changed to `--task <json_string>` and corrected task_data to `{files, action, instruction}`.

### Bug 3: Builder and designer hallucinated wrong file structure
**Root cause:** Builder and designer LLMs received only the task description string, not the actual file content. They hallucinated wrong function signatures (e.g., `dict/str` instead of `bytes/bytes`), producing diffs that failed to apply and designs that the reviewer rejected.

**Fix:**
- `build.py`: Read deliverable files from disk and inject as `context_refs` in the build prompt, plus instruct builder to return full file content (not diffs) to avoid hunk-count mismatches.
- `design.py`: Auto-extract file paths mentioned in the task spec string, read their content, and inject as `context_refs` so the designer sees actual function signatures.

### Bug 4: Wrong OpenRouter provider routing
**Root cause:** `LIFEOS_MODEL_OVERRIDE=anthropic/claude-sonnet-4-5` used the Zen endpoint, which doesn't support Anthropic model IDs, silently falling back to free models.

**Fix:** Use `openrouter/anthropic/claude-sonnet-4-5` (with the `openrouter/` prefix). `OpenCodeClient` detects this prefix and routes to OpenRouter direct REST, stripping the prefix for the actual API call.

---

## Model Comparison

| Model | Outcome | Elapsed | Failure Reason |
|-------|---------|---------|----------------|
| free (glm-5-free) | BLOCKED | 29s | Design failure (task already done) |
| free (glm-5-free + minimax-m2.5-free) | BLOCKED | 527s | Reviewer returned prose, not YAML |
| paid via Zen (anthropic/claude-sonnet-4-5) | BLOCKED | 146s | Zen doesn't support anthropic/* model IDs; fell back to free |
| paid via OR (openrouter/anthropic/claude-sonnet-4-5) | BLOCKED | 60s | Builder diff hunk-count mismatch |
| paid via OR (openrouter/anthropic/claude-sonnet-4-5) | BLOCKED | 55s | Designer hallucinated wrong signatures → reviewer rejected |
| paid via OR (openrouter/anthropic/claude-sonnet-4-5) | **PASS** | **61s** | ✓ Autonomous commit produced |

**Finding:** Free models cannot complete the loop reliably. The reviewer role requires structured YAML output; free models return prose. Paid models (claude-sonnet-4-5) complete the loop in ~61s with a real commit.

---

## Claude Code vs OpenCode: Side-by-Side

| Dimension | Claude Code (direct) | OpenCode (6-phase loop) |
|-----------|---------------------|------------------------|
| Task | Add docstrings to `sign_payload` / `verify_signature` | Same task |
| Wall clock | ~30s | 61.1s |
| Output quality | Correct types, clear descriptions | Correct types, clear descriptions (with Example blocks) |
| Review step | None (human implicit) | Automatic Architect review |
| Git commit | Manual | Autonomous steward commit |
| Audit trail | None | Ledger entry, terminal packet, agent call logs |
| Retries needed | 0 | 0 (after infrastructure fixes) |
| Cost | ~$0.01 (Claude Opus 4.6) | ~$0.08 (6x claude-sonnet-4-5 calls via OpenRouter) |

**Conclusion:** OpenCode's loop is ~2x slower and ~8x more expensive per task than direct Claude Code for simple documentation tasks. The value proposition is not speed or cost — it's **governance**: every change is independently reviewed, evidence is captured, and the steward commits deterministically. For production autonomy (unattended runs, bulk tasks, regulatory contexts), OpenCode's overhead is justified.

---

## Recommendation: Production Config

For LifeOS production autonomy:

```yaml
# config/models.yaml (all agents)
primary: openrouter/anthropic/claude-sonnet-4-5
# or for cost reduction: openrouter/anthropic/claude-haiku-4-5
```

**Required env vars:**
```
OPENROUTER_DESIGNER_KEY=sk-or-v1-...
OPENROUTER_BUILDER_KEY=sk-or-v1-...
OPENROUTER_REVIEWER_KEY=sk-or-v1-...
OPENROUTER_BUILD_CYCLE_KEY=sk-or-v1-...
```

**Do not use:** Free models (glm-5-free, kimi-k2.5-free, minimax-m2.5-free) for the reviewer role. They cannot produce structured YAML verdicts reliably.

---

## Infrastructure State After This Sprint

All 1656 tests pass. The following infrastructure changes were committed:

| Commit | Change |
|--------|--------|
| `1be0876` | Build mission applies LLM output to disk + steward interface fix |
| `122dcda` | Stage 3 tests + git status fix for untracked file detection |
| `2638962` | Live task to undocumented function + gitignore comparison log |
| `68b0ce6` | LIFEOS_MODEL_OVERRIDE env var + fix paid test repo dirtying |
| `6badf29` | Use openrouter/ prefix for paid model routing |
| `a6d84f4` | Inject actual file content into builder prompt |
| `ce05f7b` | Instruct builder to return full content + whitespace-lenient diff |
| `1da6422` | Restore ledger+sign.py before live runs |
| `b68e290` | Auto-inject actual file content into designer prompt |
| `f7daab4` | Steward commit: docstrings added autonomously ← **proof of loop** |

---

## Evidence

- Terminal packets: `artifacts/terminal/TP_run_*.yaml`
- Agent call logs: `logs/agent_calls/*.json`
- Comparison results: `artifacts/comparison_results.jsonl`
- Autonomous commit: `f7daab46d283d70d11c991dd7080c08b82974e25`
