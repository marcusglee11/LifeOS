# EOL Policy v1.0

**Version**: 1.0
**Status**: Canonical
**Enforcement**: `.gitattributes` + `core.autocrlf=false` + `coo_land_policy.py clean-check`

---

## Canonical Policy

All text files in LifeOS repositories use **LF** line endings.  This is
enforced at three layers:

### Layer 1: `.gitattributes` (In-Repo, Authoritative)

```
* text=auto eol=lf
```

This ensures Git normalizes line endings to LF in the index (repository)
regardless of the contributor's OS.

### Layer 2: Git Config (Per-Clone)

```
core.autocrlf = false
```

This MUST be set at the repo-local level to prevent the system/global
`core.autocrlf=true` (Windows default) from converting LF→CRLF on checkout.

**Enforcement**: `coo_land_policy.py clean-check` verifies this and blocks
if non-compliant.

**Auto-fix**:

```bash
python -m runtime.tools.coo_land_policy clean-check --repo . --auto-fix
```

### Layer 3: Pre-Commit Hook

The pre-commit hook (`.git/hooks/pre-commit`, sourced from `scripts/hooks/`)
blocks commits with untracked files. EOL violations surface as "modified"
files in `git status` and are caught by the clean-check gate.

## Root Cause of Historical Drift

Windows Git for Windows ships with `core.autocrlf=true` in the system
gitconfig (`C:/Program Files/Git/etc/gitconfig`).  This caused:

1. `.gitattributes eol=lf` → Git stores LF in the index
2. `core.autocrlf=true` → Git checks out files with CRLF
3. Working tree CRLF ≠ index LF → 270+ files appear "modified"
4. Zero content changes, but `git status --porcelain` is non-empty

**Fix applied**: `git config --local core.autocrlf false` + `git add --renormalize .`

## Recommended Git Config for Contributors/Agents

```bash
# After cloning, run once:
git config --local core.autocrlf false

# Verify:
python -m runtime.tools.coo_land_policy clean-check --repo .
```

## Gate Enforcement Points

| Gate | Tool | When |
|------|------|------|
| **Clean check** | `coo_land_policy.py clean-check` | Before `coo land`, `coo run-job`, closure |
| **Config compliance** | `coo_land_policy.py clean-check` | Checks `core.autocrlf` effective value |
| **EOL churn detection** | `coo_land_policy.py clean-check` | Classifies dirty state as EOL_CHURN vs CONTENT_DIRTY |
| **Acceptance closure** | `coo_acceptance_policy.py validate` | Requires CLEAN_PROOF_PRE/POST in acceptance notes |

## Receipts and Blocked Reports

- **Clean proofs**: Recorded in acceptance notes (`CLEAN_PROOF_PRE`, `CLEAN_PROOF_POST`)
- **Blocked reports**: Written to EVID dir (gitignored), never to tracked repo paths
- **Format**: `REPORT_BLOCKED__<slug>__<timestamp>.md`
