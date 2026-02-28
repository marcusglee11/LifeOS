---
title: GitHub Actions Secrets Setup
status: ACTIVE
owner: CEO
last_updated: 2026-02-28
---

# GitHub Actions Secrets Setup

Configuration guide for the LifeOS Build Loop GitHub Actions workflow.

## Required Secrets

| Secret | Purpose | Required |
|--------|---------|----------|
| `OPENROUTER_API_KEY` | LLM provider access for spine execution | Yes (for real runs) |
| `LIFEOS_PAT` | Fine-grained PAT for push + issue creation | Recommended |

The workflow degrades gracefully without secrets: missing `OPENROUTER_API_KEY` skips spine execution; missing `LIFEOS_PAT` falls back to `GITHUB_TOKEN`.

## Creating a Fine-Grained PAT

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Click **Generate new token**
3. Configure:
   - **Token name:** `lifeos-build-loop`
   - **Expiration:** 90 days (set a calendar reminder to rotate)
   - **Repository access:** Only select repositories → select `LifeOS`
   - **Permissions:**
     - Contents: Read and write
     - Issues: Read and write
     - Metadata: Read-only (auto-granted)
4. Click **Generate token** and copy the value

## Adding Repository Secrets

1. Go to **LifeOS repo → Settings → Secrets and variables → Actions**
2. Click **New repository secret** for each:
   - Name: `LIFEOS_PAT`, Value: the PAT from above
   - Name: `OPENROUTER_API_KEY`, Value: your OpenRouter API key

## Validation

After adding secrets, run a manual dry-run to validate the setup:

```bash
gh workflow run build_loop_nightly.yml -f dry_run=true
gh run list --workflow=build_loop_nightly.yml --limit=1
```

The dry-run resolves tasks and validates the environment without executing the spine.

## PAT vs GITHUB_TOKEN

| Capability | `GITHUB_TOKEN` | `LIFEOS_PAT` |
|-----------|---------------|--------------|
| Push commits | Yes | Yes |
| Create issues | Yes | Yes |
| Trigger downstream CI on push | No | Yes |
| Cross-repo access | No | If configured |

The `LIFEOS_PAT` is recommended because commits pushed with `GITHUB_TOKEN` do not trigger subsequent workflow runs (GitHub prevents recursive triggers). The build loop's manifest commits should trigger CI to validate the updated manifest.

## Rotation

- **PAT:** Rotate every 90 days. GitHub sends expiration reminders.
- **OPENROUTER_API_KEY:** Rotate per your provider's policy.
- After rotation, update the repository secret and run a dry-run to confirm.
