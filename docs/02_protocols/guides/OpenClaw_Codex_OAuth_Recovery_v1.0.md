# OpenClaw Codex OAuth Recovery v1.0

## Purpose

Provide a deterministic operator workflow for recovering `openai-codex` routing when:

- the gateway prefers expired legacy profiles ahead of a valid email-scoped profile;
- `refresh_token_reused` appears in gateway logs; or
- a fresh `openclaw configure` / `openclaw models auth login` does not recover live routing.

This guide is a local LifeOS mitigation.
It does not fix the upstream OpenClaw runtime race where multiple agents can
refresh the same Codex OAuth token concurrently.

## Symptoms

- Gateway log contains `refresh_token_reused`
- `openclaw models status --check` fails or degrades to fallback providers
- `openclaw models auth order get --provider openai-codex --json` lists expired profiles first
- `python3 runtime/tools/openclaw_auth_health.py --json` reports `codex_auth_order_stale` or `refresh_token_reused`

## Root Cause Summary

OpenClaw separates Codex auth state across three places:

- `~/.openclaw/agents/<agent>/agent/auth-state.json`
  This controls provider order.
- `~/.openclaw/agents/<agent>/agent/auth-profiles.json`
  This stores per-agent OAuth profiles.
- `~/.codex/auth.json`
  This stores the external Codex CLI managed token set.

When `auth-state.json` still prefers `openai-codex:default` or
`openai-codex:codex-cli`, the gateway can keep routing into expired profiles
even when a valid email-scoped profile exists in `auth-profiles.json`.

## Detection

Dry-run the repair tool:

```bash
python3 runtime/tools/openclaw_codex_auth_repair.py --json
```

Expected stale-order signal:

- `repair_needed: true`
- `chosen_profile_id` is the valid email-scoped profile
- `proposed_order[0]` is the same profile

Check auth health:

```bash
python3 runtime/tools/openclaw_auth_health.py --json
```

Important reason codes:

- `codex_auth_order_stale`
- `refresh_token_reused`
- `expired_or_missing`

## Repair

Apply the local repair:

```bash
python3 runtime/tools/openclaw_codex_auth_repair.py --apply --json
```

The tool:

1. Reads `auth-state.json`, `auth-profiles.json`, and `~/.codex/auth.json`
2. Ranks valid `openai-codex` OAuth profiles by latest expiry
3. Prefers email-scoped profiles over `:default` and `:codex-cli` on expiry ties
4. Runs:
   `openclaw models auth order set --provider openai-codex ...`
5. Runs:
   `openclaw secrets reload --json`
6. Writes a rollback receipt under:
   `artifacts/evidence/openclaw/codex_auth_repair/<UTC_TS>/rollback_receipt.json`

## Verification

Check the repaired order:

```bash
openclaw models auth order get --provider openai-codex --json
```

Re-run health tooling:

```bash
python3 runtime/tools/openclaw_auth_health.py --json
bash runtime/tools/openclaw_verify_surface.sh
```

Expected result:

- the valid email-scoped profile is first in the `openai-codex` order
- `codex_auth_order_stale` no longer appears
- verify-surface output includes any remaining auth warning explicitly

## Rollback

1. Open the latest receipt in `artifacts/evidence/openclaw/codex_auth_repair/<UTC_TS>/rollback_receipt.json`
2. Restore the previous order with:

```bash
openclaw models auth order set --provider openai-codex <previous-order...>
openclaw secrets reload --json
```

## Limitations

- This guide does not serialize concurrent token refreshes across agents.
- If `openclaw secrets reload` does not refresh the running gateway snapshot, restart the gateway as an operational fallback.
- The repair tool does not delete any legacy profiles. It only changes provider order.
