# Plan: COO Telegram Reliability And Operatorization

## Summary
Stabilize the current DM-only, polling-only COO Telegram surface so it is dependable for daily use before expanding scope. The goal is to make the bot feel operationally real: visible liveness, survivable transient failures, and a first-class status surface, while keeping the existing approval flow and action set unchanged.

## Key Changes
- Add `lifeos coo telegram status` with optional `--json`.
  - This becomes the operator-facing health check for the bot process.
  - It should report configured/running/error state, mode, last activity timestamps, and most recent failure reason if present.
- Persist Telegram runtime state to a small local status artifact under `artifacts/status/`.
  - Track lifecycle fields like `state` (`starting`, `running`, `stopped`, `error`), `mode`, `last_error`, `started_at`, `updated_at`.
  - Track operator-facing activity fields like `last_message_at`, `last_reply_at`, `last_callback_at`, and `last_latency_ms`.
- Make `coo telegram run` resilient to transient COO invocation failures.
  - Add bounded retry/backoff inside `invoke_coo_reasoning()` for `chat` and `direct` only.
  - Retry only transient invocation failures such as timeout/network/gateway unavailability; do not retry parse/schema failures or policy rejections.
  - Use a fixed fail-closed policy: max 2 retries after the initial attempt, with backoff `1s` then `3s`.
- Keep the Telegram UX changes already landed and build on them.
  - Preserve typing pulses during long requests.
  - Keep chat-mode reasoning at the lighter tier.
  - If retries are happening, do not spam the user; keep one typing pulse and reply only once with the final result or final failure.
- Add operator docs for always-on local use.
  - Document a user-service launch path for the bot using the existing env-file pattern.
  - Document restart/check commands using `coo telegram status` rather than raw logs.

## Public Interfaces
- New CLI surface:
  - `lifeos coo telegram status`
  - `lifeos coo telegram status --json`
- New status artifact:
  - `artifacts/status/coo_telegram_runtime.json`
  - Canonical fields: `state`, `mode`, `configured`, `started_at`, `updated_at`, `last_error`, `last_message_at`, `last_reply_at`, `last_callback_at`, `last_latency_ms`
- No scope change to Telegram permissions or supported actions.
  - Still private-chat oriented.
  - Still polling-only.
  - Still allowlisted workspace actions only.

## Test Plan
- Add CLI tests for `coo telegram status` in both text and JSON modes.
- Add adapter tests covering status-state transitions: startup, steady running, handled exception, clean shutdown.
- Add invocation tests proving:
  - chat/direct transient failures retry with `1s` then `3s` backoff
  - success after retry returns normally
  - final failure after retry raises `InvocationError`
  - parse/schema failures are not retried
  - propose mode keeps current single-shot behavior
- Add Telegram handler tests proving status activity fields update on message, reply, and callback paths.
- Run `pytest runtime/tests -q` before and after implementation.

## Assumptions And Defaults
- Scope stays local/operator-focused; no webhook mode, no group-chat expansion, and no Slack work in this step.
- Reliability work takes priority over adding delete/archive/new actions.
- The status artifact is local runtime state and should not be treated as a tracked repo deliverable.
- Always-on means documented and supportable via user-service/runbook, not a mandatory repo-managed daemon framework.
